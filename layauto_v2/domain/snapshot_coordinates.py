"""Coordinate fields of the W023 snapshot wire, using W018's signed hex values."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

from .codec import FrozenMap, Value
from .geometry import integer, mapping, sequence, text


def _encode_integer(value: Value) -> str:
    return hex(integer(value))


def _encode_fraction(value: Value) -> tuple[str, str]:
    if not isinstance(value, Fraction):
        raise ValueError('expected a fractional track length')
    return hex(value.numerator), hex(value.denominator)


def _decode_integer(value: Value) -> int:
    spelling = text(value)
    result = int(spelling, 16)
    if hex(result) != spelling:
        raise ValueError('noncanonical hexadecimal coordinate')
    return result


def _decode_fraction(value: Value) -> Fraction:
    parts = sequence(value)
    if len(parts) != 2:
        raise ValueError('expected two hexadecimal fraction components')
    n, d = (_decode_integer(part) for part in parts)
    if d <= 0:
        raise ValueError('coordinate denominator must be positive')
    result = Fraction(n, d)
    if result.denominator != d:
        raise ValueError('coordinate fraction must be reduced')
    return result


_Converter = Callable[[Value], Value]
_LENGTHS = ('first_centre_nm', 'pitch_nm', 'width_nm')
_INDICES = ('first_index', 'last_index')


def _axis(value: Value, convert_int: _Converter, convert_fraction: _Converter) -> Value:
    if value is None:
        return None
    axis = mapping(value)
    if set(axis) == {'x_edges', 'y_edges'}:
        edges = {}
        for name, edge in axis.items():
            fields = mapping(edge)
            if set(fields) != {'start_dbu', 'pitch_dbu', 'cells'}:
                raise ValueError('invalid snapshot grid edge fields')
            edges[name] = {key: convert_int(number) for key, number in fields.items()}
        return FrozenMap(edges)
    if set(axis) != {'index_axis', *_LENGTHS, *_INDICES}:
        raise ValueError('invalid snapshot track fields')
    return FrozenMap({'index_axis': axis['index_axis'],
                      **{key: convert_fraction(axis[key]) for key in _LENGTHS},
                      **{key: convert_int(axis[key]) for key in _INDICES}})


def _coordinates(state: FrozenMap, convert_int: _Converter, convert_fraction: _Converter) -> FrozenMap:
    coords = mapping(state.get('coordinates'))
    origin = sequence(coords.get('origin_nm'))
    if len(origin) != 2:
        raise ValueError('expected two snapshot origin coordinates')
    axes = mapping(coords.get('axes'))
    return FrozenMap({**state, 'coordinates': {
        **coords, 'origin_nm': tuple(convert_int(n) for n in origin),
        'axes': {name: _axis(axis, convert_int, convert_fraction) for name, axis in axes.items()},
    }})


def coordinates_to_wire(state: FrozenMap) -> FrozenMap:
    return _coordinates(state, _encode_integer, _encode_fraction)


def coordinates_from_wire(state: object) -> FrozenMap:
    return _coordinates(mapping(state), _decode_integer, _decode_fraction)
