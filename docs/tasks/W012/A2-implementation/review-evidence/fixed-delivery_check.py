"""Check A2 implementation scope and bind evidence; this is not PM acceptance."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

PREPARATION = '0213c346ac03b7b7282aae522c299155958ac8f6'
OWNERS = ('layauto_v2/normalization/local_connectivity_codec.py',
          'layauto_v2/normalization/channel_identity_codec.py')
NEW_TEST = 'tests/contracts/test_w012_typed_pack.py'
TASK = 'docs/tasks/W012-capture-wire-performance.md'
PREFIX = 'docs/tasks/W012/A2-implementation/'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pending-command-prefix', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    assert not args.output.exists(), 'preserve earlier delivery checks'

    def original(name: str) -> bytes:
        return subprocess.check_output(['git', 'show', f'{PREPARATION}:{name}'], cwd=root)

    changed = set(subprocess.check_output(
        ['git', 'diff', '--name-only', PREPARATION], cwd=root, text=True).splitlines())
    changed.update(subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard'], cwd=root, text=True).splitlines())
    assert all(name in (*OWNERS, NEW_TEST, TASK) or name.startswith(PREFIX) for name in changed)
    for name in OWNERS:
        current = (root / name).read_text()
        tree = ast.parse(current)
        helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == '_pack_for_encode')
        lines = current.splitlines(keepends=True)
        restored = ''.join(lines[:helper.lineno - 1] + lines[helper.end_lineno + 2:])
        restored = restored.replace("'record': _pack_for_encode(record)", "'record': _pack(record)")
        assert restored.encode() == original(name), name + ': change exceeds approved helper/call switch'
    if TASK in changed:
        data = (root / TASK).read_bytes()
        begin = b'<!-- A2-implementation-execution-start -->\n'
        end = b'<!-- A2-implementation-execution-end -->\n'
        assert data.count(begin) == data.count(end) == 1
        left, rest = data.split(begin)
        _, right = rest.split(end)
        assert left + right == original(TASK), 'original task/PM bytes changed'

    directory = root / PREFIX
    freeze = json.loads((directory / 'freeze-screen/freeze.json').read_text())
    for name, expected in freeze['sources']['after'].items():
        assert sha(root / name) == expected, 'frozen source/test/config changed: ' + name
    assert sorted(freeze['differences']) == sorted((*OWNERS, NEW_TEST))
    # These exact generated outputs cannot hash themselves while still being
    # written. Final Git and an independent post-completion check bind them.
    generated = {args.output.resolve()}
    if args.pending_command_prefix is not None:
        prefix = args.pending_command_prefix.resolve()
        assert prefix.parent == args.output.resolve().parent
        pending = {Path(str(prefix) + suffix) for suffix in (
            '.command.json', '.stdout.txt', '.stderr.txt')}
        assert all(path.is_file() for path in pending), 'expected active command outputs missing'
        generated.update(pending)
    materials = {str(path.relative_to(root)): sha(path)
                 for path in sorted(directory.rglob('*')) if path.is_file() and path.resolve() not in generated}
    result = {'status': 'passed', 'preparation': PREPARATION,
              'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'scope': sorted(changed), 'material_sha256': materials,
              'generated_outputs_bound_by_final_git': sorted(str(path.relative_to(root)) for path in generated),
              'source_test_config_count': len(freeze['sources']['after']),
              'checks': ['scope limited to two helpers/call sites, new formal test, new attachments and execution block',
                         'original runtime bytes restored exactly after approved two local edits',
                         'original task PM/history bytes unchanged outside execution block',
                         'actual current source/test/config equal pre-screen freeze'],
              'not_product_or_pm_acceptance': True}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('PASS A2 implementation scope, protected original bytes, frozen source and evidence hashes')


if __name__ == '__main__':
    main()
