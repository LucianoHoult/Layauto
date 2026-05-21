"""Unit tests for ``io_adapters.calibre_layer_map`` (slice 1.6).

Covers:
  * load_layer_map_with_derived: schema join, reverse index, missing-
    registry-entry detection.
  * apply_calibre_layer_overlay: A-tier center-point stamping, B-tier
    area-overlap stamping, color propagation, conflict detection,
    diffusion-sharing via duplicate device_id matches.
  * _summarise_back_to_shape_record: per-cell consensus → ShapeRecord.
"""

import os
import sys
import textwrap

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from io_adapters.calibre_layer_map import (
    load_layer_map_with_derived,
    apply_calibre_layer_overlay,
    LayerOverlayConflictError,
    _bbox_um_to_nm,
    _center_in_bbox,
    _area_overlap_ratio,
    _load_layout_to_source_from_ixref,
    _shapes_by_layer_from_device_info,
)


# =====================================================================
# Loader tests
# =====================================================================

def _write_yaml(tmp_path, name, payload):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(payload, sort_keys=False))
    return str(p)


def test_load_layer_map_with_derived_reverse_index(tmp_path):
    """Per-GDS-layer ``derived_layers`` flattens to a reverse map."""
    layer_yaml = _write_yaml(tmp_path, 'lm.yaml', {
        'layers': [
            {'name': 'POLY', 'gds': [2, 0], 'tier': 'A', 'orientation': 'V',
             'derived_layers': [
                 {'name': 'ngate_lvt', 'carries': ['device_id']},
                 {'name': 'POLY',      'carries': ['net_id']},
             ]},
            {'name': 'M1', 'gds': [5, 0], 'tier': 'A', 'orientation': 'H',
             'derived_layers': [
                 {'name': 'M1a', 'carries': ['net_id'], 'color': 'a'},
                 {'name': 'M1b', 'carries': ['net_id'], 'color': 'b'},
             ]},
            {'name': 'FIN', 'gds': [1, 0], 'tier': 'A',
             'derived_layers': []},
        ],
    })
    table = load_layer_map_with_derived(layer_yaml)
    assert set(table['gds_to_derived']) == {'POLY', 'M1'}
    assert table['derived_to_gds'] == {
        'ngate_lvt': 'POLY',
        'POLY':      'POLY',
        'M1a':       'M1',
        'M1b':       'M1',
    }
    poly_entries = table['gds_to_derived']['POLY']
    assert {e['name'] for e in poly_entries} == {'ngate_lvt', 'POLY'}
    m1a = next(e for e in table['gds_to_derived']['M1']
               if e['name'] == 'M1a')
    assert m1a['color'] == 'a'
    assert m1a['carries'] == ['net_id']


def test_load_layer_map_with_calibre_registry_join(tmp_path):
    layer_yaml = _write_yaml(tmp_path, 'lm.yaml', {
        'layers': [
            {'name': 'POLY', 'gds': [2, 0], 'tier': 'A',
             'derived_layers': [{'name': 'ngate_lvt',
                                 'carries': ['device_id']}]},
        ],
    })
    # Calibre registry: top-level list of derived layer records.
    reg_yaml = _write_yaml(tmp_path, 'cal.yaml', [
        {'name':             'ngate_lvt',
         'multi_patterning': None,
         'semantic_role':    'device_channel',
         'pin_role_hint':    'G',
         'derivation_doc':   'nmos_gate AND LVT'},
    ])
    table = load_layer_map_with_derived(layer_yaml, reg_yaml)
    assert table['derived_meta']['ngate_lvt']['pin_role_hint'] == 'G'
    assert table['missing_registry_entries'] == []


def test_load_layer_map_reports_missing_registry_entries(tmp_path):
    layer_yaml = _write_yaml(tmp_path, 'lm.yaml', {
        'layers': [{
            'name': 'M1', 'gds': [5, 0], 'tier': 'A',
            'derived_layers': [{'name': 'M1zzz', 'carries': ['net_id']}],
        }],
    })
    reg_yaml = _write_yaml(tmp_path, 'cal.yaml', [])
    table = load_layer_map_with_derived(layer_yaml, reg_yaml)
    assert table['missing_registry_entries'] == ['M1zzz']


