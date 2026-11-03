"""Finite exact mathematical partition for drawn base indexing only.

No manufacturing grid, legal routing lattice, coordinate_ref or occupancy is
owned here. Bounds are canonical integer DBU and cells are half-open. The
closure of tiled rectangles retains the source polygon's boundary.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.geometry import VERSION, GeometryRef, Rect, integer, text, version
from .layout_store import LayoutDraft

ALGORITHM = 'drawn-layer-edges/1'
BOUNDARY = 'half_open_min_included_max_excluded'


@dataclass(frozen=True)
class LayerPartition:
    layer: str
    xs: tuple[int, ...]
    ys: tuple[int, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        text(self.layer)
        for name in ('xs', 'ys'):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)):
                raise ValueError('partition axes require a sequence')
            coordinates = tuple(integer(v) for v in values)
            if len(coordinates) == 1 or coordinates != tuple(sorted(set(coordinates))):
                raise ValueError('partition axes must be empty or strictly increasing')
            object.__setattr__(self, name, coordinates)
        if bool(self.xs) != bool(self.ys):
            raise ValueError('both partition axes must be empty or finite')

    def cell_bounds(self, x: int, y: int) -> Rect:
        if not 0 <= integer(x) < len(self.xs) - 1 or not 0 <= integer(y) < len(self.ys) - 1:
            raise ValueError('cell index is outside finite partition')
        return Rect(self.xs[x], self.ys[y], self.xs[x + 1], self.ys[y + 1])

    def point_to_index(self, x: int | Fraction, y: int | Fraction) -> tuple[int, int]:
        if type(x) not in (int, Fraction) or type(y) not in (int, Fraction):
            raise ValueError('point must use exact coordinates')
        i, j = bisect_right(self.xs, x) - 1, bisect_right(self.ys, y) - 1
        self.cell_bounds(i, j)
        return i, j

    def project(self, rect: Rect) -> tuple[tuple[int, int, Rect], ...]:
        """Exact positive-area intersections; usable with explicit test axes too."""
        if type(rect) is not Rect or not self.xs or not self.ys:
            raise ValueError('projection requires a rectangle and nonempty axes')
        if rect.x0 < self.xs[0] or rect.x1 > self.xs[-1] or rect.y0 < self.ys[0] or rect.y1 > self.ys[-1]:
            raise ValueError('rectangle is outside finite partition')
        x_start, y_start = bisect_right(self.xs, rect.x0) - 1, bisect_right(self.ys, rect.y0) - 1
        x_end, y_end = bisect_left(self.xs, rect.x1), bisect_left(self.ys, rect.y1)
        result: list[tuple[int, int, Rect]] = []
        for i in range(x_start, x_end):
            for j in range(y_start, y_end):
                fragment = rect.intersection(self.cell_bounds(i, j))
                if fragment is not None:
                    result.append((i, j, fragment))
        return tuple(result)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'layer': self.layer, 'xs': self.xs, 'ys': self.ys})


def _layers(layout: LayoutDraft) -> tuple[LayerPartition, ...]:
    if type(layout) is not LayoutDraft:
        raise ValueError('partition requires an immutable layout draft')
    layers: list[LayerPartition] = []
    for policy in layout.policies:
        if not policy.projected:
            continue
        records = tuple(r for r in layout.records if r.layer == policy.name)
        xs = tuple(sorted({c for r in records for c in (r.rect.x0, r.rect.x1)}))
        ys = tuple(sorted({c for r in records for c in (r.rect.y0, r.rect.y1)}))
        layers.append(LayerPartition(policy.name, xs, ys))
    return tuple(layers)


@dataclass(frozen=True)
class BasePartition:
    layout: LayoutDraft
    layers: tuple[LayerPartition, ...]
    algorithm: str = ALGORITHM
    boundary: str = BOUNDARY
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        if self.algorithm != ALGORITHM or self.boundary != BOUNDARY:
            raise ValueError('unsupported base partition algorithm/boundary convention')
        if not isinstance(self.layers, (tuple, list)) or any(type(v) is not LayerPartition for v in self.layers):
            raise ValueError('partition layers must be exact layer partitions')
        object.__setattr__(self, 'layers', tuple(self.layers))
        if self.layers != _layers(self.layout):
            raise ValueError('partition is not reconstructable from its bound drawn geometry/policy')

    @property
    def layout_ref(self) -> GeometryRef:
        return self.layout.ref

    @property
    def ref(self) -> GeometryRef:
        return GeometryRef('base_partition', digest(self.to_value()))

    def layer(self, name: str) -> LayerPartition:
        for layer in self.layers:
            if layer.layer == name:
                return layer
        raise KeyError(name)

    def physical_to_index(self, layer: str, x_nm: int | Fraction, y_nm: int | Fraction) -> tuple[int, int]:
        if type(x_nm) not in (int, Fraction) or type(y_nm) not in (int, Fraction):
            raise ValueError('physical point must be exact')
        scale = self.layout.units.canonical_tick_nm
        return self.layer(layer).point_to_index(Fraction(x_nm) / scale, Fraction(y_nm) / scale)

    def index_to_physical(self, layer: str, x: int, y: int) -> tuple[Fraction, ...]:
        return tuple(self.layout.units.canonical_to_nm(c) for c in self.layer(layer).cell_bounds(x, y).bounds)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'algorithm': self.algorithm, 'boundary': self.boundary,
                          'layout_ref': self.layout_ref.to_value(), 'layers': tuple(v.to_value() for v in self.layers)})


def build_partition(layout: LayoutDraft) -> BasePartition:
    return BasePartition(layout, _layers(layout))
