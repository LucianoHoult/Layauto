"""Process-local Stage 1 entry: inputs-ready handoff or published rejection.

This is an internal pre-context slice, not a complete Stage 1–6 run.
"""
from __future__ import annotations

import posixpath
from pathlib import Path
from typing import TypeAlias

from layauto_v2.domain.codec import digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.publication import (
    AcquisitionEvent, InputCheckpoint, InputsReady, PipelineResult, PublicationUnavailable,
    RunAttempt, RunRequest, StageFailure, ToolRunResult, exception_causes,
    safe_exception_message, safe_exception_type,
)
from layauto_v2.domain.results import ParseResult
from layauto_v2.importers.reader import InputParser
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.tooling import FixtureCapture

PrecontextResult: TypeAlias = InputsReady | PipelineResult | PublicationUnavailable


def _drive(parser: InputParser, capture: FixtureCapture) -> ParseResult:
    try:
        request = next(parser.requests)
    except StopIteration as done:
        result: ParseResult = done.value
        return result
    while True:
        response = capture.acquire(request)
        # Only the parser's own completion is a result. A driver exception,
        # including StopIteration, must reach the stage boundary unchanged.
        try:
            request = parser.requests.send(response)
        except StopIteration as done:
            result = done.value
            return result


def _binding_failure(request: RunRequest, tool: ToolRunResult,
                     parse: ParseResult, root: str | None) -> StageFailure | None:
    if root is None:
        return None  # Invalid site path; the parser has the located failure.
    # Only captured spellings/paths are bindings. Collapsing '..' is incorrect
    # when a preceding component is a symlink, and post-capture resolve is racy.
    sources: dict[str, SourceFile] = {}
    by_uri = {source.uri: source for source in tool.sources}
    for source in tool.sources:
        sources[source.uri] = source
        sources[posixpath.join(root, source.uri)] = source
    for event in tool.events:
        if event.operation == 'read' and event.status == 'success':
            sources[event.path] = by_uri[event.uri]
    for selection in request.selections:
        selected = sources.get(selection.uri)
        if selected is None:
            if parse.status == 'success':
                return StageFailure(request.run_id, 'binding', 'UnreadSelection',
                                    'declared selection was not acquired: ' + selection.uri,
                                    SourceRef(selection.uri, field='selection'))
        elif selection.declared_sha256 is not None and selection.declared_sha256 != selected.sha256:
            return StageFailure(request.run_id, 'binding', 'InputDrift',
                                'declared SHA-256 differs from acquired bytes: ' + selection.uri,
                                selected.ref(field='declared_sha256'))
    return None


def _unavailable(repository: PublicationRepository, request: RunRequest, operation: str,
                 exc: Exception, *, tool: ToolRunResult | None = None,
                 parse: ParseResult | None = None, evidence: tuple[EvidenceRecord, ...] = (),
                 failure: StageFailure | None = None,
                 sources: tuple[SourceFile, ...] = (),
                 events: tuple[AcquisitionEvent, ...] = ()) -> PublicationUnavailable:
    attempt: RunAttempt | None = None
    checkpoint: InputCheckpoint | None = None
    try:
        attempt = repository.load_attempt(request.run_id)
        checkpoint = repository.load_checkpoint(request.run_id)
    except Exception:
        pass  # Storage may be unavailable even for diagnostic reads.
    return PublicationUnavailable(
        request.run_id, operation, safe_exception_message(exc), exception_causes(exc),
        attempt, () if checkpoint is None else checkpoint.completed,
        pending_tool=tool, pending_parse=parse, pending_evidence=evidence, pending_failure=failure,
        pending_sources=sources, pending_events=events)


def _resume(repository: PublicationRepository, request: RunRequest,
            checkpoint: InputCheckpoint) -> PrecontextResult:
    if checkpoint.outcome == 'inputs_ready':
        try:
            ready = repository.read_ready(request.run_id)
        except Exception as exc:
            return _unavailable(repository, request, 'read_ready', exc)
        if ready is None:
            raise RuntimeError('published inputs-ready checkpoint is unavailable')
        return ready
    assert checkpoint.finalize_request is not None
    try:
        return repository.finalize_precontext_failure(checkpoint.finalize_request)
    except RepositoryConflict:
        raise
    except Exception as exc:
        # Only an actual readback can confirm publication after a response loss.
        try:
            terminal = repository.read_terminal(request.run_id)
            if terminal is not None:
                return terminal
        except Exception:
            pass
        return _unavailable(repository, request, 'finalize_precontext_failure', exc)


