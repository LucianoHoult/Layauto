"""W010 PM read-only delivery content audit, without historical execution replay."""
from pathlib import Path
import ast
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
import tarfile
from urllib.parse import unquote, urlparse
import zipfile

ROOT = Path('/workspace/Layauto')
TASK = ROOT / 'docs/tasks/W010'
V = TASK / 'verification'
REVIEW = TASK / 'review'
HEAD = 'ca39aedcb71fda02f77ffda1eb5d5dddc598226e'
PRODUCT = '0f5029df935bc0acd106aad1bc2be81304d4f442'
BASE = '9758a157115cc22d91ce095ac2002209b9f210d3'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_text())

def git_archive(revision, paths):
    data = subprocess.check_output(['git', 'archive', revision, '--', *paths], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}

def artifacts(base, rows):
    for name, row in rows.items():
        data = (base / name).read_bytes()
        assert sha(data) == row['sha256'], name
        size = row.get('bytes', row.get('size_bytes'))
        if size is not None:
            assert len(data) == size, name

actual_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert actual_head == HEAD
delivery = read(TASK / 'delivery.json')
assert delivery['tested_reviewed_product_commit'] == PRODUCT
assert delivery['status'] == 'execution_reviewed_pending_pm'
manifest = read(V / 'source-manifest.json')
receipt = read(V / 'receipt.json')
files, runtime = manifest['files'], manifest['runtime_files']
assert manifest['git_head'] == PRODUCT and len(files) == 252 and len(runtime) == 94
assert sha((V / 'source-manifest.json').read_bytes()) == delivery['source_manifest_sha256'] == receipt['source_manifest_sha256']
selected = ['layauto_v2', 'tests', 'pyproject.toml', 'README.md', 'docs/tasks/W003/examples/records.json']
assert git_archive(PRODUCT, selected) == files
assert git_archive(HEAD, selected) == files
for name, digest in files.items():
    assert sha((ROOT / name).read_bytes()) == digest, name
actual_runtime = {str(p.relative_to(ROOT / 'layauto_v2')): sha(p.read_bytes())
                  for p in (ROOT / 'layauto_v2').rglob('*') if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}
assert actual_runtime == runtime
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(files) == len({m.name for m in members})
    assert all(m.isfile() for m in members)
    assert {m.name: sha(archive.extractfile(m).read()) for m in members} == files
assert sha((V / 'source-snapshot.tar.gz').read_bytes()) == delivery['source_snapshot_sha256'] == receipt['source_snapshot_sha256']

evidence_manifest = read(V / 'evidence-manifest.json')
physical = {str(p.relative_to(V)): sha(p.read_bytes()) for p in V.rglob('*')
            if p.is_file() and p.name != 'evidence-manifest.json'}
assert physical == evidence_manifest and len(evidence_manifest) == 78
assert sha((V / 'evidence-manifest.json').read_bytes()) == delivery['engineering_evidence_manifest_sha256']
assert sha((V / 'receipt.json').read_bytes()) == delivery['engineering_receipt_sha256']
assert receipt['status'] == 'passed' and receipt['source_identity_rechecked_after_all_commands'] is True
assert len(receipt['commands']) == 21
assert sha((V / 'prepare_final.py').read_bytes()) == receipt['runner_sha256']
assert sha((V / 'installed_smoke.py').read_bytes()) == receipt['smoke_sha256']
commands = []
for row in receipt['commands']:
    assert row['exit_code'] == 0
    stem = row['stdout'].removesuffix('.stdout.txt')
    assert read(V / (stem + '.json')) == row
    for stream in ('stdout', 'stderr'):
        assert sha((V / row[stream]).read_bytes()) == row[stream + '_sha256']
    commands.append({'name': stem, 'exit_code': row['exit_code'], 'cwd': row['cwd'],
                     'elapsed_seconds': row['elapsed_seconds'],
                     'stdout_sha256': row['stdout_sha256'], 'stderr_sha256': row['stderr_sha256']})

