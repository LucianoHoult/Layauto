"""Independent read-only W013 source/engineering evidence audit, no product imports.

Run without --complete while matrices run; --complete requires final receipts.
Only stdout is written by this tool. Caller saves each invocation separately.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / 'docs/tasks/W013/verification'
BASE = 'd6182fe6893c26490f9d58c6b808a5ce9910384b'
EXPECTED = '6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9'
checks = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(name, passed, detail=None):
    checks.append({'name': name, 'passed': bool(passed), 'detail': detail})


def read(path):
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def nodeids(data):
    return {line for line in data.decode().splitlines() if line.startswith('tests/') and '::' in line}


def source_id(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def command_evidence(name):
    row = read(OUT / (name + '.json'))
    check('command:' + name, row['exit_code'] == 0, row)
    for stream in ('stdout', 'stderr'):
        check('log:' + name + ':' + stream,
              sha((OUT / row[stream]).read_bytes()) == row[stream + '_sha256'])
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    selected = ('layauto_v2', 'tests', 'pyproject.toml', 'README.md', 'docs/tasks/W003/examples/records.json')
    names = set()
    for opts in ((), ('--others', '--exclude-standard')):
        names.update(p for p in git('ls-files', '-z', *opts, '--', *selected).decode().split('\0') if p)
    current = {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}
    manifest = read(OUT / 'source-manifest.json')
    expected = manifest['files']
    check('current_complete_source_selection', current == expected, {'current': len(current), 'frozen': len(expected)})
    check('source_identity', source_id(current) == manifest['source_id'] == EXPECTED, source_id(current))
    check('source_count', len(expected) == 273)
    with tarfile.open(OUT / 'source-snapshot.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        check('snapshot_only_unique_regular_files', all(m.isfile() for m in members) and len(members) == len({m.name for m in members}))
        snapshot = {m.name: sha(archive.extractfile(m).read()) for m in members if m.isfile()}
    check('snapshot_complete_bytes', snapshot == expected)
    snapshot_root = Path('/workspace/work/w013-final/source')
    actual_snapshot = {name: sha((snapshot_root / name).read_bytes()) for name in expected}
    check('executed_snapshot_bytes', actual_snapshot == expected)
    runtime = {name.removeprefix('layauto_v2/'): h for name, h in expected.items()
               if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
    check('runtime_selection', manifest['runtime_files'] == runtime, len(runtime))
    dev = read(ROOT / 'docs/tasks/W013/development/targeted-attempt-01.command.json')
    check('development_same_complete_source', dev['files'] == expected and dev['source_id_before'] == dev['source_id_after'] == EXPECTED)
    changes = git('diff', '--name-status', BASE, '--', *selected).decode().splitlines()
    check('only_expected_source_changes', len(changes) == 12 and all(
        line.split('\t')[-1].endswith(('net_regions.py', 'net_annotation.py', 'net_annotation_codec.py',
                                    'state/annotation.py', 'normalization/__init__.py', 'pyproject.toml',
                                    'test_w013_contracts.py', 'test_w013_composition.py', 'w013_cases.py'))
        for line in changes), changes)
    protected = [name for name in expected if name.startswith('tests/fixtures/') or
                 (name.startswith('layauto_v2/') and ('codec' in Path(name).name) and 'net_annotation' not in name)]
    protected_errors = [name for name in protected if sha(git('show', BASE + ':' + name)) != expected[name]]
    check('fixture_and_old_codec_bytes', not protected_errors, {'count': len(protected), 'mismatches': protected_errors})
    docs_changed = git('diff', '--name-only', BASE, '--', 'docs').decode().splitlines()
    check('old_reports_architecture_PM_pointers_unchanged', all(
        name.startswith('docs/tasks/W013/') or name == 'docs/tasks/W013-net-annotation-coverage.md'
        for name in docs_changed), docs_changed)
    task = 'docs/tasks/W013-net-annotation-coverage.md'
    current_task = (ROOT / task).read_text()
    original_task = git('show', BASE + ':' + task).decode()
    check('task_PM_requirements_unchanged', current_task.split('## 方案与决定')[0] == original_task.split('## 方案与决定')[0])
    check('task_PM_acceptance_unchanged', current_task.split('## PM 验收与交接')[1] == original_task.split('## PM 验收与交接')[1])
    baseline = (OUT / 'baseline-collection.txt').read_bytes()
    old_baseline = git('show', BASE + ':docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt')
    check('baseline_collection_original_bytes', baseline == old_baseline, sha(baseline))
    base_ids = nodeids(baseline)
    check('baseline_1656', len(base_ids) == 1656)
    collected = {}
    setup = read(ROOT / 'docs/tasks/W013/environment/receipt.json')
    for tag, version in (('310', '3.10.22'), ('312', '3.12.14')):
        environment = command_evidence('environment-' + tag)
        command_evidence('collection-' + tag)
        env = read(OUT / ('environment-' + tag + '.stdout.txt'))
        check('interpreter:' + tag, env['version'].startswith(version) and env['source_package'] == str(snapshot_root / 'layauto_v2/__init__.py'), env)
        ident = setup['identities'][tag]
        check('interpreter_binary:' + tag, sha(Path(ident['resolved_executable']).read_bytes()) == ident['resolved_executable_sha256'])
        check('environment_dependency_import_versions:' + tag, all(
            env['packages'][{'yaml': 'PyYAML'}.get(k, k)] == v for k, v in ident['dependency_imports'].items()))
        check('snapshot_command_cwd:' + tag, environment['cwd'] == str(snapshot_root))
        ids = nodeids((OUT / ('collection-' + tag + '.stdout.txt')).read_bytes())
        collected[tag] = ids
        scope = read(OUT / ('pytest-scope-' + tag + '.json'))
        added = ids - base_ids
        check('complete_test_scope:' + tag, len(ids) == 1731 and len(added) == 75 and base_ids <= ids and
              scope == {'baseline_test_count': 1656, 'current_test_count': 1731, 'added_test_count': 75, 'missing_baseline_ids': []},
              {'all': len(ids), 'added': len(added), 'missing': sorted(base_ids - ids),
               'added_files': sorted({name.split('::')[0] for name in added})})
    check('dual_collection_identical', collected['310'] == collected['312'])
    tools = read(OUT / 'tool-identity.json')
    tool_files = {'runner': 'prepare_final.py', 'source_identity': 'source_identity.py', 'smoke': 'installed_smoke.py'}
    for name, row in tools.items():
        check('engineering_tool:' + name, sha(Path(row['source']).read_bytes()) == row['sha256'] == sha((OUT / tool_files[name]).read_bytes()), row)
    clearance = read(OUT / 'resource-clearance.json')
    correction = read(ROOT / 'docs/tasks/W013/resource-clearance-reference-correction.json')
    check('clearance_preserved', sha(Path(clearance['source']).read_bytes()) == clearance['sha256'] == correction['original_clearance_sha256'])
    review_bytes = git('show', correction['correct_review_commit'] + ':' + correction['review_path'])
    check('corrected_review_content', sha(review_bytes) == correction['review_sha256'] == clearance['decision']['review_sha256'])
    old_bytes = git('show', correction['incorrect_review_commit'] + ':' + correction['review_path'])
    check('reference_correction_needed_and_not_content_change', sha(old_bytes) != correction['review_sha256'] and sha((ROOT / correction['review_path']).read_bytes()) == correction['review_sha256'])
    limits = read(OUT / 'resource-limits.json')
    check('two_workers_and_packages_after_matrices', limits['matrix_workers'] == 2 and limits['heavy_package_smokes_overlap_matrices'] is False and
          clearance['decision']['source_id'] == EXPECTED and clearance['decision']['parallel_matrices_safe'] is True)
    observed = {'receipt_exists': (OUT / 'receipt.json').exists(), 'failure_exists': (OUT / 'failure.json').exists(),
                'completed_command_receipts': sorted(path.stem for path in OUT.glob('*.json') if 'command' in read(path))}
    if args.complete:
        receipt = read(OUT / 'receipt.json')
        check('final_status', receipt['status'] == 'passed' and not (OUT / 'failure.json').exists(), receipt['actual_test_counts'])
        check('final_source_id_and_counts', receipt['source_id'] == EXPECTED and receipt['source_file_count'] == 273 and
              receipt['runtime_file_count'] == len(runtime) and receipt['actual_test_counts'] == {'310': 1731, '312': 1731})
        check('final_snapshot_and_manifest_identity', receipt['source_snapshot_sha256'] == sha((OUT / 'source-snapshot.tar.gz').read_bytes()) and
              receipt['source_manifest_sha256'] == sha((OUT / 'source-manifest.json').read_bytes()))
        check('final_freeze_rechecked', receipt['source_identity_rechecked_after_all_commands'] is True)
        for row in receipt['commands']:
            name = row['stdout'].removesuffix('.stdout.txt')
            saved = command_evidence(name)
            check('final_receipt_matches_command:' + name, row == saved)
        for tag in ('310', '312'):
            check('full_pytest:' + tag, '1731 passed' in (OUT / ('pytest-' + tag + '.stdout.txt')).read_text())
            check('full_typing:' + tag, 'Success: no issues found in 60 source files' in (OUT / ('typing-' + tag + '.stdout.txt')).read_text())
        pkg = read(OUT / 'package-identity.json')
        for kind, row in pkg.items():
            archive_path = Path(row['path'])
            if kind == 'wheel':
                with zipfile.ZipFile(archive_path) as archive:
                    actual = {name.removeprefix('layauto_v2/'): sha(archive.read(name)) for name in archive.namelist()
                              if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
            else:
                with tarfile.open(archive_path, 'r:gz') as archive:
                    actual = {'/'.join(Path(m.name).parts[2:]): sha(archive.extractfile(m).read()) for m in archive.getmembers()
                              if m.isfile() and len(Path(m.name).parts) > 2 and Path(m.name).parts[1] == 'layauto_v2'
                              and (m.name.endswith('.py') or m.name.endswith('/py.typed'))}
            check('package_runtime:' + kind, actual == row['runtime_files'] == runtime and sha(archive_path.read_bytes()) == row['sha256'])
        installs = read(OUT / 'installation-identity.json')
        for tag, row in installs.items():
            installed_root = Path(row['package']).resolve().parent
            actual = {str(path.relative_to(installed_root)): sha(path.read_bytes()) for path in installed_root.rglob('*')
                      if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}
            smoke = read(OUT / ('installed-smoke-' + tag + '.stdout.txt'))
            smoke_command = read(OUT / ('installed-smoke-' + tag + '.json'))
            check('installed_runtime:' + tag, actual == row['runtime_files'] == runtime and row['fresh_environment'] is True)
            check('source_external_isolated_smoke:' + tag, row['isolated'] == 1 and 'site-packages' in installed_root.parts and
                  not installed_root.is_relative_to(ROOT) and not Path(smoke_command['cwd']).is_relative_to(ROOT) and
                  not Path(smoke_command['cwd']).is_relative_to(snapshot_root) and '-I' in smoke_command['command'] and '-B' in smoke_command['command'])
            check('installed_combination:' + tag, smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'] and
                  set(smoke['cases']) == {'normal-direct', 'normal-readback', 'extraction-mismatch'} and
                  all(case['public_roundtrip_equal'] and case['direct_area_nm2'] == 3170 and case['targets'] == 14
                      for case in smoke['cases'].values()))
        evidence = read(OUT / 'evidence-manifest.json')
        check('all_final_evidence_hashes', all(sha((OUT / name).read_bytes()) == h for name, h in evidence.items()), len(evidence))
    result = {'auditor': '/root/input_contracts', 'utc': datetime.now(timezone.utc).isoformat(),
              'phase': 'complete' if args.complete else 'preflight-running-matrix', 'source_id': EXPECTED,
              'git_head': git('rev-parse', 'HEAD').decode().strip(), 'git_status': git('status', '--short').decode(),
              'checks': checks, 'failures': [row for row in checks if not row['passed']], 'observed_runner_state': observed,
              'status': 'passed' if args.complete and all(row['passed'] for row in checks) else
                        ('preflight_passed_final_pending' if all(row['passed'] for row in checks) else 'failed'),
              'not_run_by_auditor': ['pytest', 'mypy', 'product capture', 'build', 'installation', 'installed smoke'],
              'limits': ['This audit checks source/evidence identity; it does not replace independent product/contract review or PM acceptance.']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result['failures'] else 0)


if __name__ == '__main__':
    main()
