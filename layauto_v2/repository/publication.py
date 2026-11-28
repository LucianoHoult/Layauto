"""Process-local, single-root publication with operation-scoped idempotency.

All public readers and writers use the same mutex.
All content, attempt pointers and replay results switch in one root assignment.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from hashlib import sha256
from dataclasses import dataclass, replace
from threading import RLock
from typing import Literal, cast

from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.policy import REQUIRED_M1_RULES
from layauto_v2.domain.results import ParseResult
from layauto_v2.domain.publication import (
    BASELINE_VERSION, BaselineSnapshot, BaselineTarget, InitializationEvent, PreparedBaseline,
    SealedContext, Stage2Request, StateHead, Content, ContentRef, EvidenceAudit, FinalizeFailureRequest, InputCheckpoint,
    InputsReady, ParseAudit, PipelineResult, RunAttempt, RunRecord,
    RunRecordFreezeFailureClosure, RunRequest, StageFailure, ToolRunResult,
    WithRunRecordClosure, exception_causes, safe_exception_message,
    safe_exception_type, STAGE5_VERSION, AuditBinding, FailureCategory, PreparedStage5, Stage5Request,
    Stage5RecordClosure, Stage5FreezeFailureClosure, Stage5RunRecord,
)
from layauto_v2.domain.publication_codec import (
    content_ref, decode_record, encode_record, record_digest,
)


class RepositoryConflict(Exception):
    """Typed guard/idempotency conflict, with no mutation performed."""
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class _Replay:
    operation: str
    run_id: str
    key: str
    request_digest: str
    result_ref: ContentRef


@dataclass(frozen=True)
class _Root:
    generation: int = 0
    contents: tuple[tuple[ContentRef, bytes], ...] = ()
    attempts: tuple[tuple[str, ContentRef], ...] = ()
    replays: tuple[_Replay, ...] = ()
    heads: tuple[tuple[str, ContentRef], ...] = ()


@dataclass(frozen=True)
class RepositorySnapshot:
    """One consistent immutable observation; it does not promise durability."""
    generation: int
    attempts: tuple[RunAttempt, ...]
    content_refs: tuple[ContentRef, ...]
    idempotency_count: int
    heads: tuple[tuple[str, ContentRef], ...]
    content_bytes: int


class PublicationRepository:
    def __init__(self, *, fault_injector: Callable[[str], None] | None = None) -> None:
        self._lock = RLock()
        self._root = _Root()
        self._scope = object()
        self._run_locks: dict[str, RLock] = {}
        self._fault_injector = fault_injector

    def _fault(self, point: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    @staticmethod
    def _read(root: _Root, ref: ContentRef) -> Content:
        if type(ref) is not ContentRef:
            raise RepositoryConflict('RefConflict', 'expected a typed content ref')
        data = dict(root.contents).get(ref)
        if data is None:
            raise RepositoryConflict('RefConflict', f'unresolved content reference: {ref.id}')
        if sha256(data).hexdigest() != ref.digest:
            raise RepositoryConflict('RefConflict', f'{ref.id}: stored content digest mismatch')
        record = cast(Content, decode_record(data))
        if content_ref(record) != ref:
            raise RepositoryConflict('RefConflict', f'{ref.id}: stored content kind/run/digest mismatch')
        return record

    @classmethod
    def _attempt(cls, root: _Root, run_id: str) -> RunAttempt:
        ref = dict(root.attempts).get(run_id)
        if ref is None:
            raise RepositoryConflict('MissingAttempt', f'no attempt exists for {run_id}')
        attempt = cls._read(root, ref)
        if not isinstance(attempt, RunAttempt):
            raise RepositoryConflict('RefConflict', 'attempt pointer references a different kind')
        return attempt

    @classmethod
    def _replay(cls, root: _Root, operation: str, run_id: str, key: str,
                request_digest: str) -> Content | None:
        for entry in root.replays:
            if (entry.operation, entry.run_id, entry.key) == (operation, run_id, key):
                if entry.request_digest != request_digest:
                    raise RepositoryConflict('IdempotencyConflict', 'same operation/run/key has a different canonical request')
                return cls._read(root, entry.result_ref)
        return None

    @staticmethod
    def _put(contents: dict[ContentRef, bytes], record: Content) -> ContentRef:
        data = encode_record(record)
        ref = content_ref(record)
        prior = contents.get(ref)
        if prior is not None and prior != data:
            raise RepositoryConflict('RefConflict', 'content address collision')
        contents[ref] = data
        return ref

    def _commit(self, root: _Root, contents: dict[ContentRef, bytes],
                attempt: RunAttempt, replay: _Replay, point: str, *,
                new_head: ContentRef | None = None) -> None:
        attempt_ref = self._put(contents, attempt)
        attempts = dict(root.attempts)
        attempts[attempt.run_id] = attempt_ref
        heads = root.heads
        if new_head is not None:
            heads += ((attempt.request.lineage_id, new_head),)
        staged = _Root(root.generation + 1, tuple(contents.items()),
                       tuple(attempts.items()), root.replays + (replay,), heads)
        self._fault(point + '.before_switch')
        self._root = staged
        # This exception models response loss: the full result is already visible.
        self._fault(point + '.after_switch')

    @staticmethod
    def _guard(attempt: RunAttempt, expected_revision: int) -> None:
        if attempt.phase != 'unsealed':
            raise RepositoryConflict('TransitionConflict', 'only an unsealed attempt permits this operation')
        if type(expected_revision) is not int or expected_revision != attempt.revision:
            raise RepositoryConflict('RevisionConflict', 'attempt revision differs from the expected revision')
        if attempt.request.requested_mode != 'dummy_fixture' or attempt.request.execution_mode != 'whole_intent':
            raise RepositoryConflict('ModeConflict', 'unsupported acquisition/execution mode')

    def create_attempt(self, request: RunRequest) -> RunAttempt:
        if type(request) is not RunRequest:
            raise RepositoryConflict('RequestConflict', 'create requires a validated RunRequest')
        with self._lock:
            root = self._root
            replay = self._replay(root, 'create_attempt', request.run_id,
                                  request.idempotency_key, request.digest)
            if replay is not None:
                assert isinstance(replay, RunAttempt)
                return replay
            if request.run_id in dict(root.attempts):
                raise RepositoryConflict('RunConflict', 'proposed run id already belongs to another create request')
            self._check_head(root, request.lineage_id, request.expected_state_head)
            if request.requested_mode != 'dummy_fixture' or request.execution_mode != 'whole_intent':
                raise RepositoryConflict('ModeConflict', 'unsupported acquisition/execution mode')
            contents = dict(root.contents)
            self._put(contents, request)
            attempt = RunAttempt(request)
            attempt_ref = self._put(contents, attempt)
            entry = _Replay('create_attempt', request.run_id, request.idempotency_key,
                            request.digest, attempt_ref)
            self._commit(root, contents, attempt, entry, 'create')
            return attempt

    @contextmanager
    def orchestration(self, run_id: str) -> Iterator[None]:
        """Serialize a run's capture/recovery without expanding the atomic domain."""
        with self._lock:
            self._attempt(self._root, run_id)
            lock = self._run_locks.setdefault(run_id, RLock())
        with lock:
            yield

    def read(self, ref: ContentRef) -> Content:
        with self._lock:
            return self._read(self._root, ref)

    def load_attempt(self, run_id: str) -> RunAttempt:
        with self._lock:
            return self._attempt(self._root, run_id)

    @classmethod
    def _checkpoint(cls, root: _Root, attempt: RunAttempt) -> InputCheckpoint | None:
        if attempt.checkpoint_ref is None:
            return None
        checkpoint = cls._read(root, attempt.checkpoint_ref)
        if not isinstance(checkpoint, InputCheckpoint):
            raise RepositoryConflict('RefConflict', 'checkpoint pointer references a different kind')
        return checkpoint

    def load_checkpoint(self, run_id: str) -> InputCheckpoint | None:
        with self._lock:
            return self._checkpoint(self._root, self._attempt(self._root, run_id))

    def read_ready(self, run_id: str) -> InputsReady | None:
        with self._lock:
            root = self._root
            attempt = self._attempt(root, run_id)
            checkpoint = self._checkpoint(root, attempt)
            if checkpoint is None or checkpoint.outcome != 'inputs_ready' or attempt.phase != 'unsealed':
                return None
            assert checkpoint.parse_ref is not None and checkpoint.ready_value is not None
            return InputsReady(run_id, attempt, checkpoint.ref, checkpoint.tool_ref,
                               checkpoint.parse_ref, checkpoint.evidence_refs, checkpoint.ready_value)

    def read_terminal(self, run_id: str) -> PipelineResult | None:
        with self._lock:
            root = self._root
            attempt = self._attempt(root, run_id)
            if attempt.terminal_ref is None:
                return None
            result = self._read(root, attempt.terminal_ref)
            if not isinstance(result, PipelineResult):
                raise RepositoryConflict('RefConflict', 'terminal pointer references a different kind')
            return result

    def snapshot(self) -> RepositorySnapshot:
        with self._lock:
            root = self._root
            return RepositorySnapshot(root.generation,
                                      tuple(self._attempt(root, run) for run, _ in root.attempts),
                                      tuple(ref for ref, _ in root.contents), len(root.replays), root.heads,
                                      sum(len(data) for _, data in root.contents))

    @staticmethod
    def _check_head(root: _Root, lineage: str, expected: str | None) -> ContentRef | None:
        head = dict(root.heads).get(lineage)
        if (None if head is None else head.id) != expected:
            raise RepositoryConflict('HeadConflict', f'{lineage}: expected {expected}, found {head}')
        return head

    def load_head(self, lineage_id: str) -> ContentRef | None:
        with self._lock:
            return dict(self._root.heads).get(lineage_id)

    def _stage2_replay(self, root: _Root, request: Stage2Request) -> SealedContext | None:
        replay = self._replay(root, request.operation, request.run_id, request.idempotency_key,
                              record_digest(request))
        if replay is not None and not isinstance(replay, SealedContext):
            raise RepositoryConflict('RefConflict', 'invalid Stage 2 receipt')
        return replay

    def replay_stage2(self, request: Stage2Request) -> SealedContext | None:
        """Recover the result before a caller spends time rebuilding a checked candidate."""
        with self._lock:
            return self._stage2_replay(self._root, request)

    def _stage2_base(self, root: _Root, request: Stage2Request) -> tuple[RunAttempt, InputCheckpoint]:
        attempt = self._attempt(root, request.run_id)
        self._guard(attempt, request.expected_revision)
        if (request.lineage_id != attempt.request.lineage_id
                or request.expected_state_head != attempt.request.expected_state_head):
            raise RepositoryConflict('HeadConflict', 'Stage 2 differs from the requested starting lineage/head')
        self._check_head(root, request.lineage_id, request.expected_state_head)
        checkpoint = self._read(root, request.checkpoint_ref)
        if (not isinstance(checkpoint, InputCheckpoint) or attempt.checkpoint_ref != request.checkpoint_ref
                or checkpoint.outcome != 'inputs_ready' or checkpoint.revision != attempt.revision):
            raise RepositoryConflict('CheckpointConflict', f'{request.checkpoint_ref.id}: expected current ready input')
        return attempt, checkpoint

    @classmethod
    def _capture_binding(cls, root: _Root, checkpoint: InputCheckpoint,
                         expected_sources: FrozenMap | None = None) -> FrozenMap:
        tool = cls._read(root, checkpoint.tool_ref)
        assert checkpoint.parse_ref is not None
        parse = cls._read(root, checkpoint.parse_ref)
        if (not isinstance(tool, ToolRunResult) or not isinstance(parse, ParseAudit)
                or parse.tool_ref != checkpoint.tool_ref or parse.result.value != checkpoint.ready_value):
            raise RepositoryConflict('RefConflict', f'{checkpoint.ref.id}: inconsistent tool/parse links')
        evidence = []
        for ref in checkpoint.evidence_refs:
            audit = cls._read(root, ref)
            if (not isinstance(audit, EvidenceAudit) or audit.tool_ref != checkpoint.tool_ref
                    or audit.parse_ref != checkpoint.parse_ref):
                raise RepositoryConflict('RefConflict', f'{ref.id}: inconsistent evidence links')
            evidence.append(audit.evidence)
        if tuple(evidence) != parse.result.completed or parse.result.sources != tool.sources:
            raise RepositoryConflict('RefConflict', f'{checkpoint.ref.id}: inconsistent captured evidence')
        sources = {s.uri: s.sha256 for s in tool.sources}
        if expected_sources is not None and sources != expected_sources:
            raise RepositoryConflict('BindingConflict', f'{checkpoint.ref.id}: foreign candidate source manifest')
        # W005 probes optional normalized caches next to the header using absolute
        # paths. Preserve the acquisition spelling in the audit and bind the cache
        # role and bytes independently of a different run's working directory.
        selected = {s.uri for e in evidence for s in e.sources}
        caches = {e.uri for e in tool.events if e.operation == 'probe' and e.status == 'present'
                  and e.uri in sources and e.uri not in selected}
        return FrozenMap({'capability': 'dummy_fixture/whole_intent/stage2/1',
                          'sources': {uri: sha for uri, sha in sources.items() if uri not in caches},
                          'normalized_caches': {uri.rsplit('/', 1)[-1]: sources[uri] for uri in caches},
                          'value_digest': digest(checkpoint.ready_value),
                          'evidence': tuple(record_digest(e) for e in evidence)})

    def stage2_binding(self, request: Stage2Request, ready: InputsReady, expected_sources: FrozenMap) -> FrozenMap:
        with self._lock:
            attempt, checkpoint = self._stage2_base(self._root, request)
            if (attempt.ref != ready.attempt.ref or checkpoint.tool_ref != ready.tool_ref
                    or checkpoint.parse_ref != ready.parse_ref or checkpoint.evidence_refs != ready.evidence_refs):
                raise RepositoryConflict('ReadbackConflict', f'{request.checkpoint_ref.id}: inconsistent ready receipt')
            binding = self._capture_binding(self._root, checkpoint, expected_sources)
            if digest(ready.value) != binding['value_digest']:
                raise RepositoryConflict('ReadbackConflict', f'{request.checkpoint_ref.id}: inconsistent ready value')
            return binding

    def initialize(self, request: Stage2Request, prepared: PreparedBaseline) -> SealedContext:
        if type(prepared) is not PreparedBaseline or prepared.repository_scope is not self._scope:
            raise RepositoryConflict('BindingConflict', 'prepared baseline belongs to another repository')
        with self._lock:
            root = self._root
            replay = self._stage2_replay(root, request)
            if request != prepared.request or request.operation != 'initialize':
                raise RepositoryConflict('BindingConflict', 'prepared baseline belongs to a different request')
            if replay is not None:
                return replay
            attempt, checkpoint = self._stage2_base(root, request)
            if self._capture_binding(root, checkpoint) != prepared.snapshot.binding:
                raise RepositoryConflict('BindingConflict', f'{request.checkpoint_ref.id}: baseline binding mismatch')
            contents = dict(root.contents)
            snapshot_ref = self._put(contents, prepared.snapshot)
            target_ref = self._put(contents, prepared.target)
            event_ref = self._put(contents, InitializationEvent(request.run_id, request.lineage_id,
                                                               request.checkpoint_ref, snapshot_ref))
            head = StateHead(request.run_id, request.lineage_id, snapshot_ref, event_ref, target_ref)
            head_ref = self._put(contents, head)
            return self._seal(root, contents, request, attempt, head_ref, target_ref,
                              prepared.snapshot.binding, new_head=head_ref)

    def seal_context(self, request: Stage2Request) -> SealedContext:
        if request.operation != 'seal_context':
            raise RepositoryConflict('HeadConflict', 'seal_context requires a requested state head')
        with self._lock:
            root = self._root
            replay = self._stage2_replay(root, request)
            if replay is not None:
                return replay
            attempt, checkpoint = self._stage2_base(root, request)
            head_ref = dict(root.heads)[request.lineage_id]
            head = self._read(root, head_ref)
            if not isinstance(head, StateHead) or head.lineage_id != request.lineage_id:
                raise RepositoryConflict('RefConflict', f'{head_ref.id}: wrong lineage')
            snapshot = self._read(root, head.snapshot_ref)
            event = self._read(root, head.event_ref)
            target = self._read(root, head.target_ref)
            if (not isinstance(snapshot, BaselineSnapshot) or not isinstance(event, InitializationEvent)
                    or not isinstance(target, BaselineTarget) or event.snapshot_ref != head.snapshot_ref
                    or event.lineage_id != head.lineage_id
                    or not event.checkpoint_ref == snapshot.checkpoint_ref == target.checkpoint_ref):
                raise RepositoryConflict('RefConflict', f'{head_ref.id}: inconsistent initialization links')
            original = self._read(root, snapshot.checkpoint_ref)
            if (not isinstance(original, InputCheckpoint) or original.outcome != 'inputs_ready'
                    or self._capture_binding(root, original) != snapshot.binding):
                raise RepositoryConflict('RefConflict', f'{snapshot.checkpoint_ref.id}: invalid original snapshot binding')
            binding = self._capture_binding(root, checkpoint)
            if snapshot.binding != binding:
                old, new = snapshot.binding['sources'], binding['sources']
                assert isinstance(old, FrozenMap) and isinstance(new, FrozenMap)
                changed = sorted(uri for uri in old.keys() | new.keys() if old.get(uri) != new.get(uri))
                reason = ', '.join(changed) or 'normalized evidence or capability'
                raise RepositoryConflict('BindingConflict', f'{head_ref.id}: incompatible {reason}')
            return self._seal(root, dict(root.contents), request, attempt, head_ref, head.target_ref, binding)

    def _seal(self, root: _Root, contents: dict[ContentRef, bytes], request: Stage2Request,
              attempt: RunAttempt, head_ref: ContentRef, target_ref: ContentRef, binding: FrozenMap,
              *, new_head: ContentRef | None = None) -> SealedContext:
        context = SealedContext(request.run_id, request.checkpoint_ref, head_ref, target_ref, digest(binding))
        context_ref = self._put(contents, context)
        updated = replace(attempt, revision=attempt.revision + 1, phase='sealed_open',
                          schema_version=BASELINE_VERSION, context_ref=context_ref)
        receipt = _Replay(request.operation, request.run_id, request.idempotency_key,
                          record_digest(request), context_ref)
        self._commit(root, contents, updated, receipt, request.operation, new_head=new_head)
        return context

    def _stage5_replay(self, root: _Root, request: Stage5Request) -> Stage5RecordClosure | Stage5FreezeFailureClosure | None:
        if type(request) is not Stage5Request:
            raise RepositoryConflict('RequestConflict', 'close_stage5 requires a validated Stage5Request')
        replay = self._replay(root, request.operation, request.run_id, request.idempotency_key, record_digest(request))
        if replay is not None and not isinstance(replay, (Stage5RecordClosure, Stage5FreezeFailureClosure)):
            raise RepositoryConflict('RefConflict', 'invalid Stage 5 receipt')
        return replay

    def replay_stage5(self, request: Stage5Request) -> Stage5RecordClosure | Stage5FreezeFailureClosure | None:
        """Return a recorded close before reopening inputs or evaluating any rule."""
        with self._lock:
            return self._stage5_replay(self._root, request)

    def _stage5_base(self, root: _Root, request: Stage5Request, binding: AuditBinding) -> tuple[RunAttempt, StateHead]:
        attempt = self._attempt(root, request.run_id)
        if attempt.phase != 'sealed_open':
            raise RepositoryConflict('TransitionConflict', f'{attempt.run_id}: expected sealed_open, found {attempt.phase}')
        if attempt.revision != request.expected_revision:
            raise RepositoryConflict('RevisionConflict', 'Stage 5 attempt revision differs')
        if attempt.request.requested_mode != 'dummy_fixture' or attempt.request.execution_mode != 'whole_intent':
            raise RepositoryConflict('ModeConflict', 'unsupported Stage 5 acquisition/execution mode')
        if attempt.context_ref != request.context_ref or attempt.request.lineage_id != request.lineage_id:
            raise RepositoryConflict('BindingConflict', 'Stage 5 request differs from the sealed attempt')
        context = self._read(root, request.context_ref)
        if (not isinstance(context, SealedContext) or context.checkpoint_ref != attempt.checkpoint_ref
                or context.head_ref != request.expected_head_ref):
            raise RepositoryConflict('BindingConflict', 'Stage 5 request differs from the sealed context')
        head = self._read(root, context.head_ref)
        if (not isinstance(head, StateHead) or head.lineage_id != request.lineage_id
                or head.target_ref != context.target_ref or binding != AuditBinding(
                    request.context_ref, context.target_ref, context.head_ref, head.snapshot_ref)):
            raise RepositoryConflict('BindingConflict', 'Stage 5 audits refer to another target or layout version')
        return attempt, head

    @staticmethod
    def _verify_stage5_audits(prepared: PreparedStage5) -> None:
        planning, rules = prepared.planning, prepared.rules
        if planning.issues:
            if rules is not None:
                raise RepositoryConflict('ResultConflict', 'rule evaluation follows a rejected plan')
            return
        if not planning.observations or rules is None:
            raise RepositoryConflict('ResultConflict', 'closing requires both target proof and a formal rule invocation')
        if rules.binding != planning.binding:
            raise RepositoryConflict('BindingConflict', 'rule invocation and planning bind different publications')
        if rules.issues:
            return
        ids = tuple(row.get('id') for row in rules.checks)
        if (len(ids) != len(REQUIRED_M1_RULES) or any(name not in ids for name in REQUIRED_M1_RULES)
                or any(row.get('status') != 'pass' for row in rules.checks)):
            raise RepositoryConflict('ResultConflict', 'clean assessment requires a pass from each required rule')

    def close_stage5(self, request: Stage5Request, prepared: PreparedStage5) -> Stage5RecordClosure | Stage5FreezeFailureClosure:
        """Atomically freeze the completed checks and close a sealed whole-intent attempt."""
        with self._lock:
            root = self._root
            replay = self._stage5_replay(root, request)
            if (type(prepared) is not PreparedStage5 or prepared.repository_scope is not self._scope
                    or prepared.request != request):
                raise RepositoryConflict('BindingConflict', 'Stage 5 material belongs to a different repository or request')
            planning, rules = prepared.planning, prepared.rules
            if replay is not None:
                # A direct close supplies material as well as a recipe. Both must
                # match the winning operation, even after its response was lost.
                if isinstance(replay, Stage5FreezeFailureClosure):
                    saved = replay.completed
                else:
                    record = self._read(root, replay.run_record_ref)
                    if not isinstance(record, Stage5RunRecord):
                        raise RepositoryConflict('RefConflict', 'invalid Stage 5 RunRecord receipt')
                    saved = (record.planning_ref,) + (() if record.rule_ref is None else (record.rule_ref,))
                supplied = (content_ref(planning),) + (() if rules is None else (content_ref(rules),))
                if supplied != saved:
                    raise RepositoryConflict('IdempotencyConflict', 'same close request has different checked audits')
                return replay

            attempt, head = self._stage5_base(root, request, planning.binding)
            self._verify_stage5_audits(prepared)
            issues = planning.issues if rules is None else rules.issues
            head_status: Literal['current', 'superseded'] = (
                'current' if dict(root.heads).get(request.lineage_id) == request.expected_head_ref else 'superseded')
            if not issues:
                if head_status != 'current':
                    raise RepositoryConflict('HeadConflict', 'lineage head advanced after target and rule evaluation')
                if head.eco_commits:
                    raise RepositoryConflict('ChainConflict', 'no_change requires an empty ECO chain')

            contents = dict(root.contents)
            planning_ref = self._put(contents, planning)
            rule_ref = None if rules is None else self._put(contents, rules)
            completed = (planning_ref,) + (() if rule_ref is None else (rule_ref,))
            failure_ref = None
            if issues:
                issue = issues[0]
                category: FailureCategory = 'planning' if rules is None else 'constraint'
                if issue.causes:
                    category = 'internal'
                failure = StageFailure(request.run_id, category, issue.code, issue.message,
                                       issue.sources[0], completed, issue.causes,
                                       stage='stage4' if rules is None else 'stage5')
                failure_ref = self._put(contents, failure)

            closure: Stage5RecordClosure | Stage5FreezeFailureClosure
            try:
                self._fault('close_stage5.freeze')
                record = Stage5RunRecord(request.run_id, planning.binding, planning_ref, rule_ref, failure_ref,
                                         'no_change' if failure_ref is None else 'sealed_no_publication', head_status)
                record_ref = self._put(contents, record)
            except Exception as exc:
                freeze_failure = StageFailure(request.run_id, 'run_record_freeze', 'RunRecordFreezeFailure',
                                              safe_exception_message(exc), completed=completed,
                                              causes=exception_causes(exc), stage='run_record_freeze')
                freeze_ref = self._put(contents, freeze_failure)
                closure = Stage5FreezeFailureClosure(request.run_id, freeze_ref, completed, failure_ref)
            else:
                closure = Stage5RecordClosure(request.run_id, record_ref)
            closure_ref = self._put(contents, closure)
            updated = replace(attempt, revision=attempt.revision + 1, phase='stage5_closed',
                              closure_ref=closure_ref, schema_version=STAGE5_VERSION)
            receipt = _Replay(request.operation, request.run_id, request.idempotency_key,
                              record_digest(request), closure_ref)
            self._commit(root, contents, updated, receipt, request.operation)
            return closure

    @staticmethod
    def _source_ref(source: SourceRef, sources: dict[str, str]) -> None:
        if source.sha256 is not None and sources.get(source.uri) != source.sha256:
            raise RepositoryConflict('SourceConflict', 'located/hash ref does not match actual acquisition bytes')

    @classmethod
    def _audit_links(cls, run_id: str, tool: ToolRunResult, parse: ParseResult | None,
                     evidence: tuple[EvidenceRecord, ...], failure: StageFailure | None,
                     ready: bool) -> None:
        if type(tool) is not ToolRunResult or tool.run_id != run_id:
            raise RepositoryConflict('RunConflict', 'acquisition belongs to a different run')
        sources = {s.uri: s.sha256 for s in tool.sources}
        if type(ready) is not bool or (failure is None) != ready:
            raise RepositoryConflict('ResultConflict', 'recording must choose inputs-ready or a concrete failure')
        if parse is not None:
            if type(parse) is not ParseResult or parse.tool_run_id != tool.tool_run_id:
                raise RepositoryConflict('RefConflict', 'parse does not link this acquisition')
            if parse.sources != tool.sources:
                raise RepositoryConflict('SourceConflict', 'parse must consume the exact acquisition source bytes')
            if evidence != parse.completed:
                raise RepositoryConflict('RefConflict', 'evidence must be the completed parse records')
        if ready and (parse is None or parse.status != 'success' or tool.execution_status != 'completed'):
            raise RepositoryConflict('ResultConflict', 'inputs-ready requires completed acquisition and successful parse')
        for item in evidence:
            if type(item) is not EvidenceRecord:
                raise RepositoryConflict('RefConflict', 'invalid completed evidence')
            for source in item.sources:
                cls._source_ref(source, sources)
        if failure is not None:
            if type(failure) is not StageFailure or failure.run_id != run_id or failure.stage != 'stage1':
                raise RepositoryConflict('RunConflict', 'stage failure belongs to a different run/stage')
            if failure.source is not None:
                cls._source_ref(failure.source, sources)

    def record_audits(self, run_id: str, *, expected_revision: int, idempotency_key: str,
                      tool: ToolRunResult, parse: ParseResult | None,
                      evidence: tuple[EvidenceRecord, ...], failure: StageFailure | None = None,
                      ready: bool = False) -> InputCheckpoint:
        """Atomically save audits and a restartable ready/failure decision.

        A failure checkpoint freezes the exact finalization request. A subsequent
        caller retries that request without acquiring or parsing any file again.
        """
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise RepositoryConflict('RequestConflict', 'audit request requires an idempotency key')
        evidence = tuple(evidence)
        request_digest = digest({'run_id': run_id, 'expected_revision': expected_revision,
                                 'idempotency_key': idempotency_key, 'tool': encode_record(tool),
                                 'parse': None if parse is None else encode_record(parse),
                                 'evidence': tuple(encode_record(e) for e in evidence),
                                 'failure': None if failure is None else encode_record(failure), 'ready': ready})
        with self._lock:
            root = self._root
            replay = self._replay(root, 'record_audits', run_id, idempotency_key, request_digest)
            if replay is not None:
                assert isinstance(replay, InputCheckpoint)
                return replay
            attempt = self._attempt(root, run_id)
            self._guard(attempt, expected_revision)
            if attempt.checkpoint_ref is not None:
                raise RepositoryConflict('TransitionConflict', 'this input slice already has a checkpoint')
            self._audit_links(run_id, tool, parse, evidence, failure, ready)
            contents = dict(root.contents)
            tool_ref = self._put(contents, tool)
            parse_ref = None if parse is None else self._put(contents, ParseAudit(run_id, tool_ref, parse))
            evidence_refs = tuple(self._put(contents, EvidenceAudit(run_id, tool_ref, item, parse_ref))
                                  for item in evidence)
            completed = (tool_ref,) + (() if parse_ref is None else (parse_ref,)) + evidence_refs
            revision = attempt.revision + 1
            if ready:
                assert parse is not None and parse.value is not None
                checkpoint = InputCheckpoint(run_id, revision, tool_ref, parse_ref,
                                             evidence_refs, 'inputs_ready', ready_value=parse.value)
            else:
                assert failure is not None
                if failure.completed and failure.completed != completed:
                    raise RepositoryConflict('RefConflict', 'failure completed refs differ from this acquisition/parse')
                failure = replace(failure, completed=completed)
                failure_ref = self._put(contents, failure)
                finalize = FinalizeFailureRequest(run_id, revision,
                                                  attempt.request.idempotency_key + ':finalize_precontext_failure',
                                                  failure_ref, completed)
                checkpoint = InputCheckpoint(run_id, revision, tool_ref, parse_ref, evidence_refs,
                                             'failure', failure_ref=failure_ref, finalize_request=finalize)
            checkpoint_ref = self._put(contents, checkpoint)
            updated = replace(attempt, revision=revision, checkpoint_ref=checkpoint_ref)
            entry = _Replay('record_audits', run_id, idempotency_key, request_digest, checkpoint_ref)
            self._commit(root, contents, updated, entry, 'audits')
            return checkpoint

    def finalize_precontext_failure(self, request: FinalizeFailureRequest) -> PipelineResult:
        if type(request) is not FinalizeFailureRequest:
            raise RepositoryConflict('RequestConflict', 'finalize requires a validated request')
        request_digest = record_digest(request)
        with self._lock:
            root = self._root
            replay = self._replay(root, request.operation_kind, request.run_id,
                                  request.idempotency_key, request_digest)
            if replay is not None:
                assert isinstance(replay, PipelineResult)
                return replay
            attempt = self._attempt(root, request.run_id)
            self._guard(attempt, request.expected_revision)
            # Resolve every supplied ref before comparing the frozen decision.
            failure = self._read(root, request.failure_ref)
            if not isinstance(failure, StageFailure) or failure.run_id != request.run_id:
                raise RepositoryConflict('RefConflict', 'invalid finalization failure ref')
            for ref in request.completed:
                self._read(root, ref)
            if failure.completed != request.completed:
                raise RepositoryConflict('RefConflict', 'finalization audit refs differ from the failure')
            checkpoint = self._checkpoint(root, attempt)
            if checkpoint is None or checkpoint.outcome != 'failure' or checkpoint.finalize_request != request:
                raise RepositoryConflict('CheckpointConflict', 'finalization must replay the frozen input decision')
            contents = dict(root.contents)
            closure: WithRunRecordClosure | RunRecordFreezeFailureClosure
            try:
                self._fault('finalize.freeze')
                record = RunRecord(request.run_id, request.failure_ref, request.completed)
                record_ref = self._put(contents, record)
            except Exception as exc:
                # The sole no-RunRecord escape hatch. The original stage failure
                # remains separately addressable alongside this construction failure.
                freeze_failure = StageFailure(request.run_id, 'run_record_freeze',
                                              'RunRecordFreezeFailure', safe_exception_message(exc) or safe_exception_type(exc),
                                              completed=request.completed, causes=exception_causes(exc),
                                              stage='run_record_freeze')
                freeze_ref = self._put(contents, freeze_failure)
                closure = RunRecordFreezeFailureClosure(request.run_id, request.failure_ref,
                                                         freeze_ref, request.completed)
            else:
                closure = WithRunRecordClosure(request.run_id, record_ref,
                                                request.failure_ref, request.completed)
            closure_ref = self._put(contents, closure)
            result = PipelineResult(request.run_id, closure_ref)
            result_ref = self._put(contents, result)
            updated = replace(attempt, revision=attempt.revision + 1,
                              phase='terminal', terminal_ref=result_ref)
            entry = _Replay(request.operation_kind, request.run_id, request.idempotency_key,
                            request_digest, result_ref)
            self._commit(root, contents, updated, entry, 'finalize')
            return result