def test_load_real_project_layer_map_table():
    """Smoke test: the committed tech/{layer,calibre_layer}_map.yaml
    load + join without errors."""
    layer_yaml = os.path.join(os.path.dirname(__file__),
                              '..', '..', 'tech', 'layer_map.yaml')
    cal_yaml = os.path.join(os.path.dirname(__file__),
                            '..', '..', 'tech', 'calibre_layer_map.yaml')
    table = load_layer_map_with_derived(layer_yaml, cal_yaml)
    # POLY must list both Vt variants + the passthrough.
    poly_names = {e['name'] for e in table['gds_to_derived']['POLY']}
    assert {'ngate_lvt', 'pgate_lvt', 'POLY'}.issubset(poly_names)
    # OD must list nsd + psd as device-id sources.
    od_entries = table['gds_to_derived']['OD']
    assert 'nsd' in {e['name'] for e in od_entries}
    nsd = next(e for e in od_entries if e['name'] == 'nsd')
    assert set(nsd['carries']) == {'device_id', 'net_id'}


# =====================================================================
# Helpers
# =====================================================================

def test_bbox_um_to_nm():
    assert _bbox_um_to_nm({'x1': 0.044, 'y1': 0.0275,
                            'x2': 0.064, 'y2': 0.1525}) == (
        44.0, 27.5, 64.0, 152.5)


def test_center_in_bbox():
    assert _center_in_bbox(54.0, 90.0, (44, 27.5, 64, 152.5))
    assert not _center_in_bbox(54.0, 200.0, (44, 27.5, 64, 152.5))
    # Boundary inclusion.
    assert _center_in_bbox(44.0, 27.5, (44, 27.5, 64, 152.5))


def test_area_overlap_ratio():
    # Full containment.
    assert _area_overlap_ratio((0, 0, 10, 10), (-5, -5, 15, 15)) == 1.0
    # Half overlap.
    assert _area_overlap_ratio((0, 0, 10, 10), (5, 0, 15, 10)) == 0.5
    # Disjoint.
    assert _area_overlap_ratio((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


# =====================================================================
# Apply overlay — A-tier
# =====================================================================

class _FakeLayerGrid:
    def __init__(self, orientation, pitch, offset=0, min_width=20):
        self.orientation = orientation
        self.pitch = pitch
        self.offset = offset
        self.min_width = min_width

    def track_to_physical(self, idx):
        return self.offset + idx * self.pitch


class _FakeGrid:
    def __init__(self):
        self.layers = {}
        self.ortho_pairs = {}
        self.b_tier_axes = {}
        self.b_tier_cells = {}

    def get_ortho_layer(self, name):
        on = self.ortho_pairs.get(name)
        return self.layers.get(on) if on else None


class _FakeSegment:
    def __init__(self, layer, track_idx, start_anchor, end_anchor,
                 net_id='', device_id=None, color=None, shape_record=None):
        self.layer = layer
        self.track_idx = track_idx
        self.start_anchor = start_anchor
        self.end_anchor = end_anchor
        self.net_id = net_id
        self.device_id = device_id
        self.color = color
        self.shape_record = shape_record


class _FakeNet:
    def __init__(self, name, segments):
        self.name = name
        self.segments = segments


class _FakeModel:
    def __init__(self, nets=None, shape_pool=None):
        self.nets = nets or {}
        self.shape_pool = shape_pool or []


class _FakeShapeRecord:
    def __init__(self, layer, bbox_nm):
        self.layer = layer
        self.bbox_nm = bbox_nm
        self.net_id = None
        self.device_id = None


class _FakeCell:
    """Mimics CellOccupancy for the overlay tests."""
    def __init__(self, layer, track_a, track_b, net_id=None,
                 owner_device_id=None, shared_with=None, color=None,
                 shape_record=None):
        self.layer = layer
        self.track_a = track_a
        self.track_b = track_b
        self.net_id = net_id
        self.owner_device_id = owner_device_id
        self.shared_with = shared_with if shared_with is not None else []
        self.color = color
        self.shape_record = shape_record


def _make_poly_grid():
    """POLY (V) × FIN (H) — POLY tracks at x=44, 64; FIN tracks at y=28..152."""
    grid = _FakeGrid()
    # POLY vertical: cross-coord = X.
    grid.layers['POLY'] = _FakeLayerGrid('V', pitch=20, offset=44,
                                          min_width=20)
    # FIN horizontal: ortho axis for POLY.
    grid.layers['FIN'] = _FakeLayerGrid('H', pitch=25, offset=28,
                                         min_width=7)
    grid.ortho_pairs['POLY'] = 'FIN'
    return grid


def _write_device_info_yaml(tmp_path, devices):
    """devices = [{layout_inst, device_type_number, layers}]."""
    payload = {'devices': devices}
    p = tmp_path / 'device_info.yaml'
    p.write_text(yaml.safe_dump(payload, sort_keys=False))
    return str(p)


def _write_net_shapes_yaml(tmp_path, nets):
    payload = {'nets': nets}
    p = tmp_path / 'net_shapes.yaml'
    p.write_text(yaml.safe_dump(payload, sort_keys=False))
    return str(p)


def test_apply_overlay_a_tier_center_in_active_stamps_device(tmp_path):
    """POLY segment whose center falls inside ngate_lvt bbox → stamps
    device_id. Mirrors the active-gate cell case from the plan."""
    grid = _make_poly_grid()
    # Segment centered at (POLY track 0 → x=44, FIN tracks 0..4 → y mid = 78).
    sr = _FakeShapeRecord('POLY', (44, 28, 64, 152))
    seg = _FakeSegment('POLY', track_idx=0,
                       start_anchor=0, end_anchor=4,
                       net_id='IN', shape_record=sr)
    model = _FakeModel(nets={'IN': _FakeNet('IN', [seg])},
                       shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'POLY': [
                {'name': 'ngate_lvt', 'carries': ['device_id'],
                 'color': None, 'exclude_from_grid': False},
            ],
        },
    }
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'ngate_lvt',
                     'shapes': [{'bbox_um': {'x1': 0.040, 'y1': 0.020,
                                              'x2': 0.070, 'y2': 0.160}}]}]},
    ])
    coverage = apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=None,
        layer_map_table=layer_map_table,
    )
    assert seg.device_id == 'M0'
    assert coverage['stamped'] == 1
    # ShapeRecord summary picks up the device.
    assert sr.device_id == 'M0'


