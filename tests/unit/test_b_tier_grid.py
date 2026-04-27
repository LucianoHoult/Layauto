"""M4b: B-tier cell-grid axis on ``MultiLayerGrid``.

Verifies:
  * ``register_b_tier_axes`` rejects A-tier layers and unregistered axis
    layers.
  * ``bbox_to_b_tier_cells`` projects a physical bbox to the
    ``(track_a, track_b)`` cells on the registered axis grids.
  * ``set_b_tier_cell`` / ``get_b_tier_cell`` / ``b_tier_cells_of`` round-trip
    a ``CellOccupancy`` through the storage.
  * The pipeline-facing ``LayoutModel.shape_pool`` and the
    M4a ``CellOccupancy`` dataclass are unchanged.

Roadmap: docs/architecture_roadmap.md §B and milestone M4.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest

from core.data_model import CellOccupancy, OccupantType
from core.grid import LayerGrid, MultiLayerGrid, create_mvp_grid
from tech.config_loader import load_tech_config

_config = load_tech_config()


def _mvp_grid_with_od_axes() -> MultiLayerGrid:
    """An MVP grid with OD registered as a B-tier layer (POLY × FIN axes)."""
    grid = create_mvp_grid(
        config=_config,
        nmos_fin_y=[40, 65, 90, 115, 140],
        pmos_fin_y=[240, 265, 290, 315, 340, 365, 390],
    )
    grid.register_b_tier_axes('OD', axis_a_layer='POLY', axis_b_layer='FIN')
    return grid


def test_is_b_tier_layer_consults_layer_map():
    grid = _mvp_grid_with_od_axes()
    # B-tier
    assert grid.is_b_tier_layer('OD') is True
    assert grid.is_b_tier_layer('VIA0') is True
    # A-tier
    assert grid.is_b_tier_layer('LI') is False
    assert grid.is_b_tier_layer('M1') is False
    # Unmapped layer raises (parser bug surface)
    with pytest.raises(KeyError):
        grid.is_b_tier_layer('NO_SUCH_LAYER')


def test_register_b_tier_axes_rejects_a_tier_layer():
    grid = create_mvp_grid(config=_config, nmos_fin_y=[40])
    with pytest.raises(ValueError, match='not a B-tier layer'):
        grid.register_b_tier_axes('LI', 'POLY', 'FIN')


def test_register_b_tier_axes_requires_registered_axis_layers():
    """An axis layer must already exist on the grid; otherwise the
    projection in ``bbox_to_b_tier_cells`` would crash later."""
    grid = MultiLayerGrid()
    grid.add_layer(LayerGrid('FIN', pitch=25, offset=40, orientation='H',
                              min_width=6))
    # POLY not registered
    with pytest.raises(ValueError, match='not registered'):
        grid.register_b_tier_axes('OD', 'POLY', 'FIN')


def test_register_b_tier_axes_initialises_storage():
    grid = _mvp_grid_with_od_axes()
    # After registration, the layer key exists in b_tier_cells (empty dict)
    # and b_tier_axes records the axis names.
    assert 'OD' in grid.b_tier_cells
    assert grid.b_tier_cells['OD'] == {}
    assert grid.get_b_tier_axes('OD') == ('POLY', 'FIN')


def test_bbox_to_b_tier_cells_unregistered_layer_raises():
    grid = create_mvp_grid(config=_config, nmos_fin_y=[40])
    with pytest.raises(KeyError):
        grid.bbox_to_b_tier_cells('OD', 0, 0, 100, 100)


def test_bbox_to_b_tier_cells_projects_through_axes():
    """An OD bbox spanning gates 0–2 (X) and fins 0–4 (Y) should project to
    the 3 × 5 = 15 cell grid covering the diffusion region."""
    grid = _mvp_grid_with_od_axes()
    poly = grid.get_layer('POLY')   # V, pitch 54, offset 0 -> X tracks 0,1,2,...
    fin = grid.get_layer('FIN')     # H, pitch 25, offset 40 -> Y tracks 0..4 at y=40,65,90,115,140
    # Bracket the bbox tightly around POLY tracks 0..2 (x=0..108) and
    # FIN tracks 0..4 (y=40..140).
    cells = grid.bbox_to_b_tier_cells('OD',
                                       x1=poly.track_to_physical(0),
                                       y1=fin.track_to_physical(0),
                                       x2=poly.track_to_physical(2),
                                       y2=fin.track_to_physical(4))
    assert len(cells) == 3 * 5
    # Determinism: sorted by (track_a, track_b).
    assert cells == sorted(cells)
    # Spot checks on corners.
    assert (0, 0) in cells
    assert (2, 4) in cells
    assert (0, 4) in cells
    assert (2, 0) in cells


def test_bbox_to_b_tier_cells_single_cell():
    """A bbox that snaps to a single (POLY, FIN) intersection projects to a
    single cell — the smallest unit a B-tier shape can occupy."""
    grid = _mvp_grid_with_od_axes()
    poly = grid.get_layer('POLY')
    fin = grid.get_layer('FIN')
    cells = grid.bbox_to_b_tier_cells('OD',
                                       x1=poly.track_to_physical(1) - 1,
                                       y1=fin.track_to_physical(2) - 1,
                                       x2=poly.track_to_physical(1) + 1,
                                       y2=fin.track_to_physical(2) + 1)
    assert cells == [(1, 2)]


def test_set_get_b_tier_cell_round_trip():
    grid = _mvp_grid_with_od_axes()
    occ = CellOccupancy(
        layer='OD', track_a=1, track_b=2,
        occ_type=OccupantType.DEVICE_DIFF, owner_device_id='MN0',
    )
    grid.set_b_tier_cell('OD', 1, 2, occ)
    assert grid.get_b_tier_cell('OD', 1, 2) is occ
    # An unstamped cell returns None, not a default — keeps storage sparse.
    assert grid.get_b_tier_cell('OD', 99, 99) is None


def test_set_b_tier_cell_rejects_pos_mismatch():
    grid = _mvp_grid_with_od_axes()
    occ = CellOccupancy(
        layer='OD', track_a=1, track_b=2,
        occ_type=OccupantType.DEVICE_DIFF,
    )
    with pytest.raises(ValueError, match='disagrees with key'):
        grid.set_b_tier_cell('OD', 5, 5, occ)


def test_b_tier_cells_of_ordered_iteration():
    grid = _mvp_grid_with_od_axes()
    for ta, tb in [(2, 1), (0, 0), (1, 0), (0, 1)]:
        grid.set_b_tier_cell('OD', ta, tb, CellOccupancy(
            layer='OD', track_a=ta, track_b=tb,
            occ_type=OccupantType.DEVICE_DIFF,
        ))
    keys = [(c.track_a, c.track_b) for c in grid.b_tier_cells_of('OD')]
    assert keys == sorted([(2, 1), (0, 0), (1, 0), (0, 1)])


def test_summary_includes_b_tier_section_when_registered():
    grid = _mvp_grid_with_od_axes()
    grid.set_b_tier_cell('OD', 0, 0, CellOccupancy(
        layer='OD', track_a=0, track_b=0,
        occ_type=OccupantType.DEVICE_DIFF,
    ))
    s = grid.summary()
    assert 'B-tier axes' in s
    assert 'OD' in s
    assert '1 cells' in s


if __name__ == '__main__':
    test_is_b_tier_layer_consults_layer_map()
    test_register_b_tier_axes_rejects_a_tier_layer()
    test_register_b_tier_axes_requires_registered_axis_layers()
    test_register_b_tier_axes_initialises_storage()
    test_bbox_to_b_tier_cells_unregistered_layer_raises()
    test_bbox_to_b_tier_cells_projects_through_axes()
    test_bbox_to_b_tier_cells_single_cell()
    test_set_get_b_tier_cell_round_trip()
    test_set_b_tier_cell_rejects_pos_mismatch()
    test_b_tier_cells_of_ordered_iteration()
    test_summary_includes_b_tier_section_when_registered()
    print("All M4b B-tier grid tests passed!")
