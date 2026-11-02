"""Repository atomicity, replay, wire and cross-record contracts for W006."""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from threading import Event

import pytest

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode, freeze_map
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.publication import (
    AcquisitionEvent, ContentRef, ExceptionCause, FinalizeFailureRequest,
    InputCheckpoint, PipelineResult, RunAttempt, RunRecord,
    RunRecordFreezeFailureClosure, RunRequest, Selection, StageFailure,
    ToolRunResult, WithRunRecordClosure,
)
from layauto_v2.domain.publication_codec import (
    content_ref, decode_record, encode_record, record_digest,
)
from layauto_v2.domain.results import EvidenceIssue, ParseResult
from layauto_v2.repository import PublicationRepository, RepositoryConflict


def request(run='run', **changes):
    return replace(RunRequest(run, 'lineage', 'create-key', '/fixture/site.yaml'), **changes)


def audit_args(run='run', *, success=False):
    source = SourceFile('site.yaml', b'{"example":"captured bytes"}')
    event = AcquisitionEvent(source.uri, '/fixture/site.yaml', 'read', 'success', source.sha256)
    tool = ToolRunResult(run, run + ':tool', (source,), (event,))
    evidence = EvidenceRecord('config', FrozenMap({'x': [1, {'a': 2}]}), (source.ref(),))
    issue = EvidenceIssue('parse', 'BadSyntax', 'original bad syntax', source.ref(line=1))
    parsed = ParseResult('success' if success else 'error', FrozenMap({'ok': True}) if success else None,
                         () if success else (issue,), (evidence,), (source,), tool.tool_run_id)
    return dict(expected_revision=0, idempotency_key='audits-key', tool=tool, parse=parsed,
                evidence=(evidence,), ready=success,
                failure=None if success else StageFailure(run, 'parse', issue.code, issue.message, issue.source))


def failed_checkpoint(repository, run='run'):
    repository.create_attempt(request(run))
    return repository.record_audits(run, **audit_args(run))


def conflict(code, callable_, *args, **kwargs):
    with pytest.raises(RepositoryConflict) as caught:
        callable_(*args, **kwargs)
    assert caught.value.code == code


def test_request_is_precontext_immutable_and_digest_binds_every_caller_field():
    descriptor = {'selection': [{'declared': 'caller'}]}
    selections = [Selection('source.cdl', 'a' * 64)]
    original = RunRequest('run', 'lineage', 'key', '/fixture/site.yaml', selections,
                          raw_descriptor=descriptor)
    descriptor['selection'][0]['declared'] = 'mutated'
    selections.clear()
    assert original.raw_descriptor['selection'][0]['declared'] == 'caller'
    assert len(original.raw_input_selections) == 1
    assert original.raw_descriptor_digest and original.selection_digests
    before = original.digest
    for key, value in {
        'proposed_run_id': 'other', 'lineage_id': 'other', 'idempotency_key': 'other',
        'site_path': '/other/site.yaml', 'expected_state_head': 'head',
        'raw_input_selections': (), 'raw_descriptor': FrozenMap({'changed': True}),
        'requested_mode': 'calibre', 'execution_mode': 'explicit_partial',
    }.items():
        assert replace(original, **{key: value}).digest != before
    assert record_digest(decode_record(encode_record(original))) == before
    for name in ('canonical_context', 'target_id', 'tech_id', 'evidence_id'):
        assert not hasattr(original, name)
    with pytest.raises((FrozenInstanceError, TypeError)):
        original.raw_descriptor['selection'][0]['declared'] = 'other'


@pytest.mark.parametrize('path', ['site.yaml', './site.yaml', '//host/site', 'C:\\site.yaml', '/bad\x00site'])
def test_request_rejects_implicit_or_ambiguous_site_path(path):
    with pytest.raises(ValueError):
        request(site_path=path)