def test_apply_overlay_a_tier_no_match_keeps_none(tmp_path):
    """Segment center outside derived bbox → no stamp."""
    grid = _make_poly_grid()
    sr = _FakeShapeRecord('POLY', (44, 200, 64, 300))
    # Center y ~= 28 + 10 * 25 = 278 (10 = midpoint of anchors 8..12).
    seg = _FakeSegment('POLY', track_idx=0,
                       start_anchor=8, end_anchor=12,
                       net_id='IN', shape_record=sr)
    model = _FakeModel(nets={'IN': _FakeNet('IN', [seg])}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'POLY': [
                {'name': 'ngate_lvt', 'carries': ['device_id'],
                 'color': None, 'exclude_from_grid': False},
            ],
        },
    }
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'ngate_lvt',
                     'shapes': [{'bbox_um': {'x1': 0.040, 'y1': 0.020,
                                              'x2': 0.070, 'y2': 0.160}}]}]},
    ])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=None,
        layer_map_table=layer_map_table,
    )
    assert seg.device_id is None


def test_apply_overlay_a_tier_color_stamped_on_metal(tmp_path):
    """M1a derived layer stamps cell.color = 'a'."""
    grid = _FakeGrid()
    grid.layers['M1'] = _FakeLayerGrid('H', pitch=36, offset=200,
                                        min_width=20)
    grid.layers['LI'] = _FakeLayerGrid('V', pitch=27, offset=18,
                                        min_width=17)
    grid.ortho_pairs['M1'] = 'LI'

    sr = _FakeShapeRecord('M1', (0, 200, 108, 220))
    seg = _FakeSegment('M1', track_idx=0,
                       start_anchor=0, end_anchor=3,
                       net_id='OUT', shape_record=sr)
    model = _FakeModel(nets={'OUT': _FakeNet('OUT', [seg])},
                       shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'M1': [{'name': 'M1a', 'carries': ['net_id'],
                    'color': 'a', 'exclude_from_grid': False}],
        },
    }
    net_shapes = _write_net_shapes_yaml(tmp_path, [
        {'lvs_index': 1, 'lvs_name': 'OUT', 'schematic_name': 'OUT',
         'layers': [{'name': 'M1a',
                     'shapes': [{'bbox_um': {'x1': 0.0,   'y1': 0.200,
                                              'x2': 0.108, 'y2': 0.220}}]}]},
    ])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=None,
        net_shapes_yaml_path=net_shapes,
        layer_map_table=layer_map_table,
    )
    assert seg.color == 'a'


