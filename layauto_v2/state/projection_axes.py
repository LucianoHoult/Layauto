"""Finite declared axes for exact centre and half-open cell calculations."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from layauto_v2.domain.geometry import Rect, integer


def _exact(value: int | Fraction) -> Fraction:
    if type(value) not in (int, Fraction):
        raise ValueError('coordinate must be an exact integer or Fraction')
    return Fraction(value)


def _scale(canonical_tick_nm: int | Fraction) -> Fraction:
    scale = _exact(canonical_tick_nm)
    if scale <= 0:
        raise ValueError('canonical DBU scale must be positive')
    return scale


@dataclass(frozen=True, slots=True)
class EdgeAxis:
    """Regular cell boundaries in absolute DBU after frame and phase binding."""

    start_dbu: int
    pitch_dbu: int
    cells: int

    def __post_init__(self) -> None:
        integer(self.start_dbu)
        if integer(self.pitch_dbu) <= 0 or integer(self.cells) <= 0:
            raise ValueError('edge pitch and cell count must be positive integers')

    def edge(self, index: int) -> int:
        if not 0 <= integer(index) <= self.cells:
            raise IndexError('edge index is outside the declared axis')
        return self.start_dbu + index * self.pitch_dbu

    def index(self, point_dbu: int | Fraction) -> int:
        index = (_exact(point_dbu) - self.start_dbu) // self.pitch_dbu
        if not 0 <= index < self.cells:
            raise IndexError('point is outside the half-open cell domain')
        return index

    def span(self, low: int, high: int) -> tuple[int, int]:
        """Inclusive first and last cell indices hit by [low, high) in integer DBU."""
        if integer(low) >= integer(high):
            raise ValueError('cell projection requires a positive-length interval')
        if low < self.start_dbu or high > self.edge(self.cells):
            raise IndexError('interval extends outside the declared cell domain')
        return ((low - self.start_dbu) // self.pitch_dbu,
                (high - 1 - self.start_dbu) // self.pitch_dbu)


@dataclass(frozen=True, slots=True)
class CellGrid:
    x_edges: EdgeAxis
    y_edges: EdgeAxis

    def __post_init__(self) -> None:
        if type(self.x_edges) is not EdgeAxis or type(self.y_edges) is not EdgeAxis:
            raise ValueError('a cell grid requires two declared edge axes')

    def cell_bounds(self, i: int, j: int) -> Rect:
        return Rect(self.x_edges.edge(i), self.y_edges.edge(j),
                    self.x_edges.edge(i + 1), self.y_edges.edge(j + 1))

    def point(self, x_dbu: int | Fraction, y_dbu: int | Fraction) -> tuple[int, int]:
        return self.x_edges.index(x_dbu), self.y_edges.index(y_dbu)

    def spans(self, rect: Rect) -> tuple[int, int, int, int]:
        if type(rect) is not Rect:
            raise ValueError('cell projection requires an exact rectangle')
        x0, x1 = self.x_edges.span(rect.x0, rect.x1)
        y0, y1 = self.y_edges.span(rect.y0, rect.y1)
        return x0, x1, y0, y1

    def physical_to_index(self, x_nm: int | Fraction, y_nm: int | Fraction,
                          canonical_tick_nm: int | Fraction) -> tuple[int, int]:
        scale = _scale(canonical_tick_nm)
        return self.point(_exact(x_nm) / scale, _exact(y_nm) / scale)

    def index_to_physical(self, i: int, j: int, canonical_tick_nm: int | Fraction) -> tuple[Fraction, ...]:
        scale = _scale(canonical_tick_nm)
        return tuple(bound * scale for bound in self.cell_bounds(i, j).bounds)


@dataclass(frozen=True, slots=True)
class TrackLocation:
    status: Literal['on_track', 'off_track', 'outside_range', 'unsupported_strip']
    position_nm: Fraction
    # For each adjacent track, signed distance = query position minus its centre.
    neighbours: tuple[tuple[int, Fraction], ...] = ()


@dataclass(frozen=True, slots=True)
class TrackAxis:
    """An index runs along the strip normal; first_centre_nm belongs to first_index."""

    index_axis: Literal['x', 'y']
    first_centre_nm: Fraction
    pitch_nm: Fraction
    width_nm: Fraction
    first_index: int
    last_index: int

    def __post_init__(self) -> None:
        if type(self.index_axis) is not str or self.index_axis not in ('x', 'y'):
            raise ValueError('track index axis must be x or y')
        for name in ('first_centre_nm', 'pitch_nm', 'width_nm'):
            object.__setattr__(self, name, _exact(getattr(self, name)))
        if self.pitch_nm <= 0 or self.width_nm <= 0:
            raise ValueError('track pitch and strip width must be positive')
        if integer(self.first_index) > integer(self.last_index):
            raise ValueError('track indices require a nonempty inclusive range')

    def centre(self, index: int) -> Fraction:
        if not self.first_index <= integer(index) <= self.last_index:
            raise IndexError('track index is outside the declared range')
        return self.first_centre_nm + (index - self.first_index) * self.pitch_nm

    def locate(self, position_nm: int | Fraction) -> TrackLocation:
        position = _exact(position_nm)
        index = self.first_index + (position - self.first_centre_nm) / self.pitch_nm
        if not self.first_index <= index <= self.last_index:
            return TrackLocation('outside_range', position)
        if index.denominator == 1:
            return TrackLocation('on_track', position, ((index.numerator, Fraction(0)),))
        lower = index.numerator // index.denominator
        neighbours = tuple((i, position - self.centre(i)) for i in (lower, lower + 1))
        return TrackLocation('off_track', position, neighbours)

    def strip(self, rect: Rect, canonical_tick_nm: int | Fraction) -> TrackLocation:
        if type(rect) is not Rect:
            raise ValueError('strip projection requires an exact rectangle')
        scale = _scale(canonical_tick_nm)
        if self.index_axis == 'x':
            low, high, length = rect.x0, rect.x1, rect.y1 - rect.y0
        else:
            low, high, length = rect.y0, rect.y1, rect.x1 - rect.x0
        width = high - low
        centre = (low + high) * scale / 2
        if width * scale != self.width_nm or length <= width:
            return TrackLocation('unsupported_strip', centre)
        return self.locate(centre)
