"""Check the R7 test-only delta and the actual R6 stopped-prefix evidence.

Read existing bytes and AST only; never import tests or product modules.
"""
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
DEV = Path('docs/tasks/W014/development')
CHANGED = 'tests/contracts/test_w014_contracts.py'
FUNCTION = 'test_neutral_capture_source_set_must_close_every_consumed_owner_and_seed'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def identity(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def main():
    checks = []

    def check(ok, name):
        assert ok, name
        checks.append(name)

    before = load(DEV / 'metadata-r6-source.json')
    after = load(DEV / 'remaining-r7-source.json')
    command = load(DEV / 'targeted-r6.command.json')
    check(identity(before['files']) == before['source_id'] == command['source_id_before']
          == command['source_id_after'], 'R6 whole source identity unchanged during failed run')
    check(identity(after['files']) == after['source_id'], 'R7 whole source identity')
    check(before['files'] == command['files'] and command['source_unchanged'] is True,
          'stopped command preserves full R6 source manifest')
    check(all(sha((ROOT / n).read_bytes()) == h for n, h in after['files'].items()), 'all R7 selected live bytes')
    delta = [n for n in sorted(set(before['files']) | set(after['files']))
             if before['files'].get(n) != after['files'].get(n)]
    check(delta == [CHANGED], 'exactly one changed test file; runtime/config/fixtures unchanged')
    preserved = {}
    with tarfile.open(ROOT / DEV / 'targeted-r6-source-snapshot.tar.gz', 'r:gz') as archive:
        for member in archive.getmembers():
            check(member.isfile() and not Path(member.name).is_absolute()
                  and '..' not in Path(member.name).parts and member.name not in preserved,
                  'safe R6 source snapshot member ' + member.name)
            preserved[member.name] = archive.extractfile(member).read()
    check({n: sha(data) for n, data in preserved.items()} == before['files'], 'complete stopped R6 snapshot identity')
    original = preserved[CHANGED].decode()
    current = (ROOT / CHANGED).read_text()
    (OUT / 'candidate_r7_test_only.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), current.splitlines(True), fromfile='R4-R6/' + CHANGED, tofile='R7/' + CHANGED)))
    old_tree, new_tree = ast.parse(original), ast.parse(current)
    old_func = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == FUNCTION)
    new_func = next(node for node in new_tree.body if isinstance(node, ast.FunctionDef) and node.name == FUNCTION)

    def remove_changed_else(function):
        function = copy.deepcopy(function)
        branch = function.body[1]
        assert isinstance(branch, ast.If)
        while len(branch.orelse) == 1 and isinstance(branch.orelse[0], ast.If):
            branch = branch.orelse[0]
        branch.orelse = []
        return function

    check(ast.dump(remove_changed_else(old_func)) == ast.dump(remove_changed_else(new_func)),
          'all source/body/derived branches and common assertions unchanged')
    old_tree.body.remove(old_func)
    new_tree.body.remove(new_func)
    check(ast.dump(old_tree) == ast.dump(new_tree), 'all other module imports/fixtures/tests unchanged')
    stdout = (ROOT / DEV / 'targeted-r6.stdout.txt').read_bytes()
    stderr = (ROOT / DEV / 'targeted-r6.stderr.txt').read_bytes()
    check(sha(stdout) == command['logs']['stdout']['sha256']
          and sha(stderr) == command['logs']['stderr']['sha256'], 'original stopped stdout/stderr hashes')
    check(command['returncode'] == 1 and b'1 failed, 85 passed' in stdout
          and b"AttributeError: 'ChannelSeed' object has no attribute 'source'" in stdout,
          'original test setup failure retained without passing claim')
    collection = [line for line in (ROOT / DEV / 'collection-r6.stdout.txt').read_text().splitlines()
                  if line.startswith('tests/') and '::' in line]
    selected = []
    selectors = [arg for arg in command['argv'] if arg.startswith('tests/')]
    for selector in selectors:
        selected.extend(node for node in collection
                        if node == selector or '::' not in selector and node.partition('::')[0] == selector)
    check(len(selected) == len(set(selected)) == 165 and len(collection) == 1889, 'actual selected 165 and full 1889 nodeids')
    declared = load(DEV / 'remaining-r7-nodeids.json')
    check(selected[85] == declared['original_failed_nodeid'], 'failed node follows exactly 85 passed prefix')
    units = [node for node in selected[:85] if node.startswith('tests/unit/')]
    scope = [node for node in selected[:85] if node.startswith('tests/contracts/test_w014_body_scope.py::')]
    codec = [node for node in selected[:85] if node.startswith(CHANGED + '::')]
    check(len(units) == 56 and len(scope) == 11 and codec == declared['adopted_codec_prefix'],
          'prefix is 56 unchanged units plus 11 unchanged scope plus 18 codec cases')
    check(len(selected[85:]) == 80 and [node for node in selected[85:] if node.startswith(CHANGED + '::')]
          == declared['remaining_codec'], 'remaining 80 includes both changed channel/net branches and all suffix cases')
    check(set(selected[:85]).isdisjoint(selected[85:]), 'prefix and remaining coverage disjoint')
    result = {'status': 'test-only-identity-and-prefix-adoption-audit-passed',
        'resource_measured_source_id': before['source_id'], 'candidate_source_id': after['source_id'],
        'delta': delta, 'adopted_count': 85, 'pending_actual_count': 80,
        'adopted_nodeids': selected[:85], 'remaining_nodeids': selected[85:],
        'check_count': len(checks), 'checks': checks,
        'limitations': ['Remaining R7 execution was not yet claimed passed.',
            'No product/tests/codec/capture were executed by this audit.',
            'Final new source still requires both complete interpreter matrices.']}
    (OUT / 'candidate_r7_identity_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'resource_measured_source_id',
          'candidate_source_id', 'delta', 'adopted_count', 'pending_actual_count', 'check_count')}, indent=2))


if __name__ == '__main__':
    main()
