"""M3: ShapeRecord, parser inversion (shape_pool primary), and LVS overlay.

Verifies:
  * ``parse_bbox_by_layer`` -> ``build_shape_pool`` is the geometric truth
    pass: every GDS rectangle becomes one ShapeRecord, with
    ``net_id is None``.
  * ``apply_lvs_overlay`` stamps ``net_id`` / ``device_id`` / ``pin_role``
    onto matching records by ``(layer, bbox)`` key. Unmatched records
    remain unannotated.
  * ``LayoutModel.shape_pool`` carries the result; ``annotation_coverage``
    summarises per-layer totals.
  * ``TrackSegment.shape_record`` backlink is set by ``build_layout_model``.

Roadmap: docs/architecture_roadmap.md §A and §C, milestone M3.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.data_model import LayoutModel, ShapeRecord
from io_adapters.parser import (
    apply_lvs_overlay,
    build_layout_model,
    build_shape_pool,
    parse_bbox_by_layer,
    parse_calibre_device_query,
    parse_calibre_net_query,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures'
)


def test_shape_record_unannotated_by_default():
    """ShapeRecord with no LVS overlay reports ``is_annotated=False``."""
    sr = ShapeRecord(layer='LI', bbox_nm=(0, 0, 17, 100), desc='filler_stub')
    assert sr.is_annotated is False
    assert sr.net_id is None
    assert sr.device_id is None
    assert sr.pin_role is None
    assert sr.is_derived is False


def test_shape_record_annotated_after_overlay():
    sr = ShapeRecord(
        layer='LI', bbox_nm=(18, 13, 35, 145), desc='li_nmos_source',
        net_id='VSS', device_id='MN0', pin_role='S',
    )
    assert sr.is_annotated is True


def test_build_shape_pool_covers_every_gds_rectangle():
    """Every (layer, bbox) in bbox_data shows up exactly once in the pool."""
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json')
    )
    pool = build_shape_pool(bbox_data)
    expected = sum(len(v) for v in bbox_data.values())
    assert len(pool) == expected
    # Pre-overlay: nothing is annotated yet.
    assert all(not sr.is_annotated for sr in pool)


def test_apply_lvs_overlay_stamps_net_and_pin_role():
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json')
    )
    net_data = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json')
    )
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json')
    )
    pool = build_shape_pool(bbox_data)
    apply_lvs_overlay(pool, net_data, devices)

    # The four LI bars and four VIA0s plus four M1 routes are all LVS-tagged.
    annotated_li = [sr for sr in pool if sr.layer == 'LI' and sr.is_annotated]
    assert len(annotated_li) >= 4

    # And every VIA0 must carry a net_id (the dummy MVP guarantees full
    # via coverage; a regression here would mean parsing dropped them).
    via0 = [sr for sr in pool if sr.layer == 'VIA0']
    assert len(via0) == 4
    assert all(sr.is_annotated for sr in via0)

    # Pin role lookup: at least one LI shape on net VSS has device_id MN0.
    vss_li = [sr for sr in pool
              if sr.layer == 'LI' and sr.net_id == 'VSS']
    assert vss_li, "VSS must have at least one LI shape post-overlay"
    assert all(sr.device_id == 'MN0' for sr in vss_li)
    assert all(sr.pin_role in ('S', 'B') for sr in vss_li)


def test_dummy_gates_remain_unannotated():
    """The boundary dummy gates (POLY, ``net=''``) must survive overlay
    as unannotated records — the LVS net data does not mention them, and
    the conservative-defaults rule (§D) says we must not silently
    fabricate annotation."""
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json')
    )
    net_data = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json')
    )
    bbox_data = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json')
    )
    pool = build_shape_pool(bbox_data)
    apply_lvs_overlay(pool, net_data, devices)

    poly = [sr for sr in pool if sr.layer == 'POLY']
    # 3 POLY shapes total: 1 active gate (net=IN) + 2 dummy gates (no net)
    assert len(poly) == 3
    annotated = [sr for sr in poly if sr.is_annotated]
    unannotated = [sr for sr in poly if not sr.is_annotated]
    assert len(annotated) == 1
    assert len(unannotated) == 2


def test_layout_model_carries_shape_pool():
    model, _ = build_layout_model(
        device_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )
    assert model.shape_pool, "LayoutModel.shape_pool must be populated"

    cov = model.annotation_coverage()
    # Sanity: every layer with shapes appears in the coverage table.
    assert {'FIN', 'POLY', 'LI', 'M1', 'OD', 'VIA0'} <= set(cov.keys())
    # LI coverage in the MVP fixture is 100%.
    assert cov['LI']['unannotated'] == 0
    # POLY coverage is partial (active gate annotated, 2 dummies aren't).
    assert cov['POLY']['unannotated'] == 2


def test_track_segment_shape_record_backlink():
    """Each TrackSegment built from LVS must point back at the matching
    ShapeRecord — this is the M3 seam that replaces the M2-era loose
    ``bbox_nm`` stamp."""
    model, _ = build_layout_model(
        device_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(
            FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
    )
    for net in model.nets.values():
        for seg in net.segments:
            assert seg.shape_record is not None, \
                f"{seg} missing shape_record backlink"
            assert seg.shape_record.layer == seg.layer
            assert seg.shape_record.net_id == seg.net_id


if __name__ == '__main__':
    test_shape_record_unannotated_by_default()
    test_shape_record_annotated_after_overlay()
    test_build_shape_pool_covers_every_gds_rectangle()
    test_apply_lvs_overlay_stamps_net_and_pin_role()
    test_dummy_gates_remain_unannotated()
    test_layout_model_carries_shape_pool()
    test_track_segment_shape_record_backlink()
    print("All shape_pool / parser-inversion tests passed!")
