"""Read-only PM-01 evidence audit. No product/test/wire execution."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
p.add_argument('--complete', action='store_true')
a = p.parse_args()
root = a.root.resolve()
base = root/'docs/tasks/W016/pm01-fix'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((base/name).read_text())
frozen = read('frozen.json')
freeze_sha = sha(base/'frozen.json')
assert all(sha(root/name) == value for name, value in frozen['files'].items())
actual_inventory = {str(path.relative_to(root)): sha(path) for owner in ('layauto_v2', 'tests')
                    for path in sorted((root/owner).rglob('*'))
                    if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
actual_inventory['pyproject.toml'] = sha(root/'pyproject.toml')
assert actual_inventory == frozen['files'], 'Frozen inventory is not the complete current source/test/config tree'
runtime = {name: value for name, value in frozen['files'].items() if name.startswith('layauto_v2/')}
independent = read('independent-probe.meta.json')
assert independent['source_files'] == frozen['files'] and independent['exit_code'] == 0
assert independent['stdout_sha256'] == sha(base/'independent-probe.stdout.jsonl')
assert independent['stderr_sha256'] == sha(base/'independent-probe.stderr.txt')
reuse = read('reuse.json')
old = json.loads((root/'docs/tasks/W016/evidence/resumed/completed-source-identity.json').read_text())
changed = sorted(name for name in frozen['files'] if frozen['files'][name] != old['files'][name])
assert set(frozen['files']) == set(old['files']) and changed == reuse['changed_paths']
assert changed == ['layauto_v2/analysis.py', 'layauto_v2/normalization/analysis.py', 'tests/unit/test_analysis_api.py']
assert reuse['new_freeze_sha256'] == freeze_sha
for group in ('original_pm_records', 'adopted_parity_reports'):
    assert all(sha(root/name) == value for name, value in reuse[group].items())
assert sha(root/'docs/tasks/W016/evidence/resumed-review/parity-summary.json') == reuse['parity_summary_sha256']

reports = []
def command_report(label):
    m = read(label+'.meta.json')
    assert m['freeze_sha256'] == freeze_sha and m['exit_code'] == 0, (label, m)
    assert m['stdout_sha256'] == sha(base/(label+'.stdout.txt'))
    assert m['stderr_sha256'] == sha(base/(label+'.stderr.txt'))
    reports.append({'label': label, 'command': m['command'], 'cwd': m['cwd'],
                    'exit_code': m['exit_code'], 'elapsed_seconds': m['elapsed_seconds'],
                    'stdout_sha256': m['stdout_sha256'], 'stderr_sha256': m['stderr_sha256']})
    return m

builds = read('build-install-identity.json')
envs = []
for version in ('310', '312'):
    for label in ('mypy', 'build', 'install', 'smoke', 'combined'):
        command_report(label+'-'+version)
    assert '75 source files' in (base/('mypy-'+version+'.stdout.txt')).read_text()
    env = read('env-'+version+'.json')
    interpreter = '/tmp/pm01-dev-'+version+'/bin/python'
    snippet = 'import sys,json,importlib.metadata; print(json.dumps({"python":sys.version,"dependencies":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}}))'
    # Source checks run from the repository without -I. Their distribution
    # metadata includes the local layauto.egg-info; reproduce that same scope.
    actual = json.loads(subprocess.check_output([interpreter, '-c', snippet], cwd=root, text=True))
    assert actual['python'] == env['version'] and actual['dependencies'] == env['dependencies']
    identity = builds[version]
    site = Path(identity['install']['path'])
    assert not site.is_relative_to(root)
    assert identity['runtime_files_verified'] == len(runtime) == 121
    installed_files = {str(path.relative_to(site)): sha(path) for path in sorted((site/'layauto_v2').rglob('*')) if path.is_file() and '__pycache__' not in path.parts}
    assert installed_files == runtime
    installed = json.loads(subprocess.check_output(['/tmp/pm01-clean-'+version+'/bin/python', '-I', '-c', snippet], text=True))
    assert installed['python'] == identity['install']['version'] and installed['dependencies'] == identity['install']['packages']
    for name, expected in identity['artifacts'].items():
        path = Path('/tmp/pm01-build-'+version)/name
        assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256']
        if name.endswith('.whl'):
            with zipfile.ZipFile(path) as archive:
                assert all(hashlib.sha256(archive.read(member)).hexdigest() == value for member, value in runtime.items())
        else:
            with tarfile.open(path) as archive:
                assert all(hashlib.sha256(archive.extractfile('layauto-0.2.0/'+member).read()).hexdigest() == value for member, value in runtime.items())
    smoke = read('smoke-'+version+'.stdout.txt')
    combined = read('combined-'+version+'.stdout.txt')
    assert smoke['installed_package'] == str(site/'layauto_v2/__init__.py') == combined['installed']
    assert [(c['case'], c['status']) for c in smoke['cases']] == [('no_body','completed'),('body','completed'),('mismatch','completed'),('bad_body','rejected'),('manual','completed')]
    assert combined['status'] == 'rejected' and {f['code'] for f in combined['findings']} == {'SourceTopIdentityMismatch','UnsupportedGeometryComparator'}
    for label in ('smoke', 'combined'):
        m = read(label+'-'+version+'.meta.json')
        assert m['cwd'] == '/tmp' and '-I' in m['command']
    envs.append({'version': version, 'python': env['version'], 'dependencies_match': True,
                 'runtime_files_match': 121, 'wheel_sdist_payloads_match': True, 'source_external_six_cases': True})
assert all(sha(Path('/tmp/pm01-inputs')/name) == value for name, value in read('smoke-inputs.json').items())
collection = read('collection.json')
assert collection['freeze_sha256'] == freeze_sha
assert collection['versions']['310']['ordered_nodeids_utf8_lf_sha256'] == collection['versions']['312']['ordered_nodeids_utf8_lf_sha256']
assert all(v['node_count'] == 1961 and sum(v['paths'].values()) == 1961 and 'tests' in v['command'] for v in collection['versions'].values())

matrices = []
resources = []
if a.complete:
    for version in ('312', '310'):
        m = command_report('pytest-'+version)
        assert 'tests' in m['command'] and '-k' not in m['command'] and '-m' in m['command']
        last = (base/('pytest-'+version+'.stdout.txt')).read_text().strip().splitlines()[-1]
        match = re.fullmatch(r'(\d+) passed(?:, (\d+) subtests passed)? in ([0-9.]+)s(?: \([^\n]+\))?', last)
        assert match and int(match[1]) == 1961, last
        matrices.append({'version': version, 'passed': int(match[1]), 'subtests': int(match[2]) if match[2] else None,
                         'pytest_seconds': float(match[3]), 'exit_code': 0})
    resource_labels = []
    for path in base.glob('*.meta.json'):
        if path.name.startswith('independent-'):
            continue
        metadata = json.loads(path.read_text())
        if any(str(part).endswith(('/resource_probe.py', '/combined_cost.py')) for part in metadata.get('command', [])):
            resource_labels.append(path.name[:-len('.meta.json')])
    resource_labels.sort()
    assert len(resource_labels) == 8 and 'count-combined' in resource_labels, resource_labels
    paired = {}
    intervals = []
    for label in resource_labels:
        metadata = command_report(label)
        report = read(label+'.stdout.txt')
        key = 'combined' if report['case'] == 'pin + unsupported comparator' else report['case']
        kind = 'count' if report['counted'] else 'timed'
        assert (key, kind) not in paired
        paired[key, kind] = report
        if 'source' in report:
            expected_sources = {name: value for name, value in frozen['files'].items() if name.endswith('.py') or name == 'pyproject.toml'}
            assert report['source'] == expected_sources
        intervals.append((datetime.fromisoformat(metadata['started_utc']), datetime.fromisoformat(metadata['finished_utc'])))
        resources.append({'label': label, 'case': key, 'counted': report['counted'],
                          'elapsed_seconds': report.get('whole_public_call_seconds', report.get('elapsed_seconds')),
                          'hwm_kib': report['hwm_kib'], 'capture_bytes': report['capture_bytes'],
                          'report_bytes': report['report_bytes'], 'report_sha256': report['report_sha256'],
                          'counts': report['counts']})
    assert {key for key, kind in paired} == {'no_body', 'body', 'mismatch', 'combined'}
    for case in ('no_body', 'body', 'mismatch', 'combined'):
        timed, counted = paired[case, 'timed'], paired[case, 'count']
        assert timed['report_sha256'] == counted['report_sha256']
        assert timed['capture_bytes'] == counted['capture_bytes']
        if case != 'combined':
            assert timed['inputs'] == counted['inputs']
        else:
            assert timed['captures'] == counted['captures']
            assert set(timed['findings']) == {'SourceTopIdentityMismatch', 'UnsupportedGeometryComparator'}
        assert timed.get('whole_public_call_seconds', timed.get('elapsed_seconds')) < 120
        assert timed['hwm_kib'] < 1024*1024
        counts = counted['counts']
        for name in ('importers/calibre.py:parse_query', 'importers/cdl.py:parse_cdl', 'importers/gds.py:parse_gds'):
            assert counts[name] == 2
        for name in ('derive/channel_identity.py:build_channel_identity_draft', 'annotation/net_regions.py:build_annotation_operands', 'derive/terminal_relations.py:terminal_operands'):
            assert counts.get(name, 0) == (0 if case == 'combined' else 1)
        if case != 'combined':
            assert counts.get('derive/body_relations.py:evaluate_body_operands', 0) == (1 if case == 'body' else 0)
        else:
            assert counts['normalization/_validation.py:source_admission_problem'] == 1
            assert counts.get('state/layout_store.py:build_layout', 0) == 0
    intervals.sort()
    assert all(first[1] <= second[0] for first, second in zip(intervals, intervals[1:])), 'resource runs overlap'
    test_end = max(datetime.fromisoformat(read('pytest-'+v+'.meta.json')['finished_utc']) for v in ('312', '310'))
    assert intervals[0][0] >= test_end, 'resource timing overlapped long pytest'

print(json.dumps({'status': 'passed', 'complete': a.complete, 'freeze_sha256': freeze_sha,
                  'source_test_config_files': len(frozen['files']), 'independent_probe_exact_frozen_identity': True,
                  'changed_from_previous_freeze': changed, 'old_pm_records_and_parity_report_hashes_match': True,
                  'commands': reports, 'environments_installations': envs, 'collection': collection,
                  'matrices': matrices, 'resources': resources,
                  'scope': 'Read-only audit; no product, test, collection or old wire rerun. Collection node-count/digest evidence adopted from recorded commands; final full tests command and passed count checked when --complete.'}, indent=2))
