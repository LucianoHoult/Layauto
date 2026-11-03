"""Independent scope/dependency audit of changed product modules, without imports."""
import ast
import json
from pathlib import Path
import subprocess

root = Path.cwd()
base = '765ff864f4341b91996f70f25723411eebc0d6c2'
def names(*args):
    return subprocess.check_output(['git', *args], text=True).splitlines()

changed = names('diff', '--name-only', base, 'HEAD')
product = [p for p in changed if p.startswith('layauto_v2/')]
expected = {
    'layauto_v2/domain/geometry.py', 'layauto_v2/normalization/__init__.py',
    'layauto_v2/normalization/geometry.py', 'layauto_v2/normalization/geometry_codec.py',
    'layauto_v2/normalization/geometry_input.py', 'layauto_v2/state/coordinate.py',
    'layauto_v2/state/layout_store.py', 'layauto_v2/state/occupancy.py',
}
assert set(product) == expected, product
for prefix in ('tests/fixtures/', 'tests/support/', 'tests/unit/', 'legacy_mvp/',
               'layauto_v2/importers/', 'layauto_v2/repository/', 'layauto_v2/tooling/'):
    assert not any(p.startswith(prefix) for p in changed), prefix
assert 'layauto_v2/pipeline.py' not in changed
assert 'docs/architecture.md' not in changed
assert names('diff', '--name-only', 'aced62b0adda35fe7bcd8284a7354badc5b03649', 'HEAD',
             'layauto_v2', 'tests', 'pyproject.toml', 'README.md') == []

imports = {}
for rel in product:
    tree = ast.parse((root / rel).read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append('.' * node.level + (node.module or ''))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in ('open', 'hash', 'eval', 'exec', '__import__'), (rel, node.lineno)
    assert not any(m.startswith(('os', 'pathlib', 'io', 'subprocess', 'legacy_mvp', 'tests',
                                 'layauto_v2.pipeline', 'layauto_v2.repository',
                                 'layauto_v2.tooling', 'layauto_v2.transactions')) for m in modules), (rel, modules)
    if '/domain/' in rel or '/state/' in rel:
        assert not any(m.startswith(('layauto_v2.importers', 'layauto_v2.normalization')) for m in modules)
    imports[rel] = modules

print(json.dumps({'changed_product_modules': product,
    'post_delivery_product_test_config_changes': [],
    'fixture_support_unit_architecture_legacy_reader_pipeline_repository_tooling_unchanged': True,
    'imports': imports,
    'result': 'pass; no IO/publication/legacy dependency in changed product modules'}, indent=2))
