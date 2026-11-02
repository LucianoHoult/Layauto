"""Closed, immutable contracts for the process-local pre-context slice (no IO)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .codec import FrozenMap, digest, freeze_map
from .evidence import EvidenceRecord, SourceFile, SourceRef
from .results import EvidenceIssue, ParseResult

VERSION = 'layauto-precontext/1'
ContentKind: TypeAlias = Literal['request', 'attempt', 'tool_run', 'parse', 'evidence',
                                  'stage_failure', 'checkpoint', 'run_record',
                                  'closure', 'pipeline_result']
KINDS = ('request', 'attempt', 'tool_run', 'parse', 'evidence', 'stage_failure',
         'checkpoint', 'run_record', 'closure', 'pipeline_result')
FailureCategory: TypeAlias = Literal['read', 'config', 'parse', 'unsupported', 'binding',
                                     'internal', 'interrupted', 'run_record_freeze']


def _text(value: object, label: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f'{label} must be a nonempty string')
    value.encode('utf-8')


def _sha(value: object) -> None:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('expected SHA-256 lowercase hex')


def _version(value: str) -> None:
    if value != VERSION:
        raise ValueError('unsupported pre-context schema version')


def _revision(value: object) -> None:
    if type(value) is not int or value < 0:
        raise ValueError('revision must be a nonnegative integer')


def _sequence(owner: object, name: str, cls: type[object]) -> None:
    value = getattr(owner, name)
    if not isinstance(value, (tuple, list)) or any(type(v) is not cls for v in value):
        raise ValueError(f'invalid {name}')
    object.__setattr__(owner, name, tuple(value))


@dataclass(frozen=True)
class Selection:
    uri: str
    declared_sha256: str | None = None

    def __post_init__(self) -> None:
        _text(self.uri, 'selection URI')
        if '\x00' in self.uri:
            raise ValueError('selection URI contains NUL')
        if self.declared_sha256 is not None:
            _sha(self.declared_sha256)


@dataclass(frozen=True)
class ContentRef:
    kind: ContentKind
    run_id: str
    digest: str

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError('unsupported content ref kind')
        _text(self.run_id, 'run id')
        _sha(self.digest)

    @property
    def id(self) -> str:
        return f'{self.kind}:{self.run_id}:{self.digest}'


TypedRef = ContentRef


def _ref(ref: ContentRef, run_id: str, kinds: tuple[str, ...]) -> None:
    if type(ref) is not ContentRef or ref.run_id != run_id or ref.kind not in kinds:
        raise ValueError('reference kind/run mismatch')


def _refs(owner: object, name: str, run_id: str,
          kinds: tuple[str, ...] = ('tool_run', 'parse', 'evidence')) -> None:
    _sequence(owner, name, ContentRef)
    values: tuple[ContentRef, ...] = getattr(owner, name)
    for ref in values:
        _ref(ref, run_id, kinds)
    if len(set(values)) != len(values):
        raise ValueError('duplicate content reference')


@dataclass(frozen=True)
class RunRequest:
    proposed_run_id: str
    lineage_id: str
    idempotency_key: str
    site_path: str
    raw_input_selections: tuple[Selection, ...] = ()
    raw_capture_selections: tuple[Selection, ...] = ()
    config_policy_selections: tuple[Selection, ...] = ()
    raw_descriptor: FrozenMap = field(default_factory=lambda: FrozenMap({}))
    expected_state_head: str | None = None
    requested_mode: str = 'dummy_fixture'
    execution_mode: str = 'whole_intent'
    schema_version: str = VERSION
    operation_kind: Literal['create_attempt'] = 'create_attempt'
    kind: Literal['request'] = field(default='request', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if self.operation_kind != 'create_attempt':
            raise ValueError('invalid create operation')
        for name in ('proposed_run_id', 'lineage_id', 'idempotency_key', 'site_path',
                     'requested_mode', 'execution_mode'):
            _text(getattr(self, name), name)
        # Absolute POSIX paths bind the request independently of a later cwd.
        if not self.site_path.startswith('/') or self.site_path.startswith('//') or '\x00' in self.site_path:
            raise ValueError('site_path must be an explicit absolute POSIX path')
        if self.expected_state_head is not None:
            _text(self.expected_state_head, 'expected state head')
        for name in ('raw_input_selections', 'raw_capture_selections', 'config_policy_selections'):
            _sequence(self, name, Selection)
        uris = [s.uri for s in self.selections]
        if len(set(uris)) != len(uris):
            raise ValueError('duplicate declared selection URI')
        object.__setattr__(self, 'raw_descriptor', freeze_map(self.raw_descriptor))

    @property
    def run_id(self) -> str:
        return self.proposed_run_id

    @property
    def selections(self) -> tuple[Selection, ...]:
        return self.raw_input_selections + self.raw_capture_selections + self.config_policy_selections

    @property
    def selection_digests(self) -> FrozenMap:
        return freeze_map({name: digest(tuple({'uri': s.uri, 'declared_sha256': s.declared_sha256}
                                             for s in getattr(self, name)))
                           for name in ('raw_input_selections', 'raw_capture_selections',
                                        'config_policy_selections')})

    @property
    def raw_descriptor_digest(self) -> str:
        return digest(self.raw_descriptor)

    @property
    def digest(self) -> str:
        from .publication_codec import record_digest
        return record_digest(self)


@dataclass(frozen=True)
class RunAttempt:
    request: RunRequest
    revision: int = 0
    phase: Literal['unsealed', 'terminal'] = 'unsealed'
    checkpoint_ref: ContentRef | None = None
    terminal_ref: ContentRef | None = None
    schema_version: str = VERSION
    kind: Literal['attempt'] = field(default='attempt', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if type(self.request) is not RunRequest:
            raise ValueError('attempt requires RunRequest')
        _revision(self.revision)
        if self.phase not in ('unsealed', 'terminal'):
            raise ValueError('unsupported attempt phase')
        if self.checkpoint_ref is not None:
            _ref(self.checkpoint_ref, self.run_id, ('checkpoint',))
        if self.terminal_ref is not None:
            _ref(self.terminal_ref, self.run_id, ('pipeline_result',))
        if (self.phase == 'terminal') != (self.terminal_ref is not None):
            raise ValueError('terminal phase/pointer mismatch')
        if self.revision == 0 and (self.checkpoint_ref is not None or self.terminal_ref is not None):
            raise ValueError('revision zero must be a fresh attempt')

    @property
    def run_id(self) -> str:
        return self.request.proposed_run_id

    @property
    def ref(self) -> ContentRef:
        from .publication_codec import content_ref
        return content_ref(self)


@dataclass(frozen=True)
class ExceptionCause:
    exception_type: str
    message: str

    def __post_init__(self) -> None:
        _text(self.exception_type, 'exception type')
        if type(self.message) is not str:
            raise ValueError('exception message must be a string')
        self.message.encode('utf-8')


def exception_causes(exc: BaseException) -> tuple[ExceptionCause, ...]:
    """Snapshot explicit/implicit causes, retaining the original exception first."""
    result: list[ExceptionCause] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        result.append(ExceptionCause(type(current).__name__, str(current)))
        current = current.__cause__ if current.__cause__ is not None else (
            None if current.__suppress_context__ else current.__context__)
    return tuple(result)


@dataclass(frozen=True)
class AcquisitionEvent:
    uri: str
    path: str
    operation: Literal['read', 'probe']
    status: Literal['success', 'present', 'absent', 'error', 'interrupted']
    sha256: str | None = None
    exception_type: str | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        _text(self.uri, 'acquisition URI')
        _text(self.path, 'acquisition path')
        if self.operation not in ('read', 'probe'):
            raise ValueError('invalid acquisition operation')
        if self.status in ('error', 'interrupted'):
            _text(self.exception_type, 'acquisition exception type')
            if type(self.message) is not str or self.sha256 is not None:
                raise ValueError('failed acquisition cannot claim bytes')
        elif self.operation == 'read' and self.status == 'success':
            _sha(self.sha256)
            if self.exception_type is not None or self.message is not None:
                raise ValueError('successful acquisition cannot contain an exception')
        elif self.operation == 'probe' and self.status in ('present', 'absent'):
            if any(x is not None for x in (self.sha256, self.exception_type, self.message)):
                raise ValueError('probe cannot claim bytes or an exception')
        else:
            raise ValueError('invalid acquisition operation/status combination')


@dataclass(frozen=True)
class ToolRunResult:
    run_id: str
    tool_run_id: str
    sources: tuple[SourceFile, ...]
    events: tuple[AcquisitionEvent, ...]
    execution_status: Literal['completed', 'error', 'interrupted'] = 'completed'
    tool_name: Literal['fixture-reader'] = 'fixture-reader'
    mode: Literal['dummy_fixture'] = 'dummy_fixture'
    schema_version: str = VERSION
    kind: Literal['tool_run'] = field(default='tool_run', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _text(self.tool_run_id, 'tool run id')
        if self.tool_name != 'fixture-reader' or self.mode != 'dummy_fixture':
            raise ValueError('this acquisition contract cannot claim real EDA execution')
        _sequence(self, 'sources', SourceFile)
        _sequence(self, 'events', AcquisitionEvent)
        source_pairs = {(s.uri, s.sha256) for s in self.sources}
        if len({s.uri for s in self.sources}) != len(self.sources):
            raise ValueError('duplicate acquisition source URI')
        read_pairs = {(e.uri, e.sha256) for e in self.events if e.operation == 'read' and e.status == 'success'}
        if source_pairs != read_pairs:
            raise ValueError('acquisition events and actual source bytes disagree')
        expected = ('interrupted' if any(e.status == 'interrupted' for e in self.events) else
                    'error' if any(e.status == 'error' for e in self.events) else 'completed')
        if self.execution_status != expected:
            raise ValueError('execution status does not match actual acquisition events')


@dataclass(frozen=True)
class ParseAudit:
    run_id: str
    tool_ref: ContentRef
    result: ParseResult
    schema_version: str = VERSION
    kind: Literal['parse'] = field(default='parse', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _ref(self.tool_ref, self.run_id, ('tool_run',))
        if type(self.result) is not ParseResult or self.result.tool_run_id is None:
            raise ValueError('pipeline parse must link an actual tool run')


@dataclass(frozen=True)
class EvidenceAudit:
    run_id: str
    tool_ref: ContentRef
    evidence: EvidenceRecord
    parse_ref: ContentRef | None = None
    schema_version: str = VERSION
    kind: Literal['evidence'] = field(default='evidence', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _ref(self.tool_ref, self.run_id, ('tool_run',))
        if self.parse_ref is not None:
            _ref(self.parse_ref, self.run_id, ('parse',))
        if type(self.evidence) is not EvidenceRecord:
            raise ValueError('invalid evidence audit')


@dataclass(frozen=True)
class StageFailure:
    run_id: str
    category: FailureCategory
    code: str
    message: str
    source: SourceRef | None = None
    completed: tuple[ContentRef, ...] = ()
    causes: tuple[ExceptionCause, ...] = ()
    stage: Literal['stage1', 'run_record_freeze'] = 'stage1'
    schema_version: str = VERSION
    kind: Literal['stage_failure'] = field(default='stage_failure', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for name in ('run_id', 'code', 'message'):
            _text(getattr(self, name), name)
        if self.category not in ('read', 'config', 'parse', 'unsupported', 'binding',
                                 'internal', 'interrupted', 'run_record_freeze'):
            raise ValueError('invalid failure category')
        if self.stage not in ('stage1', 'run_record_freeze'):
            raise ValueError('invalid pre-context failure stage')
        if (self.stage == 'run_record_freeze') != (self.category == 'run_record_freeze'):
            raise ValueError('freeze failure stage/category mismatch')
        if self.source is not None and type(self.source) is not SourceRef:
            raise ValueError('invalid failure source')
        _refs(self, 'completed', self.run_id)
        _sequence(self, 'causes', ExceptionCause)
        if self.category in ('internal', 'interrupted', 'run_record_freeze') and not self.causes:
            raise ValueError('unexpected failure must preserve exception causes')


@dataclass(frozen=True)
class FinalizeFailureRequest:
    run_id: str
    expected_revision: int
    idempotency_key: str
    failure_ref: ContentRef
    completed: tuple[ContentRef, ...]
    schema_version: str = VERSION
    operation_kind: Literal['finalize_precontext_failure'] = 'finalize_precontext_failure'

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _text(self.idempotency_key, 'idempotency key')
        _revision(self.expected_revision)
        if self.operation_kind != 'finalize_precontext_failure':
            raise ValueError('invalid finalize operation')
        _ref(self.failure_ref, self.run_id, ('stage_failure',))
        _refs(self, 'completed', self.run_id)


@dataclass(frozen=True)
class InputCheckpoint:
    run_id: str
    revision: int
    tool_ref: ContentRef
    parse_ref: ContentRef | None
    evidence_refs: tuple[ContentRef, ...]
    outcome: Literal['inputs_ready', 'failure']
    failure_ref: ContentRef | None = None
    ready_value: FrozenMap | None = None
    finalize_request: FinalizeFailureRequest | None = None
    schema_version: str = VERSION
    kind: Literal['checkpoint'] = field(default='checkpoint', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _revision(self.revision)
        if self.revision < 1:
            raise ValueError('checkpoint must follow attempt creation')
        _ref(self.tool_ref, self.run_id, ('tool_run',))
        if self.parse_ref is not None:
            _ref(self.parse_ref, self.run_id, ('parse',))
        _refs(self, 'evidence_refs', self.run_id, ('evidence',))
        if self.outcome == 'inputs_ready':
            if self.parse_ref is None or self.ready_value is None or self.failure_ref is not None or self.finalize_request is not None:
                raise ValueError('invalid inputs-ready checkpoint')
            object.__setattr__(self, 'ready_value', freeze_map(self.ready_value))
        elif self.outcome == 'failure':
            if self.ready_value is not None or self.failure_ref is None or type(self.finalize_request) is not FinalizeFailureRequest:
                raise ValueError('invalid failure checkpoint')
            _ref(self.failure_ref, self.run_id, ('stage_failure',))
            if (self.finalize_request.run_id != self.run_id or self.finalize_request.failure_ref != self.failure_ref
                    or self.finalize_request.expected_revision != self.revision
                    or self.finalize_request.completed != self.completed):
                raise ValueError('checkpoint/finalize request mismatch')
        else:
            raise ValueError('invalid checkpoint discriminator')

    @property
    def completed(self) -> tuple[ContentRef, ...]:
        return (self.tool_ref,) + (() if self.parse_ref is None else (self.parse_ref,)) + self.evidence_refs

    @property
    def ref(self) -> ContentRef:
        from .publication_codec import content_ref
        return content_ref(self)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    failure_ref: ContentRef
    completed: tuple[ContentRef, ...]
    status: Literal['precontext_failure'] = 'precontext_failure'
    schema_version: str = VERSION
    kind: Literal['run_record'] = field(default='run_record', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        if self.status != 'precontext_failure':
            raise ValueError('unsupported RunRecord variant')
        _ref(self.failure_ref, self.run_id, ('stage_failure',))
        _refs(self, 'completed', self.run_id)


@dataclass(frozen=True)
class WithRunRecordClosure:
    run_id: str
    run_record_ref: ContentRef
    failure_ref: ContentRef
    completed: tuple[ContentRef, ...]
    closure_kind: Literal['with_run_record'] = 'with_run_record'
    schema_version: str = VERSION
    kind: Literal['closure'] = field(default='closure', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        if self.closure_kind != 'with_run_record':
            raise ValueError('invalid closure discriminator')
        _ref(self.run_record_ref, self.run_id, ('run_record',))
        _ref(self.failure_ref, self.run_id, ('stage_failure',))
        _refs(self, 'completed', self.run_id)


@dataclass(frozen=True)
class RunRecordFreezeFailureClosure:
    run_id: str
    failure_ref: ContentRef
    freeze_failure_ref: ContentRef
    completed: tuple[ContentRef, ...]
    closure_kind: Literal['run_record_freeze_failure'] = 'run_record_freeze_failure'
    schema_version: str = VERSION
    kind: Literal['closure'] = field(default='closure', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        if self.closure_kind != 'run_record_freeze_failure':
            raise ValueError('invalid freeze closure discriminator')
        _ref(self.failure_ref, self.run_id, ('stage_failure',))
        _ref(self.freeze_failure_ref, self.run_id, ('stage_failure',))
        _refs(self, 'completed', self.run_id)
        if self.failure_ref == self.freeze_failure_ref:
            raise ValueError('freeze failure must retain the separate original failure')


Stage5Closure: TypeAlias = WithRunRecordClosure | RunRecordFreezeFailureClosure


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    closure_ref: ContentRef
    lifecycle_status: Literal['terminal'] = 'terminal'
    deployment_disposition: Literal['reject'] = 'reject'
    schema_version: str = VERSION
    kind: Literal['pipeline_result'] = field(default='pipeline_result', init=False)

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        _ref(self.closure_ref, self.run_id, ('closure',))
        if self.lifecycle_status != 'terminal' or self.deployment_disposition != 'reject':
            raise ValueError('pre-context publication can only terminalize as reject')

    @property
    def ref(self) -> ContentRef:
        from .publication_codec import content_ref
        return content_ref(self)


@dataclass(frozen=True)
class InputsReady:
    run_id: str
    attempt: RunAttempt
    checkpoint_ref: ContentRef
    tool_ref: ContentRef
    parse_ref: ContentRef
    evidence_refs: tuple[ContentRef, ...]
    value: FrozenMap
    status: Literal['inputs_ready'] = 'inputs_ready'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _text(self.run_id, 'run id')
        if type(self.attempt) is not RunAttempt or self.attempt.run_id != self.run_id or self.attempt.phase != 'unsealed':
            raise ValueError('inputs-ready requires the same unsealed attempt')
        if self.status != 'inputs_ready':
            raise ValueError('invalid handoff discriminator')
        _ref(self.checkpoint_ref, self.run_id, ('checkpoint',))
        if self.attempt.checkpoint_ref != self.checkpoint_ref:
            raise ValueError('handoff checkpoint differs from attempt')
        _ref(self.tool_ref, self.run_id, ('tool_run',))
        _ref(self.parse_ref, self.run_id, ('parse',))
        _refs(self, 'evidence_refs', self.run_id, ('evidence',))
        object.__setattr__(self, 'value', freeze_map(self.value))


@dataclass(frozen=True)
class PublicationUnavailable:
    run_id: str
    operation: str
    message: str
    causes: tuple[ExceptionCause, ...] = ()
    attempt: RunAttempt | None = None
    completed: tuple[ContentRef, ...] = ()
    pending_tool: ToolRunResult | None = None
    pending_parse: ParseResult | None = None
    pending_evidence: tuple[EvidenceRecord, ...] = ()
    pending_failure: StageFailure | None = None
    status: Literal['publication_unavailable'] = 'publication_unavailable'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for name in ('run_id', 'operation', 'message'):
            _text(getattr(self, name), name)
        if self.status != 'publication_unavailable':
            raise ValueError('invalid publication diagnostic discriminator')
        if self.attempt is not None and (type(self.attempt) is not RunAttempt or self.attempt.run_id != self.run_id):
            raise ValueError('diagnostic attempt/run mismatch')
        _sequence(self, 'causes', ExceptionCause)
        _refs(self, 'completed', self.run_id)
        if self.pending_tool is not None and (type(self.pending_tool) is not ToolRunResult or self.pending_tool.run_id != self.run_id):
            raise ValueError('pending acquisition/run mismatch')
        if self.pending_parse is not None and type(self.pending_parse) is not ParseResult:
            raise ValueError('invalid pending parse')
        _sequence(self, 'pending_evidence', EvidenceRecord)
        if self.pending_failure is not None and (type(self.pending_failure) is not StageFailure or self.pending_failure.run_id != self.run_id):
            raise ValueError('pending failure/run mismatch')


Content: TypeAlias = RunRequest | RunAttempt | ToolRunResult | ParseAudit | EvidenceAudit | StageFailure | InputCheckpoint | RunRecord | Stage5Closure | PipelineResult
WireRecord: TypeAlias = Content | Selection | ContentRef | ExceptionCause | AcquisitionEvent | FinalizeFailureRequest | InputsReady | PublicationUnavailable | SourceFile | SourceRef | EvidenceRecord | EvidenceIssue | ParseResult
