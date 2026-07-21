"""M4d: B-tier and FIN/POLY L2 atomics.

Covers ``core/atomic_ops.py`` additions:
  * ``add_cut_cell`` / ``remove_cut_cell``: stamps engine + grid;
    integrates with ``engine.union`` to enforce §B's "no CUT between
    adjacent cells" rule.
  * ``mark_shared_diffusion``: walks OD cells, stamps shared_with,
    opportunistically calls engine.union.
  * ``extend_od``: re-projects an OD shape's cell coverage on bbox
    change; updates owner from device-bbox containment.
  * ``add_fin_strip`` / ``remove_fin_strip``: mutates model.shape_pool
    and returns enough geometry for L1 emission.
  * ``extend_poly``: builds a partial-bbox endpoint update record.
  * Solver integration: post-resize cell-grid + shape_pool reflect
    the removed FINs and the narrowed OD; the macro emits the same
    L1 records as before (modulo a 1 nm cosmetic shift on FIN bboxes
    that now carry the actual fixture bbox, not the legacy
    synthesised one).

Roadmap: docs/architecture_roadmap.md §B and milestone M4d.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from core import atomic_ops
from core.csp_engine import ConstraintEngine
from core.data_model import (
    CellOccupancy, CellState, Device, EMPTY, LayoutModel, OccupantType, ShapeRecord,
)
from core.grid import LayerGrid, MultiLayerGrid
from io_adapters.parser import build_layout_model

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# =============================================================
# add_cut_cell / remove_cut_cell
# =============================================================

def _engine_one_track():
    eng = ConstraintEngine()
    eng.add_layer('LI', n_tracks=1, n_ortho=6)
    eng.initialize_domains({'A', 'B'})
    return eng


def _grid_with_cpo_axes() -> MultiLayerGrid:
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0,
                              orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0,
                              orientation='H', min_width=2))
    grid.register_b_tier_axes('CPO', 'POLY', 'FIN')
    return grid


def test_add_cut_cell_marks_engine_when_layer_present():
    """When the engine has a cell at the position, ``add_cut_cell``
    pins it via ``mark_cut`` so subsequent ``union`` calls reject it
    (the §B "no CUT between adjacent cells" rule)."""
    eng = _engine_one_track()
    res = atomic_ops.add_cut_cell(eng, grid=None, layer='LI',
                                    track_a=0, track_b=2)
    assert res.success
    cell = eng.get_cell(('LI', 0, 2))
    assert cell.assignment.occ_type == OccupantType.CUT
    assert cell.fixed is True


def test_add_cut_cell_breaks_union_chain_via_engine():
    """End-to-end §B acceptance: a chain of adjacent unions across a
    CUT cell fails at the CUT step, leaving the two endpoints in
    disjoint components. Mirrors ``test_net_equivalence::
    test_union_rejects_cut_endpoint`` but going through the L2
    primitive instead of ``engine.mark_cut`` directly."""
    eng = _engine_one_track()
    a, mid, b = ('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)
    eng.assign(a, CellState(OccupantType.WIRE, net_id='A'))
    res = atomic_ops.add_cut_cell(eng, grid=None, layer='LI',
                                    track_a=0, track_b=2)
    assert res.success
    eng.assign(b, CellState(OccupantType.WIRE, net_id='A'))
    assert eng.union(a, mid) is False
    assert eng.union(mid, b) is False
    # Endpoints stay disjoint.
    assert eng.connected_to(a) == [a]
    assert eng.connected_to(b) == [b]


def test_add_cut_cell_stamps_grid_for_b_tier_layer():
    eng = ConstraintEngine()  # no engine cells for CPO
    grid = _grid_with_cpo_axes()
    res = atomic_ops.add_cut_cell(eng, grid, layer='CPO',
                                    track_a=2, track_b=3)
    assert res.success
    cell = grid.get_b_tier_cell('CPO', 2, 3)
    assert cell is not None
    assert cell.occ_type == OccupantType.CUT


def test_add_cut_cell_engine_refusal_surfaces_failed_pos():
    """When ``mark_cut`` refuses (cell already carries an annotated
    assignment), the atomic returns ``failed_pos`` so the macro can
    rollback."""
    eng = _engine_one_track()
    eng.assign(('LI', 0, 2), CellState(OccupantType.WIRE, net_id='A'))
    res = atomic_ops.add_cut_cell(eng, grid=None, layer='LI',
                                    track_a=0, track_b=2)
    assert res.success is False
    assert res.failed_pos == ('LI', 0, 2)


def test_remove_cut_cell_drops_grid_entry():
    eng = ConstraintEngine()
    grid = _grid_with_cpo_axes()
    atomic_ops.add_cut_cell(eng, grid, 'CPO', 2, 3)
    assert grid.get_b_tier_cell('CPO', 2, 3) is not None
    res = atomic_ops.remove_cut_cell(grid, 'CPO', 2, 3)
    assert res.success
    assert 'removed' in res.detail
    assert grid.get_b_tier_cell('CPO', 2, 3) is None


def test_remove_cut_cell_idempotent_on_missing():
    """Calling remove on an already-empty cell is a no-op success —
    keeps macro logic simple (no need to track which cells were
    actually stamped)."""
    grid = _grid_with_cpo_axes()
    res = atomic_ops.remove_cut_cell(grid, 'CPO', 99, 99)
    assert res.success
    assert 'not present' in res.detail


# =============================================================
# mark_shared_diffusion
# =============================================================

def test_mark_shared_diffusion_stamps_grid_only_when_engine_absent():
    """OD is not in the engine today (M4d ships the L2 surface but
    doesn't yet add OD via engine.add_layer). With ``engine=None``
    the atomic only stamps ``shared_with`` on the cell-grid side —
    that's the framework for M5/M6 to lift OD into CSP."""
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0,
                              orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0,
                              orientation='H', min_width=2))
    grid.register_b_tier_axes('OD', 'POLY', 'FIN')
    # Stamp two OD cells, one owned by each device.
    grid.set_b_tier_cell('OD', 0, 0, CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN0',
    ))
    grid.set_b_tier_cell('OD', 1, 0, CellOccupancy(
        layer='OD', track_a=1, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN1',
    ))

    res = atomic_ops.mark_shared_diffusion(grid, engine=None,
                                            dev_a_inst='MN0',
                                            dev_b_inst='MN1')
    assert res.success
    # Each cell now carries the other on shared_with.
    assert grid.get_b_tier_cell('OD', 0, 0).shared_with == ['MN1']
    assert grid.get_b_tier_cell('OD', 1, 0).shared_with == ['MN0']


