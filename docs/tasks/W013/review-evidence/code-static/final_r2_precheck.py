"""Independent read-only audit of completed R2 matrices/build before smoke closure."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path.cwd()
    evidence = root / 'docs/tasks/W013/verification-r2'
    source = json.loads((evidence / 'source-manifest.json').read_text())
    expected_id = '2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278'
    assert source['source_id'] == expected_id
    assert digest(json.dumps(source['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()) == expected_id
    assert len(source['files']) == 273 and len(source['runtime_files']) == 106
    frozen = Path('/workspace/work/w013-final-r2/source')
    for name, sha in source['files'].items():
        assert digest((root / name).read_bytes()) == digest((frozen / name).read_bytes()) == sha
    with tarfile.open(evidence / 'source-snapshot.tar.gz') as archive:
        members = [item for item in archive.getmembers() if item.isfile()]
        assert len(members) == len(source['files'])
        assert {item.name: digest(archive.extractfile(item).read()) for item in members} == source['files']
    checked = {}
    def command(name):
        path = evidence / (name + '.json')
        row = json.loads(path.read_text())
        assert row['exit_code'] == 0, name
        for log in ('stdout', 'stderr'):
            assert digest((evidence / row[log]).read_bytes()) == row[log + '_sha256'], name
        checked[name] = digest(path.read_bytes())
        return row
    baseline = {line for line in (evidence / 'baseline-collection.txt').read_text().splitlines() if line.startswith('tests/') and '::' in line}
    assert len(baseline) == 1656
    matrices = {}
    for tag, version in (('310', '3.10.22'), ('312', '3.12.14')):
        envrow = command('environment-' + tag)
        env = json.loads((evidence / envrow['stdout']).read_text())
        assert env['version'].startswith(version)
        assert Path(env['source_package']) == frozen / 'layauto_v2/__init__.py'
        command('collection-' + tag)
        ids = {line for line in (evidence / ('collection-' + tag + '.stdout.txt')).read_text().splitlines() if line.startswith('tests/') and '::' in line}
        assert len(ids) == 1731 and baseline <= ids
        scope = json.loads((evidence / ('pytest-scope-' + tag + '.json')).read_text())
        assert scope['missing_baseline_ids'] == [] and scope['added_test_count'] == 75
        tests = command('pytest-' + tag)
        assert '1731 passed' in (evidence / tests['stdout']).read_text()
        assert tests['cwd'] == str(frozen)
        typing = command('typing-' + tag)
        assert (evidence / typing['stdout']).read_text().strip() == 'Success: no issues found in 60 source files'
        command('pip-check-' + tag)
        matrices[tag] = {'version': version, 'tests': 1731, 'retained_baseline_nodes': 1656,
                         'added_nodes': 75, 'command_elapsed_seconds': tests['elapsed_seconds'],
                         'typing_source_files': 60}
    build = command('build')
    packages = json.loads((evidence / 'package-identity.json').read_text())
    artifacts = {}
    for kind, item in packages.items():
        path = Path(item['path'])
        assert digest(path.read_bytes()) == item['sha256']
        assert item['runtime_files'] == source['runtime_files']
        if kind == 'wheel':
            with zipfile.ZipFile(path) as archive:
                selected = [name for name in archive.namelist() if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))]
                actual = {name.removeprefix('layauto_v2/'): digest(archive.read(name)) for name in selected}
                assert len(selected) == len(actual) == 106
        else:
            with tarfile.open(path) as archive:
                selected = [entry for entry in archive.getmembers() if entry.isfile() and len(Path(entry.name).parts) > 2 and Path(entry.name).parts[1] == 'layauto_v2' and (entry.name.endswith('.py') or entry.name.endswith('/py.typed'))]
                actual = {'/'.join(Path(entry.name).parts[2:]): digest(archive.extractfile(entry).read()) for entry in selected}
                assert len(selected) == len(actual) == 106
        assert actual == source['runtime_files']
        artifacts[kind] = {'sha256': item['sha256'], 'runtime_files': 106}
    tools = json.loads((evidence / 'tool-identity.json').read_text())
    copies = {'runner': 'prepare_final.py', 'source_identity': 'source_identity.py', 'smoke': 'installed_smoke.py'}
    for name, row in tools.items():
        assert digest(Path(row['source']).read_bytes()) == digest((evidence / copies[name]).read_bytes()) == row['sha256']
    clearance = json.loads((evidence / 'resource-clearance.json').read_text())
    assert digest(Path(clearance['source']).read_bytes()) == clearance['sha256']
    assert clearance['decision']['source_id'] == expected_id and clearance['decision']['measured_source_id'].startswith('6463eb67')
    installed310 = command('installed-identity-310')
    identity310 = json.loads((evidence / installed310['stdout']).read_text())
    assert identity310['isolated'] == 1 and '/clean-310/' in identity310['package']
    print(json.dumps({'classification': 'independent-completed-matrix-build-precheck-install-smokes-pending',
        'source_id': expected_id, 'source_files_verified': 273, 'runtime_files_verified': 106,
        'frozen_source_snapshot_verified': True, 'matrices': matrices, 'build_elapsed_seconds': build['elapsed_seconds'],
        'artifacts': artifacts, 'tool_identity_verified': tools, 'checked_command_receipts': checked,
        'installed310_identity': identity310,
        'not_certified': ['final runner receipt', 'both completed installation smokes', 'final whole-task review'],
        'scope': 'Read/hashes only; no test/capture/resource/build/install rerun.'}, indent=2))


if __name__ == '__main__':
    main()
