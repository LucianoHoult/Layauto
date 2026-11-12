"""Describe all current source/test/config bytes used by the W013 final matrix.

This command does not run product code. An optional --out must be a new file.
Its source_id intentionally excludes Git metadata and absolute checkout paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


SELECTED = ('layauto_v2', 'tests', 'pyproject.toml', 'README.md',
            'docs/tasks/W003/examples/records.json')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_names(root: Path) -> list[str]:
    names: set[str] = set()
    for options in ((), ('--others', '--exclude-standard')):
        result = subprocess.check_output(['git', 'ls-files', '-z', *options, '--', *SELECTED], cwd=root)
        names.update(name for name in result.decode().split('\0') if name)
    for name in names:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('Source selection contains removed, non-file, or symlink path: ' + name)
    return sorted(names)


def files_manifest(root: Path, names: list[str]) -> dict[str, str]:
    return {name: sha((root / name).read_bytes()) for name in names}


def runtime_manifest(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): sha(path.read_bytes())
            for path in sorted(root.rglob('*'))
            if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}


def source_id(files: dict[str, str]) -> str:
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    files = files_manifest(root, source_names(root))
    result = {'source_id': source_id(files), 'files': files,
              'runtime_files': runtime_manifest(root / 'layauto_v2'),
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=root, text=True),
              'root': str(root), 'identity_algorithm': 'sha256(canonical-json(sorted relative-path -> sha256(file bytes)))'}
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x') as stream:
            stream.write(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
