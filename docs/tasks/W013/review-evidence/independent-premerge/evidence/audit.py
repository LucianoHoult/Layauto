"""Independent, read-only W013 premerge evidence audit; no product imports."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
TASK = ROOT / 'docs/tasks/W013'
V = TASK / 'verification-r2'
HEAD = 'f31df3f3e6cd5df7ecef2e1f91977c3b68a9fac4'
FROZEN = '2a45938aba8e751183d472d660a1ab66a1063636'
DELIVERY = '63a0962f1b56655f234140822bffa8f56b7bb15f'
BASE = 'd6182fe6893c26490f9d58c6b808a5ce9910384b'
EXPECTED = '2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


checks = []


def check(name, condition, detail=None):
    checks.append({'check': name, 'passed': bool(condition), 'detail': detail})


manifest = load(V / 'source-manifest.json')
receipt = load(V / 'receipt.json')
files = manifest['files']
selected = ('layauto_v2', 'tests', 'pyproject.toml', 'README.md',
            'docs/tasks/W003/examples/records.json')
names = set(git('ls-files', '-z', '--', *selected).decode().split('\0'))
names.update(git('ls-files', '-z', '--others', '--exclude-standard', '--', *selected).decode().split('\0'))
names.discard('')
check('selected_paths_complete', names == set(files) and len(files) == 273, len(names))
check('source_identity_recomputed', digest(canonical(files)) == EXPECTED == manifest['source_id'] == receipt['source_id'])
check('disk_all_273_files', all((ROOT / p).is_file() and not (ROOT / p).is_symlink() and
                               digest((ROOT / p).read_bytes()) == h for p, h in files.items()))
for revision in (FROZEN, DELIVERY, HEAD):
    check('git_all_273:' + revision, all(digest(git('show', revision + ':' + p)) == h for p, h in files.items()))
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    members = {m.name: m for m in archive.getmembers() if m.isfile()}
    check('snapshot_all_273', set(members) == set(files) and all(digest(archive.extractfile(members[p]).read()) == h for p, h in files.items()))
check('receipt_snapshot_manifest_hash', digest((V / 'source-snapshot.tar.gz').read_bytes()) == receipt['source_snapshot_sha256'] and
      digest((V / 'source-manifest.json').read_bytes()) == receipt['source_manifest_sha256'])
runtime = {p.removeprefix('layauto_v2/'): h for p, h in files.items() if p.startswith('layauto_v2/')}
check('runtime_manifest', runtime == manifest['runtime_files'] and len(runtime) == 106)
evidence = load(V / 'evidence-manifest.json')
check('81_evidence_hashes', len(evidence) == 81 and all(digest((V / p).read_bytes()) == h for p, h in evidence.items()))
check('21_commands_exit_and_streams', len(receipt['commands']) == 21 and all(c['exit_code'] == 0 and
      all(digest((V / c[s]).read_bytes()) == c[s + '_sha256'] for s in ('stdout', 'stderr')) for c in receipt['commands']))
check('receipt_full_pass', receipt['status'] == 'passed' and receipt['actual_test_counts'] == {'310': 1731, '312': 1731})
collections = []
smokes = {}
setup = load(TASK / 'environment/receipt.json')
setup_manifest = load(TASK / 'environment/manifest.json')
check('prepared_environment_evidence_hashes', all(digest((TASK / 'environment' / p).read_bytes()) == h for p, h in setup_manifest.items()), len(setup_manifest))
for tag, prefix in (('310', '3.10.22'), ('312', '3.12.14')):
    collection = {line for line in (V / ('collection-' + tag + '.stdout.txt')).read_text().splitlines() if '::' in line}
    collections.append(collection)
    check('collection_1731:' + tag, len(collection) == 1731)
    check('raw_pytest_pass:' + tag, '1731 passed' in (V / ('pytest-' + tag + '.stdout.txt')).read_text())
    check('raw_typing_60:' + tag, 'Success: no issues found in 60 source files' in (V / ('typing-' + tag + '.stdout.txt')).read_text())
    env = load(V / ('environment-' + tag + '.stdout.txt'))
    check('environment_version_and_source:' + tag, env['version'].startswith(prefix) and
          env['source_package'] == '/workspace/work/w013-final-r2/source/layauto_v2/__init__.py', env)
    prepared = load(TASK / 'environment/evidence' / ('identity' + tag + '.stdout.txt'))
    ident = setup['identities'][tag]
    check('recorded_interpreter_and_all_dependency_versions:' + tag,
          env['packages'] == prepared['packages'] and env['executable'] == prepared['executable'] == ident['executable'] and
          env['version'] == prepared['version'] == ident['version'] and
          prepared['resolved_executable_sha256'] == ident['resolved_executable_sha256'] and
          all(env['packages'][{'yaml': 'PyYAML'}.get(k, k)] == v for k, v in ident['dependency_imports'].items()))
    smoke = load(V / ('installed-smoke-' + tag + '.stdout.txt'))
    smokes[tag] = smoke
    check('installed_smoke_three_public_roundtrips:' + tag, set(smoke['cases']) == {'normal-direct', 'normal-readback', 'extraction-mismatch'} and
          all(v['public_roundtrip_equal'] for v in smoke['cases'].values()) and
          smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'])
    check('installed_smoke_import_isolation:' + tag, '/clean-' + tag + '/lib/python' in smoke['package'] and '/site-packages/' in smoke['package'])
    check('installed_smoke_expected_geometry:' + tag, all(v['targets'] == 14 and v['evidence'] == 8 and v['components'] == 6 and
          v['associated_components'] == 4 and v['unknown_components'] == 2 and v['direct_area_nm2'] == 3170 and
          v['target_area_nm2'] == (34634 if k == 'extraction-mismatch' else 35090) for k, v in smoke['cases'].items()))
check('two_collections_identical', collections[0] == collections[1])
baseline = {line for line in (V / 'baseline-collection.txt').read_text().splitlines() if '::' in line}
check('retained_1656_new_75', len(baseline) == 1656 and baseline < collections[0] and len(collections[0] - baseline) == 75)
check('baseline_immutable', digest((V / 'baseline-collection.txt').read_bytes()) == receipt['baseline_collection_sha256'] and
      (V / 'baseline-collection.txt').read_bytes() == git('show', BASE + ':docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt'))
package_rows = {}
package_identity = load(V / 'package-identity.json')
for kind, row in package_identity.items():
    path = V / 'dist' / Path(row['path']).name
    if kind == 'wheel':
        with zipfile.ZipFile(path) as archive:
            actual = {p.removeprefix('layauto_v2/'): digest(archive.read(p)) for p in archive.namelist() if p.startswith('layauto_v2/') and not p.endswith('/')}
    else:
        with tarfile.open(path) as archive:
            actual = {m.name.split('/layauto_v2/', 1)[1]: digest(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile() and '/layauto_v2/' in m.name}
    check('package_106_runtime:' + kind, actual == runtime == row['runtime_files'] and digest(path.read_bytes()) == row['sha256'])
    package_rows[kind] = {'files': len(actual), 'sha256': digest(path.read_bytes())}
for tag, row in load(V / 'installation-identity.json').items():
    check('saved_installation_106:' + tag, row['runtime_files'] == runtime and row['isolated'] == 1 and
          row['package'] == smokes[tag]['package'] and row['artifact_sha256'] == package_rows['sdist' if tag == '310' else 'wheel']['sha256'])
tools = load(V / 'tool-identity.json')
for name, row in tools.items():
    path = ROOT / 'docs/tasks/W013/verification-tools' / Path(row['source']).name
    frozen_copy = V / path.name
    check('tool_original_frozen_receipt:' + name, digest(path.read_bytes()) == digest(frozen_copy.read_bytes()) == row['sha256'] == receipt['tool_hashes'][name])
check('protected_fixture_old_codecs_unchanged', not git('diff', '--name-only', BASE, HEAD, '--', 'tests/fixtures',
      'layauto_v2/normalization/local_connectivity_codec.py', 'layauto_v2/normalization/channel_identity_codec.py'))
old = load(TASK / 'verification/source-manifest.json')
proof = load(TASK / 'resource-r2-identity-adoption.json')
delta = {p: {'measured': old['files'].get(p), 'current': files.get(p)} for p in set(old['files']) | set(files) if old['files'].get(p) != files.get(p)}
check('resource_R2_exact_test_only_delta', delta == proof['changed_files'] and set(delta) == {'tests/contracts/test_w007_contracts.py'} and
      old['runtime_files'] == runtime and proof['source_id'] == EXPECTED and proof['measured_source_id'] == old['source_id'], delta)
clearance = load(TASK / 'resource-clearance-r2.json')
for label in ('delta_proof', 'delta_review'):
    check('resource_clearance_reference:' + label, digest((ROOT / clearance[label]).read_bytes()) == clearance[label + '_sha256'])
check('resource_review_blob', digest(git('show', clearance['review_commit'] + ':' + clearance['review_path'])) == clearance['review_sha256'])
suite = load(TASK / 'resource-attempt-04/suite.json')
probe = TASK / 'resource-attempt-04/resource-probe.py'
fixed_original = {row['target']: row for row in load(ROOT / 'docs/tasks/W012/A1/preflight.json')['inputs']}
restored = {row['uri']: row for row in load(TASK / 'fixed-mismatch-restoration.json')['inputs']}
check('fixed_35_origin_chain', len(fixed_original) == len(restored) == 35 and set(fixed_original) == set(restored) and
      all(row['sha256'] == restored[uri]['sha256'] == files[str(Path(row['origin']).relative_to(ROOT))] for uri, row in fixed_original.items()))
resource_rows = []
for command in suite['commands']:
    args = command['argv']; case = args[args.index('--case') + 1]
    rdir = TASK / 'resource-attempt-04'
    report = load(rdir / (case + '.json'))
    check('resource_source_all_273:' + case, report['files'] == old['files'] and digest(canonical(report['files'])) == report['source_id'] == suite['source_id'] == proof['measured_source_id'])
    check('resource_probe_and_logs:' + case, report['probe_sha256'] == command['probe_sha256'] == digest(probe.read_bytes()) == proof['resource_probe_sha256'] and command['returncode'] == 0 and
          all(digest((rdir / (case + '.' + s + '.txt')).read_bytes()) == command[s + '_sha256'] for s in ('stdout', 'stderr')))
    sources = report['capture_sources']
    checks_source = []
    for row in sources:
        actual_uri = str(Path(report['input_site']).parent / row['uri'])
        origin = Path(fixed_original[actual_uri]['origin']) if case == 'extraction-mismatch' else Path(actual_uri)
        data = origin.read_bytes()
        checks_source.append(digest(data) == row['sha256'] and len(data) == row['bytes'])
    check('resource_capture_31_source_bytes:' + case, len(sources) == len({row['uri'] for row in sources}) == 31 and all(checks_source))
    counts = {phase: sum(call['call'] == 'W010_public_decode' and call['phase'] == phase for call in report['observed_existing_calls'])
              for phase in ('W013_build', 'W013_result_encode', 'W013_result_decode')}
    check('resource_single_W010_no_W011_and_1_1_2:' + case, report['wire_input_field_occurrences'] == 1 and report['W011_result_instances'] == 0 and report['public_roundtrip_equal'] and
          list(counts.values()) == [1, 1, 2])
    resource_rows.append({'case': case, 'wire_bytes': report['wire_bytes'], 'compact_increment': report['wire_bytes'] - report['retained_W010_wire_bytes'], 'decode_calls': counts})
old_evidence = load(TASK / 'verification/evidence-manifest.json')
check('stopped_attempt_evidence_preserved', all(digest((TASK / 'verification' / p).read_bytes()) == h for p, h in old_evidence.items()))
check('stopped_attempt_not_passed', all(load(TASK / 'verification' / ('pytest-' + t + '.json'))['exit_code'] == -15 for t in ('310', '312')))
result = {'auditor': '/root/evidence_review', 'reviewed_base': BASE, 'reviewed_head': HEAD, 'source_id': EXPECTED,
          'status': 'passed' if all(c['passed'] for c in checks) else 'failed', 'check_count': len(checks),
          'failures': [c for c in checks if not c['passed']], 'checks': checks, 'packages': package_rows, 'resource': resource_rows,
          'not_run': ['product imports/captures/tests/typing/build/installation/smoke', 'performance measurement'],
          'limitations': ['Recorded installation/interpreter/dependency identities are adopted from immutable evidence; historical hosts and installation trees do not exist in this fresh environment.',
                          'Fixed external mismatch files are absent locally; their recorded 35-file provenance chain and 31 captured source hashes per case are checked against preserved source origin bytes.',
                          'Byte audit does not replace independent product correctness review or PM integration checks.']}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result['status'] == 'passed' else 1)