def prepare_inputs(repository: PublicationRepository, request: RunRequest) -> PrecontextResult:
    """Create identity before parsing, then retain actual bytes and their audits.

    Reuse the same caller request (especially run id/key) after a lost response.
    InputsReady deliberately has no successful terminal disposition. Expected
    repository conflicts are typed exceptions; unavailable publication is an
    explicit diagnostic with no invented terminal pointer.
    """
    try:
        repository.create_attempt(request)
    except RepositoryConflict:
        raise
    except Exception as exc:
        # Even if creation committed before a response loss, do not start IO
        # until a subsequent call has successfully obtained that same attempt.
        return _unavailable(repository, request, 'create_attempt', exc)

    with repository.orchestration(request.run_id):
        try:
            terminal = repository.read_terminal(request.run_id)
            if terminal is not None:
                return terminal
            checkpoint = repository.load_checkpoint(request.run_id)
            attempt = repository.load_attempt(request.run_id)
        except Exception as exc:
            return _unavailable(repository, request, 'read_attempt', exc)
        if checkpoint is not None:
            return _resume(repository, request, checkpoint)

        tool_id = 'fixture-read:' + digest({'run_id': request.run_id, 'request': request.digest})
        capture = FixtureCapture(request.run_id, tool_id)
        parser = InputParser(Path(request.site_path), tool_run_id=tool_id)
        parse: ParseResult | None = None
        failure: StageFailure | None = None
        interrupt: KeyboardInterrupt | SystemExit | None = None
        try:
            try:
                parse = _drive(parser, capture)
            except (KeyboardInterrupt, SystemExit) as exc:
                # Install the original interrupt before any best-effort diagnostic.
                interrupt = exc
                failure = StageFailure(request.run_id, 'interrupted', safe_exception_type(exc),
                                       safe_exception_message(exc), causes=exception_causes(exc))
            except Exception as exc:
                failure = StageFailure(request.run_id, 'internal', 'InternalStageFailure',
                                       safe_exception_message(exc), causes=exception_causes(exc))

            try:
                tool = capture.freeze()
            except Exception as exc:
                # Keep the stage's original cause chain. The unavailable
                # result separately describes this diagnostic freeze failure.
                if failure is None:
                    failure = StageFailure(request.run_id, 'internal', 'InternalStageFailure',
                                           safe_exception_message(exc), causes=exception_causes(exc))
                return _unavailable(repository, request, 'freeze_tool_run', exc,
                                    parse=parse, evidence=parser.completed, failure=failure,
                                    sources=capture.sources, events=capture.events)
            if parse is not None:
                try:
                    failure = _binding_failure(request, tool, parse, parser.input_root)
                    if failure is None and parse.status == 'error':
                        issue = parse.issues[0]
                        failure = StageFailure(request.run_id, issue.category, issue.code,
                                               issue.message, issue.source)
                except Exception as exc:
                    failure = StageFailure(request.run_id, 'internal', 'InternalStageFailure',
                                           safe_exception_message(exc), causes=exception_causes(exc))
            try:
                checkpoint = repository.record_audits(
                    request.run_id, expected_revision=attempt.revision,
                    idempotency_key='inputs:' + request.idempotency_key,
                    tool=tool, parse=parse, evidence=parser.completed, failure=failure,
                    ready=failure is None)
            except RepositoryConflict:
                raise
            except Exception as exc:
                try:
                    checkpoint = repository.load_checkpoint(request.run_id)
                except Exception:
                    checkpoint = None
                if checkpoint is None:
                    return _unavailable(repository, request, 'record_audits', exc,
                                        tool=tool, parse=parse, evidence=parser.completed, failure=failure)
            return _resume(repository, request, checkpoint)
        finally:
            # Diagnostics may not swallow or replace the original interruption.
            if interrupt is not None:
                raise interrupt
