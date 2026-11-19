"""Compare three completed reports using identical absolute input paths in both versions."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

from_repo = Path.cwd()
base, inputs = map(Path, sys.argv[1:])
emit = """
from pathlib import Path
import sys
package, inputs, out = map(Path, sys.argv[1:])
sys.path.insert(0, str(package))
import layauto_v2.analysis as api
assert Path(api.__file__).resolve() == package / 'layauto_v2' / 'analysis.py'
for case in ('no_body', 'body', 'mismatch'):
    result = api.analyze_cell(api.AnalysisRequest(inputs / case / 'analysis.json'))
    assert result.request_status == 'completed'
    (out / case).write_bytes(result.report_json.encode('utf-8'))
"""
with tempfile.TemporaryDirectory() as tmp:
    dirs = []
    for label, package in [('base', base), ('fixed', from_repo)]:
        out = Path(tmp) / label
        out.mkdir()
        subprocess.run([sys.executable, '-I', '-B', '-c', emit, str(package),
                        str(inputs), str(out)], check=True)
        dirs.append(out)
    summary = {}
    for case in ('no_body', 'body', 'mismatch'):
        before, after = [(p / case).read_bytes() for p in dirs]
        assert before == after, case
        summary[case] = {'identical': True, 'bytes': len(after),
                         'sha256': hashlib.sha256(after).hexdigest()}
    print(json.dumps(summary, indent=2))
