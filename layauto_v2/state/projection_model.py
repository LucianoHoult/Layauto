"""A finite coordinate model bound to selected technology and geometry units."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeAlias

from layauto_v2.domain.codec import digest
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRef, source_value
from .projection_axes import CellGrid, EdgeAxis, TrackAxis

LayerProjection: TypeAlias = TrackAxis | CellGrid | None


def _edge_identity(axis: EdgeAxis) -> tuple[str, str, str]:
    return hex(axis.start_dbu), hex(axis.pitch_dbu), hex(axis.cells)


def _axes_identity(axes: LayerProjection) -> tuple[object, ...]:
    # Exact arithmetic can produce more decimal digits than either bounded
    # input. Hex is canonical for Python integers of any supported magnitude.
    if axes is None:
        return ('none',)
    if isinstance(axes, CellGrid):
        return ('2d_cells', _edge_identity(axes.x_edges), _edge_identity(axes.y_edges))
    lengths = tuple((hex(n.numerator), hex(n.denominator))
                    for n in (axes.first_centre_nm, axes.pitch_nm, axes.width_nm))
    return ('1d_track', axes.index_axis, lengths, hex(axes.first_index), hex(axes.last_index))


@dataclass(frozen=True)
class ProjectionModel:
    frame_origin_nm: tuple[int, int]
    layers: Mapping[str, LayerProjection]
    unit_ref: GeometryRef
    tech_sources: tuple[SourceRef, ...]
    model_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (type(self.frame_origin_nm) is not tuple or len(self.frame_origin_nm) != 2
                or any(type(n) is not int for n in self.frame_origin_nm)):
            raise ValueError('model origin must be two exact integer nm coordinates')
        if type(self.unit_ref) is not GeometryRef or self.unit_ref.kind != 'unit':
            raise ValueError('model requires a bound unit reference')
        if type(self.tech_sources) is not tuple or len(self.tech_sources) != 7:
            raise ValueError('model requires the bundle and its six captured owners')
        layers = dict(self.layers)
        for name, declaration in layers.items():
            if type(name) is not str or not name:
                raise ValueError('model requires named layers')
            if declaration is not None and type(declaration) not in (CellGrid, TrackAxis):
                raise ValueError('model requires validated layer axes or an explicit skip')
        object.__setattr__(self, 'layers', MappingProxyType(layers))
        # Both the actual captured bytes and their resolved parameter values
        # participate. A neutral model with different axes has a different ID.
        identity = digest({
            'schema': 'layauto-bound-layer-projections/1', 'origin_nm': tuple(hex(n) for n in self.frame_origin_nm),
            'sources': tuple(source_value(source) for source in self.tech_sources),
            'unit_ref': self.unit_ref.to_value(),
            'layers': {name: _axes_identity(axes) for name, axes in layers.items()},
        })
        object.__setattr__(self, 'model_id', identity)

    @property
    def coordinate_source(self) -> SourceRef:
        return self.tech_sources[5]
