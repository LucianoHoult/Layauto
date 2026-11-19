"""Measure one prepared PM-01 input per process, with separate count/timing runs."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import resource
import sys
import time

from layauto_v2.analysis import AnalysisRequest, analyze_cell

root = Path(sys.argv[1])
counted = sys.argv[2] == 'count'
counts = Counter()
functions = {'parse_gds', 'parse_cdl', 'parse_query', 'build_source_operands',
             'source_admission_problem', 'build_layout', 'build_effective_draft',
             'build_local_connectivity_draft', 'build_channel_identity_draft',
             'build_annotation_operands', 'terminal_operands'}


def profile(frame, event, arg):
    code = frame.f_code
    if event == 'call' and '/layauto_v2/' in code.co_filename:
        owner = code.co_filename.split('/layauto_v2/')[-1]
        if code.co_name in functions or code.co_name == '__post_init__':
            counts[f'{owner}:{code.co_name}'] += 1


request = AnalysisRequest(root / 'analysis.json')
if counted:
    sys.setprofile(profile)
start = time.perf_counter()
result = analyze_cell(request)
seconds = time.perf_counter() - start
sys.setprofile(None)
assert result.request_status == 'rejected' and len(result.findings) == 2
captures = {s.uri: {'sha256': s.sha256, 'bytes': len(s.data)} for s in result.captures}
assert len(captures) == len(result.captures)
report = result.report_json.encode('utf-8')
print(json.dumps({'case': 'pin + unsupported comparator', 'counted': counted,
                  'python': sys.version, 'elapsed_seconds': seconds,
                  'hwm_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  'captures': captures, 'capture_bytes': sum(x['bytes'] for x in captures.values()),
                  'report_bytes': len(report), 'report_sha256': hashlib.sha256(report).hexdigest(),
                  'counts': counts, 'findings': [f.code for f in result.findings]},
                 indent=2, sort_keys=True))
