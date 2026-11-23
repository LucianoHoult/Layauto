"""Real captures, exact hand coordinates and source-to-fragment reconstruction for W018."""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction

import pytest

from layauto_v2.domain.geometry import GeometryRef
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry
from layauto_v2.normalization.projection import ProjectionBindingError, build_discrete_occupancy
from layauto_v2.normalization.projection_model import ProjectionConfigError, bind_projection_model
from layauto_v2.state.discrete_occupancy import build_discrete_occupancy as project_layout
from layauto_v2.state.projection_axes import CellGrid
from w005_cases import FIXTURE, copy_input, without_cache
from w008_geometry_cases import EXPECTED_RECTS, area, edit_geometry, overlap_area
from w009_cases import independent_difference, rewrite_geometry, special_input
from w018_cases import COORDINATE_URI, SAMPLE, build_geometry_from_site, select_projection

LAYER_COUNTS = {
    'BOUNDARY': 1, 'BODY_N': 1, 'BODY_P': 1, 'OD': 2, 'POLY': 1, 'FIN': 18,
    'LI': 3, 'CUT': 0, 'CONTACT': 4, 'VIA0': 3, 'GCONTACT': 1,
    'BTAP_N': 0, 'BTAP_P': 0, 'M1': 4, 'MARKER': 1,
}


def occupied(geometry, budget=100, effective=None):
    result = build_discrete_occupancy(geometry, fragment_budget=budget, effective=effective)
    assert result.status == 'success' and result.value is not None
    assert result.required_fragments == len(result.value.fragments)
    return result.value


@pytest.fixture(scope='module')
def main_geometry(tmp_path_factory):
    root = copy_input(tmp_path_factory.mktemp('w018-main'))
    select_projection(root)
    return build_geometry_from_site(root)


def test_sample_identity_all_layers_and_both_directions(main_geometry):
    captured = {item.uri: item for item in main_geometry.input.parse.sources}
    assert captured[COORDINATE_URI].data == SAMPLE.read_bytes()
    occ = occupied(main_geometry, budget=48)
    layout = main_geometry.value.layout
    assert {row.layer: row.record_count for row in occ.layers} == LAYER_COUNTS
    assert len(occ.layers) == 15
    kinds = {'BOUNDARY': 'projection_none', 'MARKER': 'projection_none',
             'LI': '2d_cells', 'M1': '2d_cells', 'FIN': '1d_track'}
    assert all(row.projection == kinds.get(row.layer, 'missing_declaration') for row in occ.layers)
    assert len(main_geometry.value.fragments) == 41
    assert Counter(f.layer for f in occ.fragments) == {'FIN': 18, 'LI': 20, 'M1': 10}
    assert all(f.view == 'drawn' for f in occ.fragments)
    for record in layout.records:
        fragments = occ.for_record(record.id)
        if record.layer not in ('FIN', 'LI', 'M1'):
            assert fragments == ()
            diagnostic, = [d for d in occ.diagnostics if d.source.record_id == record.id]
            assert diagnostic.status == kinds.get(record.layer, 'missing_declaration')
            assert diagnostic.source.rect == record.rect
            continue
        independent_difference(record.rect.bounds, (), [f.rect.bounds for f in fragments])
        assert all(f.source.record_source == record.source for f in fragments)
        for fragment in fragments:
            assert fragment.unit_ref == layout.units.ref
            assert fragment in occ.in_cell(fragment.layer, *fragment.indices, view='drawn')
            assert fragment.source.record_source.sha256 == captured['source.gds'].sha256
            offset = fragment.source.record_source.byte_offset
            assert captured['source.gds'].data[offset:offset + 4] == bytes.fromhex('00040800')
    with pytest.raises((FrozenInstanceError, AttributeError)):
        occ.fragments[0].rect = None


def test_actual_fin_track_numbers_are_independent_of_stream_order(main_geometry):
    occ = occupied(main_geometry)
    layout = main_geometry.value.layout
    for k in range(18):
        fragment, = occ.in_cell('FIN', k)
        assert fragment.rect.bounds == (10, 24 + 10 * k, 110, 26 + 10 * k)
        record = layout.record(fragment.record_id)
        assert fragment.rect == record.rect
        assert record.source == fragment.source.record_source


