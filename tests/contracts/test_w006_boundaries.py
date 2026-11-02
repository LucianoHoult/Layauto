"""Keep the pre-context implementation within its declared owner boundaries."""
from __future__ import annotations

import ast
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_precontext_module_dependency_boundaries():
    forbidden = {
        'domain': ('pathlib', 'os', 'io', 'subprocess', 'layauto_v2.importers',
                   'layauto_v2.tooling', 'layauto_v2.repository', 'layauto_v2.pipeline'),
        'tooling': ('layauto_v2.importers', 'layauto_v2.repository', 'layauto_v2.pipeline'),
        'importers': ('layauto_v2.tooling', 'layauto_v2.repository', 'layauto_v2.pipeline'),
        'repository': ('layauto_v2.importers', 'layauto_v2.tooling', 'layauto_v2.transactions',
                       'layauto_v2.pipeline', 'layauto_v2.planning', 'layauto_v2.constraints',
                       'layauto_v2.export', 'layauto_v2.validation'),
    }
    violations = []
    for owner, blocked in forbidden.items():
        for path in (REPO / 'layauto_v2' / owner).glob('*.py'):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or '']
                for module in modules:
                    if module.startswith(blocked + ('legacy_mvp', 'tests')):
                        violations.append((path.name, module))
    assert violations == []


def test_coroutine_never_substitutes_a_driver_stop_iteration_for_parse_completion(monkeypatch):
    from layauto_v2.importers import reader

    error = StopIteration('acquisition implementation bug')

    def broken_driver(request):
        raise error

    monkeypatch.setattr(reader, '_component_acquire', broken_driver)
    import pytest
    with pytest.raises(StopIteration) as caught:
        reader.read_inputs(REPO / 'tests/fixtures/w003_m1/site_config.yaml')
    assert caught.value is error
