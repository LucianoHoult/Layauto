#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

out = pathlib.Path(__file__).resolve().parent
root = pathlib.Path(sys.argv[1]).resolve()
command = [sys.executable, '-B', str(out/'audit.py'), str(root)]
started = datetime.now(timezone.utc).isoformat()
then = time.monotonic()
result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out/'audit-output.txt').write_bytes(result.stdout)
receipt = {'command':command,'cwd':str(root),'started_utc':started,
           'elapsed_seconds':round(time.monotonic()-then,3),'returncode':result.returncode,
           'python':sys.version,'platform':platform.platform(),
           'output_sha256':hashlib.sha256(result.stdout).hexdigest(),
           'script_sha256':hashlib.sha256((out/'audit.py').read_bytes()).hexdigest()}
(out/'audit-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result.stdout.decode(),end='')
raise SystemExit(result.returncode)