def test_li_and_m1_each_use_their_own_declared_edges(main_geometry):
    occ = occupied(main_geometry)
    # All cell indices are hand enumerated from the GDS and reviewed edge lists.
    cases = {
        'LI': (20, 10, [
            [(1, y) for y in (3, 4, 5)], [(1, y) for y in (13, 14, 15)],
            [(4, y) for y in range(3, 17)],
        ]),
        'M1': (16, 20, [
            [(0, 2), (1, 2), (2, 2)], [(0, 7), (1, 7), (2, 7)],
            [(3, 4), (4, 4)], [(5, 4), (6, 4)],
        ]),
    }
    for layer, (pitch_x, pitch_y, expected_cells) in cases.items():
        layer_rows = occ.for_layer(layer, view='drawn')
        assert sum(f.rect.area for f in layer_rows) == {'LI': 1110, 'M1': 1340}[layer]
        for bounds, cells in zip(EXPECTED_RECTS[layer], expected_cells, strict=True):
            source = next(r for r in main_geometry.value.layout.records
                          if r.layer == layer and r.rect.bounds == bounds)
            rows = occ.for_record(source.id)
            assert {f.indices for f in rows} == set(cells)
            for f in rows:
                i, j = f.indices
                cell = (i * pitch_x, j * pitch_y, (i + 1) * pitch_x, (j + 1) * pitch_y)
                assert overlap_area(cell, f.rect.bounds) == area(f.rect.bounds)
                assert overlap_area(cell, bounds) == area(f.rect.bounds)


def test_legacy_owner_retains_geometry_and_distinguishes_missing_from_skip():
    geometry = build_geometry_from_site(FIXTURE)
    occ = occupied(geometry, budget=0)
    assert len(geometry.value.layout.records) == 40 and len(geometry.value.fragments) == 41
    assert {r.layer: r.record_count for r in occ.layers} == LAYER_COUNTS
    assert {r.projection for r in occ.layers} == {'missing_declaration'}
    assert len(occ.fragments) == 0
    assert {d.source.record_id for d in occ.diagnostics} == {r.id for r in geometry.value.layout.records}


@pytest.mark.parametrize(('path', 'replacement', 'field'), [
    (('layers', 'LI', 'y_edges'), None, 'layers/LI/y_edges'),
    (('layers', 'LI', 'x_edges', 'pitch_dbu'), 0, 'layers/LI/x_edges/pitch_dbu'),
    (('layers', 'M1', 'y_edges', 'cells'), True, 'layers/M1/y_edges/cells'),
    (('layers', 'LI', 'index_axis'), 'y', 'layers/LI/index_axis'),
    (('layers', 'BOUNDARY', 'y_edges'), {}, 'layers/BOUNDARY/y_edges'),
    (('layers', 'FIN', 'pitch_nm_ref'), 'physical#/fin_count_profile/absent', 'layers/FIN/pitch_nm_ref'),
    (('layers', 'FIN', 'projection'), 'automatic', 'layers/FIN/projection'),
    (('layers', 'ANOTHER'), {'projection': 'none'}, 'layers/ANOTHER'),
    (('units_ref',), 'formats#/cdl_dialect', 'units_ref'),
])
def test_invalid_selected_declaration_keeps_located_source_and_raw_geometry(tmp_path, path, replacement, field):
    def mutate(model):
        parent = model
        for key in path[:-1]:
            parent = parent[key]
        if replacement is None:
            del parent[path[-1]]
        else:
            parent[path[-1]] = replacement

    root = copy_input(tmp_path)
    select_projection(root, mutate=mutate)
    geometry = build_geometry_from_site(root)
    with pytest.raises(ProjectionConfigError) as caught:
        build_discrete_occupancy(geometry, fragment_budget=100)
    assert caught.value.geometry is geometry
    source = caught.value.issue.source
    assert source.uri == COORDINATE_URI and source.sha256 == hashlib.sha256((root / COORDINATE_URI).read_bytes()).hexdigest()
    assert source.field == '/coordinate_projection/' + field
    assert len(geometry.value.layout.records) == 40 and len(geometry.value.fragments) == 41


