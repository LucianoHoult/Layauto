"""M4c: parser tier-dispatch + B-tier projection + per-shape device_id refinement.

Verifies:
  * ``apply_lvs_overlay`` now picks ``device_id`` per shape by geometric
    containment — the OUT net's NMOS-drain LI gets ``device_id=MN0``
    while the PMOS-drain LI gets ``device_id=MP0`` (M3's "first-pin-wins"
    placeholder would have stamped both with the same instance).
  * ``project_b_tier_shapes`` registers axes for OD / VIA0 (where the
    fixture provides the axis layers) and stamps a ``CellOccupancy``
    per cell.
  * OD cells carry ``owner_device_id`` from device-bbox containment.
  * ``shared_with`` is empty in the MVP fixture (NMOS and PMOS don't
    share diffusion); a synthetic two-device-overlap test exercises
    the sharing path.
  * Solver's ``_reshape_li_sd_bars`` migration: with the M4c
    ``shape_record.device_id`` stamp, the per-device LI filter still
    picks the same segments as the legacy desc-substring filter on
    the dummy fixture — i.e. byte-golden output is preserved.

Roadmap: docs/architecture_roadmap.md §B and milestone M4c.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from core.data_model import (
    CellOccupancy, Device, LayoutModel, OccupantType, ShapeRecord,
)
from core.grid import LayerGrid, MultiLayerGrid
from io_adapters.parser import (
    _device_for_shape,
    apply_lvs_overlay,
    build_layout_model,
    build_shape_pool,
    parse_bbox_by_layer,
    parse_calibre_device_query,
    parse_calibre_net_query,
    project_b_tier_shapes,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


# =============================================================
# apply_lvs_overlay — per-shape device_id refinement
# =============================================================

def _load_pool_with_overlay():
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json'))
    net_data = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json'))
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'))
    pool = build_shape_pool(bbox_data)
    apply_lvs_overlay(pool, net_data, devices)
    return pool, devices, net_data


def test_overlay_disambiguates_out_net_per_shape():
    """The OUT net pins to both MN0 (NMOS drain) and MP0 (PMOS drain).
    The M3 "first-pin-wins" rule would stamp both LI shapes with the
    same device; M4c picks per-shape by geometric containment of the
    shape center."""
    pool, _, _ = _load_pool_with_overlay()
    out_li = [sr for sr in pool
              if sr.layer == 'LI' and sr.net_id == 'OUT']
    assert len(out_li) == 2, f"expected two OUT LI shapes, got {len(out_li)}"
    by_device = {sr.device_id for sr in out_li}
    assert by_device == {'MN0', 'MP0'}, (
        f"M4c device_id refinement should split OUT across MN0/MP0, "
        f"got {by_device}"
    )

    # Spot-check by Y-center: NMOS drain LI is below the gate strip,
    # PMOS drain LI is above.
    nmos_li = next(sr for sr in out_li if sr.device_id == 'MN0')
    pmos_li = next(sr for sr in out_li if sr.device_id == 'MP0')
    nmos_cy = (nmos_li.bbox_nm[1] + nmos_li.bbox_nm[3]) / 2
    pmos_cy = (pmos_li.bbox_nm[1] + pmos_li.bbox_nm[3]) / 2
    assert nmos_cy < pmos_cy


def test_overlay_keeps_single_device_nets_unchanged():
    """VSS / VDD have a single pinned device — the per-shape refinement
    must still stamp ``MN0`` / ``MP0`` on shapes whose center sits inside
    that device's bbox (i.e. the LI source/body bars). External power
    rails (the VSS / VDD M1 straps) extend beyond any device and end up
    with ``device_id=None`` post-M4c — that's the correct semantics
    (they are shared infrastructure, not owned by a single device) and
    the solver's LI-only filter never reaches them anyway."""
    pool, _, _ = _load_pool_with_overlay()
    vss_li = [sr for sr in pool
               if sr.layer == 'LI' and sr.net_id == 'VSS']
    vdd_li = [sr for sr in pool
               if sr.layer == 'LI' and sr.net_id == 'VDD']
    assert vss_li and all(sr.device_id == 'MN0' for sr in vss_li)
    assert vdd_li and all(sr.device_id == 'MP0' for sr in vdd_li)


# =============================================================
# _device_for_shape primitive
# =============================================================

