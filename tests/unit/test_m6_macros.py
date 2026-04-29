"""M6: L3 macro family + decoder rejection of derived-shape edits.

Covers:

  * ``WritebackDecoder.apply`` raises ``DerivedShapeEditError`` when an
    incoming ``EditOp`` targets a ShapeRecord stamped ``is_derived=True``
    (per docs/architecture_roadmap.md §C: only the M5 ``DRCDerivator``
    may edit C1 markings).
  * The derivator's own ops are exempt — its ``desc='derived_<layer>_y2_shift''
    convention is the disambiguator.
  * MVP byte-golden pipeline still works: the rejection check is a
    no-op when no macro reaches for derived shapes.
  * ``core/macros/cut_ops.py``: ``add_cut`` brackets ``add_cut_cell``
    in checkpoint / commit_with_full_delta; on engine refusal it
    restores; the §B "no CUT between adjacent cells" rule fires
    end-to-end through the macro.
  * ``remove_cut`` is grid-only and idempotent (per the M4d
    ``remove_cut_cell`` contract).
  * ``core/macros/share_diffusion.py``: with a synthetic two-device
    overlapping fixture, ``share_diffusion`` stamps shared_with on the
    OD cells and (when the engine models OD) records the union events
    in the returned ``CommitDelta``.
  * ``device_resize`` macro now uses ``commit_with_full_delta`` — the
    MVP buffer-resize still passes byte-golden because no unions land
    on the LI/M1 transaction (these are A-tier WIRE cells).

Roadmap: docs/architecture_roadmap.md §B / §C / §M6.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import copy

import pytest

from core import atomic_ops
from core.csp_engine import CommitDelta, ConstraintEngine
from core.data_model import (
    CellOccupancy, CellState, Device, LayoutModel, OccupantType, ShapeRecord,
)
from core.decoder import DerivedShapeEditError, WritebackDecoder
from core.diff import EditOp
from core.drc_derivator import DRCDerivator
from core.grid import LayerGrid, MultiLayerGrid
from core.macros import add_cut, remove_cut, share_diffusion
from io_adapters.parser import build_layout_model, project_b_tier_shapes
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# =============================================================
# Decoder rejection of edits to derived shapes
# =============================================================

def _model_with_derived_nwell():
    """Build a tiny model carrying one is_derived NWELL shape."""
    model = LayoutModel()
    model.shape_pool.append(ShapeRecord(
        layer='NWELL',
        bbox_nm=(0, 0, 100, 200),
        desc='nwell',
        is_derived=True,
        provenance='drc_derivator._derive_nwell',
    ))
    return model


def _orig_data_with_nwell(y2=200):
    return {
        'params': {
            'nmos_fin_y': [40, 65, 90, 115, 140],
            'pmos_fin_y': [240, 265, 290, 315, 340, 365, 390],
            'nmos_nfin': 5,
            'pmos_nfin': 7,
        },
        'shapes': {
            'FIN': [],
            'OD': [],
            'POLY': [],
            'LI': [],
            'NWELL': [{'x1': 0, 'y1': 0, 'x2': 100, 'y2': y2}],
            'BOUNDARY': [],
        },
        'devices': [],
    }


def test_decoder_rejects_macro_edit_to_derived_shape():
    """A macro-emitted EditOp on an ``is_derived=True`` shape raises."""
    config = load_tech_config()
    model = _model_with_derived_nwell()
    decoder = WritebackDecoder(MultiLayerGrid(), config)

    bad_op = EditOp(
        op_type='modify_shape',
        layer='NWELL',
        old_bbox=(0, 0, 100, 200),
        new_bbox=(0, 0, 100, 999),
        desc='evil_macro_nwell_shrink',  # NOT a derivator desc
    )
    with pytest.raises(DerivedShapeEditError) as excinfo:
        decoder.apply(_orig_data_with_nwell(), [bad_op],
                       new_nmos_nfin=4, new_pmos_nfin=6, model=model)
    assert excinfo.value.op is bad_op
    assert excinfo.value.shape_record.layer == 'NWELL'


def test_decoder_allows_derivator_edit_to_derived_shape():
    """Derivator-emitted ops carry ``desc='derived_<layer>_y2_shift'``
    and are exempt from the rejection check."""
    config = load_tech_config()
    model = _model_with_derived_nwell()
    decoder = WritebackDecoder(MultiLayerGrid(), config)

    derivator_op = EditOp(
        op_type='modify_shape',
        layer='NWELL',
        old_bbox=(0, 0, 100, 200),
        new_bbox=(0, 0, 100, 395),
        desc='derived_nwell_y2_shift',
    )
    result = decoder.apply(_orig_data_with_nwell(), [derivator_op],
                             new_nmos_nfin=4, new_pmos_nfin=6, model=model)
    assert result['shapes']['NWELL'][0]['y2'] == 395


def test_decoder_skips_check_when_no_model_passed():
    """Legacy callers that don't pass a model see prior behaviour."""
    config = load_tech_config()
    decoder = WritebackDecoder(MultiLayerGrid(), config)

    # Even though this op would target a derived shape, no model means
    # no check, no rejection.
    op = EditOp(
        op_type='modify_shape',
        layer='NWELL',
        old_bbox=(0, 0, 100, 200),
        new_bbox=(0, 0, 100, 999),
        desc='unchecked',
    )
    result = decoder.apply(_orig_data_with_nwell(), [op],
                             new_nmos_nfin=4, new_pmos_nfin=6)
    assert result['shapes']['NWELL'][0]['y2'] == 999


