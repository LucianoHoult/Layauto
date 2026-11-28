"""Orchestrate input capture, baseline publication and whole-intent Stage 4/5 closure."""
from __future__ import annotations

import posixpath
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, TypeAlias, cast

from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.publication import (
    AcquisitionEvent, AuditBinding, AuditIssue, BaselineSnapshot, BaselineTarget, ContentRef, EvidenceAudit, InitializationEvent,
    InputCheckpoint, InputsReady, ParseAudit, PipelineResult, PublicationUnavailable,
    PlanningAudit, PreparedStage5, RuleAudit, RunAttempt, RunRequest, SealedContext, Stage2Request,
    Stage5FreezeFailureClosure, Stage5RecordClosure, Stage5Request, StageFailure, StateHead, ToolRunResult, exception_causes,
    safe_exception_message, safe_exception_type,
)
from layauto_v2.domain.results import ParseResult
from layauto_v2.importers.reader import InputParser
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from layauto_v2.tooling import FixtureCapture

if TYPE_CHECKING:
    from layauto_v2.constraints.drc_context import ConstraintContext
    from layauto_v2.normalization.stage2 import Stage2Facts

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
        if attempt.context_ref is not None:
            raise RepositoryConflict('TransitionConflict', 'Stage 2 already sealed this input checkpoint')
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


def assemble_stage2(repository: PublicationRepository, ready: InputsReady, *,
                    fragment_budget: int) -> Stage2Facts:
    """Assemble unpublished facts from the selected checkpoint, without reacquiring files."""
    from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
    from layauto_v2.normalization.stage2 import Stage2Facts

    attempt = repository.load_attempt(ready.run_id)
    if attempt != ready.attempt:
        raise RepositoryConflict('ReadbackConflict', f'{ready.run_id}: inputs-ready differs from current attempt')
    # InputsReady checks each ref's kind/run and the attempt checkpoint pointer.
    # Repository.read verifies the stored kind/run/digest before returning content.
    checkpoint = cast(InputCheckpoint, repository.read(ready.checkpoint_ref))
    if (checkpoint.parse_ref != ready.parse_ref or checkpoint.tool_ref != ready.tool_ref
            or checkpoint.evidence_refs != ready.evidence_refs or checkpoint.ready_value != ready.value):
        raise RepositoryConflict('ReadbackConflict', f'{ready.checkpoint_ref.id}: inputs-ready differs from checkpoint')
    parse = cast(ParseAudit, repository.read(ready.parse_ref))
    tool = cast(ToolRunResult, repository.read(ready.tool_ref))
    evidence = tuple(cast(EvidenceAudit, repository.read(ref)) for ref in ready.evidence_refs)
    capture = geometry_from_inputs_ready(ready, checkpoint, parse, tool, evidence)
    return Stage2Facts(capture, fragment_budget, repository._scope)


def publish_stage2(repository: PublicationRepository, request: Stage2Request) -> SealedContext:
    """Publish the captured baseline or seal this run against the requested head.

    Keep the same request across retries. Disk files and the original candidate
    are unnecessary after input capture.
    """
    from layauto_v2.normalization.initial_state import build_proposed_initial_state
    from layauto_v2.transactions.initialization import InitializationTransaction

    with repository.orchestration(request.run_id):
        replay = repository.replay_stage2(request)
        if replay is not None:
            return replay
        if request.expected_state_head is not None:
            return InitializationTransaction.reuse(repository, request)
        ready = repository.read_ready(request.run_id)
        if ready is None:
            raise RepositoryConflict('TransitionConflict', 'initialization requires an unsealed ready attempt')
        if ready.checkpoint_ref != request.checkpoint_ref:
            raise RepositoryConflict('RefConflict', f'{request.checkpoint_ref.id}: differs from current checkpoint')
        if request.expected_revision != ready.attempt.revision:
            raise RepositoryConflict('RevisionConflict', 'unexpected Stage 2 input revision')
        facts = assemble_stage2(repository, ready, fragment_budget=request.fragment_budget)
        return InitializationTransaction.initialize(repository, request, ready, build_proposed_initial_state(facts))


