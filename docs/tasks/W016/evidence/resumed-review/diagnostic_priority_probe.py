"""Independent combined failures; helpers author input bytes, never observations."""
from pathlib import Path
import argparse,hashlib,json,runpy,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests/support'))
from analysis_inputs import materialize,rebind,load,write
from layauto_v2.analysis import AnalysisRequest,analyze_cell
helpers=runpy.run_path(str(root/'tests/unit/test_analysis_api.py'))
append_rect,append_seed=helpers['append_rect'],helpers['append_seed']
rows=[]
with tempfile.TemporaryDirectory(prefix='w016-review-priority-') as tmp:
 for case in ('partial_fin_source_mismatch_future','annotation_conflict_terminal_mismatch'):
  d=Path(tmp)/case
  materialize(d,external={'kind':'geometry_window','uri':'must-not-read.bundle'} if case.startswith('partial') else None)
  cdl=d/'source.cdl';text=cdl.read_text()
  if case.startswith('partial'):
   append_rect(d,'FIN',(59,27,110,29))
   assert 'NFIN=7' in text;cdl.write_text(text.replace('NFIN=7','NFIN=8'))
  else:
   append_rect(d,'M1',(130,20,140,24));append_seed(d,'n_a',(130,20,136,24));append_seed(d,'n_y',(134,20,140,24))
   assert 'MN0 Y A VSS VSS' in text;cdl.write_text(text.replace('MN0 Y A VSS VSS','MN0 VSS A VSS VSS'))
  rebind(d);r=analyze_cell(AnalysisRequest(d/'analysis.json'))
  assert r.request_status=='rejected' and r.source_comparison=='mismatch',r.findings
  if case.startswith('partial'):
   assert r.local.facets.channel_fin.status=='error'
   assert r.local.facets.channel_fin.value is not None
   assert r.local.facets.annotation.status=='available'
   assert r.local.facets.terminals.status=='not_evaluated'
   assert r.external_body.status=='unsupported'
   partial=[f for f in r.findings if f.code=='PartialFinCrossing']
   assert partial and all(f.category=='unsupported' and f.severity=='error' for f in partial)
   assert any(f.code=='SourceParameterMismatch' for f in r.findings)
  else:
   assert r.local.facets.annotation.status=='error' and r.local.facets.terminals.status=='error'
   assert r.local.facets.terminals.value is not None
   assert any(f.code=='SourceTerminalMismatch' for f in r.findings)
   terminal=next(t for t in r.local.facets.terminals.value if t.device_id.name=='MN0' and t.expected.role=='D')
   assert terminal.comparison=='mismatch' and terminal.expected.net_id.name=='VSS'
   assert [n.name for n in terminal.observed_net_ids]==['Y']
  rows.append({'case':case,'status':r.request_status,'source_comparison':r.source_comparison,
               'findings':[{'category':f.category,'severity':f.severity,'code':f.code,'source_uri':f.source.uri,'source_field':f.source.field} for f in r.findings]})
print(json.dumps({'results':rows,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'layauto_v2').rglob('*.py'))}},indent=2))
