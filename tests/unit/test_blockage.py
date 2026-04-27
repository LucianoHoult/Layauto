"""M3 acceptance: unannotated shapes project to CSP as BLOCKAGE and
obstruct subsequent ``propose_assign`` rather than being silently
overwritten.

The MVP buffer-resize path is shrink-only, so no production code today
ever calls ``propose_assign`` on cells that an unannotated shape would
cover. To exercise the acceptance contract we:

  1. Build the standard LayoutModel + LayoutSolver from fixtures.
  2. Append a synthetic *unannotated* LI ShapeRecord to ``model.shape_pool``
     in cells that lie outside the existing layout's footprint but inside
     the engine's grid.
  3. Run ``project_unannotated_blockages``.
  4. Assert the cells are now ``BLOCKAGE`` + ``fixed=True``.
  5. Run an L2 ``assign_segment_cells`` against those cells and verify it
     fails with ``failed_pos`` pointing at the blockage.

This is the "infeasible rather than silently overwriting" guarantee the
roadmap calls out for M3.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core import atomic_ops
from core.csp_engine import ConstraintEngine
from core.data_model import (
    BLOCKAGE, CellState, OccupantType, ShapeRecord, EMPTY,
)
from core.solver import LayoutSolver
from io_adapters.parser import build_layout_model
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# -----------------------------------------------------------------
# Engine-level: mark_blockage primitive
# -----------------------------------------------------------------


def _make_engine():
    engine = ConstraintEngine()
    engine.add_layer('LI', n_tracks=4, n_ortho=12)
    engine.initialize_domains({'A', 'B'})
    return engine


def test_mark_blockage_sets_fixed_singleton_domain():
    engine = _make_engine()
    pos = ('LI', 1, 5)
    assert engine.mark_blockage(pos)
    cell = engine.get_cell(pos)
    assert cell.assignment == BLOCKAGE
    assert cell.domain == {BLOCKAGE}
    assert cell.fixed is True


def test_mark_blockage_rejects_propose_assign():
    """The whole point of M3 BLOCKAGE: WIRE assignments at the cell fail."""
    engine = _make_engine()
    pos = ('LI', 1, 5)
    engine.mark_blockage(pos)
    state_a = CellState(OccupantType.WIRE, net_id='A')
    assert engine.propose_assign(pos, state_a) is False


def test_mark_blockage_idempotent():
    engine = _make_engine()
    pos = ('LI', 1, 5)
    assert engine.mark_blockage(pos)
    assert engine.mark_blockage(pos)  # second call no-ops cleanly


def test_mark_blockage_refuses_overwrite_of_assigned_cell():
    """Conservative-defaults: don't silently overwrite an annotated cell."""
    engine = _make_engine()
    pos = ('LI', 1, 5)
    state_a = CellState(OccupantType.WIRE, net_id='A')
    assert engine.propose_assign(pos, state_a)
    # The cell is now WIRE / not fixed. mark_blockage must refuse.
    assert engine.mark_blockage(pos) is False
    cell = engine.get_cell(pos)
    assert cell.assignment == state_a, "annotated assignment must stay intact"


def test_mark_blockage_out_of_bounds_returns_false():
    engine = _make_engine()
    assert engine.mark_blockage(('LI', 99, 99)) is False


# -----------------------------------------------------------------
# Solver projection: shape_pool -> CSP cells
# -----------------------------------------------------------------


def _get_solver():
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
    solver.setup_engine(layers_to_include=['LI', 'M1'])
    solver.load_existing_layout()
    return solver, config


def test_project_unannotated_blockages_no_op_on_clean_fixture():
    """The dummy MVP layout has zero unannotated LI/M1 shapes, so the
    projection must be a no-op (preserves byte-golden)."""
    solver, _ = _get_solver()
    stats = solver.project_unannotated_blockages()
    # No LI or M1 layer in stats means nothing was marked there.
    assert stats.get('LI', 0) == 0
    assert stats.get('M1', 0) == 0