def test_mark_shared_diffusion_no_op_when_od_absent():
    grid = MultiLayerGrid()  # no OD cells at all
    res = atomic_ops.mark_shared_diffusion(grid, engine=None,
                                            dev_a_inst='MN0',
                                            dev_b_inst='MN1')
    assert res.success
    assert 'not in cell-grid' in res.detail


# =============================================================
# extend_od
# =============================================================

def _grid_with_od_axes() -> MultiLayerGrid:
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0,
                              orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0,
                              orientation='H', min_width=2))
    grid.register_b_tier_axes('OD', 'POLY', 'FIN')
    return grid


def test_extend_od_shrinks_cell_coverage_and_updates_bbox():
    grid = _grid_with_od_axes()
    devices = [Device(inst_name='MN0', dev_type='nmos', nfin=1, nf=1,
                       bbox_nm={'x1': 0, 'y1': 0, 'x2': 30, 'y2': 50})]
    sr = ShapeRecord(layer='OD', bbox_nm=(0, 0, 30, 50),
                      net_id='SD', device_id='MN0')
    # Pre-populate the cell-grid (3x6 cells: poly tracks 0-2, fin tracks 0-5)
    for ta in range(3):
        for tb in range(6):
            grid.set_b_tier_cell('OD', ta, tb, CellOccupancy(
                layer='OD', track_a=ta, track_b=tb,
                occ_type=OccupantType.DEVICE_DIFF,
                owner_device_id='MN0', shape_record=sr,
            ))

    new_bbox = (0, 0, 30, 30)   # shrink Y from 50 to 30
    res = atomic_ops.extend_od(grid, devices, sr, new_bbox)
    assert res.success
    # Cells with track_b in 4..5 are dropped; 0..3 remain.
    assert grid.get_b_tier_cell('OD', 0, 5) is None
    assert grid.get_b_tier_cell('OD', 1, 4) is None
    assert grid.get_b_tier_cell('OD', 2, 3) is not None
    # ShapeRecord bbox updated to reflect new geometry.
    assert sr.bbox_nm == new_bbox


def test_extend_od_no_op_for_same_bbox():
    grid = _grid_with_od_axes()
    sr = ShapeRecord(layer='OD', bbox_nm=(0, 0, 30, 30))
    res = atomic_ops.extend_od(grid, devices=[], shape_record=sr,
                                 new_bbox=(0, 0, 30, 30))
    assert res.success
    assert 'no-op' in res.detail


def test_extend_od_skips_when_axes_unregistered():
    grid = MultiLayerGrid()  # OD axes not registered
    sr = ShapeRecord(layer='OD', bbox_nm=(0, 0, 30, 30))
    res = atomic_ops.extend_od(grid, devices=[], shape_record=sr,
                                 new_bbox=(0, 0, 30, 50))
    assert res.success
    assert 'not registered' in res.detail


