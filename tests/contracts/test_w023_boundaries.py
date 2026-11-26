"""Keep Stage 2 preparation, publication and both entry points in their owners."""
import ast
from pathlib import Path


def test_initialization_dependencies():
    root = Path(__file__).resolve().parents[2] / 'layauto_v2'
    blocked = {
        'transactions/initialization.py': ('layauto_v2.normalization', 'layauto_v2.pipeline', 'layauto_v2.importers'),
        'normalization/initial_state.py': ('layauto_v2.transactions', 'layauto_v2.repository'),
        'state/snapshot.py': ('layauto_v2.normalization', 'layauto_v2.repository', 'layauto_v2.transactions'),
        'repository/publication.py': ('layauto_v2.normalization', 'layauto_v2.transactions', 'layauto_v2.state'),
    }
    for filename, forbidden in blocked.items():
        for node in ast.walk(ast.parse((root / filename).read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or '']
            else:
                continue
            assert not any(name.startswith(forbidden) for name in modules), (filename, modules)
