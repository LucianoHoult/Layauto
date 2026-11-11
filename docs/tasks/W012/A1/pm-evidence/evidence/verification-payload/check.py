#!/usr/bin/env python3
"""Read-only PM audit of saved W012 A1 engineering/artifact evidence.

No Layauto imports, tests, codec calls, installation or performance execution.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tarfile
import zipfile

ROOT = Path('/workspace/Layauto')
OUT = Path(__file__).parent
A1 = ROOT / 'docs/tasks/W012/A1'
V = A1 / 'verification-r2'
checks = []

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    return json.loads(path.read_text())

def check(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

head = git('rev-parse', 'HEAD').decode().strip()
initial_status = git('status', '--porcelain=v1').decode()
check('requested_HEAD', head == 'db07a16fb7cbbac030adae84a9eb88cc0c8aa650', head)
manifest = read_json(V / 'source-manifest.json')
files = manifest['files']
runtime = manifest['runtime_files']
check('source_count_263', len(files) == 263)
check('runtime_count_100', len(runtime) == 100)
for name, digest in files.items():
    check('current_source_hash:' + name, sha((ROOT / name).read_bytes()) == digest)
    check('product_freeze_hash:' + name, sha(git('show', 'ca1f810c3c97376f71089d8b4054760ff198012f:' + name)) == digest)
check('runtime_is_source_subset', runtime == {n.removeprefix('layauto_v2/'): h for n,h in files.items() if n.startswith('layauto_v2/')})
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    archived = {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
check('snapshot_exact_263_payload', archived == files)

receipt = read_json(V / 'receipt.json')
check('receipt_passed_21_commands', receipt['status'] == 'passed' and len(receipt['commands']) == 21)
check('receipt_source_manifest_hash', sha((V / 'source-manifest.json').read_bytes()) == receipt['source_manifest_sha256'])
check('receipt_source_snapshot_hash', sha((V / 'source-snapshot.tar.gz').read_bytes()) == receipt['source_snapshot_sha256'])
check('receipt_runner_hash', sha((A1 / 'verification-tools/prepare_final.py').read_bytes()) == receipt['runner_sha256'])
check('receipt_smoke_hash', sha((V / 'installed_smoke.py').read_bytes()) == receipt['smoke_sha256'])
command_summary = []
for command in receipt['commands']:
    stem = command['stdout'].removesuffix('.stdout.txt')
    check('command_exit:' + stem, command['exit_code'] == 0)
    check('command_json:' + stem, read_json(V / (stem + '.json')) == command)
    for stream in ('stdout', 'stderr'):
        check('command_output_hash:' + command[stream], sha((V / command[stream]).read_bytes()) == command[stream + '_sha256'])
    command_summary.append({'name': stem, 'exit_code': command['exit_code'], 'cwd': command['cwd'], 'argv': command['command']})

baseline = set(line for line in (V / 'baseline-collection.txt').read_text().splitlines() if line.startswith('tests/') and '::' in line)
check('baseline_count_1605', len(baseline) == 1605)
check('baseline_collection_hash', sha((V / 'baseline-collection.txt').read_bytes()) == receipt['baseline_collection_sha256'])
collections = {}
test_results = {}
installation = read_json(V / 'installation-identity.json')
package_identity = read_json(V / 'package-identity.json')
for version in ('310', '312'):
    text = (V / ('collection-' + version + '.stdout.txt')).read_text()
    nodes = set(line for line in text.splitlines() if line.startswith('tests/') and '::' in line)
    collections[version] = nodes
    added = sorted(nodes - baseline)
    check('collected_1656:' + version, len(nodes) == 1656)
    check('baseline_subset:' + version, baseline <= nodes)
    check('added_51_hex_tests_only:' + version, len(added) == 51 and all(n.startswith('tests/contracts/test_w012_hex_validation.py::') for n in added))
    scope = read_json(V / ('pytest-scope-' + version + '.json'))
    check('scope_matches_actual_nodes:' + version, scope == {'baseline_test_count':1605,'current_test_count':1656,'added_test_count':51,'missing_baseline_ids':[]})
    pytest_tail = (V / ('pytest-' + version + '.stdout.txt')).read_text().splitlines()[-1]
    typing = (V / ('typing-' + version + '.stdout.txt')).read_text().strip()
    check('pytest_saved_pass_1656:' + version, re.fullmatch(r'1656 passed in [0-9.]+s \([^)]+\)', pytest_tail) is not None, pytest_tail)
    check('typing_saved_pass_54:' + version, typing == 'Success: no issues found in 54 source files', typing)
    for prefix in ('pip-check-', 'installed-pip-check-'):
        check('saved_pip_check:' + prefix + version, (V / (prefix + version + '.stdout.txt')).read_text().strip() == 'No broken requirements found.')
    identity = installation[version]
    check('saved_install_payload_matches_source:' + version, identity['runtime_files'] == runtime)
    check('saved_install_artifact_hash:' + version, sha(Path(identity['artifact']).read_bytes()) == identity['artifact_sha256'])
    install_report = read_json(V / ('install-' + version + '-report.json'))
    layauto_reports = [entry for entry in install_report['install'] if entry['metadata']['name'] == 'layauto']
    check('saved_pip_report_artifact:' + version, len(layauto_reports) == 1 and layauto_reports[0]['download_info']['url'] == 'file://' + identity['artifact'] and layauto_reports[0]['download_info']['archive_info']['hash'] == 'sha256=' + identity['artifact_sha256'])
    expected_extension = '.tar.gz' if version == '310' else '.whl'
    check('saved_install_artifact_kind:' + version, identity['artifact'].endswith(expected_extension))
    check('saved_install_isolated:' + version, identity['isolated'] == 1)
    saved_identity_stdout = read_json(V / ('installed-identity-' + version + '.stdout.txt'))
    check('saved_identity_stdout_matches:' + version, all(identity[k] == v for k,v in saved_identity_stdout.items()))
    smoke_record = read_json(V / ('installed-smoke-' + version + '.json'))
    smoke_command = smoke_record['command']
    check('saved_smoke_isolated_bytecode_disabled:' + version, smoke_command[1:3] == ['-I','-B'])
    check('saved_smoke_cwd_outside_source:' + version, not Path(smoke_record['cwd']).is_relative_to(Path('/workspace/w012-a1-final-r2/source')) and not Path(smoke_record['cwd']).is_relative_to(ROOT))
    smoke = read_json(V / ('installed-smoke-' + version + '.stdout.txt'))
    check('saved_smoke_uses_installed_package:' + version, smoke['package'] == identity['package'])
    check('saved_smoke_full_three_paths:' + version, all(k in smoke for k in ['direct','readback','extraction_mismatch']) and smoke['direct']['counts'] == {'MN0':5,'MP0':7} and smoke['readback']['counts'] == {'MN0':5,'MP0':7} and smoke['extraction_mismatch']['counts'] == {'MN0':4,'MP0':7})
    check('saved_smoke_readback_boundaries:' + version, all(smoke[k] is True for k in ['attempt_unchanged','checkpoint_unchanged','terminal_absent']))
    for k in ('direct','readback','extraction_mismatch'):
        case = smoke[k]
        check('saved_smoke_complete_local_evidence:' + version + ':' + k, case['wire_bytes'] > 54000000 and case['raw_FIN_records'] == 18 and case['local_enclosure_status'] == 'pass' and case['local_nodes'] == 14 and case['local_edges'] == 8 and case['local_components'] == 6 and case['body_shapes'] == 6)
    test_results[version] = {'pytest_tail': pytest_tail, 'typing': typing, 'baseline_count':len(baseline), 'collected':len(nodes), 'added':added, 'installed_package_path':identity['package'], 'installed_package_accessible_now':Path(identity['package']).is_file(), 'installed_interpreter_accessible_now':Path(identity['executable']).exists(), 'saved_smoke_argv':smoke_command, 'saved_smoke_cwd':smoke_record['cwd']}
check('same_collection_both_interpreters', collections['310'] == collections['312'])

package_comparison = read_json(A1 / 'package-comparison.json')
payloads = {}
artifact_summary = []
for side in ('before','after'):
    payloads[side] = {}
    for kind in ('wheel','sdist'):
        record = package_comparison['artifacts'][side][kind]
        path = A1 / record['path']
        blob = path.read_bytes()
        check('artifact_blob_hash:' + side + ':' + kind, sha(blob) == record['sha256'])
        check('artifact_blob_bytes:' + side + ':' + kind, len(blob) == record['bytes'])
        if kind == 'wheel':
            with zipfile.ZipFile(path) as z:
                payload = {n.removeprefix('layauto_v2/'):sha(z.read(n)) for n in z.namelist() if n.startswith('layauto_v2/') and not n.endswith('/')}
        else:
            with tarfile.open(path) as t:
                payload = {m.name.split('/layauto_v2/',1)[1]:sha(t.extractfile(m).read()) for m in t.getmembers() if m.isfile() and '/layauto_v2/' in m.name}
        payloads[side][kind] = payload
        check('artifact_runtime_count_100:' + side + ':' + kind, len(payload) == 100)
        if side == 'after':
            check('artifact_after_matches_source:' + kind, payload == runtime)
            check('package_identity_matches_actual:' + kind, package_identity[kind]['runtime_files'] == payload and package_identity[kind]['sha256'] == sha(blob))
        artifact_summary.append({'side':side,'kind':kind,'path':str(path),'bytes':len(blob),'sha256':sha(blob),'runtime_members':len(payload)})
    check('wheel_sdist_payload_equal:' + side, payloads[side]['wheel'] == payloads[side]['sdist'])
differences = {}
for kind in ('wheel','sdist'):
    before, after = payloads['before'][kind], payloads['after'][kind]
    differences[kind] = sorted(k for k in set(before)|set(after) if before.get(k) != after.get(k))
    check('only_codec_payload_diff:' + kind, differences[kind] == ['domain/codec.py'])
    check('comparison_record_actual:' + kind, package_comparison['runtime_payload_differences'][kind] == differences[kind])

before_identity = read_json(A1 / 'before-package/before-source-identity.json')
performance_identity = read_json(A1 / 'performance/frozen-identity.json')
before_performance_runtime = {n.removeprefix('layauto_v2/'): h for n,h in performance_identity['sources']['before'].items() if n.startswith('layauto_v2/')}
check('before_identity_performance_frozen_hash', sha((A1 / 'performance/frozen-identity.json').read_bytes()) == before_identity['performance_frozen_identity_sha256'])
check('before_runtime_matches_performance_and_real_packages', before_identity['runtime_files'] == before_performance_runtime == payloads['before']['wheel'])
with tarfile.open(A1 / 'before-package/before-source.tar') as archive:
    before_tar = {m.name:sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
check('before_source_tar_matches_selected_files', before_tar == before_identity['selected_files'])
check('before_source_tar_runtime_matches_performance', {n.removeprefix('layauto_v2/'):h for n,h in before_tar.items() if n.startswith('layauto_v2/')} == before_performance_runtime)

manifest_summary = []
for relative in ('verification-r2/evidence-manifest.json','before-package/evidence-manifest.json','handoff-artifact-manifest.json','review-evidence-manifest.json'):
    path = A1 / relative
    manifest_value = read_json(path)
    entries = manifest_value.get('files', manifest_value)
    base_directory = ROOT if 'files' in manifest_value else path.parent
    for name,digest in entries.items():
        check('evidence_manifest:' + relative + ':' + name, sha((base_directory / name).read_bytes()) == digest)
    manifest_summary.append({'path':str(path),'entries':len(entries),'all_hashes_verified':True})

check('repository_unchanged_by_audit', git('status','--porcelain=v1').decode() == initial_status)
result = {
    'status':'passed' if all(c['passed'] for c in checks) else 'failed',
    'head':head,
    'repository_initial_status':initial_status,
    'checks_total':len(checks),
    'failed_checks':[c for c in checks if not c['passed']],
    'source_files':len(files),
    'runtime_files':len(runtime),
    'commands':command_summary,
    'test_results':test_results,
    'artifacts':artifact_summary,
    'runtime_payload_differences':differences,
    'manifests':manifest_summary,
    'limitations':[
        'Saved original command outputs/receipts were inspected and hashed; no test, typing, build, install, smoke, codec or performance process was rerun.',
        'Original installed trees/interpreters are checked for current accessibility; inaccessible original trees cannot be directly rehashed in this session. Saved installation-identity contains 100 per-file hashes equal to frozen source and actual artifacts.',
        'Rebuilt before packages are available; this does not establish a before installation/smoke that was not performed.'
    ],
    'checks':checks,
}
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','commands','test_results']},ensure_ascii=False,indent=2))
raise SystemExit(0 if result['status']=='passed' else 1)
