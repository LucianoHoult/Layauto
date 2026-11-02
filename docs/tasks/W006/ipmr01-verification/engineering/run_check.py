"""Record one command, its combined output, result and immutable log hash."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('cwd')
parser.add_argument('--commit', default=None)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command
if command and command[0] == '--':
    command = command[1:]
assert command
base = Path(__file__).resolve().parent
start = datetime.now(timezone.utc).isoformat()
tick = time.monotonic()
result = subprocess.run(command, cwd=args.cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - tick
log = base / (args.label + '.txt')
log.write_bytes(result.stdout)
record = {'command': command, 'cwd': args.cwd, 'product_commit': args.commit,
          'start_utc': start, 'duration_seconds': round(elapsed, 3),
          'exit_code': result.returncode, 'combined_output': log.name,
          'log_sha256': hashlib.sha256(result.stdout).hexdigest()}
(base / (args.label + '.result.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
print(result.stdout.decode('utf-8', errors='replace')[-2500:])
raise SystemExit(result.returncode)
