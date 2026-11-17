"""Public invalid requests must return located results, not internal exceptions."""
from pathlib import Path
import argparse,hashlib,json,sys
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--require-located',action='store_true');a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root))
from layauto_v2.analysis import AnalysisRequest,analyze_cell
rows=[]
for path in (Path('/'),Path('/tmp'),Path('relative.json'),Path('/tmp/w016-review-no-manifest.json')):
 try:r=analyze_cell(AnalysisRequest(path))
 except Exception as exc:rows.append({'path':str(path),'exception':type(exc).__name__,'message':str(exc)})
 else:
  assert r.request_status=='rejected'
  rows.append({'path':str(path),'status':r.request_status,'codes':[f.code for f in r.findings]})
print(json.dumps({'results':rows,'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('layauto_v2/analysis.py','layauto_v2/importers/analysis_reader.py')}},indent=2))
if a.require_located:assert not any('exception' in row for row in rows)
