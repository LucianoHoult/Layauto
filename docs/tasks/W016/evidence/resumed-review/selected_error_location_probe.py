"""Discovery must preserve decoder's original issue source location."""
import argparse,hashlib,json,sys,tempfile
from dataclasses import asdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--require-equal',action='store_true');a=p.parse_args();root=a.root.resolve();sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tests/support'))
from analysis_inputs import materialize
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.config import load_document
from layauto_v2.importers.analysis_reader import acquire_analysis,acquire_selections
rows=[]
with tempfile.TemporaryDirectory(prefix='w016-review-location-') as tmp:
 for i,data in enumerate((b'{',b'{"schema_version":"x","schema_version":"y"}')):
  d=Path(tmp)/str(i);manifest=materialize(d,body=True);(d/'body/context.json').write_bytes(data)
  try:load_document(SourceFile('body/context.json',data))
  except InputError as exc:original=exc.issue
  else:raise AssertionError('Expected original decoder failure')
  evidence=acquire_analysis(manifest);assert not evidence.issues
  _,_,_,issues,_=acquire_selections(evidence);assert len(issues)==1
  rows.append({'original':asdict(original),'discovery':asdict(issues[0]),'same_issue':original==issues[0]})
print(json.dumps({'cases':rows,'source_sha256':hashlib.sha256((root/'layauto_v2/importers/analysis_reader.py').read_bytes()).hexdigest()},indent=2))
if a.require_equal:assert all(row['same_issue'] for row in rows)