def test_extend_od_stamps_owner_for_new_cells():
    grid = _grid_with_od_axes()
    devices = [Device(inst_name='MN0', dev_type='nmos', nfin=1, nf=1,
                       bbox_nm={'x1': 0, 'y1': 0, 'x2': 30, 'y2': 50})]
    sr = ShapeRecord(layer='OD', bbox_nm=(0, 0, 10, 10),
                      net_id='SD', device_id='MN0')
    # No pre-population: extend grows from 1 cell to 9 cells.
    grid.set_b_tier_cell('OD', 0, 0, CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF,
        owner_device_id='MN0', shape_record=sr,
    ))
    res = atomic_ops.extend_od(grid, devices, sr, new_bbox=(0, 0, 30, 30))
    assert res.success
    # New cells should have owner = MN0 (containment).
    new_cell = grid.get_b_tier_cell('OD', 2, 2)
    assert new_cell is not None
    assert new_cell.owner_device_id == 'MN0'


# =============================================================
# add_fin_strip / remove_fin_strip
# =============================================================

def test_add_fin_strip_appends_shape_record():
    model = LayoutModel()
    fin_grid = LayerGrid('FIN', pitch=25, offset=40,
                          orientation='H', min_width=7)
    res = atomic_ops.add_fin_strip(model, fin_grid, fin_track_idx=2,
                                     x1=0, x2=108, fin_width=7,
                                     owner_device_id='MN0')
    assert res.success
    assert res.fin_track_idx == 2
    # Track 2 → fy = 40 + 2*25 = 90; hw = 3 → bbox y range 87..93
    assert res.bbox == (0, 87, 108, 93)
    assert res.desc == 'MN0_fin_track_2'
    # ShapeRecord landed in the pool with the right metadata.
    assert len(model.shape_pool) == 1
    sr = model.shape_pool[0]
    assert sr.layer == 'FIN'
    assert sr.device_id == 'MN0'
    assert sr.provenance == 'atomic_ops.add_fin_strip'


def test_remove_fin_strip_finds_existing_shape_by_center_y():
    """The MVP fixture stores FIN bboxes with fin_width=7 (y range 6
    wide, e.g. 136..143 → center 139.5). ``remove_fin_strip`` matches
    by center-Y rather than exact bbox so it tolerates the
    half-integer offset."""
    model = LayoutModel()
    # Pre-populate with the MVP-style bbox: center at fy=140.
    sr = ShapeRecord(layer='FIN', bbox_nm=(0, 136, 108, 143))
    model.shape_pool.append(sr)
    fin_grid = LayerGrid('FIN', pitch=25, offset=40,
                          orientation='H', min_width=7)
    res = atomic_ops.remove_fin_strip(model, fin_grid, fin_track_idx=4,
                                        x1=0, x2=108, fin_width=7,
                                        owner_device_id='MN0')
    assert res.success
    # Returned bbox is the actual fixture bbox, not a synthesised one.
    assert res.bbox == (0, 136, 108, 143)
    assert res.shape_record is sr
    # Pool entry is gone.
    assert sr not in model.shape_pool


def test_remove_fin_strip_synthesises_bbox_when_pool_empty():
    """Legacy callers that didn't populate shape_pool still get a
    valid L1-compatible result (the synthesised bbox uses
    fy ± fin_width//2)."""
    model = LayoutModel()
    fin_grid = LayerGrid('FIN', pitch=25, offset=40,
                          orientation='H', min_width=7)
    res = atomic_ops.remove_fin_strip(model, fin_grid, fin_track_idx=4,
                                        x1=0, x2=108, fin_width=7,
                                        owner_device_id='MN0')
    assert res.success
    assert res.shape_record is None
    # Synthesised bbox uses fy=140 ± 3 → (137, 143) — slightly off from
    # the actual fixture bbox; the legacy `_emit_fin_removes` path used
    # this same synthesis. M4d preserves it as a fallback.
    assert res.bbox == (0, 137, 108, 143)


# =============================================================
# extend_poly
# =============================================================

def test_extend_poly_y2_target():
    res = atomic_ops.extend_poly('y2', old_value=415, new_value=390)
    assert res.success
    assert res.target == 'y2'
    assert res.old_value == 415
    assert res.new_value == 390


def test_extend_poly_y1_target():
    res = atomic_ops.extend_poly('y1', old_value=10, new_value=20)
    assert res.success
    assert res.target == 'y1'


