import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/workspace/Layauto')
OUT = Path('/workspace/work/w011-integration')
PYTHON = '/workspace/work/w005-pm-check-env/bin/python'
argv = [PYTHON, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
        'tests/contracts/test_w011_geometry.py', 'tests/contracts/test_w011_exceptions.py',
        '-k', 'actual_w006_readback_preserves_unsealed_attempt or '
        'existing_extraction_mismatch_is_actual or target_only_multiple_axes_do_not_change_source or '
        'original_t05_violation_and_body_scope_remain_visible or '
        'cr03_actual_w007_expected_failure_then_completion_fault_keeps_history']
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == '59f2cda44e30779bb3e82346d71a389831314506'
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
before = time.monotonic()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT))
with (OUT/'combined.stdout.txt').open('wb') as stdout, (OUT/'combined.stderr.txt').open('wb') as stderr:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
receipt = dict(argv=argv, cwd=str(ROOT), started_utc=started,
               finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               elapsed_seconds=time.monotonic()-before, returncode=result.returncode, tested_head=head,
               tested_tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
               environment_overrides={key:env[key] for key in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH')},
               interpreter=subprocess.check_output([PYTHON,'--version'], text=True).strip())
for name in ('combined.stdout.txt','combined.stderr.txt'):
    path = OUT/name
    receipt[name] = dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(OUT/'combined.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
raise SystemExit(result.returncode)
