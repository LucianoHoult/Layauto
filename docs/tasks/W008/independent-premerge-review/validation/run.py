"""Run a review check and preserve unabridged output and its command identity."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

out = Path(sys.argv[1]).resolve()
name = sys.argv[2]
command = sys.argv[3:]
out.mkdir(parents=True, exist_ok=True)
started = datetime.now(timezone.utc).isoformat()
clock = time.monotonic()
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
with (out / (name + '.txt')).open('wb') as stream:
    process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
elapsed = time.monotonic() - clock
raw = (out / (name + '.txt')).read_bytes()
receipt = {'started_utc': started, 'elapsed_seconds': elapsed,
           'command': command, 'cwd': str(Path.cwd()),
           'environment_overrides': {'PYTHONDONTWRITEBYTECODE': '1'},
           'exit_code': process.returncode, 'output': name + '.txt',
           'output_sha256': hashlib.sha256(raw).hexdigest()}
(out / (name + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
print(raw.decode(errors='replace'))
sys.exit(process.returncode)
