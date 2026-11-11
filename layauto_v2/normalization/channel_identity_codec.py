"""Closed canonical wire for channel identity observations and captured results."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain import publication_codec
from layauto_v2.domain.channel_identity import (
    CHANNEL_TYPES, ChannelRef, RationalRect, ChannelSeed, SeedIntersection,
    SeedLocation, ChannelAssociation, ChannelTopology, FinEvaluation, FinRelation,
    ChannelMeasurement, ParameterComparison,
)
from layauto_v2.domain.circuit import SemanticCircuitDraft, Parameter
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.identifiers import DeviceId, QueryKey
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.publication import WireRecord
from layauto_v2.domain.regions import RegionRef, validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.derive.channel_identity import DRAFT_TYPES, ChannelIdentityDraft
from layauto_v2.state.local_connectivity import LocalConnectivityDraft
from . import codec as semantic_codec
from . import effective_codec, geometry_codec, local_connectivity_codec
from .contracts import NormalizationResult
from .local_connectivity import LocalConnectivityResult
from .channel_identity import ChannelIdentityResult

_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'ChannelRef': (ChannelRef, ('kind', 'sha256')),
    'RationalRect': (RationalRect, ('x0', 'y0', 'x1', 'y1')),
    'ChannelSeed': (ChannelSeed, ('device_id', 'query_key', 'record', 'identity_provenance', 'schema_version')),
    'SeedIntersection': (SeedIntersection, ('seed_ref', 'channel_ref', 'intersection', 'coverage_fraction',
                                          'binding_ref', 'schema_version')),
    'SeedLocation': (SeedLocation, ('seed_ref', 'intersections', 'binding_ref', 'schema_version')),
    'ChannelAssociation': (ChannelAssociation, ('device_id', 'channel_ref', 'seed_refs', 'coverage',
                                               'coverage_fraction', 'binding_ref', 'schema_version')),
    'ChannelTopology': (ChannelTopology, ('channel_ref', 'gate_nodes', 'gate_components', 'source_node',
                                         'source_component', 'drain_node', 'drain_component',
                                         'binding_ref', 'schema_version')),
    'FinEvaluation': (FinEvaluation, ('fin_id', 'channel_ref', 'status', 'crossing', 'width_nm', 'source',
                                     'binding_ref', 'schema_version')),
    'FinRelation': (FinRelation, ('left_id', 'right_id', 'relation', 'intersection', 'channel_refs',
                                 'binding_ref', 'schema_version')),
    'ChannelMeasurement': (ChannelMeasurement, ('channel_ref', 'active_id', 'length_nm', 'evaluations',
                                               'count', 'unresolved_relations', 'binding_ref', 'schema_version')),
    'ParameterComparison': (ParameterComparison, ('device_id', 'channel_ref', 'axis', 'measured', 'declared',
                                                 'fin_id', 'binding_ref', 'schema_version')),
    'ChannelIdentityDraft': (ChannelIdentityDraft, ('local', 'source', 'seeds', 'derived', 'locations',
                                                   'associations', 'topology', 'measurements', 'fin_relations',
                                                   'comparisons', 'issues', 'schema_version')),
    'ChannelIdentityResult': (ChannelIdentityResult, ('status', 'value', 'issues', 'completed', 'input',
                                                     'semantic', 'schema_version')),
}
_LOCAL = (LocalConnectivityDraft, LocalConnectivityResult, LocalRef)
_GEOMETRY = (GeometryRecordId, GeometryRef, Rect)
_EFFECTIVE = (RegionRef,)
_SEMANTIC = (SemanticCircuitDraft, Parameter, DeviceId, QueryKey, NormalizationResult)
_CAPTURED = (EvidenceRecord, SourceRef, EvidenceIssue)
_ALL_TYPES = (DRAFT_TYPES + CHANNEL_TYPES + (ChannelIdentityResult,)
              + local_connectivity_codec._ALL_TYPES)


def _captured_bytes(value: object) -> bytes:
    return publication_codec.encode_record(cast(WireRecord, value))


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__,
                          'fields': {field: _pack(getattr(value, field)) for field in spec[1]}})
    for classes, tag, encoder in (
        (_LOCAL, 'local_record', local_connectivity_codec.encode_record),
        (_GEOMETRY, 'geometry_record', geometry_codec.encode_record),
        (_EFFECTIVE, 'effective_record', effective_codec.encode_record),
        (_SEMANTIC, 'semantic_record', semantic_codec.encode_record),
        (_CAPTURED, 'captured_record', _captured_bytes),
    ):
        if any(type(value) is cls for cls in classes):
            return FrozenMap({tag: encoder(value)})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _pack_for_encode(value: object) -> object:
    """Build operation-local tags; canonical_bytes freezes the complete tree."""
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return {'record': type(value).__name__,
                'fields': {field: _pack_for_encode(getattr(value, field)) for field in spec[1]}}
    for classes, tag, encoder in (
        (_LOCAL, 'local_record', local_connectivity_codec.encode_record),
        (_GEOMETRY, 'geometry_record', geometry_codec.encode_record),
        (_EFFECTIVE, 'effective_record', effective_codec.encode_record),
        (_SEMANTIC, 'semantic_record', semantic_codec.encode_record),
        (_CAPTURED, 'captured_record', _captured_bytes),
    ):
        if any(type(value) is cls for cls in classes):
            return {tag: encoder(value)}
    if type(value) is FrozenMap:
        return {'map': freeze(value)}
    if type(value) is tuple:
        return {'tuple': tuple(_pack_for_encode(item) for item in value)}
    return {'scalar': freeze(value)}


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged channel identity wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('expected immutable channel payload map')
        return value['map']
    if set(value) == {'tuple'}:
        items = value['tuple']
        if type(items) is not tuple:
            raise ValueError('expected channel wire tuple')
        return tuple(_unpack(item) for item in items)
    if set(value) == {'scalar'}:
        if type(value['scalar']) is FrozenMap or type(value['scalar']) is tuple:
            raise ValueError('scalar channel wire tag cannot contain collections')
        return value['scalar']
    for tag, classes, decoder in (
        ('local_record', _LOCAL, local_connectivity_codec.decode_record),
        ('geometry_record', _GEOMETRY, geometry_codec.decode_record),
        ('effective_record', _EFFECTIVE, effective_codec.decode_record),
        ('semantic_record', _SEMANTIC, semantic_codec.decode_record),
        ('captured_record', _CAPTURED, publication_codec.decode_record),
    ):
        if set(value) == {tag}:
            raw = value[tag]
            if type(raw) is not bytes:
                raise ValueError('nested channel wire record requires canonical bytes')
            result = decoder(raw)
            if not any(type(result) is cls for cls in classes):
                raise ValueError('foreign nested channel wire type')
            return result
    if (set(value) != {'record', 'fields'} or type(value['record']) is not str
            or type(value['fields']) is not FrozenMap):
        raise ValueError('invalid channel identity wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown channel identity wire record')
    constructor, fields = spec
    payload = value['fields']
    if set(payload) != set(fields):
        raise ValueError('unknown/missing channel identity wire fields')
    result = constructor(**{field: _unpack(payload[field]) for field in fields})
    if _pack(result) != value:
        raise ValueError('noncanonical channel identity wire record')
    return result


def encode_record(record: object) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported channel identity wire type')
    validate_closed_graph(record, _ALL_TYPES)
    return canonical_bytes({'wire_schema': 'layauto-channel-identity-wire/1', 'record': _pack_for_encode(record)})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if (type(value) is not FrozenMap or set(value) != {'wire_schema', 'record'}
            or value['wire_schema'] != 'layauto-channel-identity-wire/1'):
        raise ValueError('unsupported channel identity wire schema')
    result = _unpack(value['record'])
    if encode_record(result) != data:
        raise ValueError('noncanonical channel identity wire bytes')
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