def test_decoder_skips_unrelated_ops_when_model_has_no_derived_shapes():
    """If shape_pool has no derived shapes, the check returns immediately."""
    config = load_tech_config()
    model = LayoutModel()
    model.shape_pool.append(ShapeRecord(
        layer='LI', bbox_nm=(0, 0, 100, 50), is_derived=False,
    ))
    decoder = WritebackDecoder(MultiLayerGrid(), config)
    op = EditOp(
        op_type='modify_shape',
        layer='NWELL',
        old_bbox=(0, 0, 100, 999),
        new_bbox=(0, 0, 100, 1000),
    )
    # Should NOT raise: no derived shape in pool.
    result = decoder.apply(_orig_data_with_nwell(y2=999), [op],
                             new_nmos_nfin=4, new_pmos_nfin=6, model=model)
    assert result['shapes']['NWELL'][0]['y2'] == 1000


def test_decoder_pipeline_byte_golden_path_still_works():
    """The full MVP pipeline path (parser → derivator → decoder) does
    not trigger the rejection: every NWELL/BOUNDARY op carries the
    derivator's ``derived_*`` prefix, so the derived shapes happily
    accept their own derivator-emitted updates."""
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )
    config = load_tech_config()
    derivator = DRCDerivator(model, grid, config)
    nmos_fin_y_new = [40, 65, 90, 115]
    pmos_fin_y_new = [240, 265, 290, 315, 340, 365]
    edit_ops = derivator.derive_c1(nmos_fin_y_new, pmos_fin_y_new)
    assert any(op.layer == 'NWELL' for op in edit_ops)

    import json
    with open(os.path.join(FIXTURE_DIR, 'buffer_original.json')) as f:
        orig_data = json.load(f)

    decoder = WritebackDecoder(grid, config)
    # Should NOT raise: all derivator ops carry the exempt prefix.
    out = decoder.apply(orig_data, edit_ops,
                          new_nmos_nfin=4, new_pmos_nfin=6, model=model)
    assert out['shapes']['NWELL'][0]['y2'] == 395


# =============================================================
# core/macros/cut_ops.py — add_cut / remove_cut
# =============================================================

def _engine_one_track(orth=6):
    eng = ConstraintEngine()
    eng.add_layer('LI', n_tracks=1, n_ortho=orth)
    eng.initialize_domains({'A', 'B'})
    return eng


def test_add_cut_macro_brackets_in_checkpoint_commit():
    """``add_cut`` opens a checkpoint, calls L2, commits with full_delta.
    Because ``mark_cut`` pins the cell directly (bypassing the trail),
    the cell delta is naturally empty — the actual mutation is on
    ``cell.fixed`` / ``cell.assignment``. The macro's contract is:
    success returned, engine cell pinned, and ``commit_delta`` is a
    well-formed ``CommitDelta`` (even if empty)."""
    eng = _engine_one_track()
    res = add_cut(eng, grid=None, layer='LI', track_a=0, track_b=2)
    assert res.success
    assert res.commit_delta is not None
    assert isinstance(res.commit_delta, CommitDelta)
    assert res.commit_delta.unions == []
    # The actual mutation is on the engine's cell state.
    cell = eng.get_cell(('LI', 0, 2))
    assert cell.assignment.occ_type == OccupantType.CUT
    assert cell.fixed is True