def test_wire_rejects_unknown_version_fields_discriminator_and_derived_hash():
    source = SourceFile('bytes', b'hello')
    assert decode_record(encode_record(source)) == source
    wire = decode(encode_record(source))
    body = dict(wire['value']['fields'])
    for key, value in [('extra', {'scalar': 'not allowed'}), ('sha256', {'scalar': 'b' * 64})]:
        modified = dict(body)
        modified[key] = value
        malformed = canonical_bytes({'wire_schema': wire['wire_schema'],
                                     'value': {'record': 'SourceFile', 'fields': modified}})
        with pytest.raises(ValueError):
            decode_record(malformed)
    with pytest.raises(ValueError):
        replace(request(), schema_version='future/2')
    malformed = canonical_bytes({'wire_schema': 'future/2', 'value': wire['value']})
    with pytest.raises(ValueError):
        decode_record(malformed)
    # User exact payloads may resemble tags without being interpreted as records.
    req = request(raw_descriptor=freeze_map({'record': 'RunAttempt', 'fields': {'danger': True}}))
    assert decode_record(encode_record(req)) == req


def test_create_stable_identity_response_loss_and_operation_replay_precede_phase_guard():
    fired = set()
    def inject(point):
        if point == 'create.after_switch' and point not in fired:
            fired.add(point)
            raise OSError('create response lost')
    repository = PublicationRepository(fault_injector=inject)
    req = request()
    with pytest.raises(OSError, match='response lost'):
        repository.create_attempt(req)
    first = repository.load_attempt(req.run_id)
    assert first.revision == 0
    assert repository.create_attempt(req) == first
    checkpoint = repository.record_audits(req.run_id, **audit_args())
    terminal = repository.finalize_precontext_failure(checkpoint.finalize_request)
    assert repository.load_attempt(req.run_id).phase == 'terminal'
    assert repository.create_attempt(req) == first
    assert repository.record_audits(req.run_id, **audit_args()) == checkpoint
    assert repository.finalize_precontext_failure(checkpoint.finalize_request) == terminal
    assert repository.snapshot().generation == 3
    conflict('IdempotencyConflict', repository.create_attempt, replace(req, lineage_id='other'))
    conflict('TransitionConflict', repository.record_audits, req.run_id,
             **dict(audit_args(), idempotency_key='new', expected_revision=2))


@pytest.mark.parametrize('change,code', [
    ({'expected_state_head': 'existing-snapshot'}, 'HeadConflict'),
    ({'requested_mode': 'calibre'}, 'ModeConflict'),
    ({'execution_mode': 'explicit_partial'}, 'ModeConflict'),
])
def test_unsupported_first_create_guards_leave_no_attempt_or_content(change, code):
    repository = PublicationRepository()
    conflict(code, repository.create_attempt, request(**change))
    assert repository.snapshot().generation == 0
    assert not repository.snapshot().content_refs
    for unavailable in ('seal_context', 'initialize', 'close_stage5', 'append_partial', 'finalize_pipeline'):
        assert not hasattr(repository, unavailable)


def test_same_run_different_create_key_and_different_digest_conflict():
    repository = PublicationRepository()
    repository.create_attempt(request())
    conflict('RunConflict', repository.create_attempt, request(idempotency_key='another'))
    conflict('IdempotencyConflict', repository.create_attempt, request(site_path='/different/site'))


def test_ready_is_unsealed_and_has_only_resolvable_audits():
    repository = PublicationRepository()
    repository.create_attempt(request())
    checkpoint = repository.record_audits('run', **audit_args(success=True))
    ready = repository.read_ready('run')
    assert ready.status == 'inputs_ready' and ready.attempt.phase == 'unsealed'
    assert ready.attempt.revision == 1 and ready.attempt.terminal_ref is None
    assert repository.read_terminal('run') is None
    assert checkpoint.finalize_request is None and checkpoint.failure_ref is None
    assert ready.value == FrozenMap({'ok': True})
    for ref in checkpoint.completed + (checkpoint.ref, ready.attempt.ref):
        assert content_ref(repository.read(ref)) == ref
    assert not any(ref.kind in ('run_record', 'closure', 'pipeline_result') for ref in repository.snapshot().content_refs)
    assert decode_record(encode_record(ready)) == ready


