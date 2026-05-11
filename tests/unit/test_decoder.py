"""Test WritebackDecoder: writeback geometry consolidation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.parser import build_layout_model
from core.solver import LayoutSolver
from core.decoder import WritebackDecoder
from tech.config_loader import load_tech_config

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'dummy', 'fixtures')


def _resize_via_decoder(target_nmos_nfin: int, target_pmos_nfin: int):
    """Run the full resize pipeline through the decoder and return the result dict."""
    import json
    config = load_tech_config()
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
    r_n = solver.resize_device('MN0', target_nmos_nfin)
    r_p = solver.resize_device('MP0', target_pmos_nfin)
    assert r_n.success and r_p.success

    with open(os.path.join(FIXTURE_DIR, 'buffer_original.json'), encoding='utf-8') as f:
        orig_data = json.load(f)
    decoder = WritebackDecoder(grid, config)
    return decoder.apply(
        orig_data, r_n.edit_ops + r_p.edit_ops,
        target_nmos_nfin, target_pmos_nfin,
    )


def test_decoder_drops_removed_fins():
    result = _resize_via_decoder(4, 6)
    # Original has 5 NMOS + 7 PMOS = 12 fins; resized has 4 + 6 = 10
    assert len(result['shapes']['FIN']) == 10


def test_decoder_shrinks_od_to_new_fin_top():
    result = _resize_via_decoder(4, 6)
    config = load_tech_config()
    nmos_top = result['params']['nmos_fin_y'][-1]
    pmos_top = result['params']['pmos_fin_y'][-1]
    od_ext = config.OD_EXTENSION_BEYOND_FIN

    nmos_od = next(s for s in result['shapes']['OD'] if s['desc'] == 'nmos_od')
    pmos_od = next(s for s in result['shapes']['OD'] if s['desc'] == 'pmos_od')
    assert nmos_od['y2'] == nmos_top + od_ext
    assert pmos_od['y2'] == pmos_top + od_ext


def test_decoder_updates_params_and_devices():
    result = _resize_via_decoder(4, 6)
    p = result['params']
    assert p['nmos_nfin'] == 4
    assert p['pmos_nfin'] == 6
    assert len(p['nmos_fin_y']) == 4
    assert len(p['pmos_fin_y']) == 6

    nmos = next(d for d in result['devices'] if d['type'] == 'nmos')
    pmos = next(d for d in result['devices'] if d['type'] == 'pmos')
    assert nmos['nfin'] == 4
    assert pmos['nfin'] == 6


def test_decoder_extends_li_to_cover_vias():
    result = _resize_via_decoder(4, 6)
    # All LI shapes carrying via-bearing nets must enclose their via.
    config = load_tech_config()
    enc = config.VIA0_ENC_BY_LI_Y
    m1_tracks = result['params']['m1_tracks']
    for s in result['shapes']['LI']:
        desc = s.get('desc', '')
        via_y = None
        if 'nmos_source' in desc and 'VSS' in m1_tracks: via_y = m1_tracks['VSS']
        elif 'pmos_source' in desc and 'VDD' in m1_tracks: via_y = m1_tracks['VDD']
        elif 'drain' in desc and 'OUT' in m1_tracks: via_y = m1_tracks['OUT']
        elif 'gate' in desc and 'IN' in m1_tracks: via_y = m1_tracks['IN']
        if via_y is None:
            continue
        assert s['y1'] <= via_y - enc, f"{desc}: y1={s['y1']} doesn't cover {via_y}-{enc}"
        assert s['y2'] >= via_y + enc, f"{desc}: y2={s['y2']} doesn't cover {via_y}+{enc}"


def test_decoder_does_not_mutate_input():
    import json
    with open(os.path.join(FIXTURE_DIR, 'buffer_original.json'), encoding='utf-8') as f:
        orig_data = json.load(f)
    orig_snapshot = json.dumps(orig_data, sort_keys=True)
    _resize_via_decoder(4, 6)
    with open(os.path.join(FIXTURE_DIR, 'buffer_original.json'), encoding='utf-8') as f:
        orig_data_after = json.load(f)
    assert json.dumps(orig_data_after, sort_keys=True) == orig_snapshot


if __name__ == '__main__':
    test_decoder_drops_removed_fins()
    test_decoder_shrinks_od_to_new_fin_top()
    test_decoder_updates_params_and_devices()
    test_decoder_extends_li_to_cover_vias()
    test_decoder_does_not_mutate_input()
    print("All decoder tests passed!")
