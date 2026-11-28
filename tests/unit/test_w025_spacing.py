"""Geometric controls at the operand boundary shared by the spacing predicates."""
from types import SimpleNamespace

import pytest

from layauto_v2.constraints.operands import metal
from layauto_v2.constraints.result import ShapeWitness
from layauto_v2.constraints.rules import measure_spacing
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect, source_value


def piece(region, name, bounds):
    return ShapeWitness('LI', Rect(*bounds), SourceRef('drawing'), region_id=region, piece_id=name)


def test_nearest_piece_inside_concave_regions_bounding_box():
    left = piece('L', 'left', (0, 0, 2, 8))
    bottom = piece('L', 'bottom', (2, 0, 8, 2))
    island = piece('island', 'square', (5, 4, 6, 5))
    # The island lies inside the L's bounding box, 3 from its left arm
    # and 2 from its bottom arm. There is only one independent region pair.
    pair, = measure_spacing(((left, bottom), (island,)), 1, 2)
    assert (pair.first, pair.second) == (bottom, island)
    assert (pair.dx_dbu, pair.dy_dbu, pair.distance_nm, pair.status) == (0, 2, 2, 'pass')


@pytest.mark.parametrize('bounds,squared,status', [
    ((4, 2, 6, 5), 0, 'same_layer_contact'),  # corner on foot, positive edge on stem
    ((4, 6, 6, 8), 0, 'violation'),           # only a corner on stem
    ((6, 8, 7, 9), 8, 'violation'),           # sqrt(8) lies below 3
])
def test_multipart_contact_and_distance_witness(bounds, squared, status):
    foot = piece('L', 'foot', (0, 0, 4, 2))
    stem = piece('L', 'stem', (2, 2, 4, 6))
    other = piece('neighbor', 'other', bounds)
    for pieces in ((foot, stem), (stem, foot)):
        pair, = measure_spacing((pieces, (other,)), 1, 3)
        assert (pair.first, pair.second) == (stem, other)
        assert (pair.distance_squared_nm2, pair.status) == (squared, status)


def test_drawn_metal_adapter_reuses_measurement_on_another_stream():
    # A post-binding operand probe. The supported deck still binds T07 to M1.
    layers = {}
    records = {}
    source = SourceRef('drawing', 'a' * 64)
    for layer_number, name in ((10, 'M1'), (11, 'M2')):
        stream = {'element': 'BOUNDARY', 'layer': layer_number, 'datatype': 0}
        declaration = {'name': name, 'stream_key': stream, 'role': 'interconnect'}
        layers[name] = {'policy': {'declaration': declaration}}
        for index, rect in enumerate(((0, 0, 2, 2), (5, 6, 8, 8), (2, 0, 5, 1))):
            record_id = f'{name}-{index}'
            offset = 64 * (layer_number * 3 + index)
            location = SourceRef(source.uri, source.sha256, byte_offset=offset, record_index=offset // 64)
            records[record_id] = {'id': record_id, 'layer': name, 'rect': rect,
                                  'stream_key': stream, 'source': source_value(location)}
    state = FrozenMap({'layers': layers, 'geometry': {
        'units': {'contract': {'canonical_tick_nm': 1}}, 'records': records}})
    snapshot = SimpleNamespace(state=state, binding=FrozenMap({'sources': {source.uri: source.sha256}}))
    for name in layers:
        scale, operands = metal(SimpleNamespace(snapshot=snapshot), name)
        pairs = measure_spacing(operands, scale, 5)
        assert len(pairs) == 3
        assert {s.record_id for pair in pairs for s in (pair.first, pair.second)} == {
            f'{name}-0', f'{name}-1', f'{name}-2'}
        assert sorted((p.distance_squared_nm2, p.status) for p in pairs) == [
            (0, 'same_layer_contact'), (25, 'pass'), (25, 'pass')]