def test_apply_overlay_a_tier_net_conflict_raises(tmp_path):
    """Two net_shapes give the segment two different net_ids → raise."""
    grid = _make_poly_grid()
    # Segment with no pre-stamped net_id.
    sr = _FakeShapeRecord('POLY', (44, 28, 64, 152))
    seg = _FakeSegment('POLY', track_idx=0,
                       start_anchor=0, end_anchor=4,
                       net_id='', shape_record=sr)
    model = _FakeModel(nets={'X': _FakeNet('X', [seg])}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'POLY': [{'name': 'POLY', 'carries': ['net_id'],
                      'color': None, 'exclude_from_grid': False}],
        },
    }
    net_shapes = _write_net_shapes_yaml(tmp_path, [
        {'lvs_index': 1, 'lvs_name': 'NET_A', 'schematic_name': 'NET_A',
         'layers': [{'name': 'POLY',
                     'shapes': [{'bbox_um': {'x1': 0.04, 'y1': 0.02,
                                              'x2': 0.07, 'y2': 0.20}}]}]},
        {'lvs_index': 2, 'lvs_name': 'NET_B', 'schematic_name': 'NET_B',
         'layers': [{'name': 'POLY',
                     'shapes': [{'bbox_um': {'x1': 0.04, 'y1': 0.02,
                                              'x2': 0.07, 'y2': 0.20}}]}]},
    ])
    with pytest.raises(LayerOverlayConflictError, match='net_id'):
        apply_calibre_layer_overlay(
            model, grid,
            device_info_yaml_path=None,
            net_shapes_yaml_path=net_shapes,
            layer_map_table=layer_map_table,
        )


# =====================================================================
# Apply overlay — B-tier (diffusion sharing)
# =====================================================================

def _make_od_grid():
    """OD on POLY (V) × FIN (H) axes — matches existing project structure."""
    grid = _make_poly_grid()
    grid.b_tier_axes['OD'] = ('POLY', 'FIN')
    grid.b_tier_cells['OD'] = {}
    return grid


def test_apply_overlay_b_tier_diffusion_sharing(tmp_path):
    """Two nsd shapes (M0 + M1) hit the same OD cell → owner+shared."""
    grid = _make_od_grid()
    sr = _FakeShapeRecord('OD', (44, 28, 64, 53))
    cell = _FakeCell('OD', track_a=0, track_b=0, shape_record=sr)
    grid.b_tier_cells['OD'][(0, 0)] = cell
    model = _FakeModel(nets={}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'OD': [{'name': 'nsd', 'carries': ['device_id', 'net_id'],
                    'color': None, 'exclude_from_grid': False}],
        },
    }
    # Both M0 and M1 have nsd shapes covering the same cell.
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'nsd',
                     'shapes': [{'bbox_um': {'x1': 0.030, 'y1': 0.020,
                                              'x2': 0.080, 'y2': 0.060}}]}]},
        {'layout_inst': 'M1', 'device_type_number': 0,
         'layers': [{'name': 'nsd',
                     'shapes': [{'bbox_um': {'x1': 0.030, 'y1': 0.020,
                                              'x2': 0.080, 'y2': 0.060}}]}]},
    ])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=None,
        layer_map_table=layer_map_table,
    )
    assert cell.owner_device_id == 'M0'
    assert cell.shared_with == ['M1']


