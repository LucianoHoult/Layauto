"""Independent artifact/source/installed-byte audit before the final matrix ends."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path.cwd()
OUT = ROOT / 'docs/tasks/W009/verification'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((OUT / name).read_text())


def runtime(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}


def stream(text):
    values = []
    decoder = json.JSONDecoder()
    while text.strip():
        text = text.lstrip()
        value, end = decoder.raw_decode(text)
        values.append(value)
        text = text[end:]
    return values


source = load('source-manifest.json')
for path, expected in source['files'].items():
    assert sha((ROOT / path).read_bytes()) == expected, path
original = runtime(ROOT / 'layauto_v2')
assert original == source['runtime_files']
packages = load('package-identity.json')
for kind, entry in packages.items():
    artifact = Path(entry['path'])
    assert sha(artifact.read_bytes()) == entry['sha256']
    if kind == 'wheel':
        with zipfile.ZipFile(artifact) as archive:
            actual = {name[len('layauto_v2/'):]: sha(archive.read(name)) for name in archive.namelist()
                      if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
    else:
        actual = {}
        with tarfile.open(artifact, 'r:gz') as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if member.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                    actual['/'.join(parts[2:])] = sha(archive.extractfile(member).read())
    assert actual == entry['runtime_files'] == original
installs = load('installation-identity.json')
smokes = {}
for tag, install in installs.items():
    assert runtime(Path(install['installed_package']).parent) == install['runtime_files'] == original
    assert sha(Path(install['source_artifact']).read_bytes()) == install['source_sha256']
    report = load('install-' + tag + '-report.json')
    package = next(item for item in report['install'] if item['metadata']['name'].lower() == 'layauto')
    assert package['download_info']['url'] == Path(install['source_artifact']).as_uri()
    archive_info = package['download_info']['archive_info']
    reported_hash = archive_info.get('hashes', {}).get('sha256')
    if reported_hash is None:
        assert archive_info['hash'].startswith('sha256=')
        reported_hash = archive_info['hash'][len('sha256='):]
    assert reported_hash == install['source_sha256']
    info = load('installed-smoke-' + tag + '.json')
    assert info['exit_code'] == 0
    assert not Path(info['cwd']).resolve().is_relative_to(ROOT.resolve())
    assert '-I' in info['command'] and '-B' in info['command']
    log = (OUT / info['output']).read_bytes()
    assert sha(log) == info['output_sha256']
    values = stream(log.decode())
    env, checks = values[0]['environment'], values[-1]['checks']
    assert env['isolated'] == 1 and env['dont_write_bytecode']
    assert 'site-packages' in Path(env['installed_package']).parts
    assert env['package_manifest'] == original
    assert checks['status'] == 'passed'
    smokes[tag] = {'cwd': info['cwd'], 'installed_package': env['installed_package'],
                   'source_sha256': install['source_sha256'], 'checks': checks}
print(json.dumps({'status': 'passed', 'source_files': len(source['files']), 'runtime_files': len(original),
                  'source_manifest_sha256': sha((OUT / 'source-manifest.json').read_bytes()),
                  'packages': {kind: entry['sha256'] for kind, entry in packages.items()},
                  'installations': smokes}, indent=2, sort_keys=True))
