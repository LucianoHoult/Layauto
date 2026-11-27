"""Protect the read-only Stage 3 dependency direction."""
import ast
from importlib.util import resolve_name
from pathlib import Path


def imports(path, root):
    package = '.'.join(path.relative_to(root.parent).parent.parts)
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            module = resolve_name('.' * node.level + (node.module or ''), package)
            for alias in node.names:
                yield module + '.' + alias.name


def test_stage3_dependencies():
    root = Path(__file__).resolve().parents[2] / 'layauto_v2'
    for owner in ('constraints', 'tech', 'domain'):
        blocked = ['layauto_v2.' + name for name in
                   ('transactions', 'repository', 'importers', 'pipeline', 'normalization', 'tooling', 'planning')]
        if owner in ('tech', 'domain'):
            blocked += ['layauto_v2.constraints', 'layauto_v2.state']
        for path in (root / owner).glob('*.py'):
            for imported in imports(path, root):
                assert not imported.startswith((*blocked, 'legacy_mvp', 'tests', 'docs')), (path, imported)