@pytest.mark.parametrize('change,code', [
    ({'expected_revision': 1}, 'RevisionConflict'),
    ({'expected_revision': True}, 'RevisionConflict'),
    ({'failure': None}, 'ResultConflict'),
    ({'ready': True}, 'ResultConflict'),
])
def test_audit_first_request_guards_leave_only_initial_attempt(change, code):
    repository = PublicationRepository()
    repository.create_attempt(request())
    before = repository.snapshot()
    conflict(code, repository.record_audits, 'run', **dict(audit_args(), **change))
    assert repository.snapshot() == before


def test_source_parse_tool_and_failure_links_are_checked_before_publication():
    repository = PublicationRepository()
    repository.create_attempt(request())
    args = audit_args()
    original = args['parse']
    for change, code in [
        ({'tool': replace(args['tool'], run_id='other')}, 'RunConflict'),
        ({'parse': replace(original, tool_run_id='other-tool')}, 'RefConflict'),
        ({'evidence': ()}, 'RefConflict'),
        ({'failure': StageFailure('run', 'binding', 'Drift', 'wrong source', SourceRef('unknown', '0' * 64))}, 'SourceConflict'),
        ({'failure': StageFailure('other', 'parse', 'Bad', 'wrong run')}, 'RunConflict'),
    ]:
        conflict(code, repository.record_audits, 'run', **dict(args, **change))
    changed_source = SourceFile('site.yaml', b'different bytes')
    changed_event = AcquisitionEvent('site.yaml', '/fixture/site.yaml', 'read', 'success', changed_source.sha256)
    changed_tool = replace(args['tool'], sources=(changed_source,), events=(changed_event,))
    conflict('SourceConflict', repository.record_audits, 'run', **dict(args, tool=changed_tool))
    assert repository.snapshot().generation == 1


def test_checkpoint_retains_exact_finalization_request_across_storage_failure():
    fired = set()
    def inject(point):
        if point == 'finalize.before_switch' and point not in fired:
            fired.add(point)
            raise OSError('terminal storage unavailable')
    repository = PublicationRepository(fault_injector=inject)
    checkpoint = failed_checkpoint(repository)
    request_ = checkpoint.finalize_request
    before = repository.snapshot()
    with pytest.raises(OSError):
        repository.finalize_precontext_failure(request_)
    assert repository.snapshot() == before
    assert repository.read_terminal('run') is None
    recovered = repository.load_checkpoint('run')
    assert recovered == checkpoint and recovered.finalize_request == request_
    result = repository.finalize_precontext_failure(recovered.finalize_request)
    assert repository.read_terminal('run') == result
    closure = repository.read(result.closure_ref)
    assert isinstance(closure, WithRunRecordClosure)
    record = repository.read(closure.run_record_ref)
    assert isinstance(record, RunRecord)
    assert record.failure_ref == checkpoint.failure_ref
    assert record.completed == checkpoint.completed


def test_finalization_response_loss_keeps_whole_terminal_and_replays_old_revision():
    fired = set()
    def inject(point):
        if point == 'finalize.after_switch' and point not in fired:
            fired.add(point)
            raise OSError('finalize response lost')
    repository = PublicationRepository(fault_injector=inject)
    checkpoint = failed_checkpoint(repository)
    with pytest.raises(OSError):
        repository.finalize_precontext_failure(checkpoint.finalize_request)
    terminal = repository.read_terminal('run')
    assert terminal is not None
    assert repository.finalize_precontext_failure(checkpoint.finalize_request) == terminal
    assert repository.load_attempt('run').revision == 2
    conflict('IdempotencyConflict', repository.finalize_precontext_failure,
             replace(checkpoint.finalize_request, expected_revision=99))


def test_finalize_guards_wrong_revision_ref_and_frozen_decision():
    repository = PublicationRepository()
    checkpoint = failed_checkpoint(repository)
    original = checkpoint.finalize_request
    conflict('RevisionConflict', repository.finalize_precontext_failure, replace(original, expected_revision=0))
    conflict('RefConflict', repository.finalize_precontext_failure,
             replace(original, failure_ref=ContentRef('stage_failure', 'run', '0' * 64)))
    conflict('CheckpointConflict', repository.finalize_precontext_failure,
             replace(original, idempotency_key='different-finalize'))
    assert repository.read_terminal('run') is None
    with pytest.raises(ValueError):
        replace(original, failure_ref=ContentRef('stage_failure', 'other', '0' * 64))


