"""Internal-only authentication probe. This is not a public continuation API."""
from pathlib import Path
from collections import Counter
import json
import sys
import time
from layauto_v2.importers.analysis_reader import acquire_analysis
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt

counts=Counter()
def profile(frame,event,arg):
    if event=='call' and frame.f_code.co_name in ('parse_gds','parse_cdl','parse_query'):
        counts[frame.f_code.co_name]+=1
sys.setprofile(profile)
evidence=acquire_analysis(Path('/tmp/w016-resources/no_body/analysis.json'))
def forbidden(*a,**kw):raise AssertionError('receipt consumption must use captured bytes only')
Path.read_bytes=forbidden
Path.resolve=forbidden
rows=[]
for i in range(2):
    start=time.monotonic();receipt=LocalAnalysisReceipt(evidence)
    rows.append({'consumption':i+1,'seconds_profiled':time.monotonic()-start,'ref':receipt.ref,'parse_counts_cumulative':dict(counts)})
sys.setprofile(None)
assert counts=={'parse_gds':3,'parse_cdl':3,'parse_query':3},counts
assert rows[0]['ref']==rows[1]['ref']
print(json.dumps({'scope':'internal reauthentication probe; no public receipt reuse boundary','captures':len(evidence.captures),'rows':rows},indent=2))
