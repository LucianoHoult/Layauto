import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

root = Path('/workspace/Layauto')
out = Path('/workspace/work/w010-integration')
name = sys.argv[1]
command = sys.argv[2:]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root))
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
with (out / (name + '.stdout.txt')).open('wb') as stdout, (out / (name + '.stderr.txt')).open('wb') as stderr:
    completed = subprocess.run(command, cwd=root, env=env, stdout=stdout, stderr=stderr)
result = {
    'head': head, 'cwd': str(root), 'command': command,
    'env_overrides': {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root)},
    'started_utc': started, 'elapsed_seconds': round(time.monotonic() - start, 3),
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
    'packages': {key: importlib.metadata.version(key) for key in ('pytest', 'mypy', 'PyYAML')},
    'environment_scope': 'existing PM venv; not a clean install validation',
    'returncode': completed.returncode,
    'outputs': {suffix: {'path': name + '.' + suffix + '.txt', 'sha256': hashlib.sha256((out / (name + '.' + suffix + '.txt')).read_bytes()).hexdigest()} for suffix in ('stdout', 'stderr')},
}
(out / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
print((out / (name + '.stdout.txt')).read_text()[-3000:])
print((out / (name + '.stderr.txt')).read_text()[-1500:])
sys.exit(completed.returncode)