def test_add_cut_macro_restores_on_engine_refusal():
    """If the cell already carries an annotated assignment, the L2
    ``mark_cut`` call refuses; the macro restores to the checkpoint and
    surfaces ``failed_pos``."""
    eng = _engine_one_track()
    eng.assign(('LI', 0, 2), CellState(OccupantType.WIRE, net_id='A'))
    snap_before = eng.snapshot()
    res = add_cut(eng, grid=None, layer='LI', track_a=0, track_b=2)
    assert res.success is False
    assert res.failed_pos == ('LI', 0, 2)
    # Engine state must match pre-call snapshot.
    snap_after = eng.snapshot()
    assert snap_before == snap_after


def test_add_cut_macro_blocks_subsequent_union():
    """End-to-end §B "no CUT between adjacent cells" via the L3 macro."""
    eng = _engine_one_track()
    a, mid, b = ('LI', 0, 1), ('LI', 0, 2), ('LI', 0, 3)
    eng.assign(a, CellState(OccupantType.WIRE, net_id='A'))
    eng.assign(b, CellState(OccupantType.WIRE, net_id='A'))

    res = add_cut(eng, grid=None, layer='LI', track_a=0, track_b=2)
    assert res.success
    # Subsequent unions across the cut fail.
    assert eng.union(a, mid) is False
    assert eng.union(mid, b) is False
    # Endpoints stay disjoint.
    assert eng.connected_to(a) == [a]
    assert eng.connected_to(b) == [b]


def test_add_cut_macro_grid_stamp_when_engine_lacks_layer():
    """When the engine doesn't model the cut layer (e.g. fixtures that
    haven't promoted CPO into CSP yet), ``add_cut_cell``'s engine
    branch is a no-op and only the grid-side stamp lands. The macro's
    transaction still opens and commits (with empty deltas)."""
    eng = ConstraintEngine()  # empty: no CPO layer
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0, orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0, orientation='H', min_width=2))
    grid.register_b_tier_axes('CPO', 'POLY', 'FIN')

    res = add_cut(eng, grid=grid, layer='CPO', track_a=2, track_b=3)
    assert res.success
    assert isinstance(res.commit_delta, CommitDelta)
    assert res.commit_delta.cells == []
    cell = grid.get_b_tier_cell('CPO', 2, 3)
    assert cell is not None
    assert cell.occ_type == OccupantType.CUT


def test_remove_cut_macro_drops_grid_entry_and_is_idempotent():
    eng = ConstraintEngine()  # empty: no CPO layer
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0, orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0, orientation='H', min_width=2))
    grid.register_b_tier_axes('CPO', 'POLY', 'FIN')

    add_cut(eng, grid=grid, layer='CPO', track_a=2, track_b=3)
    assert grid.get_b_tier_cell('CPO', 2, 3) is not None

    res = remove_cut(grid, 'CPO', 2, 3)
    assert res.success
    assert grid.get_b_tier_cell('CPO', 2, 3) is None
    # Idempotent: calling again on an already-empty cell.
    res2 = remove_cut(grid, 'CPO', 2, 3)
    assert res2.success


# =============================================================
# core/macros/share_diffusion.py — share_diffusion
# =============================================================

def _two_device_overlap_fixture():
    """Build a fixture where two devices' bboxes overlap on OD.

    Two NMOS-style devices placed so the OD cells between their gates
    are owned by one and shared with the other (the canonical shared-S/D
    case). The model deliberately stays minimal — no nets, no LI — so
    the test exercises only the OD cell-grid + engine union path.
    """
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

    # One OD shape spanning both devices' bboxes.
    od_shape = ShapeRecord(
        layer='OD',
        bbox_nm=(0, 10, 100, 40),
        desc='shared_od',
    )
    model.shape_pool.append(od_shape)

    project_b_tier_shapes(model, grid, [devA, devB])
    return model, grid, [devA, devB]