baseline_manifest = read(TASK / 'preflight/baseline-corrected-manifest.json')
assert baseline_manifest['git_head'] == BASE and git_archive(BASE, selected) == baseline_manifest['files']
baseline_data = (V / 'baseline-collection.txt').read_bytes()
assert sha(baseline_data) == receipt['baseline_collection_sha256'] == sha((TASK / 'preflight/baseline-collection310.txt').read_bytes())
baseline_ids = {x for x in baseline_data.decode().splitlines() if x.startswith('tests/') and '::' in x}
assert len(baseline_ids) == 1149
collections = {}
for tag, version in [('310', '3.10.22'), ('312', '3.12.14')]:
    rows = [x for x in (V / ('collection-' + tag + '.stdout.txt')).read_text().splitlines()
            if x.startswith('tests/') and '::' in x]
    ids = set(rows)
    assert len(rows) == len(ids) == 1465 and baseline_ids <= ids and len(ids - baseline_ids) == 316
    collections[tag] = ids
    pytest = (V / ('pytest-' + tag + '.stdout.txt')).read_text()
    assert len(re.findall(r'^1465 passed in ', pytest, re.M)) == 1
    assert not re.search(r'\b(?:failed|skipped|deselected|error)\b', pytest)
    assert (V / ('typing-' + tag + '.stdout.txt')).read_text().strip() == 'Success: no issues found in 48 source files'
    assert read(V / ('environment-' + tag + '.stdout.txt'))['version'].startswith(version)
assert collections['310'] == collections['312']