def test_apply_overlay_b_tier_no_overlap_threshold_skip(tmp_path):
    """<50% area overlap → no stamp."""
    grid = _make_od_grid()
    sr = _FakeShapeRecord('OD', (44, 28, 64, 53))
    cell = _FakeCell('OD', track_a=0, track_b=0, shape_record=sr)
    grid.b_tier_cells['OD'][(0, 0)] = cell
    model = _FakeModel(nets={}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'OD': [{'name': 'nsd', 'carries': ['device_id', 'net_id'],
                    'color': None, 'exclude_from_grid': False}],
        },
    }
    device_info = _write_device_info_yaml(tmp_path, [
        # nsd shape only marginally overlaps the cell (corner clip).
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'nsd',
                     'shapes': [{'bbox_um': {'x1': 0.060, 'y1': 0.050,
                                              'x2': 0.070, 'y2': 0.060}}]}]},
    ])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=None,
        layer_map_table=layer_map_table,
    )
    assert cell.owner_device_id is None


def test_apply_overlay_b_tier_net_conflict_raises(tmp_path):
    """Two different net_shapes on same VIA0 cell → raise."""
    grid = _FakeGrid()
    grid.layers['LI'] = _FakeLayerGrid('V', pitch=27, offset=18, min_width=17)
    grid.layers['M1'] = _FakeLayerGrid('H', pitch=36, offset=8, min_width=20)
    grid.b_tier_axes['VIA0'] = ('LI', 'M1')
    grid.b_tier_cells['VIA0'] = {}
    sr = _FakeShapeRecord('VIA0', (10, 0, 30, 20))
    cell = _FakeCell('VIA0', track_a=0, track_b=0, shape_record=sr)
    grid.b_tier_cells['VIA0'][(0, 0)] = cell
    model = _FakeModel(nets={}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'VIA0': [{'name': 'VIA0', 'carries': ['net_id'],
                      'color': None, 'exclude_from_grid': False}],
        },
    }
    net_shapes = _write_net_shapes_yaml(tmp_path, [
        {'lvs_index': 1, 'lvs_name': 'A', 'schematic_name': 'A',
         'layers': [{'name': 'VIA0',
                     'shapes': [{'bbox_um': {'x1': 0.010, 'y1': -0.005,
                                              'x2': 0.030, 'y2': 0.025}}]}]},
        {'lvs_index': 2, 'lvs_name': 'B', 'schematic_name': 'B',
         'layers': [{'name': 'VIA0',
                     'shapes': [{'bbox_um': {'x1': 0.010, 'y1': -0.005,
                                              'x2': 0.030, 'y2': 0.025}}]}]},
    ])
    with pytest.raises(LayerOverlayConflictError, match='net_id'):
        apply_calibre_layer_overlay(
            model, grid,
            device_info_yaml_path=None,
            net_shapes_yaml_path=net_shapes,
            layer_map_table=layer_map_table,
        )


# =====================================================================
# Co-occurrence (active-gate normal state)
# =====================================================================

def test_co_occurrence_device_id_and_net_id_allowed(tmp_path):
    """Active-gate cell: one derived layer (ngate_lvt) stamps device_id;
    a different derived layer (POLY passthrough) stamps net_id. Both
    succeed without conflict."""
    grid = _make_poly_grid()
    sr = _FakeShapeRecord('POLY', (44, 28, 64, 152))
    seg = _FakeSegment('POLY', track_idx=0,
                       start_anchor=0, end_anchor=4,
                       net_id='', shape_record=sr)
    model = _FakeModel(nets={'X': _FakeNet('X', [seg])}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'POLY': [
                {'name': 'ngate_lvt', 'carries': ['device_id'],
                 'color': None, 'exclude_from_grid': False},
                {'name': 'POLY',      'carries': ['net_id'],
                 'color': None, 'exclude_from_grid': False},
            ],
        },
    }
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'ngate_lvt',
                     'shapes': [{'bbox_um': {'x1': 0.040, 'y1': 0.020,
                                              'x2': 0.070, 'y2': 0.160}}]}]},
    ])
    net_shapes = _write_net_shapes_yaml(tmp_path, [
        {'lvs_index': 1, 'lvs_name': 'IN', 'schematic_name': 'IN',
         'layers': [{'name': 'POLY',
                     'shapes': [{'bbox_um': {'x1': 0.040, 'y1': 0.010,
                                              'x2': 0.070, 'y2': 0.420}}]}]},
    ])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=net_shapes,
        layer_map_table=layer_map_table,
    )
    assert seg.device_id == 'M0'
    assert seg.net_id == 'IN'


# =====================================================================
# ShapeRecord summary derivation
# =====================================================================

