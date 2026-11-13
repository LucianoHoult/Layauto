"""Record a fresh, bounded independent probe invocation and immutable outputs."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
argv = [sys.executable, '-B', str(out / 'public_probe.py')]
hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
before = subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root, text=True)
clock = time.monotonic()
with (out / 'public.stdout.jsonl').open('xb') as stdout, (out / 'public.stderr.txt').open('xb') as stderr:
    result = subprocess.run(argv, cwd=root, stdout=stdout, stderr=stderr)
record = {
    'argv': argv, 'cwd': str(root), 'started_utc': start,
    'elapsed_seconds': time.monotonic()-clock, 'exit_code': result.returncode,
    'python': sys.version, 'platform': platform.platform(),
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'git_status_before': before,
    'git_status_after': subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=root, text=True),
    'script_sha256': hash_file(out / 'public_probe.py'),
    'stdout_sha256': hash_file(out / 'public.stdout.jsonl'),
    'stderr_sha256': hash_file(out / 'public.stderr.txt'),
}
with (out / 'public.command.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record, indent=2))
raise SystemExit(result.returncode)
