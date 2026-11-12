"""Independent test-only source delta and exact dependency-allowance review."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sid(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def main():
    root = Path.cwd()
    resource = json.loads((root / 'docs/tasks/W013/resource-attempt-04/normal-direct.json').read_text())
    old_files = resource['files']
    current = {name: sha(root / name) for name in old_files}
    delta = {name: {'measured': digest, 'current': current[name]} for name, digest in old_files.items() if current[name] != digest}
    assert set(delta) == {'tests/contracts/test_w007_contracts.py'}
    assert sid(current) == '2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278'
    test_path = root / 'tests/contracts/test_w007_contracts.py'
    tree = ast.parse(test_path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'test_normalization_and_new_domain_keep_pure_dependency_boundaries')
    allowance = next(node.value for node in ast.walk(function) if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'allowed_net_annotation_state' for target in node.targets))
    expression = compile(ast.Expression(allowance), '<actual-retained-test-allowance>', 'eval')
    cases = []
    for filename, text, expected in (
        ('normalization/net_annotation.py', 'from layauto_v2.state.annotation import AnnotationDraft', True),
        ('normalization/net_annotation_codec.py', 'from layauto_v2.state.annotation import AnnotationDraft', True),
        ('normalization/net_annotation.py', 'from layauto_v2.state.annotation import AnnotationDraft as ReadOnlyDraft', True),
        ('normalization/semantic.py', 'from layauto_v2.state.annotation import AnnotationDraft', False),
        ('domain/net_annotation.py', 'from layauto_v2.state.annotation import AnnotationDraft', False),
        ('normalization/net_annotation.py', 'from layauto_v2.state.annotation import MutableState', False),
        ('normalization/net_annotation.py', 'from layauto_v2.state.annotation import AnnotationDraft, install', False),
        ('normalization/net_annotation.py', 'from layauto_v2.state.annotation import *', False),
        ('normalization/net_annotation.py', 'import layauto_v2.state.annotation', False),
        ('normalization/net_annotation.py', 'from layauto_v2.state.other import AnnotationDraft', False),
        ('normalization/net_annotation.py', 'from layauto_v2.repository import PublicationRepository', False),
    ):
        node = ast.parse(text).body[0]
        actual = eval(expression, {'ast': ast, 'isinstance': isinstance}, {'path': Path('/runtime') / filename, 'node': node})
        assert actual is expected, (filename, text, actual)
        cases.append({'filename': filename, 'import': text, 'allowed': actual})
    before = json.loads((root / 'docs/tasks/W013/development/retained-boundary-failure.command.json').read_text())
    after = json.loads((root / 'docs/tasks/W013/development/retained-boundary-after.command.json').read_text())
    assert before['source_id_before'] == before['source_id_after'] == resource['source_id']
    assert before['returncode'] == 1 and after['returncode'] == 0
    assert after['source_id_before'] == after['source_id_after'] == sid(current)
    assert after['source_unchanged']
    for row in (before, after):
        for log in row['logs'].values():
            assert sha(Path(log['path'])) == log['sha256']
    assert '3 passed' in Path(after['logs']['stdout']['path']).read_text()
    stopped = json.loads((root / 'docs/tasks/W013/verification/controlled-stop.json').read_text())
    assert stopped['nodeid'].endswith('test_normalization_and_new_domain_keep_pure_dependency_boundaries')
    exits = {tag: json.loads((root / 'docs/tasks/W013/verification' / ('pytest-' + tag + '.json')).read_text())['exit_code'] for tag in ('310', '312')}
    assert exits == {'310': -15, '312': -15}
    result = {'classification': 'independent-retained-boundary-test-delta-review-no-product-rerun',
        'measured_source_id': resource['source_id'], 'new_source_id': sid(current), 'delta': delta,
        'runtime_config_inputs_new75tests_unchanged': True, 'actual_allowance_predicate_cases': cases,
        'failed_old_matrix_exit_codes': exits, 'retained_boundary_reproduced_before': True,
        'new_and_old_boundary_tests_3_passed': True,
        'resource_adoption_basis': 'Only one architecture-test source changed; resource probe imports no test module. Runtime/config/input/probe bytes remain at original measured identity.',
        'required_next_step': 'Freeze the new complete source and rerun both 1731-test full matrices plus required typing/build/install; old stopped runs are failures, never passed coverage.'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