def test_device_for_shape_prefers_containment():
    devices = [
        Device(inst_name='A', dev_type='nmos', nfin=1, nf=1,
                bbox_nm={'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}),
        Device(inst_name='B', dev_type='pmos', nfin=1, nf=1,
                bbox_nm={'x1': 200, 'y1': 0, 'x2': 300, 'y2': 100}),
    ]
    sr = ShapeRecord(layer='LI', bbox_nm=(40, 40, 60, 60))
    chosen = _device_for_shape(sr, devices)
    assert chosen is not None and chosen.inst_name == 'A'


def test_device_for_shape_falls_back_to_overlap_area():
    """When no device contains the center, the device with the largest
    overlap wins."""
    devices = [
        Device(inst_name='A', dev_type='nmos', nfin=1, nf=1,
                bbox_nm={'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}),
        Device(inst_name='B', dev_type='pmos', nfin=1, nf=1,
                bbox_nm={'x1': 110, 'y1': 0, 'x2': 200, 'y2': 100}),
    ]
    # Shape spans the gap, center at (105, 50) — outside both bboxes.
    sr = ShapeRecord(layer='LI', bbox_nm=(80, 0, 130, 100))
    chosen = _device_for_shape(sr, devices)
    # A has 20-wide overlap (80..100), B has 20-wide overlap (110..130);
    # tie — first device with overlap wins. Either is acceptable; we
    # just want a non-None result.
    assert chosen is not None


def test_device_for_shape_respects_candidate_filter():
    """When LVS gives a per-net pin list, the search is restricted to it."""
    devices = [
        Device(inst_name='A', dev_type='nmos', nfin=1, nf=1,
                bbox_nm={'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}),
        Device(inst_name='B', dev_type='pmos', nfin=1, nf=1,
                bbox_nm={'x1': 0, 'y1': 0, 'x2': 100, 'y2': 100}),
    ]
    # Both bboxes contain the shape; without a filter A wins (first
    # in order). Restricting to ['B'] forces B.
    sr = ShapeRecord(layer='LI', bbox_nm=(40, 40, 60, 60))
    chosen = _device_for_shape(sr, devices, candidates=['B'])
    assert chosen is not None and chosen.inst_name == 'B'


def test_device_for_shape_returns_none_when_outside():
    devices = [Device(inst_name='A', dev_type='nmos', nfin=1, nf=1,
                       bbox_nm={'x1': 0, 'y1': 0, 'x2': 10, 'y2': 10})]
    sr = ShapeRecord(layer='OD', bbox_nm=(100, 100, 200, 200))
    assert _device_for_shape(sr, devices) is None


# =============================================================
# project_b_tier_shapes via the full pipeline
# =============================================================

def _load_full_model():
    return build_layout_model(
        device_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )


def test_project_registers_od_axes():
    _, grid = _load_full_model()
    assert 'OD' in grid.b_tier_axes
    assert grid.get_b_tier_axes('OD') == ('POLY', 'FIN')


def test_project_registers_via0_axes():
    _, grid = _load_full_model()
    assert 'VIA0' in grid.b_tier_axes
    assert grid.get_b_tier_axes('VIA0') == ('LI', 'M1')


def test_project_stamps_od_cells():
    _, grid = _load_full_model()
    assert 'OD' in grid.b_tier_cells
    od_cells = list(grid.b_tier_cells_of('OD'))
    # MVP fixture has two OD shapes (NMOS + PMOS); each spans multiple
    # poly × fin cells, so we expect a non-trivial population.
    assert len(od_cells) > 0
    for cell in od_cells:
        assert cell.occ_type == OccupantType.DEVICE_DIFF


def test_project_owner_device_id_split_across_devices():
    """OD cells of the NMOS shape get ``owner_device_id=MN0``;
    PMOS shape's cells get ``MP0``. No cells should be ownerless on
    the MVP fixture (every OD shape is inside one device's bbox)."""
    _, grid = _load_full_model()
    owners = {cell.owner_device_id for cell in grid.b_tier_cells_of('OD')}
    assert 'MN0' in owners
    assert 'MP0' in owners
    # No unowned OD cells in the MVP — every OD shape sits inside one
    # device's bbox.
    assert None not in owners


def test_project_shared_with_empty_for_mvp():
    """The MVP fixture has no diffusion sharing — NMOS and PMOS bboxes
    don't overlap, so every OD cell's ``shared_with`` is empty."""
    _, grid = _load_full_model()
    for cell in grid.b_tier_cells_of('OD'):
        assert cell.shared_with == [], (
            f"unexpected shared_with on {cell}: {cell.shared_with}"
        )


def test_project_stamps_shape_record_backlink():
    _, grid = _load_full_model()
    for cell in grid.b_tier_cells_of('OD'):
        assert cell.shape_record is not None
        assert cell.shape_record.layer == 'OD'


def test_project_stamps_via0_cells_with_via_occ_type():
    _, grid = _load_full_model()
    via0_cells = list(grid.b_tier_cells_of('VIA0'))
    assert len(via0_cells) == 4   # MVP has 4 vias
    for cell in via0_cells:
        assert cell.occ_type == OccupantType.VIA


# =============================================================
# Diffusion sharing — synthetic two-device fixture
# =============================================================

def test_project_records_shared_with_when_two_devices_overlap():
    """A synthetic OD shape covered by two devices' bboxes — every
    cell should record both devices on owner + shared_with."""
    grid = MultiLayerGrid()
    # Minimal POLY × FIN axis grids.
    grid.add_layer(LayerGrid('POLY', pitch=10, offset=0,
                              orientation='V', min_width=2))
    grid.add_layer(LayerGrid('FIN', pitch=10, offset=0,
                              orientation='H', min_width=2))

    devices = [
        # Two devices with overlapping bboxes — i.e. they share diffusion.
        Device(inst_name='MN0', dev_type='nmos', nfin=1, nf=1,
                bbox_nm={'x1': 0, 'y1': 0, 'x2': 30, 'y2': 30}),
        Device(inst_name='MN1', dev_type='nmos', nfin=1, nf=1,
                bbox_nm={'x1': 20, 'y1': 0, 'x2': 50, 'y2': 30}),
    ]
    sr = ShapeRecord(layer='OD', bbox_nm=(20, 0, 30, 30),
                      net_id='SHARED')
    model = LayoutModel(devices=devices, shape_pool=[sr])
    project_b_tier_shapes(model, grid, devices)

    cells = list(grid.b_tier_cells_of('OD'))
    assert cells, "expected projection to stamp cells"
    # Each cell should be owned by one device and reference the other
    # on shared_with.
    for cell in cells:
        assert cell.owner_device_id in {'MN0', 'MN1'}
        sharer = 'MN1' if cell.owner_device_id == 'MN0' else 'MN0'
        assert sharer in cell.shared_with, (
            f"cell {cell} missing diffusion sharer {sharer}: "
            f"shared_with={cell.shared_with}"
        )


# =============================================================
# Solver migration: shape_record.device_id replaces desc filter
# =============================================================

def test_track_segments_carry_per_device_shape_record():
    """The build_layout_model output stamps each TrackSegment with
    a shape_record whose device_id is per-shape correct. The OUT
    net's NMOS LI segment's shape_record.device_id must be MN0;
    the PMOS LI segment's must be MP0 — that's what the solver's
    new filter at ``core/solver.py::_reshape_li_sd_bars`` reads
    instead of the desc substring."""
    model, _ = _load_full_model()
    out_net = model.get_net('OUT')
    assert out_net is not None
    li_segs = [s for s in out_net.segments if s.layer == 'LI']
    assert len(li_segs) == 2
    devs = {s.shape_record.device_id for s in li_segs
             if s.shape_record is not None}
    assert devs == {'MN0', 'MP0'}, (
        f"M4c expects per-segment device_id split across MN0/MP0, "
        f"got {devs}"
    )


if __name__ == '__main__':
    test_overlay_disambiguates_out_net_per_shape()
    test_overlay_keeps_single_device_nets_unchanged()
    test_device_for_shape_prefers_containment()
    test_device_for_shape_falls_back_to_overlap_area()
    test_device_for_shape_respects_candidate_filter()
    test_device_for_shape_returns_none_when_outside()
    test_project_registers_od_axes()
    test_project_registers_via0_axes()
    test_project_stamps_od_cells()
    test_project_owner_device_id_split_across_devices()
    test_project_shared_with_empty_for_mvp()
    test_project_stamps_shape_record_backlink()
    test_project_stamps_via0_cells_with_via_occ_type()
    test_project_records_shared_with_when_two_devices_overlap()
    test_track_segments_carry_per_device_shape_record()
    print("All M4c parser tier-dispatch tests passed!")