def _constraint_owner(name: str, value: FrozenMap, snapshot: BaselineSnapshot,
                      tool: ToolRunResult) -> EvidenceRecord:
    """Resolve the actual role selected by this run's bundle, including renamed owners."""
    from layauto_v2.domain.geometry import mapping, text
    from layauto_v2.importers.config import load_document

    owners = mapping(mapping(value['tech_bundle'])['owners'])
    uri = text(mapping(owners[name])['path'])
    expected = mapping(snapshot.binding['sources']).get(uri)
    source = next((s for s in tool.sources if s.uri == uri), None)
    if source is None or source.sha256 != expected:
        raise RepositoryConflict('BindingConflict', f'{tool.run_id}: /owners/{name}/path has no bound capture of {uri}')
    document = load_document(source)
    if document != mapping(value['tech'])[name]:
        raise RepositoryConflict('BindingConflict', f'{uri}: captured owner differs from sealed {name} evidence')
    return EvidenceRecord(name, document, (source.ref(),))


def open_constraint_context(repository: PublicationRepository, run_id: str,
                            context_ref: ContentRef | None) -> ConstraintContext:
    """Resolve only stored references. A reusing run keeps its own input audit and the original snapshot."""
    from layauto_v2.constraints.drc_context import CheckedVersion, ConstraintContext
    from layauto_v2.domain.geometry import mapping
    from layauto_v2.domain.source_location import ref_from_location
    from layauto_v2.normalization.semantic import build_source_operands
    from layauto_v2.state.snapshot import current_value
    from layauto_v2.tech.rules import RuleCatalog

    attempt = repository.load_attempt(run_id)
    if attempt.phase != 'sealed_open':
        raise RepositoryConflict('TransitionConflict', f'{run_id}: expected sealed_open, found {attempt.phase}')
    if not isinstance(context_ref, ContentRef) or context_ref != attempt.context_ref:
        supplied = context_ref.id if isinstance(context_ref, ContentRef) else 'missing context_ref'
        raise RepositoryConflict('ReadbackConflict', f'{run_id}: {supplied} differs from attempt.context_ref')
    # read() authenticates each ref's kind, run and digest. The immutable context
    # chooses the version even if a later publication advances the lineage head.
    sealed = cast(SealedContext, repository.read(context_ref))
    head = cast(StateHead, repository.read(sealed.head_ref))
    if (sealed.checkpoint_ref != attempt.checkpoint_ref or head.lineage_id != attempt.request.lineage_id
            or sealed.target_ref != head.target_ref):
        raise RepositoryConflict('BindingConflict', f'{context_ref.id}: inconsistent checkpoint, lineage or target')
    snapshot = cast(BaselineSnapshot, repository.read(head.snapshot_ref))
    event = cast(InitializationEvent, repository.read(head.event_ref))
    target = cast(BaselineTarget, repository.read(head.target_ref))
    if (event.snapshot_ref != head.snapshot_ref or event.lineage_id != head.lineage_id
            or not event.checkpoint_ref == snapshot.checkpoint_ref == target.checkpoint_ref):
        raise RepositoryConflict('BindingConflict', f'{sealed.head_ref.id}: inconsistent initialization links')
    checkpoint = cast(InputCheckpoint, repository.read(sealed.checkpoint_ref))
    value = checkpoint.ready_value
    if (checkpoint.outcome != 'inputs_ready' or value is None or digest(value) != snapshot.binding['value_digest']
            or sealed.binding_digest != digest(snapshot.binding)):
        raise RepositoryConflict('BindingConflict', f'{sealed.checkpoint_ref.id}: input binding differs from {head.snapshot_ref.id}')

    # A reused head reports an additional checkpoint from the creating run.
    # Authenticate that backlink before exposing it in CheckedVersion.
    if snapshot.checkpoint_ref != sealed.checkpoint_ref:
        repository.read(snapshot.checkpoint_ref)
    tool = cast(ToolRunResult, repository.read(checkpoint.tool_ref))
    rules = _constraint_owner('rules', value, snapshot, tool)
    physical = _constraint_owner('physical', value, snapshot, tool)
    version = CheckedVersion(context_ref, sealed.checkpoint_ref, checkpoint.tool_ref, sealed.head_ref,
                             head.snapshot_ref, snapshot.checkpoint_ref, snapshot.version)
    # Reuse W007's interpretation of *this checking run's* original source CDL.
    # Preparing its operand performs neither a comparison nor a rule invocation.
    cdl = mapping(value['source_cdl'])
    original = EvidenceRecord('source_cdl', cdl, (ref_from_location(mapping(cdl['source'])),))
    source_circuit = build_source_operands(original, mapping(value['tech']), mapping(value['header']),
                                          mapping(value['tech_bundle']))
    return ConstraintContext._published(version, snapshot, RuleCatalog.from_owner(rules.payload, rules.sources[0]),
                                        physical, value, current_value(source_circuit), target, head.eco_commits)


