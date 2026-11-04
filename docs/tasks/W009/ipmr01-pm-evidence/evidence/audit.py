"""PM content/receipt audit; does not rerun tests, build or installation."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path('/workspace/Layauto')
V = ROOT / 'docs/tasks/W009/ipmr01-verification'
HEAD = '6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534'
PRODUCT = '73e38df8f932bbb5bd9caf074b442ad2f5c286e9'
BASE = 'cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda name: json.loads((V / name).read_text())
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)

assert git('rev-parse', 'HEAD').decode().strip() == HEAD
subprocess.run(['git', 'merge-base', '--is-ancestor', PRODUCT, HEAD], cwd=ROOT, check=True)
m = read('source-manifest.json')
r = read('receipt.json')
assert m['git_head'] == PRODUCT and m['base_sha'] == BASE
assert len(m['files']) == 245 and len(m['runtime_files']) == 90
for name, digest in m['files'].items():
    data = (ROOT / name).read_bytes()
    assert sha(data) == digest and data == git('show', PRODUCT + ':' + name), name
runtime = {str(p.relative_to(ROOT / 'layauto_v2')): sha(p.read_bytes())
           for p in (ROOT / 'layauto_v2').rglob('*')
           if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}
assert runtime == m['runtime_files']
tracked = git('ls-files', 'layauto_v2', 'tests/unit', 'tests/contracts', 'README.md', 'pyproject.toml').decode().splitlines()
relevant = {n for n in tracked if n.endswith(('.py', '/py.typed')) or n in ('README.md', 'pyproject.toml')}
assert relevant <= set(m['files']), relevant - set(m['files'])
assert sha((V / 'source-manifest.json').read_bytes()) == r['source_manifest_sha256']
assert sha((V / 'source-snapshot.tar.gz').read_bytes()) == r['source_snapshot_sha256']
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    members = archive.getmembers()
    assert all(p.isfile() for p in members) and len({p.name for p in members}) == len(members)
    assert {p.name: sha(archive.extractfile(p).read()) for p in members} == m['files']

assert r['head'] == r['finished_head'] == PRODUCT
assert r['status'] == 'passed' and r['errors'] == []
assert r['actual_test_counts'] == {'310': 988, '312': 1149}
assert r['typing_source_counts'] == {'310': 44, '312': 44}
assert r['python310_complete_v2_rerun'] is False
assert r['test_scopes'] == {'310': {'complete_v2': False, 'paths': ['tests/contracts', 'tests/unit/test_w006_publication.py']},
                            '312': {'complete_v2': True, 'paths': ['tests/contracts', 'tests/unit']}}
assert r['runner_sha256'] == sha((V / 'runner.py').read_bytes())
assert r['smoke_script_sha256'] == sha((V / 'installed_smoke.py').read_bytes())
resume = r['resumption']
assert resume == read('resumption.json') and resume['status'] == 'passed'
assert resume['product_sha'] == PRODUCT and resume['source_manifest_sha256'] == r['source_manifest_sha256']
assert resume['script_sha256'] == sha((V / 'resume_verification.py').read_bytes())
archive = V / 'environment-disconnect-20261103'
assert json.loads((archive / 'interruption.json').read_text()) == dict(resume, status='resuming')
for name, digest in resume['archived_partial_outputs'].items():
    assert sha((archive / name).read_bytes()) == digest, name
adopted = set(resume['adopted_completed_command_receipts'])
assert len(adopted) == 16 and len(resume['archived_partial_outputs']) == 14
seen, command_checks = set(), []
for command in r['commands']:
    assert command['exit_code'] == 0 and command['head'] == command['finished_head'] == PRODUCT
    assert command['source_manifest_sha256'] == r['source_manifest_sha256']
    name = command['outputs']['stdout']['path'].removesuffix('.stdout.txt') + '.json'
    assert name not in seen and read(name) == command
    seen.add(name)
    assert (command['started_utc'] < resume['resumed_utc']) if name in adopted else (command['started_utc'] >= resume['resumed_utc'])
    for stream in command['outputs'].values():
        assert sha((V / stream['path']).read_bytes()) == stream['sha256']
    command_checks.append(name)
assert len(seen) == 24 and seen - adopted == {p + '-' + tag + '.json' for tag in ('310', '312') for p in ('environment', 'pytest', 'typing', 'pip-check')}
for tag, count in r['actual_test_counts'].items():
    assert re.findall(r'(\d+) passed(?:,|\s+in)', (V / ('pytest-' + tag + '.stdout.txt')).read_text()) == [str(count)]
    assert 'Success: no issues found in 44 source files' in (V / ('typing-' + tag + '.stdout.txt')).read_text()

packages = read('package-identity.json')
assert packages['source_manifest_sha256'] == r['source_manifest_sha256']
for kind in ('wheel', 'sdist'):
    info = packages[kind]
    path = V / 'dist' / Path(info['path']).name
    assert sha(path.read_bytes()) == info['sha256']
    if kind == 'wheel':
        with zipfile.ZipFile(path) as a:
            values = {n[len('layauto_v2/'):]: sha(a.read(n)) for n in a.namelist() if n.startswith('layauto_v2/') and n.endswith(('.py', '/py.typed'))}
    else:
        with tarfile.open(path) as a:
            values = {p.name.split('/layauto_v2/', 1)[1]: sha(a.extractfile(p).read()) for p in a.getmembers() if p.isfile() and '/layauto_v2/' in p.name and p.name.endswith(('.py', '/py.typed'))}
    assert values == runtime == info['runtime_files']
installs = read('installation-identity.json')
installation_checks = {}
for tag, info in installs.items():
    assert info['runtime_files'] == runtime
    assert info['source_sha256'] == packages['wheel' if tag == '312' else 'sdist']['sha256']
    report = V / info['pip_report']
    assert sha(report.read_bytes()) == info['pip_report_sha256']
    package = next(x for x in json.loads(report.read_text())['install'] if x['metadata']['name'].lower() == 'layauto')
    assert package['download_info']['url'] == Path(info['source_artifact']).as_uri()
    meta = package['download_info']['archive_info']
    digest = meta.get('hashes', {}).get('sha256') or meta.get('hash', '').removeprefix('sha256=')
    assert digest == info['source_sha256']
    smoke = read('installed-smoke-' + tag + '.json')
    assert '-I' in smoke['command'] and '-B' in smoke['command'] and not Path(smoke['cwd']).is_relative_to(ROOT)
    assert 'site-packages' in Path(info['installed_package']).parts and not Path(info['installed_package']).is_relative_to(ROOT)
    installation_checks[tag] = {'record_runtime_and_report_match': True, 'original_install_tree_present': Path(info['installed_package']).exists(), 'source_artifact_sha256': info['source_sha256']}

review = V / 'review'
review_receipts = ('exception-matrix.json', 'receipt-controls.json', 'independent-probe.json', 'engineering-command.json')
for name in review_receipts:
    value = json.loads((review / name).read_text())
    assert value['head'] == PRODUCT and value['returncode'] == 0
    for stream in value['outputs'].values():
        assert sha((review / stream['path']).read_bytes()) == stream['sha256']
matrix = json.loads((review / 'exception-matrix.stdout.txt').read_text())
assert matrix['case_count'] == matrix['same_object_count'] == 99 and matrix['identity_failures'] == []
for name, digest in matrix['sources'].items():
    assert m['files'][name] == digest
captured = json.loads((review / 'captured/result.json').read_text())
assert captured['head'] == PRODUCT and captured['mutation_cases'] == 1184 and captured['unexpected_exceptions'] == []
captured_identity = read('review/captured/identity.json')
assert captured_identity['head'] == PRODUCT and captured_identity['all_source_files_match_head']
for name, digest in captured_identity['source_files'].items():
    assert m['files'][name] == digest
for name, digest in captured_identity['outputs'].items():
    assert sha((review / 'captured' / name).read_bytes()) == digest
assert sha((ROOT / captured_identity['witness_script']['path']).read_bytes()) == captured_identity['witness_script']['sha256']
assert '8 passed' in (review / 'captured/snapshot-tests.stdout.txt').read_text()
snapshot = read('review/collection-snapshot-after.json')
assert snapshot['head'] == PRODUCT and all(not x['retained_invalid_none'] for x in snapshot['observations'])
controls = json.loads((review / 'receipt-controls.stdout.txt').read_text())
assert controls['case_count'] == 33 and controls['all_explicit_value_errors']
compat = read('compatibility.json')
assert compat['status'] == 'passed' and compat['baseline_sha'] == BASE and compat['final_sha'] == PRODUCT
for name, digest in compat['outputs'].items():
    assert sha((V / name).read_bytes()) == digest
assert read('review/compatibility-audit.json')['wire_and_digest_identical'] == compat['wire_and_digest_identical']
engineering = read('review/engineering-audit.json')
assert engineering['head'] == PRODUCT and engineering['source_manifest_sha256'] == r['source_manifest_sha256']
assert engineering['command_count'] == 24 and engineering['test_counts'] == r['actual_test_counts']
for tag in ('310', '312'):
    observed = read('review/actual-installed-' + tag + '.json')
    assert observed['runtime'] == runtime and 'site-packages' in Path(observed['package']).parts
    assert observed['direct_url']['url'] == Path(installs[tag]['source_artifact']).as_uri()
    assert engineering['actual_installations'][tag]['source_artifact_sha256'] == installs[tag]['source_sha256']
baseline, final = read('compatibility-baseline.stdout.json'), read('compatibility-final.stdout.json')
assert baseline['source_uris'] == final['source_uris'] and baseline['fixture'] == final['fixture']
assert baseline['wire'] == final['wire'] == compat['wire_and_digest_identical']
assert baseline['semantic_digest'] == final['semantic_digest'] == compat['semantic_digest']
for result, commit in ((baseline, BASE), (final, PRODUCT)):
    assert len(result['runtime_files']) == 90
    for name, digest in result['runtime_files'].items():
        assert sha(git('show', commit + ':layauto_v2/' + name)) == digest
recovery = read('review/recovery-identity.json')
assert recovery['all245_review_files_match_manifest_and_git'] and recovery['final_probe_outputs_match_pre_disconnect_receipts']
assert recovery['source_manifest_sha256'] == r['source_manifest_sha256']
assert recovery['captured_identity_sha256'] == sha((review / 'captured/identity.json').read_bytes())
assert recovery['captured_result_sha256'] == sha((review / 'captured/result.json').read_bytes())
for outputs in recovery['final_probe_outputs_match_pre_disconnect_receipts'].values():
    for stream in outputs.values():
        assert sha((review / stream['path']).read_bytes()) == stream['sha256']

protected = ['tests/fixtures', 'legacy_mvp', 'docs/architecture.md', 'docs/current-work.md']
protected += ['docs/tasks/W00' + n + '*' for n in ('3', '4', '5', '6', '7', '8')]
protected += ['docs/tasks/W009/' + n for n in ('verification', 'independent-premerge-review', 'independent-premerge-review.md', 'pm-evidence', 'pm-receipt.json', 'pm-receipt.md', 'ipmr01-pm-confirmation', 'code-review.md', 'plan.md', 'plan-review.md')]
changed = git('diff', '--name-only', BASE, HEAD, '--', *protected).decode().splitlines()
assert changed == [], changed

print(json.dumps({'status': 'passed', 'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'head': HEAD, 'product': PRODUCT, 'base': BASE, 'python': sys.version,
                  'source_manifest_sha256': r['source_manifest_sha256'], 'source_files': 245, 'runtime_files': 90,
                  'source_snapshot_sha256': r['source_snapshot_sha256'], 'source_archive_matches_manifest': True,
                  'commands_checked': command_checks, 'command_count': 24, 'adopted_command_count': 16,
                  'rerun_command_count': 8, 'archived_partial_outputs': 14, 'test_counts': r['actual_test_counts'],
                  'python310_complete_v2_rerun': False, 'packages': {k: packages[k]['sha256'] for k in ('wheel', 'sdist')},
                  'installation_records': installation_checks, 'review_exception_matrix': '99/99; no identity failures',
                  'captured_variants': 1184, 'malformed_receipt_controls': 33, 'compatibility_records_match': True,
                  'protected_changed_paths': changed, 'must_fix': 0,
                  'limitations': ['This audit rehashed current source/archive/package bytes and archived receipts; no pytest, typing, build, install or dynamic smoke was rerun.',
                                  'Original installation trees are absent on this host; historical actual-tree verification is adopted from the version-bound independent review.',
                                  'Historical command execution is supported by original receipts/review; byte consistency alone is not a new observation of those executions.']}, ensure_ascii=False, indent=2))
