"""Closed per-type grammar for the captured synthetic layer-discretization owner."""
from __future__ import annotations

from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap, Value, rational
from .schema import SchemaError, array, enum, integer, literal, obj, positive, text


def _exact_nm(value: Value, path: str) -> None:
    if type(value) is not int:
        try:
            rational(value)
        except ValueError as exc:
            raise SchemaError(path, 'expected integer nm or exact reduced rational') from exc


# Each reference denotes one quantity with known units and semantics. No file
# path or arbitrary numeric field is interpreted as a coordinate parameter.
_PROFILE_FIELDS = {
    'pitch_nm': 'fin_pitch_nm',
    'width_nm': 'fin_width_nm',
    'lower_edge_nm': 'fin_lower_edge_offset_nm',
}

_EDGES = obj({'pitch_dbu': positive, 'offset_dbu': integer, 'cells': positive})
_CENTRE = obj({'basis': literal('lower_edge_plus_half_width')}, {
    'lower_edge_nm': _exact_nm, 'lower_edge_nm_ref': text,
    'width_nm': _exact_nm, 'width_nm_ref': text,
})
_TRACK = obj({
    'projection': literal('1d_track'), 'index_axis': enum('x', 'y'), 'first_centre': _CENTRE,
    'index_range_inclusive': array(integer, length=2),
}, {'pitch_nm': _exact_nm, 'pitch_nm_ref': text})
_GRID = obj({'projection': literal('2d_cells'), 'x_edges': _EDGES, 'y_edges': _EDGES})
_SKIP = obj({'projection': literal('none')})
_GRAMMAR = {'1d_track': _TRACK, '2d_cells': _GRID, 'none': _SKIP}


def checked_layer(value: Value, path: str) -> FrozenMap:
    if not isinstance(value, FrozenMap):
        raise SchemaError(path, 'expected a layer declaration object')
    kind = value.get('projection')
    if not isinstance(kind, str) or kind not in _GRAMMAR:
        raise SchemaError(path + '/projection', 'expected explicit 1d_track, 2d_cells or none')
    _GRAMMAR[kind](value, path)
    return value


def nm_parameter(row: FrozenMap, field: str, profile: FrozenMap, path: str) -> Fraction:
    """Resolve one schema-checked parameter from this selected package."""
    reference = field + '_ref'
    if reference in row:
        if field in row:
            raise SchemaError(f'{path}/{reference}', f'{field} and its reference are mutually exclusive')
        target = _PROFILE_FIELDS[field]
        if row[reference] != 'physical#/fin_count_profile/' + target:
            raise SchemaError(f'{path}/{reference}', 'reference must name the selected physical ' + target)
        value = profile[target]
    elif field in row:
        value = row[field]
    else:
        raise SchemaError(f'{path}/{field}', f'requires {field} or {reference}')
    number = Fraction(value) if type(value) is int else rational(value)
    if field in ('pitch_nm', 'width_nm') and number <= 0:
        raise SchemaError(f'{path}/{reference if reference in row else field}', 'expected a positive length')
    return number