def test_reader_detects_changed_selected_bytes_before_binding(tmp_path):
    root = copy_input(tmp_path)
    select_projection(root)
    path = root / COORDINATE_URI
    path.write_bytes(path.read_bytes() + b'\n')
    result = read_inputs(root / 'site_config.yaml')
    assert result.status == 'error'
    issue, = result.issues
    assert issue.code == 'ClosureHashMismatch' and '/closure/entries/' in issue.source.field


@pytest.mark.parametrize(('phase', 'xpitch', 'ypitch', 'count', 'first_cells'), [
    (1, 20, 10, 23, {(1, 2), (1, 3), (1, 4), (1, 5)}),
    (0, 10, 20, 16, {(2, 1), (2, 2), (3, 1), (3, 2)}),
])
def test_same_gds_under_shifted_and_changed_axes(tmp_path, main_geometry, phase, xpitch, ypitch, count, first_cells):
    def mutate(model):
        li = model['layers']['LI']
        li['x_edges'].update(pitch_dbu=xpitch, cells=160 // xpitch)
        li['y_edges'].update(pitch_dbu=ypitch, cells=200 // ypitch, offset_dbu=phase)

    root = copy_input(tmp_path)
    select_projection(root, mutate=mutate)
    geometry = build_geometry_from_site(root)
    assert geometry.value == main_geometry.value
    occ = occupied(geometry)
    assert len(occ.for_layer('LI')) == count
    first = next(r for r in geometry.value.layout.records if r.rect.bounds == (28, 30, 34, 55))
    rows = occ.for_record(first.id)
    assert {f.indices for f in rows} == first_cells
    independent_difference(first.rect.bounds, (), [f.rect.bounds for f in rows])
    assert {f.model_id for f in rows}.isdisjoint(f.model_id for f in occupied(main_geometry).fragments)


def test_same_track_declaration_on_other_layer_and_shape_failures(tmp_path):
    def mutate(model):
        layers = model['layers']
        layers['CUT'] = layers.pop('FIN')

    root = copy_input(tmp_path)
    select_projection(root, mutate=mutate)
    rectangles = [(10, 24, 110, 26), (10, 29, 110, 31), (10, 23, 110, 25), (10, 24, 110, 27)]
    edit_geometry(root, append=[('CUT', rect) for rect in rectangles])
    geometry = build_geometry_from_site(root)
    occ = occupied(geometry)
    assert occ.for_layer('FIN') == ()
    first, = occ.in_cell('CUT', 0)
    assert first.rect.bounds == rectangles[0]
    issues = {d.source.rect.bounds: d for d in occ.diagnostics if d.source.layer == 'CUT'}
    assert {box: d.status for box, d in issues.items()} == {
        rectangles[1]: 'off_track', rectangles[2]: 'outside_range', rectangles[3]: 'unsupported_strip',
    }
    assert issues[rectangles[1]].track.neighbours == ((0, Fraction(5)), (1, Fraction(-5)))
    assert {r.rect.bounds for r in geometry.value.layout.records if r.layer == 'CUT'} == set(rectangles)


def test_negative_origin_nonzero_offsets_duplicates_and_partial_outside(tmp_path):
    # Explicit S2 grid has X [-6,4,14], Y [-3,1,5]. Two GDS records have identical XY.
    def mutate(model):
        model['frame_origin_nm'] = [-8, 2]
        model['layers'] = {
            'LI': {'projection': '2d_cells',
                   'x_edges': {'offset_dbu': 2, 'pitch_dbu': 10, 'cells': 2},
                   'y_edges': {'offset_dbu': -5, 'pitch_dbu': 4, 'cells': 2}},
            'BTAP_N': {'projection': 'none'},
        }
        model['layers']['CUT'] = model['layers']['LI'].copy()

    root = copy_input(tmp_path)
    select_projection(root, mutate=mutate)
    inside = (-2, -1, 6, 3)
    outside = (-7, -1, 6, 3)
    rewrite_geometry(root, replace_layers={'LI': [inside, inside, outside]})
    geometry = build_geometry_from_site(root)
    occ = occupied(geometry, budget=8)
    reports = {r.layer: (r.record_count, r.projection) for r in occ.layers}
    assert reports['CUT'] == (0, '2d_cells')
    assert reports['BTAP_N'] == (0, 'projection_none')
    assert reports['BTAP_P'] == (0, 'missing_declaration')
    records = [r for r in geometry.value.layout.records if r.layer == 'LI' and r.rect.bounds == inside]
    assert len(records) == len({r.id for r in records}) == 2
    for record in records:
        rows = occ.for_record(record.id)
        assert {f.indices: f.rect.bounds for f in rows} == {
            (0, 0): (-2, -1, 4, 1), (0, 1): (-2, 1, 4, 3),
            (1, 0): (4, -1, 6, 1), (1, 1): (4, 1, 6, 3),
        }
        assert independent_difference(inside, (), [f.rect.bounds for f in rows]) == 32
    cell = occ.in_cell('LI', 1, 1)
    assert len(cell) == 2 and {f.record_id for f in cell} == {r.id for r in records}
    assert len({f.source.record_source.byte_offset for f in cell}) == 2
    rejected, = [d for d in occ.diagnostics if d.source.layer == 'LI']
    assert rejected.status == 'outside_range' and rejected.source.rect.bounds == outside
    assert occ.for_record(rejected.source.record_id) == ()


def test_cut_islands_same_cell_loses_no_area_or_provenance(tmp_path):
    def special_grid(model):
        li = model['layers']['LI']
        li['x_edges'].update(pitch_dbu=32, cells=5)
        li['y_edges'].update(pitch_dbu=16, cells=13)

    root = copy_input(tmp_path)
    special_input(root)
    without_cache(root)  # The optional main-cell cache describes a different top.
    select_projection(root, mutate=special_grid)
    geometry = build_geometry_from_site(root)
    effective = build_effective_geometry(geometry)
    assert effective.status == 'success', effective.issues
    occ = occupied(geometry, budget=5, effective=effective)
    raw, = occ.in_cell('LI', 4, 1, view='drawn')
    assert raw.rect.bounds == (130, 20, 150, 24)
    assert raw.source.record_source.byte_offset == 182
    assert raw.region_ref is None and raw.piece_ref is None and not raw.contributors
    cut, = [r for r in geometry.value.layout.records if r.layer == 'CUT']
    assert cut.rect.bounds == (139, 18, 141, 26) and cut.source.byte_offset == 246
    pieces = sorted(occ.in_cell('LI', 4, 1, view='effective'), key=lambda f: f.rect.x0)
    assert [f.rect.bounds for f in pieces] == [(130, 20, 139, 24), (141, 20, 150, 24)]
    assert [f.rect.area for f in pieces] == [36, 36] and pieces[1].rect.x0 - pieces[0].rect.x1 == 2
    assert independent_difference(raw.rect.bounds, [cut.rect.bounds], [f.rect.bounds for f in pieces]) == 72
    assert pieces == sorted(occ.for_record(raw.record_id, view='effective'), key=lambda f: f.rect.x0)
    assert all(f.record_id == raw.record_id and f.contributors == (cut.id,) for f in pieces)
    regions = effective.value.for_record(raw.record_id).regions
    expected = {(region.ref, piece.ref, piece.rect) for region in regions for piece in region.pieces}
    assert {(f.region_ref, f.piece_ref, f.rect) for f in pieces} == expected
    other, = occ.in_cell('LI', 1, 1, view='effective')
    assert other.rect.area == 40 and not other.contributors


def test_equal_drawn_geometry_with_different_capture_rejects_effective_result(tmp_path, main_geometry):
    root = copy_input(tmp_path)
    select_projection(root, mutate=lambda m: m['layers']['LI']['x_edges'].update(offset_dbu=1))
    other_geometry = build_geometry_from_site(root)
    assert other_geometry.value == main_geometry.value
    effective = build_effective_geometry(other_geometry)
    with pytest.raises(ProjectionBindingError) as caught:
        build_discrete_occupancy(main_geometry, effective=effective, fragment_budget=100)
    assert caught.value.geometry is main_geometry
    assert caught.value.issue.code == 'ForeignEffectiveGeometry' and caught.value.issue.source.uri


def test_cumulative_budget_rejects_before_any_cell_bounds(main_geometry, monkeypatch):
    assert len(occupied(main_geometry, budget=48).fragments) == 48
    def no_cells(*args):
        pytest.fail('occupancy must finish counting all inputs before enumerating any cell')
    monkeypatch.setattr(CellGrid, 'cell_bounds', no_cells)
    result = build_discrete_occupancy(main_geometry, fragment_budget=47)
    assert result.status == 'resource_limit' and result.value is None
    assert result.required_fragments == 48 and result.budget == 47
    assert result.exceeded_at is not None
    assert result.exceeded_at.record_source == result.layout.record(result.exceeded_at.record_id).source
    assert len(result.layout.records) == 40


def test_billion_by_billion_sparse_domain_and_unaffordable_full_window(tmp_path, monkeypatch):
    def massive(model):
        li = model['layers']['LI']
        model['layers'] = {'LI': li}
        li['x_edges'].update(cells=10**9, pitch_dbu=1)
        li['y_edges'].update(cells=10**9, pitch_dbu=1)

    root = copy_input(tmp_path)
    select_projection(root, mutate=massive)
    geometry = build_geometry_from_site(root)
    sparse = occupied(geometry, budget=1110)
    assert len(sparse.fragments) == 1110
    assert sparse.in_cell('LI', 10**9 - 1, 10**9 - 1) == ()
    # Same captured model, finite GDS rectangle large enough to cover the entire grid.
    rewrite_geometry(root, replace_layers={'LI': [(0, 0, 10**9, 10**9)]})
    full = build_geometry_from_site(root)
    def no_cells(*args):
        pytest.fail('unaffordable full grid must be rejected before allocating intersection fragments')
    monkeypatch.setattr(CellGrid, 'cell_bounds', no_cells)
    result = build_discrete_occupancy(full, fragment_budget=1110)
    assert result.status == 'resource_limit' and result.required_fragments == 10**18
    assert result.value is None and result.exceeded_at.rect.bounds == (0, 0, 10**9, 10**9)


def test_state_rejects_coordinates_bound_to_another_unit(main_geometry):
    model = bind_projection_model(main_geometry)
    foreign = replace(model, unit_ref=GeometryRef('unit', 'f' * 64))
    with pytest.raises(ValueError, match='unit'):
        project_layout(main_geometry.value.layout, foreign, fragment_budget=100)


def test_direct_physical_parameters_on_vertical_poly_strip(tmp_path):
    def vertical(model):
        model['frame_origin_nm'] = [7, -13]
        model['layers'] = {
            'POLY': {
                'projection': '1d_track', 'index_axis': 'x', 'pitch_nm': 9,
                'first_centre': {'basis': 'lower_edge_plus_half_width', 'lower_edge_nm': 51, 'width_nm': 4},
                'index_range_inclusive': [-3, 2],
            },
        }

    root = copy_input(tmp_path)
    select_projection(root, mutate=vertical)
    geometry = build_geometry_from_site(root)
    occ = occupied(geometry, budget=1)
    poly, = occ.in_cell('POLY', -3)
    assert poly.rect.bounds == (58, 10, 62, 190)
    axis = occ.model.layers['POLY']
    assert axis.centre(-3) == 60 and axis.centre(-2) == 69
    assert axis.locate(Fraction(129, 2)).neighbours == ((-3, Fraction(9, 2)), (-2, Fraction(-9, 2)))
