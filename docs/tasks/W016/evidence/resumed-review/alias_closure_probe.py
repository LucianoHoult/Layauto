"""Independent actual-file alias closure and role probes; no product input edits."""
from dataclasses import replace
import argparse
import hashlib
import json
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--require-closed',action='store_true')
args=parser.parse_args();root=args.root.resolve();sys.path.insert(0,str(root))
from layauto_v2.importers.analysis_reader import acquire_analysis
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt
from layauto_v2.domain.codec import FrozenMap
p=root/'docs/tasks/W015/evidence/candidate-input/analysis.json'
e=acquire_analysis(p);assert not e.issues
valid=LocalAnalysisReceipt(e)
results=[]
for kind in ('unused_alias','wrong_gds_role','missing_first_alias','relative_actual_path'):
 aliases=dict(e.aliases)
 if kind=='unused_alias': aliases['never-requested-role']=str(p)
 elif kind=='wrong_gds_role':
  gds=e.value['config']['inputs']['gds'];cdl=e.value['config']['inputs']['source_cdl']
  aliases[gds]=aliases[cdl]
 elif kind=='missing_first_alias': aliases.pop(e.captures[0].uri)
 else: aliases[e.captures[0].uri]='analysis.json'
 altered=replace(e,aliases=FrozenMap(aliases))
 try:
  candidate=LocalAnalysisReceipt(altered)
 except ValueError as exc:
  results.append({'case':kind,'rejected':True,'error':str(exc)})
 else:
  results.append({'case':kind,'rejected':False,'changed_receipt_ref':valid.ref!=candidate.ref})
report={'results':results,'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('layauto_v2/normalization/analysis_input.py','layauto_v2/importers/analysis_reader.py','layauto_v2/domain/analysis.py')},'input_manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
print(json.dumps(report,indent=2))
assert all(row['rejected'] for row in results if args.require_closed or row['case'] not in ('unused_alias','relative_actual_path'))
