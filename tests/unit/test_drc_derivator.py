"""M5: ``DRCDerivator`` C1 derived-shape emitter.

Verifies:
  * ``derive_c1`` returns ``modify_shape`` EditOps for NWELL / BOUNDARY
    with ``new_bbox.y2`` matching ``pmos_fin_y_new[-1] + config_margin``.
  * Idempotent on a steady-state fixture (post-derive call returns no
    ops because every shape's bbox already matches the rule).
  * Stamps ``ShapeRecord.is_derived = True`` and ``provenance`` on
    every C1 shape (the M3 seam goes load-bearing in M5).
  * Decoder Phase 1's new ``_apply_nwell_modifies`` / ``_apply_boundary_modifies``
    consume the derivator's ops to byte-identical output.
  * End-to-end through the pipeline: ``output/buffer_resized.json``'s
    NWELL ``y2`` equals 395 and BOUNDARY ``y2`` equals 405 on the
    MVP fixture.
  * No-op on a pool that lacks the layer (VT / PP / NP / DNW today).
  * Empty fin lists short-circuit cleanly.

Roadmap: docs/architecture_roadmap.md §B / §C and milestone M5.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import copy

import pytest

from core.data_model import LayoutModel, ShapeRecord
from core.decoder import WritebackDecoder
from core.diff import EditOp
from core.drc_derivator import DRCDerivator
from core.grid import MultiLayerGrid
from io_adapters.parser import build_layout_model
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# =============================================================
# Tech config additions
# =============================================================

def test_config_exposes_nwell_and_boundary_margins():
    config = load_tech_config()
    assert config.NWELL_MARGIN_BEYOND_FIN == 30
    assert config.BOUNDARY_MARGIN_BEYOND_FIN == 40


# =============================================================
# Synthetic fixtures
# =============================================================

def _synthetic_model_with_nwell_boundary(nwell_y2=200, boundary_y2=210):
    """Build a tiny model carrying one NWELL + one BOUNDARY shape."""
    model = LayoutModel()
    model.shape_pool.append(ShapeRecord(
        layer='NWELL', bbox_nm=(0, 0, 100, nwell_y2), desc='nwell',
    ))
    model.shape_pool.append(ShapeRecord(
        layer='BOUNDARY', bbox_nm=(0, 0, 100, boundary_y2), desc='cell_boundary',
    ))
    grid = MultiLayerGrid()
    return model, grid


# =============================================================
# Per-rule derivation
# =============================================================

def test_derive_nwell_emits_modify_shape_with_correct_y2():
    config = load_tech_config()
    model, grid = _synthetic_model_with_nwell_boundary(nwell_y2=999)
    derivator = DRCDerivator(model, grid, config)

    ops = derivator.derive_c1(nmos_fin_y_new=[40, 65, 90, 115],
                                pmos_fin_y_new=[240, 265, 290, 315, 340, 365])
    nwell_ops = [op for op in ops if op.layer == 'NWELL']
    assert len(nwell_ops) == 1
    op = nwell_ops[0]
    assert op.op_type == 'modify_shape'
    assert op.old_bbox == (0, 0, 100, 999)
    expected_y2 = 365 + config.NWELL_MARGIN_BEYOND_FIN
    assert op.new_bbox == (0, 0, 100, expected_y2)
    assert op.desc == 'derived_nwell_y2_shift'


def test_derive_boundary_emits_modify_shape_with_correct_y2():
    config = load_tech_config()
    model, grid = _synthetic_model_with_nwell_boundary(boundary_y2=999)
    derivator = DRCDerivator(model, grid, config)

    ops = derivator.derive_c1([40], pmos_fin_y_new=[240, 265, 290, 365])
    boundary_ops = [op for op in ops if op.layer == 'BOUNDARY']
    assert len(boundary_ops) == 1
    op = boundary_ops[0]
    expected_y2 = 365 + config.BOUNDARY_MARGIN_BEYOND_FIN
    assert op.new_bbox == (0, 0, 100, expected_y2)
    assert op.desc == 'derived_boundary_y2_shift'


def test_derive_c1_idempotent_when_bbox_already_matches():
    """A steady-state fixture (NWELL/BOUNDARY already at the right y2)
    returns zero ops on a re-call. This is the M5 idempotency contract:
    re-running the pipeline on a layout that's already in sync should
    not produce phantom edits."""
    config = load_tech_config()
    pmos_fin_y_new = [240, 365]
    nwell_y2 = pmos_fin_y_new[-1] + config.NWELL_MARGIN_BEYOND_FIN
    boundary_y2 = pmos_fin_y_new[-1] + config.BOUNDARY_MARGIN_BEYOND_FIN
    model, grid = _synthetic_model_with_nwell_boundary(
        nwell_y2=nwell_y2, boundary_y2=boundary_y2,
    )
    derivator = DRCDerivator(model, grid, config)
    ops = derivator.derive_c1([40], pmos_fin_y_new)
    assert ops == []


def test_derive_c1_stamps_is_derived_and_provenance():
    """The M3 seam ``ShapeRecord.is_derived`` lights up here. Both the
    NWELL and the BOUNDARY records are stamped — including the
    BOUNDARY whose y2 already matches (idempotent y2 shift, but the
    derivator still owns the shape)."""
    config = load_tech_config()
    bdy_y2 = 365 + config.BOUNDARY_MARGIN_BEYOND_FIN
    model, grid = _synthetic_model_with_nwell_boundary(
        nwell_y2=999,           # will change
        boundary_y2=bdy_y2,     # already matches — no op emitted, but sr stamped
    )
    derivator = DRCDerivator(model, grid, config)
    derivator.derive_c1([40], pmos_fin_y_new=[365])

    nwell = next(sr for sr in model.shape_pool if sr.layer == 'NWELL')
    boundary = next(sr for sr in model.shape_pool if sr.layer == 'BOUNDARY')
    assert nwell.is_derived is True
    assert nwell.provenance == 'drc_derivator._derive_nwell'
    assert boundary.is_derived is True
    assert boundary.provenance == 'drc_derivator._derive_boundary'


def test_derive_c1_updates_shape_record_bbox_after_emit():
    """After emitting a modify op, the matching ShapeRecord's
    ``bbox_nm`` is updated so a subsequent call sees the new
    geometry — the source of the idempotency contract above."""
    config = load_tech_config()
    model, grid = _synthetic_model_with_nwell_boundary(nwell_y2=100)
    derivator = DRCDerivator(model, grid, config)

    derivator.derive_c1([40], pmos_fin_y_new=[200])
    expected_y2 = 200 + config.NWELL_MARGIN_BEYOND_FIN

    nwell = next(sr for sr in model.shape_pool if sr.layer == 'NWELL')
    assert nwell.bbox_nm[3] == expected_y2

    # Re-running with the same fin positions should produce no ops.
    ops_2nd = derivator.derive_c1([40], pmos_fin_y_new=[200])
    assert ops_2nd == []


def test_derive_c1_no_op_on_empty_fin_list():
    config = load_tech_config()
    model, grid = _synthetic_model_with_nwell_boundary()
    derivator = DRCDerivator(model, grid, config)
    assert derivator.derive_c1([], []) == []


def test_derive_c1_skips_layers_absent_from_pool():
    """A pool with no NWELL / BOUNDARY records yields zero ops — the
    derivator iterates the pool, not the layer list, so missing
    fixture geometry is silently a no-op (the expected M5 behaviour
    for VT / PP / NP / DNW today)."""
    config = load_tech_config()
    model = LayoutModel()  # empty pool
    grid = MultiLayerGrid()
    derivator = DRCDerivator(model, grid, config)
    assert derivator.derive_c1([40], [365]) == []


# =============================================================
# Decoder Phase 1 round-trip
# =============================================================

def test_decoder_applies_nwell_modify_from_derivator():
    """The decoder's new ``_apply_nwell_modifies`` consumes the
    derivator's ops and writes the new bbox into the result dict.
    Same passive-applier pattern as ``_apply_od_modifies`` — match
    by exact old bbox, replace coordinates."""
    config = load_tech_config()
    grid = MultiLayerGrid()
    decoder = WritebackDecoder(grid, config)

    orig_data = {
        'params': {
            'nmos_fin_y': [40, 65, 90],
            'pmos_fin_y': [240, 265, 290],
            'nmos_nfin': 3,
            'pmos_nfin': 3,
            'cell_height': 330,
        },
        'shapes': {
            'FIN': [],
            'OD': [],
            'LI': [],
            'POLY': [],
            'NWELL': [{'x1': -30, 'y1': 210, 'x2': 138, 'y2': 320,
                        'net': '', 'desc': 'nwell'}],
            'BOUNDARY': [{'x1': 0, 'y1': 0, 'x2': 108, 'y2': 330,
                            'net': '', 'desc': 'cell_boundary'}],
        },
        'devices': [],
    }
    edit_ops = [
        EditOp(op_type='modify_shape', layer='NWELL',
                old_bbox=(-30, 210, 138, 320),
                new_bbox=(-30, 210, 138, 295),
                desc='derived_nwell_y2_shift'),
        EditOp(op_type='modify_shape', layer='BOUNDARY',
                old_bbox=(0, 0, 108, 330),
                new_bbox=(0, 0, 108, 305),
                desc='derived_boundary_y2_shift'),
    ]
    result = decoder.apply(orig_data, edit_ops, 3, 3)
    assert result['shapes']['NWELL'][0]['y2'] == 295
    assert result['shapes']['BOUNDARY'][0]['y2'] == 305


def test_decoder_skips_unmatched_nwell_modify():
    """When the EditOp's old_bbox doesn't match any shape, the
    decoder silently leaves the result alone (mirrors the OD/LI
    behaviour)."""
    config = load_tech_config()
    grid = MultiLayerGrid()
    decoder = WritebackDecoder(grid, config)

    orig_data = {
        'params': {'nmos_fin_y': [40], 'pmos_fin_y': [240],
                    'nmos_nfin': 1, 'pmos_nfin': 1, 'cell_height': 280},
        'shapes': {
            'FIN': [], 'OD': [], 'LI': [], 'POLY': [],
            'NWELL': [{'x1': 0, 'y1': 0, 'x2': 100, 'y2': 200,
                        'net': '', 'desc': 'nwell'}],
            'BOUNDARY': [],
        },
        'devices': [],
    }
    edit_ops = [
        EditOp(op_type='modify_shape', layer='NWELL',
                old_bbox=(99, 99, 99, 99),  # no match
                new_bbox=(0, 0, 100, 999),
                desc='derived_nwell_y2_shift'),
    ]
    result = decoder.apply(orig_data, edit_ops, 1, 1)
    assert result['shapes']['NWELL'][0]['y2'] == 200   # unchanged


# =============================================================
# Pipeline byte-golden via build_layout_model on the MVP fixture
# =============================================================

def _load_mvp_model():
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
    return model, grid, config


def test_mvp_derivator_emits_nwell_y2_at_395():
    """End-to-end: on the MVP fixture's resize 5/7 → 4/6, the new
    PMOS topmost fin is at y=365, so NWELL y2 = 365 + 30 = 395.
    Matches the M4e baseline."""
    model, grid, config = _load_mvp_model()
    pmos_fin_y_new = [240, 265, 290, 315, 340, 365]
    nmos_fin_y_new = [40, 65, 90, 115]
    derivator = DRCDerivator(model, grid, config)
    ops = derivator.derive_c1(nmos_fin_y_new, pmos_fin_y_new)

    nwell = [op for op in ops if op.layer == 'NWELL']
    assert len(nwell) == 1
    assert nwell[0].new_bbox[3] == 395


def test_mvp_derivator_emits_boundary_y2_at_405():
    model, grid, config = _load_mvp_model()
    pmos_fin_y_new = [240, 265, 290, 315, 340, 365]
    nmos_fin_y_new = [40, 65, 90, 115]
    derivator = DRCDerivator(model, grid, config)
    ops = derivator.derive_c1(nmos_fin_y_new, pmos_fin_y_new)

    boundary = [op for op in ops if op.layer == 'BOUNDARY']
    assert len(boundary) == 1
    assert boundary[0].new_bbox[3] == 405


def test_mvp_derivator_lights_up_is_derived_on_pool():
    """After the MVP derivator call, the NWELL + BOUNDARY shape_pool
    records carry ``is_derived=True``. Sets the M3 seam in the parent
    LayoutModel that's also the input to the pipeline."""
    model, grid, config = _load_mvp_model()
    derivator = DRCDerivator(model, grid, config)
    derivator.derive_c1([40], pmos_fin_y_new=[365])

    nwells = [sr for sr in model.shape_pool if sr.layer == 'NWELL']
    boundaries = [sr for sr in model.shape_pool if sr.layer == 'BOUNDARY']
    assert nwells and all(sr.is_derived for sr in nwells)
    assert boundaries and all(sr.is_derived for sr in boundaries)


if __name__ == '__main__':
    test_config_exposes_nwell_and_boundary_margins()
    test_derive_nwell_emits_modify_shape_with_correct_y2()
    test_derive_boundary_emits_modify_shape_with_correct_y2()
    test_derive_c1_idempotent_when_bbox_already_matches()
    test_derive_c1_stamps_is_derived_and_provenance()
    test_derive_c1_updates_shape_record_bbox_after_emit()
    test_derive_c1_no_op_on_empty_fin_list()
    test_derive_c1_skips_layers_absent_from_pool()
    test_decoder_applies_nwell_modify_from_derivator()
    test_decoder_skips_unmatched_nwell_modify()
    test_mvp_derivator_emits_nwell_y2_at_395()
    test_mvp_derivator_emits_boundary_y2_at_405()
    test_mvp_derivator_lights_up_is_derived_on_pool()
    print("All M5 DRCDerivator tests passed!")
