"""Record a development check with actual source identity and unmodified logs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from source_identity import files_manifest, source_id, source_names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
    if not argv:
        parser.error('a command is required')
    root, prefix = args.root.resolve(), args.prefix.resolve()
    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {kind: Path(str(prefix) + suffix) for kind, suffix in
             (('stdout', '.stdout.txt'), ('stderr', '.stderr.txt'), ('receipt', '.command.json'))}
    if any(path.exists() for path in paths.values()):
        raise RuntimeError('An original check attempt exists; choose a new prefix')
    names = source_names(root)
    before = files_manifest(root, names)
    overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root),
                 'MYPY_CACHE_DIR': '/workspace/work/w014-mypy-development',
                 'MPLCONFIGDIR': '/workspace/work/w014-env/mplconfig'}
    started, tick = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with paths['stdout'].open('xb') as stdout, paths['stderr'].open('xb') as stderr:
        process = subprocess.run(argv, cwd=root, env=dict(os.environ, **overrides), stdout=stdout, stderr=stderr)
    after = files_manifest(root, source_names(root))
    row = {'argv': argv, 'cwd': str(root), 'environment_overrides': overrides,
           'utc_start': started, 'elapsed_seconds': time.monotonic() - tick,
           'returncode': process.returncode, 'source_id_before': source_id(before),
           'source_id_after': source_id(after), 'source_unchanged': before == after,
           'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
           'files': before,
           'logs': {kind: {'path': str(paths[kind]), 'sha256': hashlib.sha256(paths[kind].read_bytes()).hexdigest()}
                    for kind in ('stdout', 'stderr')}}
    with paths['receipt'].open('x') as stream:
        stream.write(json.dumps(row, indent=2) + '\n')
    print(json.dumps({'returncode': process.returncode, 'source_unchanged': before == after,
                      'elapsed_seconds': row['elapsed_seconds'], 'source_id': row['source_id_before']}), flush=True)
    if before != after:
        raise RuntimeError('Product source/test/config bytes changed during the check')
    raise SystemExit(process.returncode)


if __name__ == '__main__':
    main()
