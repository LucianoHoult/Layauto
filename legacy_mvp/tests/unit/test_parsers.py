"""Test IO parsers: Calibre JSON and bbox parsing."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.parser import (
    parse_calibre_device_query,
    parse_calibre_net_query,
    parse_bbox_by_layer,
    build_layout_model,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')


def test_parse_devices():
    devices = parse_calibre_device_query(
        os.path.join(FIXTURE_DIR, 'calibre_device_query.json'))
    assert len(devices) == 2
    
    mn = next(d for d in devices if d.inst_name == 'MN0')
    assert mn.dev_type == 'nmos'
    assert mn.nfin == 5
    assert mn.pins['G'] == 'IN'
    assert mn.pins['D'] == 'OUT'


def test_parse_nets():
    nets = parse_calibre_net_query(
        os.path.join(FIXTURE_DIR, 'calibre_net_query.json'))
    assert 'VSS' in nets
    assert 'VDD' in nets
    assert 'IN' in nets
    assert 'OUT' in nets
    assert nets['VSS']['type'] == 'power'
    assert len(nets['VSS']['shapes']) > 0


def test_parse_bbox():
    bbox = parse_bbox_by_layer(
        os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'))
    assert 'FIN' in bbox
    assert 'LI' in bbox
    assert 'M1' in bbox
    assert len(bbox['FIN']) == 12  # 5 NMOS + 7 PMOS fins


def test_build_layout_model():
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(FIXTURE_DIR, 'buffer_original.json'),
    )
    
    assert len(model.devices) == 2
    assert len(model.nets) == 4
    assert model.cell_width_nm > 0
    assert model.cell_height_nm > 0
    
    # Check grid was created properly
    assert 'LI' in grid.layers
    assert grid.get_layer('LI').pitch == 27


def test_net_segments_populated():
    model, grid = build_layout_model(
        device_query_path=os.path.join(FIXTURE_DIR, 'calibre_device_query.json'),
        net_query_path=os.path.join(FIXTURE_DIR, 'calibre_net_query.json'),
        bbox_path=os.path.join(FIXTURE_DIR, 'bbox_by_layer.json'),
    )
    
    vss = model.nets['VSS']
    assert len(vss.segments) >= 1
    assert len(vss.vias) >= 1
    
    out = model.nets['OUT']
    assert len(out.segments) >= 2  # NMOS drain LI + PMOS drain LI


if __name__ == '__main__':
    test_parse_devices()
    test_parse_nets()
    test_parse_bbox()
    test_build_layout_model()
    test_net_segments_populated()
    print("All parser tests passed!")
