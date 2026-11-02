"""Lossless reader for the declared flat GDSII BOUNDARY rectangle subset.

The stream state machine and REAL8 decoder are new code. No third-party float
geometry reader or fixture helper participates in runtime interpretation.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from fractions import Fraction

from layauto_v2.domain.codec import FrozenMap, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import Category, InputError
from ._access import exact, integer, mapping, sequence, string


@dataclass(frozen=True)
class _Record:
    kind: int
    dtype: int
    payload: bytes
    offset: int
    index: int


_NAMES = {0: 'HEADER', 1: 'BGNLIB', 2: 'LIBNAME', 3: 'UNITS', 4: 'ENDLIB',
          5: 'BGNSTR', 6: 'STRNAME', 7: 'ENDSTR', 8: 'BOUNDARY', 9: 'PATH',
          10: 'SREF', 11: 'AREF', 12: 'TEXT', 13: 'LAYER', 14: 'DATATYPE',
          16: 'XY', 17: 'ENDEL', 21: 'NODE', 26: 'STRANS', 27: 'MAG',
          28: 'ANGLE', 43: 'PROPATTR', 44: 'PROPVALUE', 45: 'BOX'}
_SUPPORTED = {0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 16, 17}


def _error(source: SourceFile, record: _Record, code: str, message: str,
           category: Category = 'parse') -> InputError:
    return InputError(category, code, message, source.ref(byte_offset=record.offset,
                                                        record_index=record.index))


def _records(source: SourceFile, limit: int) -> tuple[_Record, ...]:
    records: list[_Record] = []
    offset = 0
    while offset < len(source.data):
        ref = source.ref(byte_offset=offset, record_index=len(records))
        if len(records) >= limit:
            raise InputError('parse', 'RecordLimitExceeded', 'GDS stream record limit exceeded', ref)
        if len(source.data) - offset < 4:
            raise InputError('parse', 'TruncatedGdsRecord', 'incomplete record header', ref)
        size, kind, dtype = struct.unpack('>HBB', source.data[offset:offset + 4])
        if size < 4 or size % 2:
            raise InputError('parse', 'InvalidGdsRecordLength', 'record length must be even and at least four', ref)
        if offset + size > len(source.data):
            raise InputError('parse', 'TruncatedGdsRecord', 'record payload exceeds source bytes', ref)
        record = _Record(kind, dtype, source.data[offset + 4:offset + size], offset, len(records))
        if kind not in _SUPPORTED:
            name = _NAMES.get(kind, f'0x{kind:02x}')
            raise _error(source, record, f'UnsupportedGdsElement:{name}',
                         f'{name} is outside flat_boundary_rectangles/1', 'unsupported')
        records.append(record)
        offset += size
    return tuple(records)


def decode_real8(raw: bytes) -> Fraction:
    """Decode GDSII REAL8 directly from sign/exponent/mantissa bits."""
    if len(raw) != 8:
        raise ValueError('REAL8 must contain eight bytes')
    mantissa = int.from_bytes(raw[1:], 'big')
    if mantissa == 0:
        if raw != bytes(8):
            raise ValueError('noncanonical REAL8 zero')
        return Fraction(0)
    if raw[1] >> 4 == 0:
        raise ValueError('unnormalized REAL8 mantissa')
    exponent = (raw[0] & 0x7f) - 64
    power = Fraction(16 ** exponent) if exponent >= 0 else Fraction(1, 16 ** -exponent)
    return (-1 if raw[0] & 0x80 else 1) * Fraction(mantissa, 1 << 56) * power


def _bind_real8(source: SourceFile, record: _Record, raw: bytes,
                nominal: Fraction, field: str) -> FrozenMap:
    try:
        decoded = decode_real8(raw)
    except ValueError as exc:
        raise _error(source, record, 'InvalidGdsReal8', str(exc)) from exc
    exponent = (raw[0] & 0x7f) - 64
    power = Fraction(16 ** exponent) if exponent >= 0 else Fraction(1, 16 ** -exponent)
    ulp = power / (1 << 56)
    scaled = nominal / ulp
    floor = scaled.numerator // scaled.denominator
    remainder = scaled - floor
    nearest = floor + int(remainder > Fraction(1, 2) or
                          (remainder == Fraction(1, 2) and floor % 2 == 1))
    mantissa = int.from_bytes(raw[1:], 'big')
    if (nominal <= 0 or decoded <= 0 or not Fraction(1, 16) <= nominal / power < 1
            or abs(decoded - nominal) > ulp / 2 or mantissa != nearest):
        raise _error(source, record, 'UnitScaleMismatch',
                     f'{field} does not bind to nominal scale under nearest56 contract', 'binding')
    return freeze_map({'raw': raw, 'exact': decoded, 'nominal': nominal,
                       'encoding_delta': decoded - nominal, 'ulp': ulp,
                       'byte_offset': record.offset + 4 + (8 if field == 'metres_per_tick' else 0),
                       'record_index': record.index})


def _ascii_name(source: SourceFile, record: _Record) -> str:
    raw = record.payload
    if raw.endswith(b'\x00'):
        raw = raw[:-1]
    if not raw or b'\x00' in raw or any(v < 33 or v > 126 for v in raw):
        raise _error(source, record, 'InvalidGdsName', 'name must be nonempty printable ASCII with only final NUL padding')
    return raw.decode('ascii')


def _rectangle(source: SourceFile, record: _Record) -> tuple[tuple[tuple[int, int], ...], tuple[int, int, int, int]]:
    if len(record.payload) != 40:
        raise _error(source, record, 'UnsupportedNonrectangle', 'BOUNDARY requires five XY pairs including closure', 'unsupported')
    coords = struct.unpack('>10i', record.payload)
    xy = tuple((coords[i], coords[i + 1]) for i in range(0, 10, 2))
    corners = xy[:-1]
    xs, ys = {x for x, _ in corners}, {y for _, y in corners}
    edges = tuple((xy[i + 1][0] - xy[i][0], xy[i + 1][1] - xy[i][1]) for i in range(4))
    if (xy[0] != xy[-1] or len(set(corners)) != 4 or len(xs) != 2 or len(ys) != 2
            or any((dx == 0) == (dy == 0) for dx, dy in edges)
            or any((edges[i][0] == 0) == (edges[(i + 1) % 4][0] == 0) for i in range(4))):
        raise _error(source, record, 'UnsupportedNonrectangle', 'polygon is not a closed axis-aligned rectangle', 'unsupported')
    return xy, (min(xs), min(ys), max(xs), max(ys))


def parse_gds(source: SourceFile, tech: FrozenMap) -> FrozenMap:
    """Parse every record, retaining original ticks and exact unit binding."""
    formats = mapping(tech['formats'])
    capability = mapping(formats['geometry_capability'])
    unit_contract = mapping(formats['unit_scale_contract'])
    if capability['id'] != 'flat_boundary_rectangles/1' or unit_contract['id'] != 'toy_gds_real8_nm/1':
        raise InputError('unsupported', 'UnsupportedGdsProfile', 'unimplemented GDS/unit profile', source.ref())
    records = _records(source, integer(mapping(formats['limits'])['max_records']))
    layer_map: dict[tuple[int, int], str] = {}
    for item in sequence(mapping(tech['drawn'])['layers']):
        layer = mapping(item)
        declared_key = mapping(layer['stream_key'])
        if declared_key['element'] == 'BOUNDARY':
            stream_key = (integer(declared_key['layer']), integer(declared_key['datatype']))
            if stream_key in layer_map:
                raise InputError('config', 'DuplicateStreamKey', 'duplicate BOUNDARY stream key', source.ref())
            layer_map[stream_key] = string(layer['name'])
    cursor = 0

    def take(kind: int, dtype: int, size: int | None = None) -> _Record:
        nonlocal cursor
        if cursor >= len(records):
            raise InputError('parse', 'TruncatedGdsStructure', f'missing {_NAMES[kind]}',
                             source.ref(byte_offset=len(source.data), record_index=cursor))
        rec = records[cursor]
        if rec.kind != kind:
            raise _error(source, rec, 'InvalidGdsStructure', f'expected {_NAMES[kind]}, got {_NAMES[rec.kind]}')
        if rec.dtype != dtype or (size is not None and len(rec.payload) != size):
            raise _error(source, rec, 'InvalidGdsRecordType', f'invalid {_NAMES[kind]} data type or payload size')
        cursor += 1
        return rec

    version = take(0, 2, 2)
    if struct.unpack('>h', version.payload)[0] != integer(capability['version']):
        raise _error(source, version, 'UnsupportedGdsVersion', 'stream version differs from profile', 'unsupported')
    lib_dates = take(1, 2, 24)
    library = _ascii_name(source, take(2, 6))
    units_record = take(3, 5, 16)
    first = exact(unit_contract['gds_units_first_nominal'])
    second = exact(unit_contract['nominal_tick_m'])
    if first <= 0 or second / first != exact(unit_contract['nominal_user_unit_m']):
        raise _error(source, units_record, 'UnitScaleMismatch', 'inconsistent nominal user/tick ratio', 'binding')
    units = {'contract': unit_contract['id'],
             'user_units_per_tick': _bind_real8(source, units_record, units_record.payload[:8], first, 'user_units_per_tick'),
             'metres_per_tick': _bind_real8(source, units_record, units_record.payload[8:], second, 'metres_per_tick')}
    cell_dates = take(5, 2, 24)
    top = _ascii_name(source, take(6, 6))
    elements: list[dict[str, object]] = []
    while cursor < len(records) and records[cursor].kind == 8:
        boundary = take(8, 0, 0)
        layer_rec, datatype_rec = take(13, 2, 2), take(14, 2, 2)
        layer_num, datatype = struct.unpack('>h', layer_rec.payload)[0], struct.unpack('>h', datatype_rec.payload)[0]
        key = (layer_num, datatype)
        if key not in layer_map:
            raise _error(source, layer_rec, 'UnknownStreamKey', f'undeclared BOUNDARY layer/datatype {key}', 'unsupported')
        xy_rec = take(16, 3)
        xy, bbox = _rectangle(source, xy_rec)
        end = take(17, 0, 0)
        elements.append({'element': 'BOUNDARY', 'layer': layer_num, 'datatype': datatype,
                         'canonical_layer': layer_map[key], 'xy': xy, 'bbox': bbox,
                         'byte_offset': boundary.offset, 'record_index': boundary.index,
                         'xy_byte_offset': xy_rec.offset + 4, 'xy_record_index': xy_rec.index,
                         'byte_length': end.offset + 4 - boundary.offset})
    take(7, 0, 0)
    if cursor < len(records) and records[cursor].kind == 5:
        raise _error(source, records[cursor], 'UnsupportedGdsHierarchy', 'additional cells are outside flat single-cell profile', 'unsupported')
    take(4, 0, 0)
    if cursor != len(records):
        raise _error(source, records[cursor], 'TrailingGdsRecords', 'records follow ENDLIB')
    return freeze_map({'schema_version': 'layauto-gds-evidence/1', 'top': top,
                       'library': library, 'library_timestamps': lib_dates.payload,
                       'cell_timestamps': cell_dates.payload, 'elements': elements,
                       'units': units, 'stream_record_count': len(records),
                       'source': {'uri': source.uri, 'sha256': source.sha256},
                       'raw_document': source.data})
