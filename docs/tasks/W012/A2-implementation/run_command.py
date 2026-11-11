"""Record an engineering command without overwriting earlier evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
    if not argv:
        parser.error('a command is required')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    paths = {key: Path(str(args.out) + suffix) for key, suffix in (
        ('command', '.command.json'), ('stdout', '.stdout.txt'), ('stderr', '.stderr.txt'))}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError('refusing to overwrite command evidence: ' + str(args.out))
    source = {}
    for base in ('layauto_v2', 'tests'):
        for path in sorted((args.cwd / base).rglob('*.py')):
            source[str(path.relative_to(args.cwd))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('pyproject.toml',):
        source[name] = hashlib.sha256((args.cwd / name).read_bytes()).hexdigest()
    record = {'argv': argv, 'cwd': str(args.cwd), 'source_sha256': source,
              'start_utc': datetime.now(timezone.utc).isoformat(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'environment': {key: os.environ.get(key) for key in (
                  'PYTHONPATH', 'PYTHONHASHSEED', 'PYTHONDONTWRITEBYTECODE')}}
    with paths['command'].open('x') as stream:
        json.dump(record, stream, indent=2)
    start = time.perf_counter()
    with paths['stdout'].open('xb') as stdout, paths['stderr'].open('xb') as stderr:
        result = subprocess.run(argv, cwd=args.cwd, stdout=stdout, stderr=stderr, check=False)
    record.update(exit_code=result.returncode, elapsed_seconds=time.perf_counter() - start,
                  end_utc=datetime.now(timezone.utc).isoformat(),
                  stdout_sha256=hashlib.sha256(paths['stdout'].read_bytes()).hexdigest(),
                  stderr_sha256=hashlib.sha256(paths['stderr'].read_bytes()).hexdigest())
    paths['command'].write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'out': str(args.out), 'exit_code': result.returncode,
                      'elapsed_seconds': record['elapsed_seconds']}), flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
