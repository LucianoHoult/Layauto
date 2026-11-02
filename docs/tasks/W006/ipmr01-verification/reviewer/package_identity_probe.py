"""Independent comparison of new engineering snapshot/packages with Git."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

repo = Path(__file__).resolve().parents[5]
manifest = json.loads((repo / 'docs/tasks/W006/ipmr01-verification/engineering/source-manifest.json').read_text())
product = manifest['product_commit']
snapshot = Path(manifest['snapshot'])
files = manifest['files']
for name, expected in files.items():
    git_bytes = subprocess.check_output(['git', 'show', product + ':' + name], cwd=repo)
    assert hashlib.sha256(git_bytes).hexdigest() == expected, name
    assert (snapshot / name).read_bytes() == git_bytes, name
    assert (repo / name).read_bytes() == git_bytes, name
package_files = {name: sha for name, sha in files.items() if name.startswith('layauto_v2/')}
dist = Path(sys.argv[1])
wheel = dist / 'layauto-0.2.0-py3-none-any.whl'
sdist = dist / 'layauto-0.2.0.tar.gz'
with zipfile.ZipFile(wheel) as archive:
    assert {name for name in archive.namelist() if name.startswith('layauto_v2/') and not name.endswith('/')} == set(package_files)
    assert not any(name.startswith(('tests/', 'legacy_mvp/', 'docs/')) for name in archive.namelist())
    for name, sha in package_files.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == sha, name
with tarfile.open(sdist) as archive:
    for name, sha in package_files.items():
        assert hashlib.sha256(archive.extractfile('layauto-0.2.0/' + name).read()).hexdigest() == sha, name
assert 'layauto_v2/py.typed' in package_files
result = {'product_commit': product, 'source_snapshot_git_workspace_files': len(files),
          'new_wheel_and_sdist_package_files': len(package_files),
          'new_package_bytes_verified_directly': True,
          'sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (wheel, sdist)}}
print(json.dumps(result, indent=2))
