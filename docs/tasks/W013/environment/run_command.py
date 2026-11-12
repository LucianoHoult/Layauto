"""Record one environment-only setup command without replacing prior attempts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('safe attempt name and command are required')
    evidence = Path(__file__).resolve().parent / 'evidence'
    prefix = evidence / args.name
    for suffix in ('.command.json', '.stdout.txt', '.stderr.txt'):
        if prefix.with_suffix(suffix).exists():
            raise RuntimeError('Prior attempt is preserved: ' + str(prefix))
    work = Path('/workspace/work/w013-env')
    overrides = {
        'UV_PYTHON_INSTALL_DIR': str(work / 'python'),
        'UV_PYTHON_BIN_DIR': str(work / 'bin'),
        'UV_CACHE_DIR': str(work / 'uv-cache'),
        'PIP_CACHE_DIR': str(work / 'pip-cache'),
        'PYTHONDONTWRITEBYTECODE': '1',
        'MPLCONFIGDIR': str(work / 'mplconfig'),
    }
    env = dict(os.environ, **overrides)
    start = time.monotonic()
    started = datetime.now(timezone.utc).isoformat()
    with prefix.with_suffix('.stdout.txt').open('wb') as stdout, prefix.with_suffix('.stderr.txt').open('wb') as stderr:
        completed = subprocess.run(command, cwd=work, env=env, stdout=stdout, stderr=stderr)
    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    row = {
        'argv': command, 'cwd': str(work), 'environment_overrides': overrides,
        'inherited_proxy_and_ca_preserved': True,
        'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
        'seconds': time.monotonic() - start, 'returncode': completed.returncode,
        'runner_sha256': sha(Path(__file__).resolve()),
        'stdout': prefix.name + '.stdout.txt', 'stdout_sha256': sha(prefix.with_suffix('.stdout.txt')),
        'stderr': prefix.name + '.stderr.txt', 'stderr_sha256': sha(prefix.with_suffix('.stderr.txt')),
    }
    prefix.with_suffix('.command.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps(row), flush=True)
    raise SystemExit(completed.returncode)


if __name__ == '__main__':
    main()
