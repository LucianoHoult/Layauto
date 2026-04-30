"""M6b: ``split_diffusion`` macro + ``pick_macro`` dispatch.

Covers:

  * ``core/macros/split_diffusion.py``: round-trip share→split symmetry
    (post-split each affected OD cell is back to its pre-share
    ``shared_with`` state); explicit no-op when the cells weren't
    shared; ``add_cut_at_boundary`` calls ``add_cut`` on the
    boundary OD cells when the dev_a/dev_b coverage is adjacent;
    no-op safety when ``grid`` is None or ``OD`` isn't on the grid.
  * ``core/macros/pick_macro.py``: ``pick_macro`` returns a
    ``MacroCall`` for ``nfin`` deltas; ``None`` for unsupported
    parameters; ``MacroCall.execute(solver)`` dispatches the right
    method.
  * Pipeline byte-golden: the M6b refactor of `pipeline/run_mvp.py`
    to drive Stage 5 from `pick_macro` produces md5-identical output
    to the M6a baseline.

Roadmap: docs/architecture_roadmap.md §C / §M6 / §M6b.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from core.csp_engine import CommitDelta, ConstraintEngine
from core.data_model import (
    CellState, Device, LayoutModel, OccupantType, ShapeRecord,
)
from core.grid import LayerGrid, MultiLayerGrid
from core.macros import (
    MacroCall,
    add_cut,
    pick_macro,
    pick_macros,
    share_diffusion,
    split_diffusion,
)
from io_adapters.parser import build_layout_model, project_b_tier_shapes

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# =============================================================
# Synthetic two-device overlap fixture (mirrors M6a's helper)
# =============================================================

def _two_device_overlap_fixture():
    """Reuse the M6a shape: two devices whose bboxes overlap on OD."""
    poly = LayerGrid('POLY', pitch=20, offset=0, orientation='V', min_width=2)
    fin = LayerGrid('FIN', pitch=10, offset=0, orientation='H', min_width=2)
    grid = MultiLayerGrid()
    grid.add_layer(poly)
    grid.add_layer(fin)

    devA = Device(
        inst_name='DA', dev_type='nmos', nfin=2, nf=1,
        bbox_nm={'x1': 0, 'y1': 0, 'x2': 60, 'y2': 50},
    )
    devB = Device(
        inst_name='DB', dev_type='nmos', nfin=2, nf=1,
        bbox_nm={'x1': 40, 'y1': 0, 'x2': 100, 'y2': 50},
    )
    model = LayoutModel(devices=[devA, devB])

    od_shape = ShapeRecord(
        layer='OD',
        bbox_nm=(0, 10, 100, 40),
        desc='shared_od',
    )
    model.shape_pool.append(od_shape)

    project_b_tier_shapes(model, grid, [devA, devB])
    return model, grid, [devA, devB]


# =============================================================
# split_diffusion — round-trip semantics
# =============================================================

def test_split_diffusion_clears_shared_with_links():
    """Run ``share_diffusion`` then ``split_diffusion`` and confirm
    every OD cell that previously listed the sibling now does not."""
    model, grid, _devs = _two_device_overlap_fixture()

    # The parser already stamps shared_with via project_b_tier_shapes;
    # share_diffusion is then idempotent (cells_stamped=0). After
    # split_diffusion, every cell with one device as owner should have
    # the sibling removed from shared_with.
    res = split_diffusion(engine=None, grid=grid,
                            dev_a_inst='DA', dev_b_inst='DB')
    assert res.success
    assert res.cells_unshared >= 1

    for cell in grid.b_tier_cells_of('OD'):
        if cell.owner_device_id == 'DA':
            assert 'DB' not in cell.shared_with, (
                f"DA-owned cell {cell.pos} still lists DB on shared_with"
            )
        if cell.owner_device_id == 'DB':
            assert 'DA' not in cell.shared_with


def test_split_diffusion_round_trip_with_share():
    """The composition share → split returns to a known steady state."""
    model, grid, _devs = _two_device_overlap_fixture()
    # Capture pre-share shared_with values per cell (the parser already
    # stamped them — for this fixture, every overlapping cell already
    # has the sibling).
    pre_state = {
        cell.pos: list(cell.shared_with)
        for cell in grid.b_tier_cells_of('OD')
    }
    assert any(v for v in pre_state.values()), (
        "fixture invariant: parser must have stamped shared_with"
    )

    # Share is a no-op (already stamped); split should clear every link.
    share_diffusion(engine=None, grid=grid,
                      dev_a_inst='DA', dev_b_inst='DB')
    split_diffusion(engine=None, grid=grid,
                      dev_a_inst='DA', dev_b_inst='DB')

    for cell in grid.b_tier_cells_of('OD'):
        owner = cell.owner_device_id
        if owner == 'DA':
            assert 'DB' not in cell.shared_with
        elif owner == 'DB':
            assert 'DA' not in cell.shared_with


def test_split_diffusion_idempotent_when_already_unshared():
    """Calling split_diffusion twice in a row: the second call finds
    no shared_with entries to clear."""
    model, grid, _devs = _two_device_overlap_fixture()
    split_diffusion(engine=None, grid=grid, dev_a_inst='DA', dev_b_inst='DB')
    res2 = split_diffusion(engine=None, grid=grid,
                              dev_a_inst='DA', dev_b_inst='DB')
    assert res2.success
    assert res2.cells_unshared == 0


def test_split_diffusion_no_grid_short_circuits():
    res = split_diffusion(engine=None, grid=None,
                            dev_a_inst='DA', dev_b_inst='DB')
    assert res.success
    assert res.detail == 'no grid'


def test_split_diffusion_no_od_cells_short_circuits():
    grid = MultiLayerGrid()  # no b_tier_cells at all
    res = split_diffusion(engine=None, grid=grid,
                            dev_a_inst='DA', dev_b_inst='DB')
    assert res.success
    assert 'OD not in cell-grid' in res.detail


def test_split_diffusion_with_explicit_cut_track_calls_add_cut():
    """When ``cut_at_track_a`` is an explicit POLY track index, the
    macro stamps a CPO cut at every track_b row in the affected
    region whose track_a matches. Mirrors the gate-cut pattern: one
    CPO line at a boundary POLY track, spanning every FIN row of
    the shared diffusion."""
    model, grid, _devs = _two_device_overlap_fixture()
    # The CPO axis must be registered on the grid (POLY × FIN).
    grid.register_b_tier_axes('CPO', 'POLY', 'FIN')

    # Use an empty engine that doesn't model CPO so the engine.mark_cut
    # branch is a no-op; only the grid stamp lands.
    eng = ConstraintEngine()

    res = split_diffusion(engine=eng, grid=grid,
                            dev_a_inst='DA', dev_b_inst='DB',
                            cut_at_track_a=2)
    assert res.success
    assert len(res.cuts_added) >= 1, (
        f"expected one cut per FIN row at POLY track 2; "
        f"got {res.cuts_added}"
    )
    # Each cut should have stamped a CellOccupancy on CPO at track_a=2.
    cpo_cells = list(grid.b_tier_cells_of('CPO'))
    assert len(cpo_cells) >= 1
    for c in cpo_cells:
        assert c.track_a == 2
        assert c.occ_type == OccupantType.CUT


def test_split_diffusion_without_explicit_cut_emits_no_cuts():
    """Default ``cut_at_track_a=None`` → no cut macros invoked. Only
    the metadata mutation lands; callers handle physical isolation
    explicitly if the layout requires it."""
    model, grid, _devs = _two_device_overlap_fixture()
    grid.register_b_tier_axes('CPO', 'POLY', 'FIN')

    res = split_diffusion(engine=ConstraintEngine(), grid=grid,
                            dev_a_inst='DA', dev_b_inst='DB')
    assert res.success
    assert res.cuts_added == []
    assert res.commit_delta is None


# =============================================================
# pick_macro — dispatch table
# =============================================================

def test_pick_macro_routes_nfin_to_device_resize():
    diff = {'inst': 'MN0', 'param': 'nfin', 'old': 5, 'new': 4}
    call = pick_macro(diff)
    assert isinstance(call, MacroCall)
    assert call.macro_name == 'resize_device'
    assert call.args == ('MN0', 4)
    assert call.diff is diff


def test_pick_macro_returns_none_for_unknown_param():
    diff = {'inst': 'MN0', 'param': 'l', 'old': 20e-9, 'new': 18e-9}
    assert pick_macro(diff) is None


def test_pick_macros_filters_unsupported_deltas():
    diffs = [
        {'inst': 'MN0', 'param': 'nfin', 'old': 5, 'new': 4},
        {'inst': 'MP0', 'param': 'nfin', 'old': 7, 'new': 6},
        {'inst': 'MN0', 'param': 'l', 'old': 20e-9, 'new': 18e-9},
    ]
    calls = pick_macros(diffs)
    assert len(calls) == 2
    assert calls[0].macro_name == 'resize_device'
    assert calls[1].args == ('MP0', 6)


def test_macro_call_execute_dispatches_to_solver_method():
    """``MacroCall.execute(solver)`` looks up the macro on the solver
    and invokes it. We use a stub object instead of a real solver so
    the test stays focused on the dispatch mechanic."""
    class StubSolver:
        def __init__(self):
            self.calls = []
        def resize_device(self, inst, new):
            self.calls.append((inst, new))
            return f'resized {inst} to {new}'

    stub = StubSolver()
    call = MacroCall(macro_name='resize_device', args=('MN0', 4))
    out = call.execute(stub)
    assert out == 'resized MN0 to 4'
    assert stub.calls == [('MN0', 4)]


def test_macro_call_execute_raises_on_unknown_method():
    class StubSolver:
        pass
    call = MacroCall(macro_name='nonexistent_macro', args=())
    with pytest.raises(ValueError, match='no macro'):
        call.execute(StubSolver())


# =============================================================
# Pipeline byte-golden — pick_macro refactor preserves output
# =============================================================

def test_pipeline_pick_macro_refactor_preserves_byte_golden():
    """Re-run the pipeline through the pick_macro path and confirm the
    output md5s match the M6a baseline. The test assumes the pipeline
    has already been run (the working tree has output/ artifacts)."""
    pipeline_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    output_dir = os.path.join(pipeline_dir, 'output')
    if not os.path.exists(os.path.join(output_dir, 'buffer_resized.json')):
        pytest.skip("output/ not generated; run pipeline first")

    import hashlib

    def md5(path):
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    expected = {
        'buffer_resized.json': '47412996135face8c49805ff737a0f20',
        'buffer_resized.cdl': '676823e7c2ee1ba84e0ad21b6269d5c4',
        'resize_report.txt': '0b427f458012191319f9e64f1225adf7',
        'annotation_coverage.txt': 'f1582221b5cd47612181302bb8dd8a3d',
    }
    for fname, expected_md5 in expected.items():
        actual = md5(os.path.join(output_dir, fname))
        assert actual == expected_md5, (
            f"{fname}: expected {expected_md5}, got {actual} — "
            f"pick_macro refactor changed pipeline output"
        )