def test_share_diffusion_macro_no_engine_stamps_grid_only():
    """With ``engine=None``, the macro routes to the L2 atomic which
    stamps ``shared_with`` on every OD cell whose owner is one of the
    pair. ``commit_delta`` is None because no transaction was opened."""
    model, grid, devices = _two_device_overlap_fixture()
    res = share_diffusion(None, grid, 'DA', 'DB')
    assert res.success
    assert res.commit_delta is None
    # At least one OD cell should now carry the sibling on shared_with.
    found_sharing = False
    for cell in grid.b_tier_cells_of('OD'):
        if cell.shared_with:
            found_sharing = True
            break
    assert found_sharing, "expected at least one OD cell with shared_with set"


def test_share_diffusion_macro_with_engine_records_unions_in_delta():
    """With an engine modelling OD, the macro records every adjacent-OD
    union in the returned ``CommitDelta.unions``. The MVP fixture's two
    overlapping devices share at least one adjacent OD-cell pair so at
    least one union event lands."""
    model, grid, devices = _two_device_overlap_fixture()

    # Build engine modelling OD only — bounds derived from b_tier_cells.
    eng = ConstraintEngine()
    cells = grid.b_tier_cells.get('OD', {})
    tas = [a for (a, _b) in cells.keys()]
    tbs = [b for (_a, b) in cells.keys()]
    margin = 1
    eng.add_layer(
        'OD',
        n_tracks=max(tas) - min(tas) + 1 + 2 * margin,
        n_ortho=max(tbs) - min(tbs) + 1 + 2 * margin,
        track_range=(min(tas) - margin, max(tas) + margin + 1),
        ortho_range=(min(tbs) - margin, max(tbs) + margin + 1),
    )
    eng.initialize_domains(
        net_ids=set(),
        layer_occ_types={'OD': {OccupantType.EMPTY, OccupantType.DEVICE_DIFF}},
    )
    # Seed engine cells from the grid.
    for cell in grid.b_tier_cells_of('OD'):
        if eng.get_cell(cell.pos) is None:
            continue
        eng.assign(cell.pos, CellState(cell.occ_type, net_id=cell.net_id))

    res = share_diffusion(eng, grid, 'DA', 'DB')
    assert res.success
    assert isinstance(res.commit_delta, CommitDelta)
    # ``cells_stamped`` is naturally 0 here: ``project_b_tier_shapes``
    # already stamped ``shared_with`` during the parser path
    # (overlapping device bboxes are detected at parse time). The
    # macro's incremental work is the engine union pass, where the
    # adjacent OD-cell pairs become electrically equivalent.
    assert res.cells_unioned >= 1
    # Some union calls are no-op successes (cells already in the same
    # component); only actual merges land on the trail. So the trail
    # delta is a lower bound on the L2 atomic's True-return count.
    assert len(res.commit_delta.unions) >= 1
    assert len(res.commit_delta.unions) <= res.cells_unioned


def test_share_diffusion_macro_no_grid_short_circuits():
    res = share_diffusion(None, None, 'DA', 'DB')
    assert res.success
    assert res.detail == 'no grid'


# =============================================================
# device_resize macro flipped to commit_with_full_delta
# =============================================================

def test_resize_macro_uses_commit_with_full_delta(capsys):
    """The L3 ``device_resize`` macro must call
    ``commit_with_full_delta`` (M6 flip), not ``commit_with_delta``.
    We assert by capturing the macro's print which says
    "{N} cell-level changes, {M} union events" — the second number is
    the marker that ``commit_with_full_delta`` was used."""
    from core.solver import LayoutSolver

    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )
    config = load_tech_config()
    solver = LayoutSolver(model, grid, config=config)
    solver.setup_engine()
    solver.load_existing_layout()
    solver.load_b_tier_cells_into_engine()
    res = solver.resize_device('MN0', 4)
    assert res.success
    out = capsys.readouterr().out
    assert 'union events' in out, (
        f"resize macro should print 'union events' marker from "
        f"commit_with_full_delta; got:\n{out}"
    )