def test_shape_record_summary_one_net_consensus(tmp_path):
    """A shape backing two cells with the same net → ShapeRecord.net_id
    is set to that net."""
    grid = _make_poly_grid()
    sr = _FakeShapeRecord('POLY', (44, 28, 64, 152))
    seg = _FakeSegment('POLY', track_idx=0,
                       start_anchor=0, end_anchor=4,
                       net_id='IN', shape_record=sr)
    model = _FakeModel(nets={'IN': _FakeNet('IN', [seg])},
                       shape_pool=[sr])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=None,
        net_shapes_yaml_path=None,
        layer_map_table={'gds_to_derived': {}},
    )
    assert sr.net_id == 'IN'


def test_shape_record_summary_multi_device_leaves_none(tmp_path):
    """Two B-tier cells of the same shape with different devices →
    ShapeRecord.device_id stays None (no consensus)."""
    grid = _make_od_grid()
    sr = _FakeShapeRecord('OD', (44, 28, 64, 200))
    cell0 = _FakeCell('OD', 0, 0, owner_device_id='M0', shape_record=sr)
    cell1 = _FakeCell('OD', 0, 1, owner_device_id='M1', shape_record=sr)
    grid.b_tier_cells['OD'][(0, 0)] = cell0
    grid.b_tier_cells['OD'][(0, 1)] = cell1
    model = _FakeModel(nets={}, shape_pool=[sr])
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=None,
        net_shapes_yaml_path=None,
        layer_map_table={'gds_to_derived': {}},
    )
    assert sr.device_id is None


# =====================================================================
# Smoke: live buffer fixture through the real overlay
# =====================================================================

def test_layout_to_source_from_ixref(tmp_path):
    ix = tmp_path / 'ixref.yaml'
    ix.write_text(yaml.safe_dump({
        'cell': {'layout_name': 'X', 'source_name': 'X',
                  'layout_pin_count': 4, 'source_pin_count': 4},
        'devices': [
            {'layout_inst': 'M0', 'source_inst': 'MN0', 'sd_swapped': False},
            {'layout_inst': 'M1', 'source_inst': 'MP0', 'sd_swapped': True},
        ],
    }))
    mapping = _load_layout_to_source_from_ixref(str(ix))
    assert mapping == {'M0': 'MN0', 'M1': 'MP0'}


def test_layout_to_source_missing_ixref_returns_empty(tmp_path):
    assert _load_layout_to_source_from_ixref(None) == {}
    assert _load_layout_to_source_from_ixref(str(tmp_path / 'nope.yaml')) == {}


def test_device_info_index_translates_layout_inst(tmp_path):
    """Codex P1 regression: device_info.yaml uses LVS names (M0/M1) but
    the rest of LayoutModel uses schematic names (MN0/MP0). With the
    iXref-derived translation table, the stamped device_id must be the
    schematic name."""
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'nsd',
                     'shapes': [{'bbox_um': {'x1': 0.0, 'y1': 0.0,
                                              'x2': 0.01, 'y2': 0.01}}]}]},
        {'layout_inst': 'M1', 'device_type_number': 1,
         'layers': [{'name': 'psd',
                     'shapes': [{'bbox_um': {'x1': 0.0, 'y1': 0.02,
                                              'x2': 0.01, 'y2': 0.03}}]}]},
    ])
    idx = _shapes_by_layer_from_device_info(
        device_info, layout_to_source={'M0': 'MN0', 'M1': 'MP0'})
    assert idx['nsd'][0]['device_id'] == 'MN0'
    assert idx['psd'][0]['device_id'] == 'MP0'


