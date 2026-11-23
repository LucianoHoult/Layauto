"""Bind the selected coordinate owner to authenticated W008 inputs, without IO."""
from __future__ import annotations

from dataclasses import replace
from typing import Literal, cast

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import UnitBinding, integer, mapping, sequence
from layauto_v2.domain.regions import validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.state.projection_axes import CellGrid, EdgeAxis, TrackAxis
from layauto_v2.state.projection_model import LayerProjection, ProjectionModel
from layauto_v2.tech.projection import checked_layer, nm_parameter
from layauto_v2.tech.schema import LAYER_DISCRETIZATION, SchemaError
from .effective import _INPUT_TYPES
from .geometry import GeometryResult


class ProjectionConfigError(ValueError):
    """An invalid selected declaration, with its source location and prior geometry."""

    def __init__(self, issue: EvidenceIssue, geometry: GeometryResult) -> None:
        self.issue = issue
        self.geometry = geometry
        super().__init__(issue.message)


def _edge_axis(spec: FrozenMap, origin_nm: int, dimension: int, units: UnitBinding) -> EdgeAxis:
    if origin_nm % units.canonical_tick_nm:
        raise SchemaError(f'/coordinate_projection/frame_origin_nm/{dimension}',
                          'cell grid origin is not exactly representable in canonical DBU')
    start = units.nm_to_canonical(origin_nm) + integer(spec['offset_dbu'])
    return EdgeAxis(start, integer(spec['pitch_dbu']), integer(spec['cells']))


def _bind_layer(row: FrozenMap, path: str, origin: tuple[int, int],
                units: UnitBinding, profile: FrozenMap) -> LayerProjection:
    kind = row['projection']
    if kind == 'none':
        return None
    if kind == '2d_cells':
        return CellGrid(_edge_axis(mapping(row['x_edges']), origin[0], 0, units),
                        _edge_axis(mapping(row['y_edges']), origin[1], 1, units))

    assert kind == '1d_track'  # checked_layer selects and closes the variant.
    axis = cast("Literal['x', 'y']", row['index_axis'])
    centre = mapping(row['first_centre'])
    width = nm_parameter(centre, 'width_nm', profile, path + '/first_centre')
    lower = nm_parameter(centre, 'lower_edge_nm', profile, path + '/first_centre')
    pitch = nm_parameter(row, 'pitch_nm', profile, path)
    first_index, last_index = map(integer, sequence(row['index_range_inclusive']))
    if first_index > last_index:
        raise SchemaError(path + '/index_range_inclusive', 'track index range must be ordered')
    return TrackAxis(axis, origin[0 if axis == 'x' else 1] + lower + width / 2,
                     pitch, width, first_index, last_index)


def bind_projection_model(geometry: GeometryResult) -> ProjectionModel:
    if type(geometry) is not GeometryResult or geometry.status != 'success' or geometry.value is None:
        raise ValueError('coordinate binding requires a successful captured GeometryResult')
    validate_closed_graph(geometry, _INPUT_TYPES)
    layout = geometry.value.layout
    tech = mapping(geometry.input.value['tech'])
    sources = next(record.sources for record in geometry.completed if record.kind == 'tech')
    projection = mapping(mapping(tech['coordinate'])['coordinate_projection'])
    x_nm, y_nm = map(integer, sequence(projection['frame_origin_nm']))
    origin = (x_nm, y_nm)
    declarations: dict[str, LayerProjection] = {}
    if projection['id'] == LAYER_DISCRETIZATION:
        try:
            if projection['units_ref'] != 'formats#/unit_scale_contract':
                raise SchemaError('/coordinate_projection/units_ref',
                                  'grid units must reference the selected formats unit_scale_contract')
            known_layers = {policy.name for policy in layout.policies}
            profile = mapping(mapping(tech['physical'])['fin_count_profile'])
            for name, value in mapping(projection['layers']).items():
                token = name.replace('~', '~0').replace('/', '~1')
                path = '/coordinate_projection/layers/' + token
                if name not in known_layers:
                    raise SchemaError(path, 'unknown layer in the selected drawn owner')
                row = checked_layer(value, path)
                declarations[name] = _bind_layer(row, path, origin, layout.units, profile)
        except SchemaError as exc:
            issue = EvidenceIssue('config', 'InvalidProjectionDeclaration', str(exc),
                                  replace(sources[5], field=exc.path))
            raise ProjectionConfigError(issue, geometry) from exc
    return ProjectionModel(origin, declarations, layout.units.ref, sources)
