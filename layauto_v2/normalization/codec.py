"""Versioned closed wire codec for semantic normalization, with exact scalars."""
from __future__ import annotations

import hashlib
from collections.abc import Callable

from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef, SourceFile
from layauto_v2.domain.results import ParseResult
from layauto_v2.domain.publication import InputsReady, InputCheckpoint, ParseAudit, ToolRunResult, EvidenceAudit
from layauto_v2.domain import publication_codec
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId, DeltaId, QueryKey
from layauto_v2.domain.circuit import Parameter, Terminal, Membership, Device, Net, Cell, SemanticCircuitDraft, TargetCircuit
from layauto_v2.domain.intent import TargetDifference
from .contracts import (
    ReadbackBinding, NormalizationInput, NormalizationIssue, DeviceIdentity, NetIdentity,
    DeviceAnnotationSeed, NetAnnotationSeed, NormalizationFacts, NormalizationResult,
)

_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'CellId': (CellId, ('name',)),
    'DeviceId': (DeviceId, ('cell', 'name')),
    'NetId': (NetId, ('cell', 'name')),
    'DeltaId': (DeltaId, ('value',)),
    'QueryKey': (QueryKey, ('header_id', 'query_run_id', 'database_id', 'kind', 'identity', 'index')),
    'Parameter': (Parameter, ('axis', 'token', 'exact', 'unit', 'lexeme', 'source', 'field_evidence')),
    'Terminal': (Terminal, ('role', 'net_id', 'source')),
    'Membership': (Membership, ('device_id', 'terminal')),
    'Device': (Device, ('id', 'model', 'terminals', 'parameters', 'field_sources', 'preservation')),
    'Net': (Net, ('id', 'port_indices', 'global_net', 'memberships', 'sources')),
    'Cell': (Cell, ('id', 'ports', 'globals', 'devices', 'nets', 'field_sources')),
    'SemanticCircuitDraft': (SemanticCircuitDraft, ('cells', 'selected_cell', 'profile_id', 'dialect', 'preservation', 'schema_version')),
    'TargetCircuit': (TargetCircuit, ('cells', 'profile_id', 'dialect', 'preservation', 'schema_version')),
    'TargetDifference': (TargetDifference, ('delta_id', 'op_type', 'operand_ref', 'scope', 'semantic_before', 'semantic_after', 'required_capability', 'obligations', 'provenance', 'axis', 'hard_constraints', 'preferences', 'source', 'schema_version')),
    'ReadbackBinding': (ReadbackBinding, ('ready', 'checkpoint', 'parse_audit', 'tool_run', 'evidence_audits', 'schema_version')),
    'NormalizationInput': (NormalizationInput, ('parse', 'readback', 'schema_version')),
    'NormalizationIssue': (NormalizationIssue, ('category', 'code', 'message', 'source', 'schema_version')),
    'DeviceIdentity': (DeviceIdentity, ('device_id', 'query_key', 'sd_swap', 'provenance')),
    'NetIdentity': (NetIdentity, ('net_id', 'query_key', 'provenance')),
    'DeviceAnnotationSeed': (DeviceAnnotationSeed, ('semantic_id', 'query_key', 'record')),
    'NetAnnotationSeed': (NetAnnotationSeed, ('semantic_id', 'query_key', 'record')),
    'NormalizationFacts': (NormalizationFacts, ('source', 'target', 'differences', 'device_identities', 'net_identities', 'device_seeds', 'net_seeds', 'schema_version')),
    'NormalizationResult': (NormalizationResult, ('status', 'value', 'issues', 'completed', 'input', 'schema_version')),
}
_EXTERNAL = (SourceRef, SourceFile, EvidenceRecord, ParseResult, InputsReady, InputCheckpoint, ParseAudit, ToolRunResult, EvidenceAudit)


def _pack(value: object) -> Value:
    spec = _SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': type(value).__name__, 'fields': {key: _pack(getattr(value, key)) for key in spec[1]}})
    if isinstance(value, _EXTERNAL) and type(value) in _EXTERNAL:
        return FrozenMap({'captured_record': publication_codec.encode_record(value)})
    if isinstance(value, FrozenMap):
        return FrozenMap({'map': value})
    if isinstance(value, tuple):
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if not isinstance(value, FrozenMap):
        raise ValueError('expected tagged normalization wire value')
    if set(value) == {'map'}:
        if not isinstance(value['map'], FrozenMap):
            raise ValueError('expected frozen payload map')
        return value['map']
    if set(value) == {'scalar'}:
        if isinstance(value['scalar'], (FrozenMap, tuple)):
            raise ValueError('scalar tag cannot contain a collection')
        return value['scalar']
    if set(value) == {'tuple'}:
        values = value['tuple']
        if not isinstance(values, tuple):
            raise ValueError('expected wire tuple')
        return tuple(_unpack(item) for item in values)
    if set(value) == {'captured_record'}:
        data = value['captured_record']
        if type(data) is not bytes:
            raise ValueError('captured record must contain canonical wire bytes')
        captured = publication_codec.decode_record(data)
        if type(captured) not in _EXTERNAL:
            raise ValueError('unsupported captured record type')
        return captured
    if set(value) != {'record', 'fields'} or not isinstance(value['record'], str) or not isinstance(value['fields'], FrozenMap):
        raise ValueError('invalid normalization wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown normalization wire record')
    constructor, fields = spec
    if set(value['fields']) != set(fields):
        raise ValueError('unknown/missing normalization record fields')
    # Decode children before constructor shape translation. A child's captured
    # decoder may raise an unexpected exception which must retain its identity
    # through every enclosing record, including NormalizationResult.
    decoded = {field: _unpack(value['fields'][field]) for field in fields}
    if value['record'] in ('NormalizationInput', 'ReadbackBinding'):
        # These receipt constructors validate their shapes before using their
        # children. Their internal reconstruction failures retain identity.
        result = constructor(**decoded)
    else:
        try:
            result = constructor(**decoded)
        except (TypeError, KeyError, AttributeError, UnicodeError) as exc:
            raise ValueError('invalid normalization record fields') from exc
    if _pack(result) != value:
        raise ValueError('noncanonical normalization record')
    return result


def encode_record(record: object) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported normalization record type')
    return canonical_bytes({'wire_schema': 'layauto-normalization-wire/1', 'record': _pack(record)})


def decode_record(data: bytes) -> object:
    value = decode(data)
    if not isinstance(value, FrozenMap) or set(value) != {'wire_schema', 'record'} or value['wire_schema'] != 'layauto-normalization-wire/1':
        raise ValueError('unsupported normalization wire schema')
    result = _unpack(value['record'])
    if encode_record(result) != data:
        raise ValueError('noncanonical normalization wire bytes')
    return result


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