def test_freeze_failure_is_the_only_no_runrecord_closure_and_retains_original_cause():
    def inject(point):
        if point == 'finalize.freeze':
            try:
                raise ValueError('construction root cause')
            except ValueError as exc:
                raise RuntimeError('record freeze failed') from exc
    repository = PublicationRepository(fault_injector=inject)
    checkpoint = failed_checkpoint(repository)
    result = repository.finalize_precontext_failure(checkpoint.finalize_request)
    closure = repository.read(result.closure_ref)
    assert isinstance(closure, RunRecordFreezeFailureClosure)
    assert closure.failure_ref == checkpoint.failure_ref and closure.completed == checkpoint.completed
    failure = repository.read(closure.freeze_failure_ref)
    assert failure.category == failure.stage == 'run_record_freeze'
    assert [c.exception_type for c in failure.causes] == ['RuntimeError', 'ValueError']
    assert not any(ref.kind == 'run_record' for ref in repository.snapshot().content_refs)
    assert result.deployment_disposition == 'reject'
    assert repository.finalize_precontext_failure(checkpoint.finalize_request) == result


@pytest.mark.parametrize('interrupt', [KeyboardInterrupt, SystemExit])
def test_repository_does_not_swallow_interrupts_or_publish_half_freeze(interrupt):
    def inject(point):
        if point == 'finalize.freeze':
            raise interrupt('stop')
    repository = PublicationRepository(fault_injector=inject)
    checkpoint = failed_checkpoint(repository)
    before = repository.snapshot()
    with pytest.raises(interrupt):
        repository.finalize_precontext_failure(checkpoint.finalize_request)
    assert repository.snapshot() == before
    assert repository.read_terminal('run') is None


def test_multithread_same_requests_publish_once_and_conflicting_create_has_one_winner():
    repository = PublicationRepository()
    with ThreadPoolExecutor(max_workers=8) as pool:
        attempts = list(pool.map(lambda _: repository.create_attempt(request()), range(16)))
    assert len({a.ref for a in attempts}) == 1
    checkpoint = repository.record_audits('run', **audit_args())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: repository.finalize_precontext_failure(checkpoint.finalize_request), range(16)))
    assert len({r.ref for r in results}) == 1
    assert repository.snapshot().generation == 3
    competing = PublicationRepository()
    def create(index):
        try:
            return competing.create_attempt(request(lineage_id=f'lineage-{index}'))
        except RepositoryConflict as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=8) as pool:
        winners = list(pool.map(create, range(16)))
    assert sum(isinstance(v, RunAttempt) for v in winners) == 1
    assert winners.count('IdempotencyConflict') == 15
    assert competing.snapshot().generation == 1


def test_reader_cannot_observe_staged_runrecord_or_terminal_before_root_switch():
    entered, release, reader_started = Event(), Event(), Event()
    def inject(point):
        if point == 'finalize.before_switch':
            entered.set()
            assert release.wait(5)
    repository = PublicationRepository(fault_injector=inject)
    checkpoint = failed_checkpoint(repository)
    before = repository.snapshot()
    assert not any(r.kind in ('run_record', 'closure', 'pipeline_result') for r in before.content_refs)
    def read_snapshot():
        reader_started.set()
        return repository.snapshot()
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(repository.finalize_precontext_failure, checkpoint.finalize_request)
        assert entered.wait(5)
        reader = pool.submit(read_snapshot)
        assert reader_started.wait(5)
        assert not reader.done()
        release.set()
        result = writer.result(timeout=5)
        after = reader.result(timeout=5)
    assert after.attempts[0].terminal_ref == result.ref
    assert {'run_record', 'closure', 'pipeline_result'} <= {r.kind for r in after.content_refs}
    assert before.attempts[0].terminal_ref is None


