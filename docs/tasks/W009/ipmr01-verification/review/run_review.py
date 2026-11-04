"""Independent IPMR-01 checks with command, version and raw-output receipts."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
name = sys.argv[1]
commands = {
    'exception-matrix': [sys.executable, '-B', 'docs/tasks/W009/independent-premerge-review/provenance-exceptions/exception_paths.py'],
    'independent-probe': [sys.executable, '-B', str(OUT / 'probe.py')],
    'receipt-controls': [sys.executable, '-B', str(OUT / 'receipt_controls.py')],
    'engineering-command': [sys.executable, '-B', str(OUT / 'engineering_audit.py')],
    'formal-regressions': [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp=/workspace/work/w009-ipmr01-review-work/pytest', 'tests/contracts/test_w009_nested_base_decode.py', 'tests/contracts/test_w009_nested_receipt_exceptions.py', 'tests/contracts/test_w009_captured_decode_exceptions.py'],
}
env = dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT), XDG_CACHE_HOME='/workspace/work/w009-ipmr01-review-work/cache', MPLCONFIGDIR='/workspace/work/w009-ipmr01-review-work/mpl', MPLBACKEND='Agg')
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
started = datetime.now(timezone.utc).isoformat()
t0 = time.monotonic()
with (OUT / (name + '.stdout.txt')).open('wb') as stdout, (OUT / (name + '.stderr.txt')).open('wb') as stderr:
    result = subprocess.run(commands[name], cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
receipt = dict(command=commands[name], cwd=str(ROOT), head=head, python=sys.version, executable=sys.executable, platform=platform.platform(), started_utc=started, elapsed_seconds=round(time.monotonic()-t0,3), returncode=result.returncode, outputs={})
for stream in ('stdout', 'stderr'):
    path = OUT / (name + '.' + stream + '.txt')
    receipt['outputs'][stream] = dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), size=path.stat().st_size)
(OUT / (name + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
raise SystemExit(result.returncode)
