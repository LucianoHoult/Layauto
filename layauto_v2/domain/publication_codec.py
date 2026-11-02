"""Explicit, closed tagged wire codec for the pre-context contracts.

Every record type has a fixed field list. User payload maps are opaque exact
values, so a payload resembling a record tag cannot be decoded as a record.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import cast

from .codec import FrozenMap, Value, canonical_bytes, decode, freeze
from .evidence import EvidenceRecord, SourceFile, SourceRef
from .results import EvidenceIssue, ParseResult
from .publication import (
    AcquisitionEvent, Content, ContentRef, EvidenceAudit, ExceptionCause,
    FinalizeFailureRequest, InputCheckpoint, InputsReady, ParseAudit, PipelineResult,
    PublicationUnavailable, RunAttempt, RunRecord, RunRecordFreezeFailureClosure,
    RunRequest, Selection, StageFailure, ToolRunResult, WireRecord, WithRunRecordClosure,
)

# This is deliberately a wire-schema table, not an unrestricted dataclass codec.
_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    'Selection': (Selection, ('uri', 'declared_sha256')),
    'ContentRef': (ContentRef, ('kind', 'run_id', 'digest')),
    'ExceptionCause': (ExceptionCause, ('exception_type', 'message')),
    'AcquisitionEvent': (AcquisitionEvent, ('uri', 'path', 'operation', 'status', 'sha256', 'exception_type', 'message')),
    'SourceRef': (SourceRef, ('uri', 'sha256', 'field', 'line', 'column', 'byte_offset', 'record_index')),
    'SourceFile': (SourceFile, ('uri', 'data', 'sha256')),
    'EvidenceIssue': (EvidenceIssue, ('category', 'code', 'message', 'source')),
    'EvidenceRecord': (EvidenceRecord, ('kind', 'payload', 'sources', 'parser_version', 'schema_version')),
    'ParseResult': (ParseResult, ('status', 'value', 'issues', 'completed', 'sources', 'tool_run_id', 'schema_version')),
    'RunRequest': (RunRequest, ('proposed_run_id', 'lineage_id', 'idempotency_key', 'site_path', 'raw_input_selections', 'raw_capture_selections', 'config_policy_selections', 'raw_descriptor', 'expected_state_head', 'requested_mode', 'execution_mode', 'schema_version', 'operation_kind', 'kind')),
    'RunAttempt': (RunAttempt, ('request', 'revision', 'phase', 'checkpoint_ref', 'terminal_ref', 'schema_version', 'kind')),
    'ToolRunResult': (ToolRunResult, ('run_id', 'tool_run_id', 'sources', 'events', 'execution_status', 'tool_name', 'mode', 'schema_version', 'kind')),
    'ParseAudit': (ParseAudit, ('run_id', 'tool_ref', 'result', 'schema_version', 'kind')),
    'EvidenceAudit': (EvidenceAudit, ('run_id', 'tool_ref', 'evidence', 'parse_ref', 'schema_version', 'kind')),
    'StageFailure': (StageFailure, ('run_id', 'category', 'code', 'message', 'source', 'completed', 'causes', 'stage', 'schema_version', 'kind')),
    'FinalizeFailureRequest': (FinalizeFailureRequest, ('run_id', 'expected_revision', 'idempotency_key', 'failure_ref', 'completed', 'schema_version', 'operation_kind')),
    'InputCheckpoint': (InputCheckpoint, ('run_id', 'revision', 'tool_ref', 'parse_ref', 'evidence_refs', 'outcome', 'failure_ref', 'ready_value', 'finalize_request', 'schema_version', 'kind')),
    'RunRecord': (RunRecord, ('run_id', 'failure_ref', 'completed', 'status', 'schema_version', 'kind')),
    'WithRunRecordClosure': (WithRunRecordClosure, ('run_id', 'run_record_ref', 'failure_ref', 'completed', 'closure_kind', 'schema_version', 'kind')),
    'RunRecordFreezeFailureClosure': (RunRecordFreezeFailureClosure, ('run_id', 'failure_ref', 'freeze_failure_ref', 'completed', 'closure_kind', 'schema_version', 'kind')),
    'PipelineResult': (PipelineResult, ('run_id', 'closure_ref', 'lifecycle_status', 'deployment_disposition', 'schema_version', 'kind')),
    'InputsReady': (InputsReady, ('run_id', 'attempt', 'checkpoint_ref', 'tool_ref', 'parse_ref', 'evidence_refs', 'value', 'status', 'schema_version')),
    'PublicationUnavailable': (PublicationUnavailable, ('run_id', 'operation', 'message', 'causes', 'attempt', 'completed', 'pending_tool', 'pending_parse', 'pending_evidence', 'pending_failure', 'status', 'schema_version')),
}


def _pack(value: object) -> Value:
    name = type(value).__name__
    spec = _SPEC.get(name)
    if spec is not None and type(value) is spec[0]:
        return FrozenMap({'record': name, 'fields': {key: _pack(getattr(value, key)) for key in spec[1]}})
    if isinstance(value, FrozenMap):
        return FrozenMap({'value': value})
    if isinstance(value, tuple):
        return FrozenMap({'tuple': tuple(_pack(v) for v in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if not isinstance(value, FrozenMap):
        raise ValueError('expected tagged wire value')
    if set(value) == {'value'}:
        result = value['value']
        if not isinstance(result, FrozenMap):
            raise ValueError('expected an exact payload map')
        return result
    if set(value) == {'scalar'}:
        scalar = value['scalar']
        if isinstance(scalar, (FrozenMap, tuple)):
            raise ValueError('container cannot use scalar tag')
        return scalar
    if set(value) == {'tuple'}:
        items = value['tuple']
        if not isinstance(items, tuple):
            raise ValueError('expected tuple wire value')
        return tuple(_unpack(v) for v in items)
    if set(value) != {'record', 'fields'}:
        raise ValueError('invalid wire value discriminator')
    name, body = value['record'], value['fields']
    if not isinstance(name, str) or name not in _SPEC or not isinstance(body, FrozenMap):
        raise ValueError('unknown wire record')
    constructor, keys = _SPEC[name]
    if set(body) != set(keys):
        raise ValueError(f'unknown/missing {name} fields')
    decoded = {key: _unpack(body[key]) for key in keys}
    # Derived ids/discriminators are included in wire and checked after construction.
    derived = {'sha256'} if name == 'SourceFile' else ({'kind'} if name in {
        'RunRequest', 'RunAttempt', 'ToolRunResult', 'ParseAudit', 'EvidenceAudit',
        'StageFailure', 'InputCheckpoint', 'RunRecord', 'WithRunRecordClosure',
        'RunRecordFreezeFailureClosure', 'PipelineResult'} else set())
    try:
        record = constructor(**{key: val for key, val in decoded.items() if key not in derived})
    except (TypeError, AttributeError, UnicodeError) as exc:
        raise ValueError(f'invalid {name} fields') from exc
    if _pack(record) != value:
        raise ValueError('wire discriminator, derived hash, or canonical value mismatch')
    return record


def encode_record(record: WireRecord) -> bytes:
    spec = _SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported wire record type')
    return canonical_bytes({'wire_schema': 'layauto-precontext-wire/1', 'value': _pack(record)})


def decode_record(data: bytes) -> WireRecord:
    value = decode(data)
    if not isinstance(value, FrozenMap) or set(value) != {'wire_schema', 'value'} or value['wire_schema'] != 'layauto-precontext-wire/1':
        raise ValueError('unsupported pre-context wire schema')
    result = cast(WireRecord, _unpack(value['value']))
    if encode_record(result) != data:
        raise ValueError('noncanonical record bytes')
    return result


def record_digest(record: WireRecord) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()


def content_ref(record: Content) -> ContentRef:
    if not isinstance(record, (RunRequest, RunAttempt, ParseAudit, EvidenceAudit,
                               StageFailure, InputCheckpoint, RunRecord,
                               WithRunRecordClosure, RunRecordFreezeFailureClosure,
                               PipelineResult, ToolRunResult)):
        raise ValueError('record is not repository content')
    return ContentRef(record.kind, record.run_id, record_digest(record))
