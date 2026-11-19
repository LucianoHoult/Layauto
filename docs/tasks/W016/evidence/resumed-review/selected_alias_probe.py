"""Actual selected-document URI error and valid-alias regression probe."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import sys
import tempfile

parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
root=args.root.resolve();sys.path.insert(0,str(root))
from layauto_v2.analysis import AnalysisRequest,analyze_cell
materialize=runpy.run_path(str(root/'tests/unit/test_analysis_foundation.py'))['materialize']

def save(path,value):path.write_text(json.dumps(value,sort_keys=True,separators=(',',':')))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rebind(directory):
 path=directory/'local-header.json';header=json.loads(path.read_text())
 for entry in header['closure']['entries']:entry['sha256']=sha(directory/entry['uri'])
 header['closure']['sha256']=hashlib.sha256(json.dumps(header['closure']['entries'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
 save(path,header)
rows=[]
with tempfile.TemporaryDirectory(prefix='w016-review-selected-') as tmp:
 for kind in ('body','manual'):
  directory=Path(tmp)/kind;directory.mkdir();manifest=materialize(directory)
  config=json.loads(manifest.read_text());gds=config['inputs']['gds'];cdl=config['inputs']['source_cdl']
  (directory/'layout-alias.gds').symlink_to(gds)
  if kind=='body':
   config['external_body']={'kind':'synthetic_context','uri':'body.json'}
   doc=json.loads((root/'tests/fixtures/w003_m1/body/context.json').read_text());field='source_gds';selected='external_body'
   doc[field]={'uri':'unknown-layout.gds','sha256':sha(directory/gds)}
  else:
   config['manual_intent']={'kind':'declaration','uri':'manual.json'};field='source_layout';selected='manual_intent'
   doc={'schema_version':'layauto-manual-supply-declaration/1','author':'independent-review','created_at':'2026-11-17T00:00:00Z',
        'source_layout':{'uri':'unknown-layout.gds','sha256':sha(directory/gds)},
        'source_netlist':{'uri':cdl,'sha256':sha(directory/cdl)},'cell':'INV_M1_SYNTH','instance_hint':None,
        'assertions':[{'device':'MN0','role':'B','expected_supply_label':'DECLARED_ONLY'}]}
  save(manifest,config);rebind(directory);document=directory/(kind+'.json');save(document,doc)
  bad=analyze_cell(AnalysisRequest(manifest))
  assert bad.request_status=='rejected' and bad.local is not None
  issues=getattr(bad,selected).issues
  expected='BodySourceBindingMismatch' if kind=='body' else 'ManualSourceBindingMismatch'
  assert expected in {i.code for i in issues},issues
  old_report=bad.report_json
  doc[field]['uri']='invalid\x00layout.gds';save(document,doc)
  invalid=analyze_cell(AnalysisRequest(manifest))
  assert invalid.request_status=='rejected' and invalid.local is not None
  assert 'InvalidInputPath' in {i.code for i in getattr(invalid,selected).issues}
  doc[field]['uri']='layout-alias.gds';save(document,doc)
  good=analyze_cell(AnalysisRequest(manifest))
  assert good.request_status=='completed' and good.local is not None,good.findings
  assert getattr(good,selected).status==('evaluated' if kind=='body' else 'declared')
  assert good.local.receipt_ref==bad.local.receipt_ref
  assert bad.report_json==old_report and bad.request_status=='rejected'
  rows.append({'kind':kind,'bad_status':bad.request_status,'bad_codes':[i.code for i in issues],
               'good_status':good.request_status,'selection_status':getattr(good,selected).status,
               'local_receipt_unchanged':True,'old_result_unchanged':True,'invalid_binding_path_located':True})
report={'cases':rows,'source_sha256':{str(p.relative_to(root)):sha(p) for p in sorted((root/'layauto_v2').rglob('*.py'))}}
print(json.dumps(report,indent=2))