def test_apply_overlay_translates_layout_inst_via_ixref(tmp_path):
    """End-to-end: overlay run with ixref_yaml_path stamps schematic
    names onto B-tier cells. Without translation the cell would carry
    'M0' and break the solver's sr.device_id == device.inst_name filter."""
    grid = _make_od_grid()
    sr = _FakeShapeRecord('OD', (44, 28, 64, 53))
    cell = _FakeCell('OD', track_a=0, track_b=0, shape_record=sr)
    grid.b_tier_cells['OD'][(0, 0)] = cell
    model = _FakeModel(nets={}, shape_pool=[sr])
    layer_map_table = {
        'gds_to_derived': {
            'OD': [{'name': 'nsd', 'carries': ['device_id'],
                    'color': None, 'exclude_from_grid': False}],
        },
    }
    device_info = _write_device_info_yaml(tmp_path, [
        {'layout_inst': 'M0', 'device_type_number': 0,
         'layers': [{'name': 'nsd',
                     'shapes': [{'bbox_um': {'x1': 0.030, 'y1': 0.020,
                                              'x2': 0.080, 'y2': 0.060}}]}]},
    ])
    ixref = tmp_path / 'ixref.yaml'
    ixref.write_text(yaml.safe_dump({
        'cell': {'layout_name': 'X', 'source_name': 'X',
                  'layout_pin_count': 4, 'source_pin_count': 4},
        'devices': [
            {'layout_inst': 'M0', 'source_inst': 'MN0', 'sd_swapped': False},
        ],
    }))
    apply_calibre_layer_overlay(
        model, grid,
        device_info_yaml_path=device_info,
        net_shapes_yaml_path=None,
        layer_map_table=layer_map_table,
        ixref_yaml_path=str(ixref),
    )
    # The cell — and the ShapeRecord summary — must carry 'MN0', not 'M0'.
    assert cell.owner_device_id == 'MN0'
    assert sr.device_id == 'MN0'


def test_net_data_from_net_shapes_matches_legacy_query(fixture_dir):
    """Slice 1.6b: the net_shapes-sourced net_data must carry the same
    shapes (layer + nm bbox) and reconstructed pins as the legacy
    calibre_net_query.json, so the production net-source cutover is
    byte-golden-safe."""
    import json
    from io_adapters.parser import (
        parse_calibre_device_query, net_data_from_net_shapes,
    )
    devices = parse_calibre_device_query(
        os.path.join(fixture_dir, 'calibre_device_query.json'))
    new = net_data_from_net_shapes(
        os.path.join(fixture_dir, 'net_shapes.yaml'), devices)
    legacy = json.load(
        open(os.path.join(fixture_dir, 'calibre_net_query.json')))

    assert set(new) == set(legacy)
    for net_name in legacy:
        # Same shape geometry (layer + integer-nm bbox), order-insensitive.
        def key(s):
            return (s['layer'], s['x1'], s['y1'], s['x2'], s['y2'])
        new_shapes = {key(s) for s in new[net_name]['shapes']}
        legacy_shapes = {key(s) for s in legacy[net_name]['shapes']}
        assert new_shapes == legacy_shapes, (
            f"{net_name}: net_shapes geometry != legacy net_query")
        # Same pins (reconstructed from device pin maps).
        assert (sorted(tuple(p) for p in new[net_name]['pins'])
                == sorted(tuple(p) for p in legacy[net_name]['pins']))
        # Same net type heuristic.
        assert new[net_name]['type'] == legacy[net_name]['type']


def test_apply_overlay_on_live_buffer_fixture_no_conflicts(fixture_dir):
    """Run the real overlay against the live buffer fixture + the
    committed device_info.yaml / net_shapes.yaml. Must not raise."""
    from io_adapters.parser import build_layout_model
    layer_yaml = os.path.join(os.path.dirname(__file__),
                              '..', '..', 'tech', 'layer_map.yaml')
    cal_yaml = os.path.join(os.path.dirname(__file__),
                            '..', '..', 'tech', 'calibre_layer_map.yaml')
    model, grid = build_layout_model(
        device_query_path=os.path.join(fixture_dir,
                                         'calibre_device_query.json'),
        net_query_path=os.path.join(fixture_dir,
                                      'calibre_net_query.json'),
        bbox_path=os.path.join(fixture_dir, 'bbox_by_layer.json'),
        layout_json_path=os.path.join(fixture_dir,
                                        'buffer_original.json'),
        device_info_yaml_path=os.path.join(fixture_dir,
                                             'device_info.yaml'),
        net_shapes_yaml_path=os.path.join(fixture_dir,
                                            'net_shapes.yaml'),
        layer_yaml_path=layer_yaml,
        calibre_layer_map_yaml_path=cal_yaml,
    )
    coverage = getattr(model, 'calibre_layer_overlay_coverage', None)
    assert coverage is not None
    assert coverage['derived_shape_count'] > 0
    assert coverage['cells_visited'] > 0
