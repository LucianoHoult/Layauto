"""Independent premerge evidence audit; no product, package install or heavy tests.

Run from repository root: python -B docs/tasks/W012/A1/premerge-review-evidence/engineering/check.py
Prints the complete result to stdout. Does not rewrite historical evidence.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[6]
A1 = ROOT / 'docs/tasks/W012/A1'
V = A1 / 'verification-r2'
HEAD = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'
BASE = '0a3326aa363477724465886cd05874d0997fba3e'
FREEZE = 'ca1f810c3c97376f71089d8b4054760ff198012f'
REVIEW = '44a91c472fdeba5bb4b8a6071c0580313336c379'
checks = Counter()
read_hashes = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    data = path.read_bytes()
    read_hashes[str(path.relative_to(ROOT))] = sha(data)
    return data


def js(path):
    return json.loads(read(path))


def require(condition, category, detail):
    if not condition:
        raise AssertionError((category, detail))
    checks[category] += 1


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


manifest = js(V / 'source-manifest.json')
require(manifest['git_head'] == '212554cdc402f6b86e92b8b81cd43752a01ff858', 'source', 'manifest starting HEAD')
require(len(manifest['files']) == 263 and len(manifest['runtime_files']) == 100, 'source', '263/100')
for name, digest in manifest['files'].items():
    require(sha(read(ROOT / name)) == digest, 'source', name)
    for version in (FREEZE, REVIEW, HEAD):
        require(sha(git('show', version + ':' + name)) == digest, 'source_versions', (version, name))
with tarfile.open(V / 'source-snapshot.tar.gz') as archive:
    members = {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
require(members == manifest['files'], 'snapshot', 'complete member map')

scope = git('diff', '--name-status', BASE, HEAD).decode().splitlines()
require(len(scope) == 595, 'scope', 'all main..head paths')
runtime_changes = [line for line in scope if '\tlayauto_v2/' in line]
test_changes = [line for line in scope if '\ttests/' in line]
require(runtime_changes == ['M\tlayauto_v2/domain/codec.py'], 'scope', 'only runtime change')
require(test_changes == ['A\ttests/contracts/test_w012_hex_validation.py'], 'scope', 'only formal test change')
post_review = git('diff', '--name-only', REVIEW, HEAD).decode().splitlines()
require(not any(p.startswith(('layauto_v2/', 'tests/')) or p == 'pyproject.toml' for p in post_review), 'scope', 'post-review source unchanged')
require(not any(p.startswith('docs/tasks/W012/') and '/A1' not in p for p in post_review), 'scope', 'post-review P1/P2 unchanged')

receipt = js(V / 'receipt.json')
require(receipt['status'] == 'passed' and len(receipt['commands']) == 21, 'commands', '21 complete commands')
require(sha(read(V / 'source-manifest.json')) == receipt['source_manifest_sha256'], 'commands', 'source manifest hash')
require(sha(read(V / 'source-snapshot.tar.gz')) == receipt['source_snapshot_sha256'], 'commands', 'snapshot hash')
for row in receipt['commands']:
    name = row['stdout'].removesuffix('.stdout.txt')
    require(js(V / (name + '.json')) == row, 'commands', name + ' receipt identity')
    require(row['exit_code'] == 0 and row['started_at_utc'] < row['finished_at_utc'], 'commands', name + ' completion')
    for stream in ('stdout', 'stderr'):
        require(sha(read(V / row[stream])) == row[stream + '_sha256'], 'command_outputs', (name, stream))
evidence_manifest = js(V / 'evidence-manifest.json')
require(len(evidence_manifest) == 78, 'evidence_manifest', '78 attachments')
for name, digest in evidence_manifest.items():
    require(sha(read(V / name)) == digest, 'evidence_manifest', name)
baseline_ids = {s for s in read(V / 'baseline-collection.txt').decode().splitlines() if s.startswith('tests/') and '::' in s}
require(len(baseline_ids) == 1605, 'tests', '1605 original nodes')
ids_by_python = {}
for tag in ('310', '312'):
    ids = {s for s in read(V / ('collection-' + tag + '.stdout.txt')).decode().splitlines() if s.startswith('tests/') and '::' in s}
    require(len(ids) == 1656 and baseline_ids <= ids, 'tests', tag + ' baseline retained')
    require(len(ids - baseline_ids) == 51 and all('test_w012_hex_validation.py::' in s for s in ids - baseline_ids), 'tests', tag + ' 51 additions')
    ids_by_python[tag] = ids
    require('1656 passed in ' in read(V / ('pytest-' + tag + '.stdout.txt')).decode(), 'tests', tag + ' full pytest result')
    require(read(V / ('typing-' + tag + '.stdout.txt')).decode().strip() == 'Success: no issues found in 54 source files', 'typing', tag)
require(ids_by_python['310'] == ids_by_python['312'], 'tests', 'same dual collection')

def payload(path):
    if path.suffix == '.whl':
        with zipfile.ZipFile(path) as archive:
            return {n.split('layauto_v2/', 1)[1]: sha(archive.read(n)) for n in archive.namelist() if n.startswith('layauto_v2/') and not n.endswith('/')}
    with tarfile.open(path) as archive:
        return {m.name.split('/layauto_v2/', 1)[1]: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile() and '/layauto_v2/' in m.name}

comparison = js(A1 / 'package-comparison.json')
payloads = {}
for side, formats in comparison['artifacts'].items():
    payloads[side] = {}
    for format_name, record in formats.items():
        path = A1 / record['path']
        require(sha(read(path)) == record['sha256'], 'packages', (side, format_name, 'archive hash'))
        files = payload(path)
        require(len(files) == 100, 'packages', (side, format_name, '100 members'))
        payloads[side][format_name] = files
    require(payloads[side]['wheel'] == payloads[side]['sdist'], 'packages', side + ' wheel/sdist same payload')
require(payloads['after']['wheel'] == manifest['runtime_files'], 'packages', 'after equals frozen runtime')
for name, digest in payloads['before']['wheel'].items():
    require(sha(git('show', BASE + ':layauto_v2/' + name)) == digest, 'packages', 'before main source ' + name)
require([n for n in payloads['before']['wheel'] if payloads['before']['wheel'][n] != payloads['after']['wheel'][n]] == ['domain/codec.py'], 'packages', 'only codec payload difference')
installation = js(V / 'installation-identity.json')
installation_trees_present = {}
smokes = {}
for tag, record in installation.items():
    installation_trees_present[tag] = Path(record['package']).exists()
    require(record['isolated'] == 1 and record['runtime_files'] == manifest['runtime_files'], 'installation_evidence', tag + ' identity')
    row = js(V / ('installed-smoke-' + tag + '.json'))
    require('-I' in row['command'] and '-B' in row['command'], 'installation_evidence', tag + ' isolated command')
    require(not Path(row['cwd']).is_relative_to(ROOT) and not Path(row['cwd']).is_relative_to(Path('/workspace/w012-a1-final-r2/source')), 'installation_evidence', tag + ' outside source')
    smoke = js(V / ('installed-smoke-' + tag + '.stdout.txt'))
    for route in ('direct', 'readback', 'extraction_mismatch'):
        expected = {'MN0': 4, 'MP0': 7} if route == 'extraction_mismatch' else {'MN0': 5, 'MP0': 7}
        require(smoke[route]['counts'] == expected and smoke[route]['raw_FIN_records'] == 18, 'installation_evidence', (tag, route))
        require((smoke[route]['local_nodes'], smoke[route]['local_edges'], smoke[route]['local_components'], smoke[route]['body_shapes']) == (14, 8, 6, 6), 'installation_evidence', (tag, route, 'full facts'))
    require(smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'], 'installation_evidence', tag + ' readback boundaries')
    smokes[tag] = smoke

interruption = js(A1 / 'interruption-01.json')
require(len(interruption['files']) == 26, 'recovery', '26 original partial attachments')
for name, digest in interruption['files'].items():
    require(sha(read(A1 / 'verification-attempt-01' / name)) == digest, 'recovery', name)
require('passed' not in read(A1 / 'verification-attempt-01/pytest-310.stdout.txt').decode(), 'recovery', 'partial not passed')
wrapper = js(A1 / 'final-r2-runner.command.json')
require('exit_code' not in wrapper and wrapper['launch_status'].startswith('started;'), 'recovery', 'wrapper remains unclosed')
reconnect = js(A1 / 'reconnect-02.json')
require('survived' in reconnect['observed'] and 'not yet a pass' in reconnect['partial_progress'], 'recovery', 'disconnect distinguished from completion')
original_r01 = js(A1 / 'early-review-evidence/runner-R01-reproduction.json')
closed_r01 = js(A1 / 'early-review-evidence/runner-R01-fix-verification.json')
require(original_r01['interrupted_stdout_overwritten'] and original_r01['frozen_identity_overwritten'], 'R01', 'original reproduced overwrite retained')
require(sha(read(A1 / 'early-review-evidence/run_performance-before-R01.py.txt')) == original_r01['source_sha256'], 'R01', 'original buggy source retained')
require(sha(read(A1 / 'run_performance.py')) == closed_r01['source_sha256'], 'R01', 'closed runner source unchanged')

# New independent guard exercise. Substitute only identity/preflight and a Popen
# sentinel; call the actual runner in isolated empty/nonempty temporary stages.
spec = importlib.util.spec_from_file_location('premerge_actual_runner', A1 / 'run_performance.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
guard_results = []
with tempfile.TemporaryDirectory(prefix='premerge-r01-') as temp:
    temp_root = Path(temp)
    for index, names in enumerate((('interrupted.stdout.txt',), ('interrupted.stderr.txt',), ('frozen-identity.json',), ('interrupted.stdout.txt', 'interrupted.stderr.txt', 'frozen-identity.json'))):
        sandbox = temp_root / str(index)
        sandbox.mkdir()
        for name in ('probe.py', 'run_performance.py'):
            (sandbox / name).write_text('# guard input substitute\n')
        (sandbox / 'selfcheck.json').write_text(json.dumps({'tool_sha256': sha((sandbox / 'probe.py').read_bytes())}))
        directory = sandbox / 'performance'
        directory.mkdir()
        original_bytes = {name: ('prior evidence ' + name).encode() for name in names}
        for name, data in original_bytes.items():
            (directory / name).write_bytes(data)
        before, after = sandbox / 'before', sandbox / 'after'
        module.ROOT, module.OUT, module.PROBE = sandbox, sandbox, sandbox / 'probe.py'
        module.RUNTIMES = {'before': before, 'after': after}
        module.WORK = sandbox / 'work'
        module.identity = lambda path: {'layauto_v2/domain/codec.py': 'old'} if path == before else {'layauto_v2/domain/codec.py': 'new', 'tests/contracts/test_w012_hex_validation.py': 'new'}
        def forbidden(*args, **kwargs):
            raise AssertionError('Popen was reached')
        old_argv, old_popen = sys.argv, module.subprocess.Popen
        try:
            sys.argv = ['run_performance.py', '--stage', 'baseline']
            module.subprocess.Popen = forbidden
            try:
                module.main()
            except RuntimeError as error:
                require(str(error) == 'Stage contains prior evidence; do not overwrite or silently resume it', 'R01_new_guard', names)
            else:
                raise AssertionError('nonempty stage accepted')
        finally:
            sys.argv, module.subprocess.Popen = old_argv, old_popen
        require({p.name: p.read_bytes() for p in directory.iterdir()} == original_bytes, 'R01_new_guard', 'exact original bytes ' + str(names))
        require(not module.WORK.exists(), 'R01_new_guard', 'no work/process ' + str(names))
        guard_results.append({'prior_files': list(names), 'refused_before_process': True, 'all_bytes_preserved': True})

print(json.dumps({
    'status': 'passed', 'audit_time_utc': datetime.now(timezone.utc).isoformat(),
    'review_base': BASE, 'review_head': HEAD, 'product_test_freeze': FREEZE,
    'independence': 'New premerge-session read-only engineering evidence auditor; no earlier A1 design/implementation/formal-test/performance-tool participation.',
    'checks_by_category': dict(checks), 'total_checks': sum(checks.values()),
    'main_to_head_changed_paths': len(scope), 'main_to_head_scope_counts': {'docs': 593, 'runtime': 1, 'new_formal_test': 1},
    'post_original_review_changed_paths': len(post_review),
    'actual_source_files': 263, 'actual_runtime_files': 100, 'full_command_count': 21,
    'baseline_nodes': 1605, 'new_nodes': 51, 'dual_complete_nodes': 1656,
    'four_actual_packages_read': True, 'package_payload_only_difference': 'domain/codec.py',
    'old_installation_trees_present_on_this_host': installation_trees_present,
    'new_R01_guard_exercises': guard_results,
    'remaining_mandatory_findings': 0,
    'limitations': [
        'Original dual full matrices, typing, installations and complete synthetic smokes are accepted through unchanged source, original command/output hashes and prior independent review, not rerun here.',
        'Original installation trees are absent locally; archived identity maps were verified against the actual after packages/frozen source; no claim of reading installed files now.',
        'Installation-smoke mismatch inputs used temporary paths, so its wire hashes are not fixed-URI benchmark identities or identical across interpreters.',
        'Outer r2 polling wrapper has no exit result; success is established by 21 internal complete command receipts plus final receipt.',
        'New R01 exercise is a finite isolated runner-guard probe; no product or performance sample launched.'
    ],
    'actual_read_sha256': read_hashes,
}, indent=2, ensure_ascii=False))
