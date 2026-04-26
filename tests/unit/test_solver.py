"""Test solver: CSP loading and resize operations."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.parser import build_layout_model
from core.solver import LayoutSolver
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')
_config = load_tech_config()


def _get_solver():
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
        config=_config,
    )
    solver = LayoutSolver(model, grid, _config)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    solver.load_existing_layout()
    return solver


def test_csp_load_no_violations():
    solver = _get_solver()
    assert solver.engine.is_feasible()
    stats = solver.engine.domain_stats()
    assert stats['empty_domain'] == 0


def test_resize_nmos_success():
    solver = _get_solver()
    result = solver.resize_device('MN0', 4)
    assert result.success
    assert len(result.edit_ops) > 0


def test_resize_pmos_success():
    solver = _get_solver()
    result = solver.resize_device('MP0', 6)
    assert result.success


def test_resize_invalid_device():
    solver = _get_solver()
    result = solver.resize_device('NONEXISTENT', 4)
    assert not result.success


def test_resize_increase_rejected():
    solver = _get_solver()
    result = solver.resize_device('MN0', 8)  # Increase from 5
    assert not result.success


def test_edit_ops_contain_fin_removal():
    solver = _get_solver()
    result = solver.resize_device('MN0', 4)
    fin_removes = [op for op in result.edit_ops
                   if op.op_type == 'remove_shape' and op.layer == 'FIN']
    assert len(fin_removes) == 1  # Remove 1 fin


def test_resize_device_rolls_back_engine_on_csp_conflict():
    """M2 acceptance: macro returns infeasible + restores CSP on conflict.

    The MVP shrink path doesn't naturally trigger an L2 propose_assign,
    so we monkey-patch ``atomic_ops.modify_segment`` to simulate a
    cell-level conflict (e.g. a hypothetical LI-vs-VIA collision under
    a future extension scenario). The macro must:

      * return ``ResizeResult(success=False, ...)``;
      * restore the CSP engine so its post-call snapshot equals the
        pre-call snapshot byte-for-byte.
    """
    from core import atomic_ops as ao

    solver = _get_solver()
    snap_before = solver.engine.snapshot()

    original_modify = ao.modify_segment
    ao.modify_segment = lambda *args, **kwargs: ao.AtomicResult(
        success=False, failed_pos=('LI', 1, 99), detail='injected conflict',
    )
    try:
        result = solver.resize_device('MN0', 4)
    finally:
        ao.modify_segment = original_modify

    assert result.success is False
    assert 'conflict' in result.message.lower()

    snap_after = solver.engine.snapshot()
    assert snap_before == snap_after, (
        "CSP state must be byte-equal to the pre-call snapshot after rollback"
    )


def test_resize_device_commits_csp_delta_on_success():
    """Successful resize commits + truncates the trail past the macro's checkpoint."""
    solver = _get_solver()
    cp_outside = solver.engine.checkpoint()
    result = solver.resize_device('MN0', 4)
    assert result.success
    # Trail past the outer checkpoint exists only for committed deltas
    # — the macro's internal checkpoint is gone (commit truncates).
    # A subsequent restore from cp_outside still rolls back successfully.
    solver.engine.restore(cp_outside)


if __name__ == '__main__':
    test_csp_load_no_violations()
    test_resize_nmos_success()
    test_resize_pmos_success()
    test_resize_invalid_device()
    test_resize_increase_rejected()
    test_edit_ops_contain_fin_removal()
    test_resize_device_rolls_back_engine_on_csp_conflict()
    test_resize_device_commits_csp_delta_on_success()
    print("All solver tests passed!")
