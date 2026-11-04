"""Closed canonical wire for capture-bound geometry and neutral draft values."""
from __future__ import annotations

import hashlib
from collections.abc import Callable

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain import publication_codec
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.geometry import (
    GeometryRef, GeometryRecordId, OccupantFragmentId, Rect, StreamLayerKey,
    UnitBinding, LayerPolicy, DrawnRecord,
)
from layauto_v2.state.layout_store import LayoutDraft
from layauto_v2.state.coordinate import LayerPartition, BasePartition
from layauto_v2.state.occupancy import BaseCellId, OccupantFragment, BaseOccupancy
from . import codec as semantic_codec
from .contracts import NormalizationInput
from .geometry_input import GeometryInput
from .geometry import GeometryResult

_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'GeometryRef': (GeometryRef, ('kind', 'sha256')),
    'GeometryRecordId': (GeometryRecordId, ('sha256',)),
    'OccupantFragmentId': (OccupantFragmentId, ('sha256',)),
    'Rect': (Rect, ('x0', 'y0', 'x1', 'y1')),
    'StreamLayerKey': (StreamLayerKey, ('element', 'layer', 'datatype')),
    'UnitBinding': (UnitBinding, ('contract', 'encoded', 'source', 'schema_version')),
    'LayerPolicy': (LayerPolicy, ('declaration', 'source', 'schema_version')),
    'DrawnRecord': (DrawnRecord, ('id', 'top', 'stream_key', 'layer', 'purpose', 'source', 'raw_xy', 'rect',
                                  'unit_ref', 'policy_ref', 'preservation', 'schema_version')),
    'LayoutDraft': (LayoutDraft, ('gds', 'drawn', 'formats', 'units', 'policies', 'records', 'schema_version')),
    'LayerPartition': (LayerPartition, ('layer', 'xs', 'ys', 'schema_version')),
    'BasePartition': (BasePartition, ('layout', 'layers', 'algorithm', 'boundary', 'schema_version')),
    'BaseCellId': (BaseCellId, ('partition_ref', 'layer', 'x', 'y')),
    'OccupantFragment': (OccupantFragment, ('id', 'record_id', 'cell', 'rect', 'unit_ref', 'schema_version')),
    'BaseOccupancy': (BaseOccupancy, ('partition', 'fragments', 'schema_version')),
    'GeometryInput': (GeometryInput, ('semantic_input', 'schema_version')),
    'GeometryResult': (GeometryResult, ('status', 'value', 'issues', 'completed', 'input', 'schema_version')),
}
_EXTERNAL = (SourceRef, EvidenceRecord, EvidenceIssue)


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__, 'fields': {field: _pack(getattr(value, field)) for field in spec[1]}})
    if type(value) is NormalizationInput:
        return FrozenMap({'semantic_input': semantic_codec.encode_record(value)})
    if isinstance(value, _EXTERNAL) and type(value) in _EXTERNAL:
        return FrozenMap({'captured_record': publication_codec.encode_record(value)})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged geometry wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('expected immutable payload map')
        return value['map']
    if set(value) == {'tuple'}:
        items = value['tuple']
        if type(items) is not tuple:
            raise ValueError('expected wire tuple')
        return tuple(_unpack(item) for item in items)
    if set(value) == {'scalar'}:
        if isinstance(value['scalar'], (FrozenMap, tuple)):
            raise ValueError('scalar tag cannot contain a collection')
        return value['scalar']
    if set(value) == {'semantic_input'}:
        raw = value['semantic_input']
        if type(raw) is not bytes:
            raise ValueError('semantic receipt requires canonical bytes')
        record = semantic_codec.decode_record(raw)
        if type(record) is not NormalizationInput:
            raise ValueError('geometry wire contains a non-input semantic record')
        return record
    if set(value) == {'captured_record'}:
        raw = value['captured_record']
        if type(raw) is not bytes:
            raise ValueError('captured record requires canonical bytes')
        record = publication_codec.decode_record(raw)
        if type(record) not in _EXTERNAL:
            raise ValueError('foreign captured geometry wire type')
        return record
    if set(value) != {'record', 'fields'} or type(value['record']) is not str or type(value['fields']) is not FrozenMap:
        raise ValueError('invalid geometry wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown geometry wire record')
    constructor, fields = spec
    payload = value['fields']
    if set(payload) != set(fields):
        raise ValueError('unknown/missing geometry wire fields')
    # Constructors reject malformed fields explicitly. Algorithm/capture
    # reconstruction failures must keep their identity through the whole chain.
    decoded = {field: _unpack(payload[field]) for field in fields}
    result = constructor(**decoded)
    if _pack(result) != value:
        raise ValueError('noncanonical geometry wire record')
    return result


def encode_record(record: object) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported geometry wire type')
    return canonical_bytes({'wire_schema': 'layauto-geometry-wire/1', 'record': _pack(record)})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if type(value) is not FrozenMap or set(value) != {'wire_schema', 'record'} or value['wire_schema'] != 'layauto-geometry-wire/1':
        raise ValueError('unsupported geometry wire schema')
    result = _unpack(value['record'])
    if encode_record(result) != data:
        raise ValueError('noncanonical geometry wire bytes')
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
