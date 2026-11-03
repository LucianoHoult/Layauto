import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

root = Path('/workspace/Layauto')
out = Path('/workspace/work/w008-pm/geometry-check')
command = [sys.executable, '-B', str(out / 'probe.py')]
environment = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root)}
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
source_paths = ['layauto_v2/domain/geometry.py', 'layauto_v2/state/layout_store.py', 'layauto_v2/state/coordinate.py', 'layauto_v2/state/occupancy.py', 'layauto_v2/normalization/geometry.py']
started = datetime.now(timezone.utc).isoformat()
completed = subprocess.run(command, cwd=root, env={**os.environ, **environment}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'output.txt').write_bytes(completed.stdout)
receipt = {'scope': 'bounded PM math / aggregate probe only', 'head': head, 'delivery': 'aced62b0adda35fe7bcd8284a7354badc5b03649', 'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(), 'command': command, 'cwd': str(root), 'environment_overrides': environment, 'python_version': sys.version, 'platform': platform.platform(), 'returncode': completed.returncode, 'output_sha256': hashlib.sha256(completed.stdout).hexdigest(), 'probe_sha256': hashlib.sha256((out / 'probe.py').read_bytes()).hexdigest(), 'source_sha256': {path: hashlib.sha256((root/path).read_bytes()).hexdigest() for path in source_paths}}
(out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
sys.stdout.buffer.write(completed.stdout)
print('exit:', completed.returncode)
raise SystemExit(completed.returncode)