def test_dependency_direction_and_no_builtin_hash_as_content_identity():
    repository_root = Path(__file__).resolve().parents[2]
    for relative in ('layauto_v2/domain/publication.py', 'layauto_v2/domain/publication_codec.py',
                     'layauto_v2/repository/publication.py'):
        tree = ast.parse((repository_root / relative).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != 'hash'
            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                assert not module.startswith(('layauto_v2.importers', 'layauto_v2.tooling',
                                               'layauto_v2.transactions', 'legacy_mvp', 'tests'))
            if '/domain/' in relative and isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or '']
                assert not any(name.startswith(('os', 'pathlib', 'subprocess', 'threading')) for name in names)


def test_canonical_record_identity_is_stable_across_process_hash_seeds():
    import os
    import subprocess
    import sys
    program = "from layauto_v2.domain.publication import RunRequest,Selection; print(RunRequest('run','lineage','key','/fixture/site',raw_input_selections=(Selection('source.cdl','a'*64),),raw_descriptor={'nested':[1,{'字':'值'}]}).digest)"
    repo = Path(__file__).resolve().parents[2]
    outputs = [subprocess.check_output([sys.executable, '-B', '-c', program], cwd=repo,
                                      env=dict(os.environ, PYTHONHASHSEED=seed), text=True).strip()
               for seed in ('1', '88888')]
    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == 64


@pytest.mark.parametrize('constructor', [
    lambda: ContentRef('unknown', 'run', '0' * 64),
    lambda: Selection('source', 'not-a-sha256'),
    lambda: RunRequest('run', 'lineage', 'key', '/site', [Selection('dup')], [Selection('dup')]),
    lambda: RunAttempt(request(), phase='sealed_open'),
    lambda: RunAttempt(request(), phase='terminal'),
    lambda: AcquisitionEvent('source', '/source', 'read', 'success'),
    lambda: AcquisitionEvent('source', '/source', 'probe', 'present', '0' * 64),
    lambda: AcquisitionEvent('source', '/source', 'read', 'error'),
    lambda: ToolRunResult('run', 'tool', (), (), mode='calibre'),
    lambda: ToolRunResult('run', 'tool', (SourceFile('source', b'read'),), ()),
    lambda: ToolRunResult('run', 'tool', (), (), execution_status='error'),
    lambda: StageFailure('run', 'internal', 'Bug', 'a bug'),
    lambda: StageFailure('run', 'run_record_freeze', 'Freeze', 'failed', causes=(ExceptionCause('Error', ''),)),
    lambda: RunRecord('run', ContentRef('stage_failure', 'run', '0' * 64), (), status='success'),
    lambda: PipelineResult('run', ContentRef('closure', 'run', '0' * 64), deployment_disposition='accept'),
])
def test_runtime_contracts_reject_illegal_combinations(constructor):
    with pytest.raises(ValueError):
        constructor()


@pytest.mark.parametrize('point', ['create.before_switch', 'audits.before_switch'])
def test_pre_switch_failure_leaves_no_half_records(point):
    def inject(actual):
        if actual == point:
            raise OSError('write unavailable')
    repository = PublicationRepository(fault_injector=inject)
    before = repository.snapshot()
    if point.startswith('create'):
        with pytest.raises(OSError):
            repository.create_attempt(request())
    else:
        repository.create_attempt(request())
        before = repository.snapshot()
        with pytest.raises(OSError):
            repository.record_audits('run', **audit_args())
        assert repository.load_checkpoint('run') is None
    assert repository.snapshot() == before


def test_audit_response_loss_recovers_same_checkpoint_without_reconstructing_failure():
    fired = set()
    def inject(point):
        if point == 'audits.after_switch' and point not in fired:
            fired.add(point)
            raise OSError('checkpoint response lost')
    repository = PublicationRepository(fault_injector=inject)
    repository.create_attempt(request())
    with pytest.raises(OSError):
        repository.record_audits('run', **audit_args())
    checkpoint = repository.load_checkpoint('run')
    assert checkpoint.outcome == 'failure'
    assert checkpoint.finalize_request.expected_revision == 1
    assert repository.record_audits('run', **audit_args()) == checkpoint
    result = repository.finalize_precontext_failure(checkpoint.finalize_request)
    assert repository.read_terminal('run') == result
