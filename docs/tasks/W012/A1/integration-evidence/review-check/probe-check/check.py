"""Read-only identity audit of the delivered premerge review evidence.

Does not execute project code, pytest, probe.py, seal.py, or mutate repository.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/workspace/Layauto')
OUT = Path('/workspace/work/w012-a1-integration/review-check/probe-check')
EVIDENCE = ROOT / 'docs/tasks/W012/A1/premerge-review-evidence'
HEAD = '1a1459e3179e7bd234e4971c1969a6a78f387fd2'
MERGE = '08dd232139918dc97b0a6d255aad237eb844686a'
REVIEWED = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'
BASE = '0a3326aa363477724465886cd05874d0997fba3e'


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


start_head = git('rev-parse', 'HEAD').decode().strip()
assert start_head in (HEAD, MERGE), start_head
assert git('rev-parse', start_head + '^{tree}') == git('rev-parse', HEAD + '^{tree}')
start_status = git('status', '--porcelain=v1')
assert not start_status, start_status
manifest_path = EVIDENCE / 'files-manifest.json'
manifest = json.loads(manifest_path.read_text())
assert len(manifest) == 67
for name, identity in manifest.items():
    assert sha(ROOT / name) == identity, name
seal = json.loads((EVIDENCE / 'seal-result.json').read_text())
assert seal['manifest_sha256'] == sha(manifest_path)
assert seal['manifest_files'] == len(manifest)
assert seal['reviewed_head'] == REVIEWED
assert seal['new_formal_passed'] == 111
assert seal['finite_candidates'] == 150728
assert seal['new_mandatory_findings'] == seal['remaining_mandatory_findings'] == 0
excluded = {'files-manifest.json', 'seal-result.json', 'seal.stdout.txt',
            'seal.stderr.txt', 'seal.command.json'}
actual = {str(p.relative_to(ROOT)) for p in EVIDENCE.rglob('*')
          if p.is_file() and p.name not in excluded}
actual |= {'docs/tasks/W012/A1/independent-premerge-review.md',
           'docs/tasks/W012-capture-wire-performance.md'}
assert set(manifest) == actual

commands = {}
for p in sorted(EVIDENCE.glob('*.command.json')):
    label = p.name.removesuffix('.command.json')
    command = json.loads(p.read_text())
    assert command['cwd'] == str(ROOT), label
    assert command['reviewed_head'] == REVIEWED, label
    assert command['argv'][0] == '/workspace/.venvs/layauto/bin/python' or label.endswith('diff-check'), label
    for stream in ('stdout', 'stderr'):
        assert sha(EVIDENCE / (label + '.' + stream + '.txt')) == command[stream + '_sha256'], (label, stream)
    commands[label] = command
for label, code in seal['root_command_exit_codes'].items():
    assert commands[label]['exit_code'] == code
assert commands['seal']['exit_code'] == 0
assert json.loads((EVIDENCE / 'seal.stdout.txt').read_text()) == seal

passed = {}
for label, count in (('targeted-formal', 89), ('affected-formal', 22)):
    command = commands[label]
    assert command['exit_code'] == 0
    assert command['argv'][1:6] == ['-B', '-m', 'pytest', '-p', 'no:cacheprovider']
    assert command['environment_overrides']['PYTHONDONTWRITEBYTECODE'] == '1'
    assert command['environment_overrides']['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'
    text = (EVIDENCE / (label + '.stdout.txt')).read_text()
    assert re.search(r'\b' + str(count) + r' passed in ', text)
    assert not (EVIDENCE / (label + '.stderr.txt')).read_bytes()
    passed[label] = count
collection = (EVIDENCE / 'affected-collection.stdout.txt').read_text()
nodes = [line for line in collection.splitlines() if line.startswith('tests/')]
assert len(nodes) == len(set(nodes)) == 22
assert '22 tests collected in ' in collection
assert commands['affected-collection']['argv'] == commands['affected-formal']['argv'][:6] + ['--collect-only'] + commands['affected-formal']['argv'][6:]
assert len({n.split('::')[0] for n in nodes}) == 2

result_path = EVIDENCE / 'contracts/result.json'
probe_result = json.loads(result_path.read_text())
assert commands['independent-probe-r3']['exit_code'] == 0
assert commands['independent-probe-r3']['argv'][2] == 'docs/tasks/W012/A1/premerge-review-evidence/contracts/probe.py'
assert (EVIDENCE / 'independent-probe-r3.stdout.txt').read_bytes() == result_path.read_bytes()
assert not (EVIDENCE / 'independent-probe-r3.stderr.txt').read_bytes()
assert probe_result['reviewed_base'] == BASE and probe_result['reviewed_head'] == REVIEWED
assert not probe_result['must_fix_findings']
candidate_count = 256 ** 2 + 256 ** 2 + sum(7 ** n for n in range(6)) + 10 * 4 + 8
assert candidate_count == probe_result['checks_by_kind']['candidates'] == 150728
assert probe_result['checks_by_kind']['finite-acceptance'] == 2 * candidate_count
assert probe_result['checks_by_kind']['finite-before-after-errors-and-bytes'] == candidate_count
sources = {}
for label, rev in (('original', BASE), ('delivered', REVIEWED)):
    source = git('show', rev + ':layauto_v2/domain/codec.py')
    snapshot = EVIDENCE / ('contracts/' + label + '-codec.py.txt')
    assert source == snapshot.read_bytes()
    assert hashlib.sha256(source).hexdigest() == probe_result['source_sha256'][label]
    sources[label] = {'git_rev': rev, 'sha256': sha(snapshot)}
assert git('show', HEAD + ':layauto_v2/domain/codec.py') == (EVIDENCE / 'contracts/delivered-codec.py.txt').read_bytes()
for label, filename in (('independent-probe', 'probe-attempt01.py.txt'),
                        ('independent-probe-r2', 'probe-attempt02.py.txt'),
                        ('independent-probe-r3', 'probe.py')):
    assert sha(EVIDENCE / 'contracts' / filename) == seal['probe_source_snapshots'][label]
assert commands['independent-probe']['exit_code'] == commands['independent-probe-r2']['exit_code'] == 1
assert 'AssertionError: canonical-check-after-json-and-hex' in (EVIDENCE / 'independent-probe.stderr.txt').read_text()
assert 'TypeError: Object of type bytes is not JSON serializable' in (EVIDENCE / 'independent-probe-r2.stderr.txt').read_text()
tree = ast.parse((EVIDENCE / 'contracts/probe.py').read_text())
oracle = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'oracle')
oracle_calls = [ast.unparse(n.func) for n in ast.walk(oracle) if isinstance(n, ast.Call)]
assert sorted(oracle_calls) == sorted(['bytearray', 'NIBBLES.get', 'bytes', 'output.append']), oracle_calls
assert probe_result['private_len_fault_before_after'] == ['accepted', 'private len side effect']
assert 'Finite synthetic' in probe_result['limitations']
assert git('rev-parse', 'HEAD').decode().strip() == start_head
assert git('status', '--porcelain=v1') == start_status

report = {
    'status': 'passed', 'head': start_head, 'delivery': HEAD, 'reviewed_head': REVIEWED,
    'manifest_files_checked': len(manifest), 'manifest_sha256': sha(manifest_path),
    'root_command_stream_pairs_checked': len(commands),
    'formal_original_passed': passed, 'formal_original_total': sum(passed.values()),
    'affected_unique_collected_nodes': len(nodes),
    'finite_candidate_count_recalculated': candidate_count,
    'probe_result_sha256': sha(result_path), 'probe_sources': sources,
    'failed_probe_attempts_preserved': 2,
    'new_mandatory_findings': 0, 'remaining_mandatory_findings': 0,
    'acceptance': 'The delivered 111 original test outcomes, 150728 finite probe outcome, and zero-finding review can be accepted as evidence bound to the reviewed source.',
    'limitations': [
        'This audit reads original output and identities; it does not rerun pytest, product code, the finite probe, or seal.py.',
        'Finite synthetic candidates are not formal tests and provide no exhaustive production/max-input guarantee.',
        'Private malicious str-subclass len behavior differs as already disclosed; public JSON str ingress is the reviewed boundary.',
        'No verification of large wire payloads, original installation trees, complete performance measurements, or engineering matrix in this subcheck.',
    ],
    'repository_worktree_unchanged': True,
}
(OUT / 'result.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(report, indent=2, ensure_ascii=False))
