"""Verify newly built wheel and sdist source content against the frozen snapshot."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import zipfile

base = Path(__file__).resolve().parent
manifest = json.loads((base / 'source-manifest.json').read_text())
source = Path(manifest['snapshot'])
dist = Path(sys.argv[1]).resolve()
files = manifest['files']
drift = [name for name, sha in files.items()
         if hashlib.sha256((source / name).read_bytes()).hexdigest() != sha]
assert not drift, drift
product = {name: sha for name, sha in files.items() if name.startswith('layauto_v2/')}
wheel = dist / 'layauto-0.2.0-py3-none-any.whl'
sdist = dist / 'layauto-0.2.0.tar.gz'
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert not any(name.startswith(('legacy_mvp/', 'tests/', 'docs/')) for name in names)
    assert 'layauto_v2/py.typed' in names
    assert {name for name in names if name.startswith('layauto_v2/') and not name.endswith('/')} == set(product)
    for name, sha in product.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == sha, name
with tarfile.open(sdist) as archive:
    for name, sha in product.items():
        stream = archive.extractfile('layauto-0.2.0/' + name)
        assert stream is not None and hashlib.sha256(stream.read()).hexdigest() == sha, name
result = {'product_commit': manifest['product_commit'], 'snapshot_drift': drift,
          'verified_package_source_files': len(product), 'py_typed_present': True,
          'wheel_excludes_legacy_tests_docs': True, 'sdist_sources_match': True,
          'artifacts': {path.name: {'bytes': path.stat().st_size,
                                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path in (wheel, sdist)}}
(base / 'artifact-identity.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
