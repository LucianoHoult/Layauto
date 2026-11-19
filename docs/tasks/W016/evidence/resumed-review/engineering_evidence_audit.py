"""Read-only independent audit of completed-source engineering evidence.

Does not rerun product tests or encode old wire. Output is a review sidecar.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
evidence = root/'docs/tasks/W016/evidence/resumed'
base = evidence/'completed'
manifest_path = evidence/'completed-source-identity.json'
manifest = json.loads(manifest_path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name): return json.loads((base/name).read_text())
manifest_sha = sha(manifest_path)
assert all(sha(root/name) == value for name, value in manifest['files'].items())
runtime = {name: value for name, value in manifest['files'].items() if name.startswith('layauto_v2/')}

def nodes(name):
    return [line for line in (base/name).read_text().splitlines() if line.startswith('tests/') and '::' in line]
all310, all312 = nodes('collection-all-310.txt'), nodes('collection-all-312.txt')
long = nodes('collection-order-312.txt')
assert all310 == all312 and len(all310) == len(set(all310)) == 1956
assert len(long) == len(set(long)) == 1953
assert set(long) <= set(all310)
supplement = sorted(set(all310)-set(long))
assert len(supplement) == 3 and all(n.startswith('tests/fixture_support/test_w004_body.py::') for n in supplement)
assert not set(long).intersection(supplement)
scope = read('collection-scope.json')
assert scope['supplement_nodes'] == supplement and scope['source_manifest_sha256'] == manifest_sha
assert all(sha(base/name) == value for name, value in scope['collections'].items())

reports = []
for name in ('pure-seams', 'mypy-310', 'mypy-312', 'build-310', 'build-312', 'installed-smoke-310', 'installed-smoke-312'):
    meta = read(name+'.json')
    assert meta['exit_code'] == 0 and meta['source_manifest_sha256'] == manifest_sha
    assert all(sha(base/meta[k]) == meta[k+'_sha256'] for k in ('stdout', 'stderr'))
    reports.append({'report': name+'.json', 'sha256': sha(base/(name+'.json')), 'exit_code': 0, 'original_output_hashes_match': True})

environment_rows = []
install_rows = []
for version in ('310', '312'):
    env = read('environment-'+version+'.json')
    cmd = [env['executable'], '-I', '-c', 'import sys,json,importlib.metadata; print(json.dumps({"python":sys.version,"dependencies":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}}))']
    actual = json.loads(subprocess.check_output(cmd, text=True))
    assert actual['python'] == env['python'] and actual['dependencies'] == env['dependencies']
    environment_rows.append({'version': version, 'python': env['python'], 'dependency_count': len(env['dependencies']), 'current_environment_matches': True})
    install = read('installation-identity-'+version+'.json')
    assert install['matched_runtime_files'] == runtime
    package = Path(install['package'])
    assert not package.is_relative_to(root)
    assert all(sha(package.parent/name) == value for name, value in runtime.items())
    meta = read('installed-smoke-'+version+'.json')
    assert meta['cwd'] == '/tmp' and '-I' in meta['command']
    installed_env = json.loads(subprocess.check_output([meta['command'][0], *cmd[1:]], text=True))
    assert installed_env['python'] == install['python'] and installed_env['dependencies'] == install['dependencies']
    smoke = read('installed-smoke-'+version+'.stdout.txt')
    assert smoke['installed_package'] == str(package/'__init__.py')
    assert [(c['case'], c['status']) for c in smoke['cases']] == [('no_body', 'completed'), ('body', 'completed'), ('mismatch', 'completed'), ('bad_body', 'rejected'), ('manual', 'completed')]
    install_rows.append({'version': version, 'runtime_files': len(runtime), 'all_installed_bytes_match_frozen_source': True,
                         'outside_repository': True, 'installed_dependencies_match': True, 'five_actual_file_cases': True})

artifacts = read('build-artifacts.json')
for name, identity in artifacts.items():
    version, filename = name.split('/', 1)
    path = Path('/tmp/w016-build-completed-'+version)/filename
    assert path.stat().st_size == identity['bytes'] and sha(path) == identity['sha256']
    if filename.endswith('.whl'):
        with zipfile.ZipFile(path) as archive:
            assert all(hashlib.sha256(archive.read(member)).hexdigest() == value for member, value in runtime.items())
    else:
        with tarfile.open(path) as archive:
            assert all(hashlib.sha256(archive.extractfile('layauto-0.2.0/'+member).read()).hexdigest() == value for member, value in runtime.items())

smoke_inputs = read('smoke-input-identity.json')
assert sha(Path(smoke_inputs['actual_script_path'])) == smoke_inputs['actual_script_sha256']
assert all(sha(Path(smoke_inputs['root'])/name) == value for name, value in smoke_inputs['files'].items())

resource_rows = []
for case in ('no-body', 'body', 'mismatch'):
    timed, counted = read('resource-'+case+'.json'), read('count-'+case+'.json')
    assert timed['source'] == counted['source']
    assert all(manifest['files'][name] == value for name, value in timed['source'].items())
    assert timed['inputs'] == counted['inputs'] and timed['report_sha256'] == counted['report_sha256']
    assert not timed['counted'] and counted['counted']
    assert timed['whole_public_call_seconds'] < 120 and timed['hwm_kib'] < 1024*1024
    assert timed['dependencies'] == read('environment-312.json')['dependencies']
    counts = counted['counts']
    for key in ('importers/calibre.py:parse_query', 'importers/cdl.py:parse_cdl', 'importers/gds.py:parse_gds'):
        assert counts[key] == 2
    for key in ('annotation/net_regions.py:build_annotation_operands', 'derive/channel_identity.py:build_channel_identity_draft', 'derive/terminal_relations.py:terminal_operands'):
        assert counts[key] == 1
    assert counts.get('derive/body_relations.py:evaluate_body_operands', 0) == (1 if case == 'body' else 0)
    resource_rows.append({'case': case, 'seconds': timed['whole_public_call_seconds'], 'hwm_kib': timed['hwm_kib'],
                          'report_bytes': timed['report_bytes'], 'capture_bytes': timed['capture_bytes'],
                          'source_inputs_dependencies_and_report_hash_match': True, 'expected_full_parse_and_neutral_build_counts': True})

print(json.dumps({'status': 'passed', 'scope': 'Independent read-only metadata/actual installed and artifact byte audit; no product rerun.',
                  'manifest_sha256': manifest_sha, 'source_files_checked': len(manifest['files']),
                  'collection': {'full_nodes': len(all310), 'long_suite_nodes': len(long), 'supplement_nodes': supplement,
                                 'same_ordered_full_nodes_both_interpreters': True, 'disjoint_union_exactly_full_tests': True},
                  'execution_reports': reports, 'environments': environment_rows, 'installations': install_rows,
                  'build_artifacts_all_bytes_and_runtime_payloads_match': True, 'smoke_inputs_and_driver_match': True,
                  'resources': resource_rows, 'full_matrices': 'Pending; collection equality and successful smoke do not prove pytest execution.'}, indent=2))
