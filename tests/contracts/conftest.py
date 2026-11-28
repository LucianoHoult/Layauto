import pytest


@pytest.fixture(scope='session')
def normal_rules(tmp_path_factory):
    """One W026 normal publication and one check shared by all rule contracts."""
    from w026_cases import inspect_published, stage_rules
    root = stage_rules(tmp_path_factory.mktemp('w026-normal'), 'normal')
    return inspect_published(root, 'normal')