def test_synthetic_li_stub_marks_cells_as_blockage():
    """Inject an unannotated LI ShapeRecord on track 1 spanning ortho 5-6,
    project, and assert the affected cells flip to BLOCKAGE."""
    solver, config = _get_solver()
    grid = solver.grid

    # Pick a track + ortho range that maps cleanly to engine cells *and*
    # is empty on the existing layout. Engine LI grid runs tracks [-1,6);
    # tracks 0/1/2 host the four annotated S/D bars + gate contact.
    # Track 4 is well clear of the annotated footprint.
    li_grid = grid.get_layer('LI')
    m1_grid = grid.get_layer('M1')
    track_idx = 4
    ortho_start, ortho_end = 5, 6

    # Compute a bbox that the grid will round-trip back to the same
    # (track_idx, start_anchor, end_anchor).
    cx = li_grid.track_to_physical(track_idx)
    y_start = m1_grid.track_to_physical(ortho_start)
    y_end = m1_grid.track_to_physical(ortho_end)
    half_w = config.LI_WIDTH // 2
    bbox = (cx - half_w, y_start, cx + half_w, y_end)

    stub = ShapeRecord(
        layer='LI', bbox_nm=bbox, desc='synthetic_stub',
    )
    # Both fields are None by default - reaffirm for clarity.
    assert stub.is_annotated is False
    solver.model.shape_pool.append(stub)

    # First confirm the cells are not yet BLOCKAGE.
    for o in (ortho_start, ortho_end):
        cell = solver.engine.get_cell(('LI', track_idx, o))
        assert cell is not None
        assert cell.assignment != BLOCKAGE

    stats = solver.project_unannotated_blockages()
    assert stats.get('LI', 0) >= 2

    # Each cell is now a fixed BLOCKAGE.
    for o in (ortho_start, ortho_end):
        cell = solver.engine.get_cell(('LI', track_idx, o))
        assert cell.assignment == BLOCKAGE
        assert cell.fixed is True


def test_li_stub_makes_assign_segment_cells_infeasible():
    """M3 acceptance: an unannotated LI stub blocks an L2 assign-extension.

    Mirrors the resize-extension scenario the roadmap calls out — L3
    macros that try to grow a segment into the stub's cells must surface
    ``failed_pos`` rather than silently overwriting the obstacle.
    """
    solver, config = _get_solver()
    grid = solver.grid
    li_grid = grid.get_layer('LI')
    m1_grid = grid.get_layer('M1')

    # Pick LI track 4 (well clear of the four annotated S/D + gate
    # tracks 0/1/2) and ortho 5 (well inside engine ortho range
    # [-2,14)). The bbox is a tiny rectangle centered exactly on
    # (track_idx=4, ortho=5) so build_layout_model's grid round-trip
    # places the cell exactly where we expect.
    track_idx = 4
    ortho_target = 5
    cx = li_grid.track_to_physical(track_idx)
    y_along = m1_grid.track_to_physical(ortho_target)
    half_w = config.LI_WIDTH // 2
    bbox = (cx - half_w, y_along - 1, cx + half_w, y_along + 1)

    stub = ShapeRecord(layer='LI', bbox_nm=bbox, desc='unannotated_stub')
    solver.model.shape_pool.append(stub)

    target_pos = ('LI', track_idx, ortho_target)
    pre_cell = solver.engine.get_cell(target_pos)
    assert pre_cell is not None, \
        f"engine must model {target_pos} for this test"
    assert pre_cell.assignment == EMPTY, \
        f"target cell must be unoccupied pre-projection (got {pre_cell.assignment})"

    stats = solver.project_unannotated_blockages()
    assert stats.get('LI', 0) >= 1

    # Now ask L2 to assign WIRE into the blocked cell — the L3 macro's
    # extension path surfaces ``failed_pos`` instead of silently
    # overwriting the obstacle.
    cp = solver.engine.checkpoint()
    res = atomic_ops.assign_segment_cells(
        solver.engine, 'LI', track_idx,
        [ortho_target], net_id='SYN',
    )
    assert res.success is False
    assert res.failed_pos == target_pos
    # Engine state restorable.
    solver.engine.restore(cp)


if __name__ == '__main__':
    test_mark_blockage_sets_fixed_singleton_domain()
    test_mark_blockage_rejects_propose_assign()
    test_mark_blockage_idempotent()
    test_mark_blockage_refuses_overwrite_of_assigned_cell()
    test_mark_blockage_out_of_bounds_returns_false()
    test_project_unannotated_blockages_no_op_on_clean_fixture()
    test_synthetic_li_stub_marks_cells_as_blockage()
    test_li_stub_makes_assign_segment_cells_infeasible()
    print("All blockage / M3-acceptance tests passed!")
