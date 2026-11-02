"""Export the declared commit and retain SHA-256 identities for its input files."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

repository, commit, destination = sys.argv[1:]
repository = Path(repository).resolve()
destination = Path(destination).resolve()
assert not destination.exists(), destination
commit = subprocess.check_output(['git', 'rev-parse', commit], cwd=repository, text=True).strip()
paths = ['layauto_v2', 'tests', 'pyproject.toml', 'README.md',
         'docs/tasks/W003/examples/records.json',
         'docs/tasks/W006/verification/wheel_smoke.py',
         'docs/tasks/W006/independent-premerge-verification/double_exception.py']
archive_bytes = subprocess.check_output(['git', 'archive', '--format=tar', commit, *paths], cwd=repository)
destination.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
    for entry in archive.getmembers():
        assert not entry.issym() and not entry.islnk(), entry.name
        assert (destination / entry.name).resolve().is_relative_to(destination), entry.name
    archive.extractall(destination, filter='data')
files = {}
for path in sorted(destination.rglob('*')):
    if path.is_file():
        relative = path.relative_to(destination).as_posix()
        data = path.read_bytes()
        assert data == subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=repository)
        files[relative] = hashlib.sha256(data).hexdigest()
result = {'product_commit': commit, 'git_archive_paths': paths, 'snapshot': str(destination),
          'file_count': len(files), 'files': files}
(Path(__file__).parent / 'source-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'product_commit': commit, 'snapshot': str(destination), 'files_verified_against_git': len(files)}, indent=2))
