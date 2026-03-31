"""
Integration test: full round-trip through the pipeline.

1. Generate dummy fixtures (already done by gen_buffer_layout.py)
2. Parse fixtures into LayoutModel
3. Load into CSP, verify no violations
4. Execute resize
5. Apply edits, write output GDS
6. Compare output shapes against expectations

This test does NOT require gdstk or klayout — it works purely
at the JSON/coordinate level.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.parser import build_layout_model
from io_adapters.cdl_parser import parse_cdl, diff_cdl, get_device_param
from core.solver import LayoutSolver
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')


def _get_nfin_values():
    """Get nfin values from CDL fixtures."""
    orig_cdl = parse_cdl(os.path.join(FIXTURE_DIR, 'buffer_original.cdl'))
    target_cdl = parse_cdl(os.path.join(FIXTURE_DIR, 'buffer_target.cdl'))
    nmos_nfin = get_device_param(orig_cdl, 'MN0', 'nfin', 5)
    pmos_nfin = get_device_param(orig_cdl, 'MP0', 'nfin', 7)
    nmos_nfin_target = get_device_param(target_cdl, 'MN0', 'nfin', 4)
    pmos_nfin_target = get_device_param(target_cdl, 'MP0', 'nfin', 6)
    return nmos_nfin, pmos_nfin, nmos_nfin_target, pmos_nfin_target


def test_full_roundtrip():
    """End-to-end: parse -> CSP -> resize -> verify edit ops generated."""
    config = load_tech_config()
    nmos_nfin, pmos_nfin, nmos_nfin_target, pmos_nfin_target = _get_nfin_values()

    # Stage 2: Parse
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
        config=config,
    )
    assert model.cell_name == f'INV_N{nmos_nfin}_P{pmos_nfin}'

    # Stage 3-4: CSP setup + load
    solver = LayoutSolver(model, grid, config)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    load_ok = solver.load_existing_layout()
    assert load_ok, "CSP loading failed — existing layout violates DRC?"
    assert solver.engine.is_feasible()

    # Stage 5: Resize both devices
    r1 = solver.resize_device('MN0', nmos_nfin_target)
    assert r1.success, f"NMOS resize failed: {r1.message}"

    r2 = solver.resize_device('MP0', pmos_nfin_target)
    assert r2.success, f"PMOS resize failed: {r2.message}"

    # Verify edit ops make sense
    all_ops = r1.edit_ops + r2.edit_ops
    assert len(all_ops) >= 4  # At minimum: 2 fin removes + 2 OD resizes

    fin_removes = [op for op in all_ops
                   if op.op_type == 'remove_shape' and op.layer == 'FIN']
    assert len(fin_removes) == 2

    od_resizes = [op for op in all_ops if op.layer == 'OD']
    assert len(od_resizes) == 2

    print(f"Round-trip test passed: {len(all_ops)} edit operations generated")


def test_resized_params_correct():
    """Verify the resized model has correct device parameters."""
    config = load_tech_config()
    _, _, nmos_nfin_target, _ = _get_nfin_values()

    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
        config=config,
    )

    solver = LayoutSolver(model, grid, config)
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    solver.load_existing_layout()

    r1 = solver.resize_device('MN0', nmos_nfin_target)
    new_model = solver.apply_resize_to_model('MN0', nmos_nfin_target, r1)

    mn = new_model.get_device('MN0')
    assert mn.nfin == nmos_nfin_target


if __name__ == '__main__':
    test_full_roundtrip()
    test_resized_params_correct()
    print("All integration tests passed!")
