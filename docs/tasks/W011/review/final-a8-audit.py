"""Independent read-only audit of completed W011 evidence; no product imports/tests."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/tasks/W011'
V = BASE / 'verification'
R = BASE / 'resources'
SOURCE = 'e89bdaa6a091f56cfaf7862dced7232d34e22514'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def indexed(directory, name='evidence-manifest.json', exact=True):
    expected = read(directory / name)
    actual = {str(p.relative_to(directory)): digest(p) for p in directory.rglob('*')
              if p.is_file() and p.name != name}
    assert all(actual.get(k) == v for k, v in expected.items())
    if exact:
        assert actual == expected
    return {'sha256': digest(directory / name), 'indexed_files': len(expected)}


def runtime(directory):
    files = [p for p in directory.rglob('*') if p.is_file()
             and (p.suffix == '.py' or p.name == 'py.typed')]
    assert all(not p.is_symlink() for p in files)
    return {str(p.relative_to(directory)): digest(p) for p in files}


def command(directory, row):
    assert row['exit_code'] == 0
    for stream in ('stdout', 'stderr'):
        name = row.get(stream, row.get('case', '') + '.' + stream + '.txt')
        assert digest(directory / name) == row[stream + '_sha256']
    assert row['started_at_utc'] < row['finished_at_utc']


meta = read(V / 'source-manifest.json')
assert meta['git_head'] == SOURCE
assert len(meta['files']) == 262 and len(meta['runtime_files']) == 100
assert all(digest(ROOT / p) == h for p, h in meta['files'].items())
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    members = [p for p in archive.getmembers() if p.isfile()]
    assert len(members) == len({p.name for p in members}) == 262
    assert {p.name: hashlib.sha256(archive.extractfile(p).read()).hexdigest()
            for p in members} == meta['files']
assert not subprocess.check_output(['git', 'diff', '8917d38', SOURCE, '--', 'layauto_v2'], cwd=ROOT)

verification = read(V / 'receipt.json')
assert verification['status'] == 'passed' and len(verification['commands']) == 21
assert verification['actual_test_counts'] == {'310': 1605, '312': 1605}
for name, field in [('source-manifest.json', 'source_manifest_sha256'),
                    ('source-snapshot.tar.gz', 'source_snapshot_sha256'),
                    ('baseline-collection.txt', 'baseline_collection_sha256'),
                    ('prepare_final.py', 'runner_sha256'), ('installed_smoke.py', 'smoke_sha256')]:
    assert digest(V / name) == verification[field]
for row in verification['commands']:
    command(V, row)
    assert read(V / (row['stdout'].removesuffix('.stdout.txt') + '.json')) == row
baseline = {p for p in (V / 'baseline-collection.txt').read_text().splitlines()
            if p.startswith('tests/') and '::' in p}
gates = read(V / 'resource-gate-validation.json')
matrix = {}
for tag in ('310', '312'):
    ids = [p for p in (V / f'collection-{tag}.stdout.txt').read_text().splitlines()
           if p.startswith('tests/') and '::' in p]
    assert len(ids) == len(set(ids)) == 1605 and len(baseline) == 1465
    assert set(ids[:1465]) == baseline and all('/test_w011_' in p for p in ids[1465:])
    summary = re.findall(r'^(\d+) passed in ([\d.]+)s', (V / f'pytest-{tag}.stdout.txt').read_text(), re.M)
    assert summary == [('1605', '12905.97' if tag == '310' else '7310.82')]
    assert (V / f'typing-{tag}.stdout.txt').read_text().strip() == 'Success: no issues found in 54 source files'
    rows = [json.loads(p) for p in (V / f'resource-gate-{tag}.jsonl').read_text().splitlines()]
    assert rows == gates['events'][tag]
    assert [p['event'] for p in rows] == ['WAIT', 'ACQUIRED', 'SESSION_FINISH_LOCK_RETAINED', 'RELEASED']
    assert all(p['first_gated_node'] == ids[1465] and p['lock_fd_inheritable'] is False
               and p['plugin_sha256'] == digest(V / 'w011_resource_gate.py') for p in rows)
    assert rows[-1]['subprocess_exit_code'] == 0
    matrix[tag] = {'tests': 1605, 'pytest_seconds': float(summary[0][1]),
                   'command_seconds': read(V / f'pytest-{tag}.json')['elapsed_seconds'],
                   'gate_wait_seconds': (datetime.fromisoformat(rows[1]['observed_at_utc'])
                                         - datetime.fromisoformat(rows[0]['observed_at_utc'])).total_seconds()}
assert len({(p['lock_path'], p['lock_device'], p['lock_inode'])
            for rows in gates['events'].values() for p in rows}) == 1
assert gates['events']['312'][2]['observed_at_utc'] < gates['events']['310'][1]['observed_at_utc']

packages = read(V / 'package-identity.json')
for kind, item in packages.items():
    path = V / 'dist' / Path(item['path']).name
    assert digest(path) == item['sha256']
    if kind == 'wheel':
        with zipfile.ZipFile(path) as archive:
            names = [p for p in archive.namelist() if p.startswith('layauto_v2/')
                     and (p.endswith('.py') or p.endswith('/py.typed'))]
            assert len(names) == len(set(names)) == 100
            hashes = {p.removeprefix('layauto_v2/'): hashlib.sha256(archive.read(p)).hexdigest() for p in names}
    else:
        with tarfile.open(path) as archive:
            members = [p for p in archive.getmembers() if p.isfile()
                       and '/layauto_v2/' in p.name and (p.name.endswith('.py') or p.name.endswith('/py.typed'))]
            assert len(members) == len({p.name for p in members}) == 100
            hashes = {p.name.split('/layauto_v2/', 1)[1]: hashlib.sha256(archive.extractfile(p).read()).hexdigest()
                      for p in members}
    assert hashes == item['runtime_files'] == meta['runtime_files']
installations = read(V / 'installation-identity.json')
smokes = {}
for tag in ('310', '312'):
    identity = installations[tag]
    package = Path(identity['package']).parent
    assert 'site-packages' in package.parts and f'clean-{tag}' in package.parts
    assert runtime(package) == identity['runtime_files'] == meta['runtime_files']
    assert identity['isolated'] == 1 and identity['fresh_environment'] is True
    assert identity['artifact_sha256'] == packages['sdist' if tag == '310' else 'wheel']['sha256']
    row = read(V / f'installed-smoke-{tag}.json')
    assert row['command'][1:3] == ['-I', '-B']
    assert row['cwd'] == '/workspace/work/w011-final-e89bdaa/installed-cwd'
    output = read(V / row['stdout'])
    assert output['attempt_unchanged'] and output['package'] == identity['package']
    for case in ('direct', 'readback', 'extraction_mismatch'):
        actual = output[case]
        assert actual['counts'] == {'MN0': 4 if case == 'extraction_mismatch' else 5, 'MP0': 7}
        assert actual['difference_count'] == (1 if case == 'extraction_mismatch' else 0)
        assert actual['comparison_status'] == ('mismatch' if case == 'extraction_mismatch' else 'equal')
    smokes[tag] = {'command_seconds': row['elapsed_seconds'], 'cases': {p: output[p] for p in ('direct', 'readback', 'extraction_mismatch')}}
assert read(V / 'installed-smoke-310.json')['finished_at_utc'] < read(V / 'create-install-312.json')['started_at_utc']

resources = read(R / 'receipt.json')
assert resources['status'] == 'passed' and resources['one_fresh_process_per_case']
assert resources['full_source_tests_config_unchanged']
identity = read(R / 'source-identity.json')
assert identity == resources['source_identity']
assert identity['tested_source_commit'] == SOURCE
assert identity['verification_receipt_sha256'] == digest(V / 'receipt.json')
assert identity['verification_source_manifest_sha256'] == digest(V / 'source-manifest.json')
assert identity['runtime_files'] == meta['runtime_files']
assert identity['probe_sha256'] == digest(R / 'resource_probe.py')
assert identity['launcher_sha256'] == digest(R / 'run_resources.py')
resource_cases = {}
last = read(V / 'installed-smoke-312.json')['finished_at_utc']
for row in resources['commands']:
    command(R, row)
    assert row == read(R / (row['case'] + '.command.json'))
    assert last < row['started_at_utc']
    last = row['finished_at_utc']
    result = read(R / (row['case'] + '.json'))
    assert result['command_argv'] == row['command'] and result['git_head'] == SOURCE
    assert result['source_unchanged_during_probe'] and row['runtime_matches_verified_snapshot_before_and_after']
    assert result['source_manifest'] == {**{'layauto_v2/' + p: h for p, h in meta['runtime_files'].items()}, 'pyproject.toml': meta['files']['pyproject.toml']}
    facts = result['result']
    assert facts['public_roundtrip_equal'] and facts['status'] == 'success'
    assert facts['raw_capture_count'] == len(facts['capture_sources']) == 31
    assert facts['raw_capture_bytes'] == sum(p['bytes'] for p in facts['capture_sources']) == 280706
    assert facts['FIN_evaluations'] == 36 and facts['drawn_FIN_record_count'] == 18
    assert facts['counts'] == {'MN0': 4 if row['case'] == 'extraction-mismatch' else 5, 'MP0': 7}
    resource_cases[row['case']] = {'command_seconds': row['elapsed_seconds'], 'wall_seconds': result['wall_seconds'],
                                  'wire_bytes': facts['result_wire_bytes'], 'wire_sha256': facts['result_wire_sha256'],
                                  'peak_rss_kib': result['process_peak_rss_kib']}

observer = BASE / 'preflight/final-attempt02'
summary = read(observer / 'resource-observations-summary.json')
assert digest(observer / 'resource-observations.jsonl') == summary['raw_sha256']
samples = [json.loads(p) for p in (observer / 'resource-observations.jsonl').read_text().splitlines()]
assert len(samples) == summary['sample_count'] == 1399
assert max(p['cgroup_memory_current_bytes'] for p in samples) == summary['max_sampled_cgroup_memory_bytes']
peaks = {}
for sample in samples:
    for process in sample['processes']:
        key = str(process['pid'])
        peaks[key] = max(peaks.get(key, 0), process['rss_kib'])
assert peaks == {k: p['rss_kib'] for k, p in summary['max_sampled_process_rss_by_pid'].items()}
old = BASE / 'verification-attempt-01'
assert read(old / 'pytest-310.json')['exit_code'] == 1
assert '2 failed, 1603 passed in 9500.70s' in (old / 'pytest-310.stdout.txt').read_text()
assert not subprocess.check_output(['git', 'diff', '81e01da', '--', 'tests/fixtures', 'docs/current-work.md'], cwd=ROOT)

print(json.dumps({'schema': 'layauto-w011-independent-a8-audit/1', 'status': 'passed',
                  'audited_at_utc': datetime.now(timezone.utc).isoformat(), 'reviewer': '/root/code_review',
                  'command': [sys.executable, *sys.argv], 'cwd': str(Path.cwd()),
                  'python': sys.version,
                  'audit_script_sha256': digest(Path(__file__)), 'source_commit': SOURCE,
                  'runtime_equivalent_to': '8917d38d916c914bfa785cb116982f3f299b38de',
                  'source_files': 262, 'runtime_files': 100,
                  'source_manifest_sha256': digest(V / 'source-manifest.json'),
                  'source_snapshot_sha256': digest(V / 'source-snapshot.tar.gz'),
                  'verification_receipt_sha256': digest(V / 'receipt.json'),
                  'verification_index': indexed(V), 'resources_receipt_sha256': digest(R / 'receipt.json'),
                  'resources_index': indexed(R), 'old_failed_attempt_index': indexed(old),
                  'preflight_index_at_audit': indexed(BASE / 'preflight', 'archive-manifest.json', False),
                  'matrix': matrix, 'smokes': smokes, 'resource_cases': resource_cases,
                  'observer_sample_count': len(samples), 'observer_raw_sha256': summary['raw_sha256'],
                  'limitations': ['Read-only evidence audit, no product imports or heavy rerun.',
                                  'Wire bytes are measured by archived successful probes; audit does not rerun codecs.',
                                  'Live install file audit depends on this workspace; package archives and manifests are durable.',
                                  'Final Git commit/push and PM acceptance remain execution/PM actions.']}, indent=2))