packages = read(V / 'package-identity.json')
for kind, row in packages.items():
    path = V / 'dist' / Path(row['path']).name
    assert sha(path.read_bytes()) == row['sha256']
    if kind == 'wheel':
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert len(names) == len(set(names))
            actual = {name.removeprefix('layauto_v2/'): sha(archive.read(name)) for name in names
                      if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
            assert 'Requires-Python: >=3.10' in archive.read('layauto-0.2.0.dist-info/METADATA').decode()
    else:
        with tarfile.open(path) as archive:
            names = archive.getnames()
            assert len(names) == len(set(names))
            actual = {}
            for m in archive.getmembers():
                parts = Path(m.name).parts
                if m.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                    actual['/'.join(parts[2:])] = sha(archive.extractfile(m).read())
    assert actual == runtime == row['runtime_files']

install_observations = {}
for tag, row in read(V / 'installation-identity.json').items():
    assert row['runtime_files'] == runtime and row['isolated'] == 1 and row['fresh_environment'] is True
    artifact = Path(row['artifact'])
    actual_artifact = V / 'dist' / artifact.name
    assert sha(actual_artifact.read_bytes()) == row['artifact_sha256']
    report = read(V / ('install-' + tag + '-report.json'))
    entry = next(x for x in report['install'] if x['metadata']['name'] == 'layauto')
    assert Path(unquote(urlparse(entry['download_info']['url']).path)) == artifact
    assert entry['download_info']['archive_info']['hash'] == 'sha256=' + row['artifact_sha256']
    smoke_row = read(V / ('installed-smoke-' + tag + '.json'))
    smoke = read(V / ('installed-smoke-' + tag + '.stdout.txt'))
    assert smoke_row['command'][1:3] == ['-I', '-B']
    assert not Path(smoke_row['cwd']).is_relative_to(ROOT)
    assert smoke['package'] == row['package'] and 'site-packages' in Path(row['package']).parts
    assert smoke['attempt_unchanged'] is True
    assert all((smoke[x]['nodes'], smoke[x]['edges'], smoke[x]['components'], smoke[x]['audits'], smoke[x]['local_enclosure_status'])
               == (14, 8, 6, 16, 'pass') for x in ('direct', 'readback'))
    install_observations[tag] = {'historical_install_tree_present': Path(row['package']).exists(),
                                 'historical_package': row['package'], 'artifact_sha256': row['artifact_sha256'],
                                 'archived_records_consistent': True}

review_identity = read(REVIEW / 'final-review-identity.json')
assert review_identity['product_head'] == PRODUCT and review_identity['status'] == 'passed' and review_identity['must_fix_findings'] == 0
assert sha((REVIEW / 'final-review-identity.json').read_bytes()) == delivery['independent_review_identity_sha256']
assert sha((TASK / 'code-review.md').read_bytes()) == delivery['independent_code_review_sha256'] == review_identity['code_review_sha256']
artifacts(ROOT, review_identity['artifacts'])
task_text = (ROOT / 'docs/tasks/W010-local-contact-connectivity.md').read_text()
review_section = task_text.split('## Review结论（reviewer）\n', 1)[1].split('\n## PM验收与交接（PM）', 1)[0]
assert sha(review_section.encode()) == delivery['task_review_section_sha256'] == review_identity['task_review_section_sha256']
for name in ('main-probe.receipt.json', 'math-receipt.json'):
    artifacts(REVIEW, read(REVIEW / name)['artifacts'])
boundary = read(REVIEW / 'boundary-receipt.json')
assert boundary['status'] == 'passed' and boundary['observed_exit_code'] == 0
assert boundary['summary']['failures'] == [] and boundary['summary']['constructor_faults'] == boundary['summary']['same_object_and_history'] == 220
for name, digest in boundary['artifact_sha256'].items(): assert sha((REVIEW / name).read_bytes()) == digest
for name, digest in boundary['source_sha256'].items(): assert sha((ROOT / 'layauto_v2' / name).read_bytes()) == digest
old_audit = read(REVIEW / 'evidence-audit.json')
assert old_audit['head'] == PRODUCT and old_audit['status'] == 'passed' and old_audit['check_count'] == 68
assert all(c['passed'] for c in old_audit['checks'])

performance = read(TASK / 'performance.json')
assert performance['probe_sha256'] == sha((TASK / 'performance_probe.py').read_bytes())
for name, digest in performance['source_files_sha256'].items(): assert sha((ROOT / name).read_bytes()) == digest
delivery_manifest = read(TASK / 'delivery-manifest.json')
assert delivery_manifest['tested_reviewed_product_commit'] == PRODUCT
artifacts(ROOT, delivery_manifest['files'])
scope = read(TASK / 'scope-check.json')
protected = subprocess.check_output(['git', 'diff', '--name-only', BASE, HEAD, '--', *scope['protected_paths']], cwd=ROOT, text=True).splitlines()
assert not protected
old_changes = []
for name in baseline_manifest['files']:
    if not name.startswith('tests/') or not name.endswith('.py'): continue
    before = subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)
    after = (ROOT / name).read_bytes()
    if before != after: old_changes.append(name)
    old_names = {n.name for n in ast.walk(ast.parse(before)) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    new_names = {n.name for n in ast.walk(ast.parse(after)) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    assert old_names <= new_names
assert old_changes == ['tests/contracts/test_w007_contracts.py']
preflight = read(TASK / 'preflight/setup-receipt.json')
r1 = read(TASK / 'verification-r1/failure.json')
assert 'partial' in preflight['baseline310_status'] and r1['status'] == 'failed_and_interrupted'
assert r1['source_git_head'] != PRODUCT

print(json.dumps({'status': 'passed', 'must_fix': 0, 'head': HEAD, 'product': PRODUCT, 'base': BASE,
                  'python': sys.version, 'platform': platform.platform(), 'script_sha256': sha(Path(__file__).read_bytes()),
                  'source_files': len(files), 'runtime_files': len(runtime),
                  'source_manifest_sha256': delivery['source_manifest_sha256'],
                  'source_snapshot_sha256': delivery['source_snapshot_sha256'],
                  'source_archive_matches_git_and_current': True, 'evidence_files': len(evidence_manifest),
                  'commands': commands, 'command_count': len(commands), 'raw_output_count': 2 * len(commands),
                  'test_counts': receipt['actual_test_counts'], 'baseline_tests_retained': len(baseline_ids), 'new_tests': 316,
                  'packages': {k: v['sha256'] for k, v in packages.items()},
                  'installations': install_observations,
                  'historical_test_source_tree_present': Path('/workspace/work/w010-final-0f5029d/source').exists(),
                  'independent_review_artifacts': len(review_identity['artifacts']),
                  'delivery_manifest_files': len(delivery_manifest['files']), 'protected_changed_paths': protected,
                  'old_changed_tests': old_changes, 'historical_partial_records_separated': True,
                  'limitations': ['No pytest, typing, build, installation, original smoke or historical installed import rerun.',
                                  'Historical test/installation trees not traversed by this audit; presence flags recorded. Actual historical-tree/import conclusions adopted from original independent review.',
                                  'Current content hashes and archived-record consistency do not independently re-observe historical command execution.',
                                  'Does not establish production performance, PDK/EDA or full Stage2/M1 admission.']}, ensure_ascii=False, indent=2))
