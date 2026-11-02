from pathlib import Path
import hashlib
import json
import tarfile
import zipfile

base = Path(__file__).parent
manifest = json.loads((base / 'tested-source-manifest.json').read_text())
source = base / 'source'
drift = [p for p, h in manifest['files'].items()
         if hashlib.sha256((source / p).read_bytes()).hexdigest() != h]
assert not drift, drift
product = {p: h for p, h in manifest['files'].items() if p.startswith('layauto_v2/')}
wheel = base / 'dist/layauto-0.2.0-py3-none-any.whl'
sdist = base / 'dist/layauto-0.2.0.tar.gz'
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    mismatch = [p for p, h in product.items()
                if p not in names or hashlib.sha256(archive.read(p)).hexdigest() != h]
    assert not mismatch, mismatch
    assert 'layauto_v2/py.typed' in names
    assert not any(x.startswith(('legacy_mvp/', 'tests/', 'docs/')) for x in names)
with tarfile.open(sdist) as archive:
    mismatch = []
    for p, h in product.items():
        f = archive.extractfile('layauto-0.2.0/' + p)
        if f is None or hashlib.sha256(f.read()).hexdigest() != h:
            mismatch.append(p)
    assert not mismatch, mismatch
out = {
    'commit': manifest['commit'], 'snapshot_source_test_drift': drift,
    'package_source_files_verified': len(product),
    'wheel_package_scope': 'layauto_v2 only; py.typed present; no legacy/tests/docs',
    'sdist_product_sources_match': True,
    'artifacts': {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                           'bytes': p.stat().st_size} for p in (wheel, sdist)},
}
(base / 'build-artifact-identity.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
