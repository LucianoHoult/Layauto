"""Independently read completed development receipts; no product tests rerun."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/workspace/Layauto')
HERE = Path(__file__).resolve().parent
PREFIX = ROOT / 'docs/tasks/W012/A2-implementation'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def ids(path):
    return {line for line in path.read_text().splitlines() if line.startswith('tests/') and '::' in line}


def main():
    destination = HERE / 'correctness-check.json'
    assert not destination.exists()
    sources = read(PREFIX / 'freeze-screen/freeze.json')['sources']['after']
    checked = []
    expected = {'affected-r1': '185 passed', 'new-tests-integrated': '82 passed',
                'new-tests-310': '82 passed', 'typing-310': '54 source files',
                'typing-312': '54 source files', 'formal-collection': '1738 tests collected'}
    for name, marker in expected.items():
        command_path = PREFIX / 'development' / (name + '.command.json')
        command = read(command_path)
        assert command['exit_code'] == 0
        outputs = {}
        for kind in ('stdout', 'stderr'):
            path = PREFIX / 'development' / (name + '.' + kind + '.txt')
            outputs[kind] = path.read_bytes()
            assert sha(outputs[kind]) == command[kind + '_sha256']
        assert marker in outputs['stdout'].decode() and outputs['stderr'] == b''
        for source, expected_hash in command['source_sha256'].items():
            assert source in sources and sources[source] == expected_hash
        checked.append({'name': name, 'argv': command['argv'], 'exit_code': 0,
            'marker': marker, 'command_sha256': sha(command_path.read_bytes()),
            'source_entries_checked': len(command['source_sha256'])})
    current = ids(PREFIX / 'development/formal-collection.stdout.txt')
    baseline = ids(ROOT / 'docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt')
    assert len(baseline) == 1656 and len(current) == 1738 and baseline <= current
    assert len(current - baseline) == 82
    assert all(name.startswith('tests/contracts/test_w012_typed_pack.py::') for name in current - baseline)
    delta = read(PREFIX / 'development/formal-collection-delta.json')
    assert delta['baseline_count'] == 1656 and delta['current_count'] == 1738
    assert not delta['missing'] and set(delta['added']) == current - baseline
    wanted = {'test_w011_exceptions.py': 53, 'test_w011_contracts.py': 44,
              'test_w010_contracts.py': 80, 'test_w009_captured_decode_exceptions.py': 8}
    counts = {}
    for filename, expected_count in wanted.items():
        selected = [name for name in current if name.startswith('tests/contracts/' + filename + '::')]
        if filename == 'test_w009_captured_decode_exceptions.py':
            selected = [name for name in selected if '::test_public_collections_validate_and_store_one_snapshot[' in name]
        assert len(selected) == expected_count
        counts[filename] = len(selected)
    assert sum(counts.values()) == 185
    failure = read(PREFIX / 'development/initial-typing-missing-module.json')
    assert failure['exit_code'] == 1 and 'No module named mypy' in failure['output']
    result = {'status': 'passed', 'raw_completed_commands': checked,
        'formal_baseline_nodes': len(baseline), 'formal_current_nodes': len(current),
        'all_original_nodes_retained': True, 'new_node_count': 82,
        'affected_actual_selection_counts': counts, 'initial_typing_failure_preserved': True,
        'scope': 'Read/hash/collection review of actual new-source development checks; no final full matrix/installation/benchmark claim.'}
    with destination.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS completed 185 affected, dual82, dualtyping54 raw hashes/source identities and retained1656+82 nodes')


if __name__ == '__main__':
    main()
