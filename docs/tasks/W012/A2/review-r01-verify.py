"""Execute the repaired generated-output assignment/link loop in isolation."""
import ast
import hashlib
import json
import re
import tempfile
from pathlib import Path

SOURCE = Path('/workspace/Layauto/docs/tasks/W012/A2')
HERE = Path(__file__).resolve().parent
checker = SOURCE / 'delivery_check.py'
tree = ast.parse(checker.read_text())
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
assignment = next(node for node in main.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'generated' for target in node.targets))
loop = next(node for node in main.body if isinstance(node, ast.For)
            and isinstance(node.target, ast.Name) and node.target.id == 'path')
fragment = compile(ast.fix_missing_locations(ast.Module(body=[assignment, loop], type_ignores=[])),
                   str(checker), 'exec')
generated_names = {'delivery-check.command.json', 'delivery-check-result.json',
                   'delivery-check.stdout.txt', 'delivery-check.stderr.txt'}
with tempfile.TemporaryDirectory(prefix='w012-a2-r01-fixed-', dir='/workspace/work') as directory:
    fixture = Path(directory) / 'docs/tasks/W012/A2'
    fixture.mkdir(parents=True)
    for name in ('plan.md', 'delivery.md'):
        (fixture / name).write_bytes((SOURCE / name).read_bytes())
    for name in ('plan.md', 'delivery.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', (fixture / name).read_text()):
            if '://' in target or target in generated_names:
                continue
            path = fixture / target.split('#')[0]
            if path.exists():
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Link-existence fixture only; no approval or result.\n')
    assert not any((fixture / name).exists() for name in generated_names)
    exec(fragment, {'HERE': fixture, 're': re})
    assert not any((fixture / name).exists() for name in generated_names)
    with (fixture / 'delivery.md').open('a') as stream:
        stream.write('\n[missing ordinary input](missing-input.json)\n')
    try:
        exec(fragment, {'HERE': fixture, 're': re})
    except AssertionError as exc:
        assert exc.args[0][1] == 'missing-input.json'
    else:
        raise AssertionError('ordinary missing link was incorrectly exempted')
record = {'status': 'passed', 'checker_sha256': hashlib.sha256(checker.read_bytes()).hexdigest(),
          'original_checker_sha256': hashlib.sha256((SOURCE / 'delivery_check-before-R01.py.txt').read_bytes()).hexdigest(),
          'method': 'Exact repaired AST assignment and for loop, executed only in throwaway link fixture',
          'generated_output_paths_absent_and_not_precreated': sorted(generated_names),
          'ordinary_missing_link_still_rejected': True,
          'not_run': 'Full delivery checker; product runtime paths or matrix'}
(HERE / 'review-r01-verify-result.json').write_text(json.dumps(record, indent=2) + '\n')
print('PASS: repaired original link loop accepts four absent self-generated outputs without precreating them')
print('PASS: the same loop still rejects missing ordinary input link')
print('Original -> repaired checker:', record['original_checker_sha256'], '->', record['checker_sha256'])
