"""Preserve actual source-review command outputs, identity, and completion."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
root = here.parents[3]
script = here / 'source-probe.py'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root),
           XDG_CACHE_HOME='/tmp/w010-source-cache', MPLCONFIGDIR='/tmp/w010-source-mpl')
command = [sys.executable, '-B', str(script)]
receipt = {'command': command, 'cwd': str(root),
           'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
           'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
           'env_overrides': {k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH','XDG_CACHE_HOME','MPLCONFIGDIR')}}
start = time.monotonic()
with (here/'source-probe.stdout.json').open('wb') as out, (here/'source-probe.stderr.txt').open('wb') as err:
    proc = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=err)
receipt.update(exit_code=proc.returncode, elapsed_seconds=time.monotonic()-start,
               completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
receipt['outputs'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      (here/'source-probe.stdout.json', here/'source-probe.stderr.txt')}
(here/'source-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
raise SystemExit(proc.returncode)
