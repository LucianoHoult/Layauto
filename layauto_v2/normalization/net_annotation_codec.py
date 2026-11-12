"""Closed W013 wire with one complete, authenticated W010 Value subtree.

The old W010 wire is restored byte for byte before its unchanged public decoder
is called. No complete input is replaced by a ref or hex-wrapped a second time.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.identifiers import CellId, NetId, QueryKey
from layauto_v2.domain.local_connectivity import ContactComponent, ContactNode, LocalRef
from layauto_v2.domain.net_annotation import (
    AnnotationBinding, AnnotationFragment, AnnotationIssue, AnnotationRef, AnnotationTargetId,
    LayerCoverage, MatchEvidence, NetComponentSummary, NetEvidence, RecordClassification,
    TargetEvidence, TargetIntersection,
)
from layauto_v2.domain.regions import ExactRegion, RegionRef, validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.state.annotation import AnnotationDraft
from . import local_connectivity_codec
from .local_connectivity import LocalConnectivityResult
from .net_annotation import NetAnnotationResult

WIRE_VERSION = 'layauto-net-annotation-wire/1'

# Each allowed type and every persisted field is explicitly named.
_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'CellId': (CellId, ('name',)),
    'NetId': (NetId, ('cell', 'name')),
    'QueryKey': (QueryKey, ('header_id', 'query_run_id', 'database_id', 'kind', 'identity', 'index')),
    'GeometryRecordId': (GeometryRecordId, ('sha256',)),
    'Rect': (Rect, ('x0', 'y0', 'x1', 'y1')),
    'GeometryRef': (GeometryRef, ('kind', 'sha256')),
    'RegionRef': (RegionRef, ('kind', 'sha256')),
    'LocalRef': (LocalRef, ('kind', 'sha256')),
    'ExactRegion': (ExactRegion, ('owner_id', 'role', 'contributors', 'unit_ref', 'operator_ref',
                                   'rectangles', 'schema_version')),
    'ContactNode': (ContactNode, ('layer', 'region', 'binding_ref', 'schema_version')),
    'ContactComponent': (ContactComponent, ('members', 'binding_ref', 'schema_version')),
    'RationalRect': (RationalRect, ('x0', 'y0', 'x1', 'y1')),
    'SourceRef': (SourceRef, ('uri', 'sha256', 'field', 'line', 'column', 'byte_offset', 'record_index')),
    'EvidenceRecord': (EvidenceRecord, ('kind', 'payload', 'sources', 'parser_version', 'schema_version')),
    'EvidenceIssue': (EvidenceIssue, ('category', 'code', 'message', 'source')),
    'NetEvidence': (NetEvidence, ('net_id', 'query_key', 'record', 'identity_provenance', 'schema_version')),
    'AnnotationRef': (AnnotationRef, ('kind', 'sha256')),
    'AnnotationBinding': (AnnotationBinding, ('local_ref', 'effective_ref', 'geometry_ref', 'unit_ref',
        'partition_ref', 'tick_nm', 'top', 'source_cell', 'source_digest', 'derived', 'drawn', 'topology',
        'drawn_record_ids', 'capture_binding', 'scope', 'validity', 'schema_version')),
    'AnnotationTargetId': (AnnotationTargetId, ('binding_ref', 'layer', 'record_id', 'region_ref', 'schema_version')),
    'TargetEvidence': (TargetEvidence, ('target_id', 'node', 'component_ref', 'drawn_rectangle', 'source',
                                       'tick_nm', 'schema_version')),
    'TargetIntersection': (TargetIntersection, ('target_ref', 'rectangles', 'schema_version')),
    'MatchEvidence': (MatchEvidence, ('evidence_ref', 'intersections', 'boundary_targets', 'trimmed',
                                     'unmatched', 'policy', 'status', 'schema_version')),
    'AnnotationFragment': (AnnotationFragment, ('target_ref', 'rectangles', 'evidence_refs', 'net_ids',
                                               'status', 'validity', 'schema_version')),
    'RecordClassification': (RecordClassification, ('record_id', 'layer', 'role', 'classification',
        'rectangle', 'source', 'cell_coordinates', 'schema_version')),
    'LayerCoverage': (LayerCoverage, ('layer', 'drawn_shape_count', 'cell_count', 'target_count', 'total_area',
        'covered_area', 'uncovered_area', 'conflict_area', 'component_conflict_area', 'source_refs',
        'evidence_refs', 'unit', 'denominator', 'schema_version')),
    'NetComponentSummary': (NetComponentSummary, ('component_ref', 'members', 'target_refs',
        'observed_net_ids', 'evidence_refs', 'directly_covered_targets', 'status', 'schema_version')),
    'AnnotationIssue': (AnnotationIssue, ('issue', 'target_refs', 'component_refs', 'evidence_refs',
        'net_ids', 'severity', 'recommended_action', 'schema_version')),
    'AnnotationDraft': (AnnotationDraft, ('binding', 'evidence', 'targets', 'matches', 'fragments',
        'coverage', 'components', 'classifications', 'issues', 'schema_version')),
}


def _types() -> tuple[type[object], ...]:
    return tuple(cast(type[object], spec[0]) for spec in _SPEC.values())


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__,
                          'fields': {name: _pack(getattr(value, name)) for name in spec[1]}})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged net annotation wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('expected immutable net annotation map payload')
        return value['map']
    if set(value) == {'tuple'}:
        items = value['tuple']
        if type(items) is not tuple:
            raise ValueError('expected net annotation tuple payload')
        return tuple(_unpack(item) for item in items)
    if set(value) == {'scalar'}:
        if type(value['scalar']) in (FrozenMap, tuple):
            raise ValueError('net annotation scalar cannot contain collections')
        return value['scalar']
    if (set(value) != {'record', 'fields'} or type(value['record']) is not str
            or type(value['fields']) is not FrozenMap):
        raise ValueError('invalid net annotation wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown net annotation wire record')
    constructor, names = spec
    fields = value['fields']
    if set(fields) != set(names):
        raise ValueError('unknown/missing net annotation wire fields')
    result = constructor(**{name: _unpack(fields[name]) for name in names})
    if _pack(result) != value:
        raise ValueError('noncanonical net annotation record')
    return result


def _compact(result: NetAnnotationResult) -> FrozenMap:
    return FrozenMap({'record': 'NetAnnotationResult', 'fields': {
        'status': _pack(result.status), 'value': _pack(result.value),
        'issues': _pack(result.issues), 'schema_version': _pack(result.schema_version),
    }})


def _validate_result(result: NetAnnotationResult) -> NetAnnotationResult:
    validate_closed_graph(result, _types() + local_connectivity_codec._ALL_TYPES + (NetAnnotationResult,))
    rebuilt = NetAnnotationResult(result.input, result.schema_version)
    if canonical_bytes(_compact(result)) != canonical_bytes(_compact(rebuilt)):
        raise ValueError('net annotation result differs from complete captured reconstruction')
    return rebuilt


def encode_record(record: object) -> bytes:
    if type(record) is NetAnnotationResult:
        rebuilt = _validate_result(record)
        old_bytes = local_connectivity_codec.encode_record(rebuilt.input)
        old_value = decode(old_bytes)
        return canonical_bytes({'wire_schema': WIRE_VERSION,
                                'captured_input_wire': old_value, 'record': _compact(rebuilt)})
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported net annotation wire type')
    validate_closed_graph(record, _types())
    packed = _pack(record)
    rebuilt_record = _unpack(packed)
    if canonical_bytes(_pack(rebuilt_record)) != canonical_bytes(packed):
        raise ValueError('net annotation record differs from public reconstruction')
    return canonical_bytes({'wire_schema': WIRE_VERSION, 'record': packed})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if type(value) is not FrozenMap or value.get('wire_schema') != WIRE_VERSION:
        raise ValueError('unsupported net annotation wire schema')
    if set(value) == {'wire_schema', 'record'}:
        result = _unpack(value['record'])
        validate_closed_graph(result, _types())
        if canonical_bytes({'wire_schema': WIRE_VERSION, 'record': _pack(result)}) != data:
            raise ValueError('noncanonical net annotation wire bytes')
        return result
    if set(value) != {'wire_schema', 'captured_input_wire', 'record'}:
        raise ValueError('unknown/missing net annotation envelope fields')
    # The original full canonical W010 packet is present, not an unauthenticated
    # digest. Its unchanged decoder checks the complete captured input chain.
    input = local_connectivity_codec.decode_record(canonical_bytes(value['captured_input_wire']))
    if type(input) is not LocalConnectivityResult:
        raise ValueError('net annotation result requires a complete W010 result')
    result = NetAnnotationResult(input)
    if canonical_bytes(_compact(result)) != canonical_bytes(value['record']):
        raise ValueError('net annotation wire differs from complete captured reconstruction')
    # domain.decode already authenticated the canonical envelope bytes. Every
    # retained output is compared above; re-entering public encode here would
    # unnecessarily add a third complete W010 authentication during decode.
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
