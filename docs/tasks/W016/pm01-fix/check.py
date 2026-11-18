"""Record a command against the PM-01 source freeze. Invoke from the repo root."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', type=Path, default=Path.cwd())
    parser.add_argument('label')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    frozen = evidence / 'frozen.json'
    files = json.loads(frozen.read_text())['files']

    def verify():
        for name, expected in files.items():
            if sha(Path(name)) != expected:
                raise ValueError(f'frozen file changed: {name}')

    verify()
    out = evidence / f'{args.label}.stdout.txt'
    err = evidence / f'{args.label}.stderr.txt'
    start = time.monotonic()
    meta = {'command': args.command, 'cwd': str(args.cwd), 'freeze_sha256': sha(frozen),
            'started_utc': datetime.now(timezone.utc).isoformat()}
    with out.open('xb') as stdout, err.open('xb') as stderr:
        status = subprocess.call(args.command, cwd=args.cwd, stdout=stdout, stderr=stderr,
                                 env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                                      'PYTHONUNBUFFERED': '1', 'MPLCONFIGDIR': '/tmp/pm01-mpl'})
    verify()
    meta.update(exit_code=status, elapsed_seconds=time.monotonic()-start,
                finished_utc=datetime.now(timezone.utc).isoformat(),
                stdout_sha256=sha(out), stderr_sha256=sha(err))
    (evidence / f'{args.label}.meta.json').write_text(json.dumps(meta, indent=2)+'\n')
    raise SystemExit(status)


if __name__ == '__main__':
    main()