def _internal_issue(exc: Exception, ref: ContentRef) -> AuditIssue:
    return AuditIssue('InternalStageFailure', safe_exception_message(exc) or safe_exception_type(exc),
                      (SourceRef(ref.id, ref.digest),), exception_causes(exc))


def prepare_stage5(repository: PublicationRepository, request: Stage5Request, *,
                   on_timing: Callable[[str, float], None] | None = None) -> PreparedStage5:
    """Plan on the sealed snapshot, then invoke the mandatory whole-cell checker once.

    The optional observer receives elapsed seconds for each stage reached. Timings
    are external measurements and do not participate in the canonical receipt.
    """
    from layauto_v2.constraints import check_rules
    from layauto_v2.constraints.audit import freeze_rule_audit
    from layauto_v2.planning import plan_no_change

    if type(request) is not Stage5Request:
        raise RepositoryConflict('RequestConflict', 'preparation requires a Stage5Request')
    attempt = repository.load_attempt(request.run_id)
    if attempt.phase != 'sealed_open':
        raise RepositoryConflict('TransitionConflict', f'{request.run_id}: expected a sealed open attempt')
    if request.expected_revision != attempt.revision:
        raise RepositoryConflict('RevisionConflict', 'Stage 5 request uses a stale attempt revision')
    if request.context_ref != attempt.context_ref or request.lineage_id != attempt.request.lineage_id:
        raise RepositoryConflict('BindingConflict', 'Stage 5 request differs from the sealed run')
    sealed = cast(SealedContext, repository.read(request.context_ref))
    if sealed.head_ref != request.expected_head_ref:
        raise RepositoryConflict('HeadConflict', 'Stage 5 request selects a different head from its context')
    head = cast(StateHead, repository.read(sealed.head_ref))
    binding = AuditBinding(request.context_ref, sealed.target_ref, sealed.head_ref, head.snapshot_ref)

    started = perf_counter()
    try:
        view = open_constraint_context(repository, request.run_id, request.context_ref)
        plan = plan_no_change(view, binding)
        planning = plan.audit
    except RepositoryConflict:
        raise
    except Exception as exc:
        planning = PlanningAudit(binding, (), (_internal_issue(exc, binding.snapshot_ref),))
    if on_timing is not None:
        on_timing('planning', perf_counter() - started)
    rules = None
    if not planning.issues:
        started = perf_counter()
        try:
            report = check_rules(view)
            if report.version != view.version or report.catalog != view.catalog:
                raise RepositoryConflict('BindingConflict', 'rule report differs from the selected run, version or catalog')
            rules = freeze_rule_audit(binding, report)
        except RepositoryConflict:
            raise
        except Exception as exc:
            rules = RuleAudit(binding, (), (_internal_issue(exc, binding.context_ref),))
        if on_timing is not None:
            on_timing('rules', perf_counter() - started)
    return PreparedStage5._checked(repository._scope, request, planning, rules)


def run_stage5(repository: PublicationRepository, request: Stage5Request) -> Stage5RecordClosure | Stage5FreezeFailureClosure:
    """Run Stage 4 and close Stage 5, or return the original closure on replay."""
    with repository.orchestration(request.run_id):
        replay = repository.replay_stage5(request)
        if replay is not None:
            return replay
        return repository.close_stage5(request, prepare_stage5(repository, request))
