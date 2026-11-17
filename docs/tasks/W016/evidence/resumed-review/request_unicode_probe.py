"""Public request malformed Unicode boundary; preserve each actual outcome."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--require-located', action='store_true')
a = p.parse_args()
root = a.root.resolve()
sys.path.insert(0, str(root))
from layauto_v2.analysis import AnalysisRequest, analyze_cell

rows = []
for path in ('/tmp/\ud800.json', '/tmp/\udcff.json', '/tmp/合法-不存在-w016.json'):
    try:
        result = analyze_cell(AnalysisRequest(Path(path)))
    except Exception as exc:
        rows.append({'path': path, 'exception': type(exc).__name__, 'message': str(exc)})
    else:
        rows.append({'path': path, 'status': result.request_status,
                     'findings': [{'code': f.code, 'uri': f.source.uri, 'field': f.source.field} for f in result.findings]})
report = {'cases': rows, 'source_sha256': hashlib.sha256((root/'layauto_v2/analysis.py').read_bytes()).hexdigest()}
print(json.dumps(report, indent=2))
if a.require_located:
    assert all(row.get('status') == 'rejected' and row['findings'] for row in rows)
    assert all(row['findings'][0]['code'] == 'InvalidAnalysisRequest' for row in rows[:2])