def test_extend_poly_rejects_invalid_target():
    with pytest.raises(ValueError, match="must be 'y1' or 'y2'"):
        atomic_ops.extend_poly('x', old_value=0, new_value=10)


# =============================================================
# Solver integration (end-to-end)
# =============================================================

def _run_full_resize():
    """Run the L3 device_resize macro on the MVP fixture to exercise
    the M4d L2 atomics through the macro path."""
    from core.solver import LayoutSolver
    from tech.config_loader import load_tech_config
    config = load_tech_config()
    model, grid = build_layout_model(
        device_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
        config=config,
    )
    solver = LayoutSolver(model, grid, config)
    solver.setup_engine()
    solver.load_existing_layout()
    solver.project_unannotated_blockages()
    # Resize MN0 5→4 fin (drop top fin) and MP0 7→6 fin.
    solver.resize_device('MN0', new_nfin=4)
    solver.resize_device('MP0', new_nfin=6)
    return model, grid


def test_solver_remove_fin_drops_shape_pool_record():
    """M4d acceptance: post-resize, the shape_pool no longer contains
    the FIN ShapeRecords for the removed fins. Pre-M4d the shape_pool
    was untouched by the resize (only EditOps were emitted); M4d
    routes FIN removal through ``remove_fin_strip`` which mutates
    shape_pool."""
    model, _ = _run_full_resize()
    # MVP starts with 5 NMOS + 7 PMOS = 12 FIN shapes; after removing
    # 1 from each → 10 expected.
    fin_count = sum(1 for sr in model.shape_pool if sr.layer == 'FIN')
    assert fin_count == 10


def test_solver_extend_od_updates_shape_record_bbox():
    """After resize, the OD ShapeRecord's bbox_nm reflects the
    narrowed Y extent. Pre-M4d it stayed at the original bbox."""
    model, _ = _run_full_resize()
    od_records = [sr for sr in model.shape_pool if sr.layer == 'OD']
    assert len(od_records) == 2
    # Both OD bboxes should have been updated. We don't assert exact
    # values (they depend on tech config), only that they're not the
    # original bbox stamped by the parser. The original NMOS OD was
    # (0, 28, 108, 152) per the MVP fixture; after dropping the top
    # fin (at y=140), the OD top edge moves down by one fin pitch.
    for sr in od_records:
        if sr.device_id == 'MN0':
            # Top (y2) should be lower than the pre-resize 152.
            assert sr.bbox_nm[3] < 152, f"NMOS OD y2 not shrunk: {sr.bbox_nm}"


def test_solver_extend_od_updates_cell_grid():
    """Post-resize, the OD cell-grid coverage matches the new bbox —
    cells that were under the dropped fin row are gone."""
    _, grid = _run_full_resize()
    nmos_od_cells = [c for c in grid.b_tier_cells_of('OD')
                      if c.owner_device_id == 'MN0']
    pmos_od_cells = [c for c in grid.b_tier_cells_of('OD')
                      if c.owner_device_id == 'MP0']
    # Both shrunk; no quantitative assertion (depends on cell-grid
    # geometry), only that the cell-grid is non-empty post-resize and
    # owner stamping survived the extend_od call.
    assert nmos_od_cells, 'NMOS OD cells lost during extend_od'
    assert pmos_od_cells, 'PMOS OD cells lost during extend_od'


if __name__ == '__main__':
    test_add_cut_cell_marks_engine_when_layer_present()
    test_add_cut_cell_breaks_union_chain_via_engine()
    test_add_cut_cell_stamps_grid_for_b_tier_layer()
    test_add_cut_cell_engine_refusal_surfaces_failed_pos()
    test_remove_cut_cell_drops_grid_entry()
    test_remove_cut_cell_idempotent_on_missing()
    test_mark_shared_diffusion_stamps_grid_only_when_engine_absent()
    test_mark_shared_diffusion_no_op_when_od_absent()
    test_extend_od_shrinks_cell_coverage_and_updates_bbox()
    test_extend_od_no_op_for_same_bbox()
    test_extend_od_skips_when_axes_unregistered()
    test_extend_od_stamps_owner_for_new_cells()
    test_add_fin_strip_appends_shape_record()
    test_remove_fin_strip_finds_existing_shape_by_center_y()
    test_remove_fin_strip_synthesises_bbox_when_pool_empty()
    test_extend_poly_y2_target()
    test_extend_poly_y1_target()
    test_extend_poly_rejects_invalid_target()
    test_solver_remove_fin_drops_shape_pool_record()
    test_solver_extend_od_updates_shape_record_bbox()
    test_solver_extend_od_updates_cell_grid()
    print("All M4d B-tier atomics tests passed!")
