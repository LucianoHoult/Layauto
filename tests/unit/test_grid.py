"""Test grid coordinate ↔ track index transformations."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.grid import LayerGrid, create_mvp_grid


def test_layer_grid_basic():
    lg = LayerGrid('M1', pitch=36, offset=18, orientation='H', min_width=20)
    assert lg.track_to_physical(0) == 18
    assert lg.track_to_physical(1) == 54
    assert lg.physical_to_track(18) == 0
    assert lg.physical_to_track(54) == 1


def test_layer_grid_roundtrip():
    lg = LayerGrid('LI', pitch=27, offset=0, orientation='V', min_width=17)
    for idx in range(-2, 10):
        phys = lg.track_to_physical(idx)
        back = lg.physical_to_track(phys)
        assert back == idx, f"Roundtrip failed: {idx} → {phys} → {back}"


def test_layer_grid_snap():
    lg = LayerGrid('M1', pitch=36, offset=18, orientation='H', min_width=20)
    # Exactly on track
    assert lg.is_on_track(18)
    assert lg.is_on_track(54)
    # Off track
    assert not lg.is_on_track(30)


def test_mvp_grid_creation():
    grid = create_mvp_grid(
        nmos_fin_y=[40, 65, 90, 115, 140],
        pmos_fin_y=[240, 265, 290, 315, 340, 365, 390],
    )
    assert 'FIN' in grid.layers
    assert 'POLY' in grid.layers
    assert 'LI' in grid.layers
    assert 'M1' in grid.layers
    
    li = grid.get_layer('LI')
    assert li.pitch == 27
    assert li.physical_to_track(27) == 1  # S/D position
    assert li.physical_to_track(54) == 2  # Gate position
    assert li.physical_to_track(81) == 3  # S/D position


def test_grid_ortho_pairs():
    grid = create_mvp_grid(nmos_fin_y=[40])
    assert grid.ortho_pairs['LI'] == 'M1'
    assert grid.ortho_pairs['M1'] == 'LI'
    assert grid.ortho_pairs['FIN'] == 'POLY'


def test_physical_to_segment_coords():
    grid = create_mvp_grid(nmos_fin_y=[40, 65, 90, 115, 140])
    
    # A vertical LI bar at x=27 spanning y=13 to y=145
    coords = grid.physical_to_segment_coords('LI', 18, 13, 36, 145)
    assert coords['track_idx'] == 1  # x=27 → LI track 1


if __name__ == '__main__':
    test_layer_grid_basic()
    test_layer_grid_roundtrip()
    test_layer_grid_snap()
    test_mvp_grid_creation()
    test_grid_ortho_pairs()
    test_physical_to_segment_coords()
    print("All grid tests passed!")
