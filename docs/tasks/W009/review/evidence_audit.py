"""Independent review of the final W009 execution evidence and package bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path.cwd()
OUT = ROOT / 'docs/tasks/W009/verification'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text())


def runtime(root):
    return {str(path.relative_to(root)): sha(path.read_bytes())
            for path in sorted(root.rglob('*'))
            if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}


def json_stream(text):
    records = []
    decoder = json.JSONDecoder()
    while text.strip():
        text = text.lstrip()
        value, end = decoder.raw_decode(text)
        records.append(value)
        text = text[end:]
    return records


receipt = read('receipt.json')
assert receipt['status'] == 'passed'
manifest = read('source-manifest.json')
manifest_bytes = (OUT / 'source-manifest.json').read_bytes()
assert receipt['source_manifest_sha256'] == sha(manifest_bytes)
assert not [path for path, expected in manifest['files'].items()
            if sha((ROOT / path).read_bytes()) != expected]
source = runtime(ROOT / 'layauto_v2')
assert source == manifest['runtime_files']
commands = []
tests = {}
for command in receipt['commands']:
    assert command['exit_code'] == 0
    log = (OUT / command['output']).read_bytes()
    assert sha(log) == command['output_sha256']
    name = command['output']
    if name.startswith('pytest-'):
        count = int(re.search(rb'(\d+) passed', log).group(1))
        assert count == 914
        tests[name] = count
    if name.startswith('typing-'):
        assert b'Success: no issues found in 44 source files' in log
    if name.startswith('installed-smoke-'):
        assert not Path(command['cwd']).resolve().is_relative_to(ROOT.resolve())
        assert '-I' in command['command'] and '-B' in command['command']
        records = json_stream(log.decode())
        environment, checks = records[0]['environment'], records[-1]['checks']
        assert checks['status'] == 'passed'
        assert environment['isolated'] == 1 and environment['dont_write_bytecode']
        assert 'site-packages' in Path(environment['installed_package']).parts
        assert environment['package_manifest'] == source
    commands.append({'output': name, 'sha256': sha(log), 'cwd': command['cwd']})
assert len(tests) == 2 and len(set(tests.values())) == 1
packages = read('package-identity.json')
wheel = Path(packages['wheel']['path'])
sdist = Path(packages['sdist']['path'])
assert sha(wheel.read_bytes()) == packages['wheel']['sha256']
assert sha(sdist.read_bytes()) == packages['sdist']['sha256']
with zipfile.ZipFile(wheel) as archive:
    wheel_files = {name[len('layauto_v2/'):]: sha(archive.read(name))
                   for name in archive.namelist() if name.startswith('layauto_v2/')
                   and (name.endswith('.py') or name.endswith('/py.typed'))}
with tarfile.open(sdist, 'r:gz') as archive:
    sdist_files = {}
    for member in archive.getmembers():
        parts = Path(member.name).parts
        if (member.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2'
                and (parts[-1].endswith('.py') or parts[-1] == 'py.typed')):
            sdist_files['/'.join(parts[2:])] = sha(archive.extractfile(member).read())
assert source == wheel_files == sdist_files
installs = read('installation-identity.json')
for tag, installation in installs.items():
    assert installation['runtime_files'] == source
    assert runtime(Path(installation['installed_package']).parent) == source
    artifact = Path(installation['source_artifact'])
    assert sha(artifact.read_bytes()) == installation['source_sha256']
output = {'status': 'passed', 'manifest_sha256': sha(manifest_bytes),
          'source_files': len(manifest['files']), 'runtime_files': len(source),
          'commands': commands, 'tests': tests,
          'packages': {kind: entry['sha256'] for kind, entry in packages.items()},
          'installed_tags': sorted(installs)}
print(json.dumps(output, indent=2, sort_keys=True))
