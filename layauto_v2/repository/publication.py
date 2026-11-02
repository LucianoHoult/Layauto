"""Process-local, single-root publication with operation-scoped idempotency.

No file persistence, crash durability, state publication, or Stage 5 success
operations are provided. All public readers and writers use the same mutex;
all content, attempt pointers and replay results switch in one root assignment.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from threading import RLock
from typing import cast

from layauto_v2.domain.codec import digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.results import ParseResult
from layauto_v2.domain.publication import (
    Content, ContentRef, EvidenceAudit, FinalizeFailureRequest, InputCheckpoint,
    InputsReady, ParseAudit, PipelineResult, RunAttempt, RunRecord,
    RunRecordFreezeFailureClosure, RunRequest, StageFailure, ToolRunResult,
    WithRunRecordClosure, exception_causes, safe_exception_message,
    safe_exception_type,
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


@dataclass(frozen=True)
class RepositorySnapshot:
    """One consistent immutable observation; it does not promise durability."""
    generation: int
    attempts: tuple[RunAttempt, ...]
    content_refs: tuple[ContentRef, ...]
    idempotency_count: int


class PublicationRepository:
    def __init__(self, *, fault_injector: Callable[[str], None] | None = None) -> None:
        self._lock = RLock()
        self._root = _Root()
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
        record = cast(Content, decode_record(data))
        if content_ref(record) != ref:
            raise RepositoryConflict('RefConflict', 'stored content kind/run/digest mismatch')
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
                attempt: RunAttempt, replay: _Replay, point: str) -> None:
        attempt_ref = self._put(contents, attempt)
        attempts = dict(root.attempts)
        attempts[attempt.run_id] = attempt_ref
        staged = _Root(root.generation + 1, tuple(contents.items()),
                       tuple(attempts.items()), root.replays + (replay,))
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
            if request.expected_state_head is not None:
                raise RepositoryConflict('HeadConflict', 'this pre-context repository has no state head')
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
                                      tuple(ref for ref, _ in root.contents), len(root.replays))

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
