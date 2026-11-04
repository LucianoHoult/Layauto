"""Closed canonical wire for effective drafts and their capture-bound result."""
from __future__ import annotations

import hashlib
from collections.abc import Callable

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain import publication_codec
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import GeometryRef, GeometryRecordId, Rect
from layauto_v2.domain.regions import ExactRegion, OperatorBinding, RecordRegions, RegionPiece, RegionRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.state.occupancy import BaseOccupancy
from layauto_v2.state.regions import EffectiveDraft
from . import geometry_codec
from .geometry import GeometryResult
from .effective import EffectiveGeometryResult

_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'RegionRef': (RegionRef, ('kind', 'sha256')),
    'RegionPiece': (RegionPiece, ('region_ref', 'rect', 'schema_version')),
    'ExactRegion': (ExactRegion, ('owner_id', 'role', 'contributors', 'unit_ref', 'operator_ref',
                                  'rectangles', 'schema_version')),
    'OperatorBinding': (OperatorBinding, ('physical', 'drawn', 'unit_ref', 'schema_version')),
    'RecordRegions': (RecordRegions, ('record_id', 'operation', 'contributors', 'unit_ref',
                                     'operator_ref', 'regions', 'schema_version')),
    'EffectiveDraft': (EffectiveDraft, ('base', 'operators', 'records', 'schema_version')),
    'EffectiveGeometryResult': (EffectiveGeometryResult, ('status', 'value', 'issues', 'completed',
                                                         'input', 'schema_version')),
}
_GEOMETRY = (GeometryRef, GeometryRecordId, Rect, BaseOccupancy, GeometryResult)
_CAPTURED = (EvidenceRecord, EvidenceIssue)


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__,
                          'fields': {field: _pack(getattr(value, field)) for field in spec[1]}})
    if type(value) in _GEOMETRY:
        return FrozenMap({'geometry_record': geometry_codec.encode_record(value)})
    if isinstance(value, _CAPTURED) and type(value) in _CAPTURED:
        return FrozenMap({'captured_record': publication_codec.encode_record(value)})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged effective geometry wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('expected immutable map payload')
        return value['map']
    if set(value) == {'tuple'}:
        items = value['tuple']
        if type(items) is not tuple:
            raise ValueError('expected effective wire tuple')
        return tuple(_unpack(item) for item in items)
    if set(value) == {'scalar'}:
        if isinstance(value['scalar'], (FrozenMap, tuple)):
            raise ValueError('scalar tag cannot contain collections')
        return value['scalar']
    if set(value) == {'geometry_record'}:
        raw = value['geometry_record']
        if type(raw) is not bytes:
            raise ValueError('geometry record requires canonical bytes')
        result = geometry_codec.decode_record(raw)
        if type(result) not in _GEOMETRY:
            raise ValueError('foreign nested geometry wire type')
        return result
    if set(value) == {'captured_record'}:
        raw = value['captured_record']
        if type(raw) is not bytes:
            raise ValueError('captured record requires canonical bytes')
        result = publication_codec.decode_record(raw)
        if type(result) not in _CAPTURED:
            raise ValueError('foreign nested captured wire type')
        return result
    if (set(value) != {'record', 'fields'} or type(value['record']) is not str
            or type(value['fields']) is not FrozenMap):
        raise ValueError('invalid effective geometry wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown effective geometry wire record')
    constructor, fields = spec
    payload = value['fields']
    if set(payload) != set(fields):
        raise ValueError('unknown/missing effective geometry wire fields')
    # Every constructor validates its field types before using them. Do not
    # translate TypeError/KeyError here: they can be unexpected algorithm errors
    # from aggregate reconstruction and must retain their exception identity.
    decoded = {field: _unpack(payload[field]) for field in fields}
    result = constructor(**decoded)
    if _pack(result) != value:
        raise ValueError('noncanonical effective geometry record')
    return result


def encode_record(record: object) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported effective geometry wire type')
    return canonical_bytes({'wire_schema': 'layauto-effective-geometry-wire/1', 'record': _pack(record)})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if (type(value) is not FrozenMap or set(value) != {'wire_schema', 'record'}
            or value['wire_schema'] != 'layauto-effective-geometry-wire/1'):
        raise ValueError('unsupported effective geometry wire schema')
    result = _unpack(value['record'])
    if encode_record(result) != data:
        raise ValueError('noncanonical effective geometry wire bytes')
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
