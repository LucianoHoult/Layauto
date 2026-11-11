"""Fresh, non-overwriting command capture for this independent session only."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
label, *argv = sys.argv[1:]
if argv and argv[0] == '--':
    argv.pop(0)
if not argv or '/' in label:
    raise SystemExit('usage: run_command.py LABEL -- COMMAND [ARG...]')
paths = {name: OUT / (label + '.' + name) for name in ('stdout.txt', 'stderr.txt', 'command.json')}
if any(path.exists() for path in paths.values()):
    raise SystemExit('refusing existing evidence label')
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
           MPLCONFIGDIR='/workspace/work/w012-a1-premerge/mplconfig')
started = dt.datetime.now(dt.timezone.utc).isoformat()
before = time.monotonic()
with paths['stdout.txt'].open('xb') as stdout, paths['stderr.txt'].open('xb') as stderr:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
record = {
    'argv': argv, 'cwd': str(ROOT), 'started_at_utc': started,
    'finished_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    'elapsed_seconds': time.monotonic() - before, 'exit_code': result.returncode,
    'reviewed_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'environment_overrides': {key: env[key] for key in (
        'PYTHONDONTWRITEBYTECODE', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'MPLCONFIGDIR')},
    'stdout_sha256': hashlib.sha256(paths['stdout.txt'].read_bytes()).hexdigest(),
    'stderr_sha256': hashlib.sha256(paths['stderr.txt'].read_bytes()).hexdigest(),
}
paths['command.json'].write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
raise SystemExit(result.returncode)
