"""Test solver: CSP loading and resize operations."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.parser import build_layout_model
from core.solver import LayoutSolver

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')


def _get_solver():
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )
    solver = LayoutSolver(model, grid)
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


if __name__ == '__main__':
    test_csp_load_no_violations()
    test_resize_nmos_success()
    test_resize_pmos_success()
    test_resize_invalid_device()
    test_resize_increase_rejected()
    test_edit_ops_contain_fin_removal()
    print("All solver tests passed!")
