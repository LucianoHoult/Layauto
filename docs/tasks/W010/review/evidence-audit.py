"""Independent W010 engineering evidence audit; reads existing artifacts only.

Run from the repository root with Python 3.10+ and -B.  This does not rerun the
full regression, typing, build, installation, or original installed smoke.
"""
from __future__ import annotations

import hashlib
import io
import json
import ast
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from urllib.parse import unquote, urlparse
import zipfile


ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/tasks/W010/review'
EVIDENCE = ROOT / 'docs/tasks/W010/verification'
HEAD = '0f5029df935bc0acd106aad1bc2be81304d4f442'
BASE = '9758a157115cc22d91ce095ac2002209b9f210d3'
EXPECTED = {
    'source-manifest.json': 'cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889',
    'source-snapshot.tar.gz': '493d36ebeb4bd5d43f8bbb06139b27e3be7997dad12e913c9ca36c362ba843d1',
    'receipt.json': '856f78919b92098632fda3ca988ebcc6f4b739c817794fce691035e028562b9a',
    'evidence-manifest.json': 'ebf1cf092ba9168ae37dfd622aa47cae39ce812786e5c9e84bd485064d88593c',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def git_archive(revision: str, paths: list[str]) -> dict[str, str]:
    data = subprocess.check_output(['git', 'archive', revision, '--', *paths], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {member.name: sha(archive.extractfile(member).read())
                for member in archive.getmembers() if member.isfile()}


def runtime_at(base: Path) -> dict[str, str]:
    return {str(path.relative_to(base)): sha(path.read_bytes())
            for path in sorted(base.rglob('*'))
            if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}


def main() -> None:
    checks = []

    def check(name: str, condition: bool, **details) -> None:
        checks.append({'name': name, 'passed': bool(condition), **details})

    actual_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    check('head', actual_head == HEAD, actual=actual_head, expected=HEAD)
    for name, expected in EXPECTED.items():
        check('frozen_sha:' + name, sha((EVIDENCE / name).read_bytes()) == expected,
              actual=sha((EVIDENCE / name).read_bytes()), expected=expected)

    manifest = read_json(EVIDENCE / 'source-manifest.json')
    files, runtime = manifest['files'], manifest['runtime_files']
    check('manifest_head_and_count', manifest['git_head'] == HEAD and len(files) == 252 and len(runtime) == 94)
    selected = ['layauto_v2', 'tests', 'pyproject.toml', 'README.md', 'docs/tasks/W003/examples/records.json']
    git_files = git_archive(HEAD, selected)
    check('all_source_bytes_match_frozen_git', git_files == files, count=len(git_files))
    check('all_source_bytes_match_current_checkout', all(sha((ROOT / p).read_bytes()) == h for p, h in files.items()))
    snapshot_source = Path('/workspace/work/w010-final-0f5029d/source')
    check('all_source_bytes_match_actual_test_source', all(sha((snapshot_source / p).read_bytes()) == h for p, h in files.items()))
    with tarfile.open(EVIDENCE / 'source-snapshot.tar.gz') as archive:
        members = archive.getmembers()
        archive_files = {m.name: sha(archive.extractfile(m).read()) for m in members if m.isfile()}
        check('snapshot_exact_members_and_bytes', len(members) == len(files) and len({m.name for m in members}) == len(members)
              and archive_files == files, member_count=len(members))
    check('runtime_manifest_matches_current_source', runtime_at(ROOT / 'layauto_v2') == runtime)

    evidence_manifest = read_json(EVIDENCE / 'evidence-manifest.json')
    physical_evidence = {str(p.relative_to(EVIDENCE)): sha(p.read_bytes()) for p in EVIDENCE.rglob('*')
                         if p.is_file() and p.name != 'evidence-manifest.json'}
    check('all_evidence_files_exact_set_and_bytes', physical_evidence == evidence_manifest and len(evidence_manifest) == 78,
          manifest_entries=len(evidence_manifest), total_files_including_manifest=len(physical_evidence) + 1)
    receipt = read_json(EVIDENCE / 'receipt.json')
    check('receipt_passed_21', receipt['status'] == 'passed' and len(receipt['commands']) == 21
          and all(row['exit_code'] == 0 for row in receipt['commands']))
    check('runner_and_smoke_identity', sha((EVIDENCE / 'prepare_final.py').read_bytes()) == receipt['runner_sha256']
          and sha((EVIDENCE / 'installed_smoke.py').read_bytes()) == receipt['smoke_sha256'])
    for row in receipt['commands']:
        name = row['stdout'].removesuffix('.stdout.txt')
        check('command_receipt_and_outputs:' + name,
              read_json(EVIDENCE / (name + '.json')) == row
              and sha((EVIDENCE / row['stdout']).read_bytes()) == row['stdout_sha256']
              and sha((EVIDENCE / row['stderr']).read_bytes()) == row['stderr_sha256'],
              command=row['command'], cwd=row['cwd'], elapsed_seconds=row['elapsed_seconds'])

    baseline = {line for line in (EVIDENCE / 'baseline-collection.txt').read_text().splitlines()
                if line.startswith('tests/') and '::' in line}
    preflight = ROOT / 'docs/tasks/W010/preflight'
    baseline_manifest = read_json(preflight / 'baseline-corrected-manifest.json')
    check('baseline_snapshot_matches_base_git', baseline_manifest['git_head'] == BASE
          and git_archive(BASE, selected) == baseline_manifest['files'])
    check('retained_collection_same_as_preflight', sha((EVIDENCE / 'baseline-collection.txt').read_bytes())
          == sha((preflight / 'baseline-collection310.txt').read_bytes()) == receipt['baseline_collection_sha256'])
    collections = {}
    for tag, version in [('310', '3.10.22'), ('312', '3.12.14')]:
        text = (EVIDENCE / ('collection-' + tag + '.stdout.txt')).read_text()
        rows = [line for line in text.splitlines() if line.startswith('tests/') and '::' in line]
        ids = set(rows)
        collections[tag] = ids
        check('baseline_retention_and_final_ids:' + tag, len(baseline) == 1149 and len(rows) == len(ids) == 1465
              and baseline <= ids and len(ids - baseline) == 316,
              baseline_count=len(baseline), final_count=len(ids), added_count=len(ids - baseline),
              missing_baseline_ids=sorted(baseline - ids))
        pytest = (EVIDENCE / ('pytest-' + tag + '.stdout.txt')).read_text()
        check('full_pytest_summary:' + tag, len(re.findall(r'^1465 passed in ', pytest, re.M)) == 1
              and not re.search(r'\b(?:failed|skipped|deselected|error)\b', pytest))
        check('strict_typing_summary:' + tag, (EVIDENCE / ('typing-' + tag + '.stdout.txt')).read_text().strip()
              == 'Success: no issues found in 48 source files')
        env = read_json(EVIDENCE / ('environment-' + tag + '.stdout.txt'))
        check('test_environment:' + tag, env['version'].startswith(version)
              and Path(env['source_package']) == snapshot_source / 'layauto_v2/__init__.py')
    check('same_ids_both_interpreters', collections['310'] == collections['312'])

    packages = read_json(EVIDENCE / 'package-identity.json')
    package_files = {}
    for kind, row in packages.items():
        path = Path(row['path'])
        check('artifact_bytes:' + kind, sha(path.read_bytes()) == row['sha256'])
        if kind == 'wheel':
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                actual = {name.removeprefix('layauto_v2/'): sha(archive.read(name)) for name in names
                          if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
                check('wheel_no_duplicate_members', len(names) == len(set(names)))
                metadata = archive.read('layauto-0.2.0.dist-info/METADATA').decode()
                check('package_minimum_python', 'Requires-Python: >=3.10' in metadata)
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
                actual = {}
                for m in archive.getmembers():
                    parts = Path(m.name).parts
                    if m.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                        actual['/'.join(parts[2:])] = sha(archive.extractfile(m).read())
                check('sdist_no_duplicate_members', len(names) == len(set(names)))
        package_files[kind] = actual
        check('artifact_all_runtime_bytes:' + kind, actual == runtime == row['runtime_files'], count=len(actual))

    installations = read_json(EVIDENCE / 'installation-identity.json')
    fresh_commands = []
    for tag, row in installations.items():
        package = Path(row['package']).parent
        clean = Path('/workspace/work/w010-final-0f5029d/clean-' + tag)
        check('actual_install_all_runtime_bytes:' + tag, runtime_at(package) == runtime == row['runtime_files'], count=len(runtime))
        check('actual_install_location:' + tag, package.is_relative_to(clean) and 'site-packages' in package.parts
              and row['isolated'] == 1 and row['fresh_environment'] is True)
        report = read_json(EVIDENCE / ('install-' + tag + '-report.json'))
        entries = [x for x in report['install'] if x['metadata']['name'] == 'layauto']
        direct_url = read_json(package.parent / 'layauto-0.2.0.dist-info/direct_url.json')
        entry = entries[0]
        artifact = Path(row['artifact'])
        expected_hash = sha(artifact.read_bytes())
        check('install_report_actual_artifact:' + tag, len(entries) == 1 and entry['requested']
              and Path(unquote(urlparse(entry['download_info']['url']).path)) == artifact
              and entry['download_info']['archive_info']['hash'] == 'sha256=' + expected_hash
              and row['artifact_sha256'] == expected_hash
              and direct_url['url'] == entry['download_info']['url'],
              direct_url_archive_info=direct_url['archive_info'],
              provenance_basis='pip install report artifact SHA-256 plus actual artifact and complete installed runtime comparison; 3.10 pip leaves direct_url archive_info empty')
        config = (clean / 'pyvenv.cfg').read_text()
        check('install_isolated_from_system_site_packages:' + tag, 'include-system-site-packages = false' in config)
        smoke_row = read_json(EVIDENCE / ('installed-smoke-' + tag + '.json'))
        smoke = read_json(EVIDENCE / ('installed-smoke-' + tag + '.stdout.txt'))
        check('installed_smoke_scope_and_results:' + tag, smoke_row['command'][1:3] == ['-I', '-B']
              and not Path(smoke_row['cwd']).is_relative_to(ROOT)
              and not Path(smoke_row['cwd']).is_relative_to(snapshot_source)
              and Path(smoke['package']).parent == package
              and smoke['attempt_unchanged'] is True
              and all((smoke[x]['nodes'], smoke[x]['edges'], smoke[x]['components'], smoke[x]['audits'], smoke[x]['local_enclosure_status'])
                      == (14, 8, 6, 16, 'pass') for x in ['direct', 'readback']))
        command = [str(clean / 'bin/python'), '-I', '-B', '-c',
                   'import layauto_v2,sys,json,importlib.metadata as m; print(json.dumps({"package":layauto_v2.__file__,"executable":sys.executable,"version":sys.version,"isolated":sys.flags.isolated,"distribution_version":m.version("layauto")}))']
        done = subprocess.run(command, cwd='/workspace', capture_output=True, text=True)
        fresh_commands.append({'command': command, 'cwd': '/workspace', 'exit_code': done.returncode,
                               'stdout': done.stdout, 'stderr': done.stderr})
        check('reviewer_actual_installed_import:' + tag, done.returncode == 0
              and Path(json.loads(done.stdout)['package']).parent == package)
    performance = read_json(ROOT / 'docs/tasks/W010/performance.json')
    check('performance_probe_bytes_and_runtime_identity', performance['probe_sha256']
          == sha((ROOT / 'docs/tasks/W010/performance_probe.py').read_bytes())
          and all(sha((ROOT / p).read_bytes()) == h for p, h in performance['source_files_sha256'].items()))
    scope = read_json(ROOT / 'docs/tasks/W010/scope-check.json')
    protected_diff = subprocess.check_output(['git', 'diff', '--name-only', BASE, HEAD, '--', *scope['protected_paths']], cwd=ROOT, text=True)
    check('independent_protected_paths_diff', scope['base'] == BASE and scope['product_head'] == HEAD
          and len(scope['protected_paths']) == 16 and not protected_diff.strip(), paths=scope['protected_paths'])
    old_tests = [p for p in baseline_manifest['files'] if p.startswith('tests/') and p.endswith('.py')]
    changed_old = []
    lost_test_functions = []
    for name in old_tests:
        before = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
        after = (ROOT / name).read_bytes()
        if before != after:
            changed_old.append(name)
        old_names = {x.name for x in ast.walk(ast.parse(before)) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name.startswith('test_')}
        new_names = {x.name for x in ast.walk(ast.parse(after)) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name.startswith('test_')}
        lost_test_functions.extend(name + ':' + x for x in sorted(old_names - new_names))
    check('old_test_sources_and_names_preserved', changed_old == ['tests/contracts/test_w007_contracts.py']
          and not lost_test_functions, old_python_file_count=len(old_tests),
          changed_old_files=changed_old, lost_test_functions=lost_test_functions)

    result = {'schema': 'w010-independent-engineering-audit/1', 'actor': '/root/code_review/evidence_review',
              'base': BASE, 'head': HEAD, 'command': [sys.executable, '-B', str(Path(__file__).resolve())],
              'cwd': str(Path.cwd()), 'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
              'status': 'passed' if all(row['passed'] for row in checks) else 'failed',
              'check_count': len(checks), 'checks': checks, 'actual_reviewer_commands': fresh_commands,
              'adopted_execution': 'Original dual 1465 tests, dual strict typing, new build/installs and dual installed composition smoke, after independent raw-output/source/package/actual-install checks.',
              'not_reexecuted': ['Full regression', 'strict typing', 'build', 'installation', 'original installed composition smoke'],
              'limitations': 'Evidence authentication and actual installed import checks; does not establish production performance, PDK/EDA or full Stage2/M1 admission.'}
    (OUT / 'evidence-audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': result['status'], 'check_count': len(checks),
                      'failures': [row for row in checks if not row['passed']]}, indent=2))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
