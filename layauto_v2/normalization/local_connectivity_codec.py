"""Closed, canonical wire for neutral local graphs and captured results."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain import publication_codec
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef
from layauto_v2.domain.local_connectivity import (
    LocalRef, LocalContactBinding, ContactNode, ContactEdge, EnclosureSide,
    ContactComponent, LOCAL_TYPES,
)
from layauto_v2.domain.regions import ExactRegion, RegionRef, validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.publication import WireRecord
from layauto_v2.state.local_connectivity import DRAFT_TYPES, LocalConnectivityDraft
from layauto_v2.state.regions import EffectiveDraft
from . import effective_codec, geometry_codec
from . import codec as semantic_codec
from .effective import EffectiveGeometryResult
from .local_connectivity import LocalConnectivityResult

_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'LocalRef': (LocalRef, ('kind', 'sha256')),
    'LocalContactBinding': (LocalContactBinding, ('physical', 'drawn', 'rules', 'effective_ref',
                                               'unit_ref', 'top', 'scope', 'schema_version')),
    'ContactNode': (ContactNode, ('layer', 'region', 'binding_ref', 'schema_version')),
    'ContactEdge': (ContactEdge, ('kind', 'endpoints', 'binding_ref', 'connector_id', 'schema_version')),
    'EnclosureSide': (EnclosureSide, ('connector_id', 'node_ref', 'layer', 'margin_ticks',
                                     'status', 'binding_ref', 'schema_version')),
    'ContactComponent': (ContactComponent, ('members', 'binding_ref', 'schema_version')),
    'LocalConnectivityDraft': (LocalConnectivityDraft, ('effective', 'binding', 'nodes', 'edges',
                                                        'audits', 'components', 'schema_version')),
    'LocalConnectivityResult': (LocalConnectivityResult, ('status', 'value', 'issues', 'completed',
                                                         'input', 'schema_version')),
}
_EFFECTIVE = (ExactRegion, RegionRef, EffectiveDraft, EffectiveGeometryResult)
_GEOMETRY = (GeometryRecordId, GeometryRef)
_CAPTURED = (EvidenceRecord, EvidenceIssue)
_ALL_TYPES = DRAFT_TYPES + LOCAL_TYPES + (LocalConnectivityResult,) + tuple(
    cast(type[object], spec[0]) for registry in
    (effective_codec._SPEC, geometry_codec._SPEC, semantic_codec._SPEC, publication_codec._SPEC)
    for spec in registry.values())


def _captured_bytes(value: object) -> bytes:
    return publication_codec.encode_record(cast(WireRecord, value))


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__,
                          'fields': {field: _pack(getattr(value, field)) for field in spec[1]}})
    for classes, tag, encoder in (
        (_EFFECTIVE, 'effective_record', effective_codec.encode_record),
        (_GEOMETRY, 'geometry_record', geometry_codec.encode_record),
        (_CAPTURED, 'captured_record', _captured_bytes),
    ):
        if any(type(value) is cls for cls in classes):
            return FrozenMap({tag: encoder(value)})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged local connectivity wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('expected immutable local map payload')
        return value['map']
    if set(value) == {'tuple'}:
        items = value['tuple']
        if type(items) is not tuple:
            raise ValueError('expected local wire tuple')
        return tuple(_unpack(item) for item in items)
    if set(value) == {'scalar'}:
        if type(value['scalar']) is FrozenMap or type(value['scalar']) is tuple:
            raise ValueError('scalar wire tag cannot contain collections')
        return value['scalar']
    for tag, classes, decoder in (
        ('effective_record', _EFFECTIVE, effective_codec.decode_record),
        ('geometry_record', _GEOMETRY, geometry_codec.decode_record),
        ('captured_record', _CAPTURED, publication_codec.decode_record),
    ):
        if set(value) == {tag}:
            raw = value[tag]
            if type(raw) is not bytes:
                raise ValueError('nested local wire record requires canonical bytes')
            result = decoder(raw)
            if not any(type(result) is cls for cls in classes):
                raise ValueError('foreign nested local wire type')
            return result
    if (set(value) != {'record', 'fields'} or type(value['record']) is not str
            or type(value['fields']) is not FrozenMap):
        raise ValueError('invalid local connectivity wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown local connectivity wire record')
    constructor, fields = spec
    payload = value['fields']
    if set(payload) != set(fields):
        raise ValueError('unknown/missing local connectivity wire fields')
    result = constructor(**{field: _unpack(payload[field]) for field in fields})
    if _pack(result) != value:
        raise ValueError('noncanonical local connectivity record')
    return result


def encode_record(record: object) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported local connectivity wire type')
    validate_closed_graph(record, _ALL_TYPES)
    return canonical_bytes({'wire_schema': 'layauto-local-connectivity-wire/1', 'record': _pack(record)})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if (type(value) is not FrozenMap or set(value) != {'wire_schema', 'record'}
            or value['wire_schema'] != 'layauto-local-connectivity-wire/1'):
        raise ValueError('unsupported local connectivity wire schema')
    result = _unpack(value['record'])
    if encode_record(result) != data:
        raise ValueError('noncanonical local connectivity wire bytes')
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
