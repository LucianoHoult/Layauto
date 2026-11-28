"""Stage 5 close, replay and failure recovery on real process-local publications."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest

from layauto_v2 import constraints, pipeline
from layauto_v2.constraints import engine
from layauto_v2.domain.publication import ContentRef, RunRequest, Stage5Request, Stage5RunRecord
from layauto_v2.domain.publication_codec import content_ref, encode_record
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w023_cases import capture, sample


def seal(repo, root, run, lineage, *, head=None):
    _, baseline = capture(repo, root, run, lineage=lineage, head=head)
    context = pipeline.publish_stage2(repo, baseline)
    request = Stage5Request.from_sealed(repo.load_attempt(run), context, idempotency_key='close')
    return request, context


@pytest.fixture(scope='module')
def baselines(tmp_path_factory):
    # Later checking runs can reuse the version-zero publication for each input.
    repo = PublicationRepository()
    samples = {}
    for lineage in ('normal', 'c13'):
        root = sample(tmp_path_factory.mktemp(lineage), c13=lineage == 'c13')
        request, context = seal(repo, root, lineage, lineage)
        samples[lineage] = root, request, context
    return repo, samples


def reusing(baselines, run, *, lineage='normal'):
    repo, samples = baselines
    root, _, origin = samples[lineage]
    request, context = seal(repo, root, run, lineage, head=origin.head_ref.id)
    return repo, request, context


def conflict(code, callback, *args):
    with pytest.raises(RepositoryConflict) as caught:
        callback(*args)
    assert caught.value.code == code


def change_live_head(repo, lineage, replacement, patch):
    # W023 publishes only version zero. Move just the live pointer between
    # preparation and close to exercise the same CAS a later ECO would face.
    heads = dict(repo._root.heads)
    heads[lineage] = replacement
    patch.setattr(repo, '_root', replace(repo._root, heads=tuple(heads.items())))


def test_unsealed_attempt_cannot_close_stage5():
    repo = PublicationRepository()
    attempt = repo.create_attempt(RunRequest('open', 'L', 'create', '/fixture/site.yaml'))
    request = Stage5Request(attempt.run_id, 'L', attempt.revision,
                            ContentRef('sealed_context', attempt.run_id, '0' * 64),
                            ContentRef('state_head', attempt.run_id, '0' * 64), 'close')
    before = repo.snapshot()
    conflict('TransitionConflict', pipeline.run_stage5, repo, request)
    assert repo.snapshot() == before and repo.replay_stage5(request) is None


def test_checked_material_is_bound_to_this_repository_run_and_version(baselines, monkeypatch):
    repo, samples = baselines
    _, req, context = samples['normal']
    _, foreign, other_context = samples['c13']
    prepared = pipeline.prepare_stage5(repo, req)
    before = repo.snapshot()
    conflict('BindingConflict', repo.close_stage5, foreign, prepared)
    with pytest.raises(ValueError):
        replace(prepared, rules=None)
    for changed in (replace(req, expected_head_ref=other_context.head_ref),
                    replace(req, lineage_id=foreign.lineage_id)):
        with pytest.raises(RepositoryConflict):
            pipeline.run_stage5(repo, changed)
    conflict('RevisionConflict', pipeline.run_stage5, repo, replace(req, expected_revision=0))
    assert repo.snapshot() == before

    other_repo = PublicationRepository()
    conflict('BindingConflict', other_repo.close_stage5, req, prepared)
    assert other_repo.replay_stage5(req) is None
    conflict('MissingAttempt', other_repo.load_attempt, req.run_id)
    conflict('RefConflict', other_repo.read, req.context_ref)

    # A stale reference of the right kind/run must not select a different context.
    stale_context = replace(req.context_ref, digest='0' * 64)
    with pytest.raises(RepositoryConflict):
        pipeline.run_stage5(repo, replace(req, context_ref=stale_context))
    assert repo.snapshot() == before

    # Injection at the repository's trusted producer boundary: even two
    # mutually consistent audits must point to the snapshot bound by the head.
    wrong_snapshot = replace(repo.read(context.head_ref).snapshot_ref, digest='1' * 64)
    binding = replace(prepared.planning.binding, snapshot_ref=wrong_snapshot)
    wrong = type(prepared)._checked(prepared.repository_scope, req,
                                    replace(prepared.planning, binding=binding),
                                    replace(prepared.rules, binding=binding))
    conflict('BindingConflict', repo.close_stage5, req, wrong)
    assert repo.snapshot() == before

    with monkeypatch.context() as patch:
        change_live_head(repo, req.lineage_id, other_context.head_ref, patch)
        before_close = repo.snapshot()
        conflict('HeadConflict', repo.close_stage5, req, prepared)
        assert repo.snapshot() == before_close
        assert repo.replay_stage5(req) is None

    # Model a concurrent revision update that keeps the attempt sealed/open.
    updated = replace(repo.load_attempt(req.run_id), revision=req.expected_revision + 1)
    attempts = dict(repo._root.attempts)
    attempts[req.run_id] = content_ref(updated)
    contents = repo._root.contents + ((content_ref(updated), encode_record(updated)),)
    with monkeypatch.context() as patch:
        patch.setattr(repo, '_root', replace(repo._root, attempts=tuple(attempts.items()), contents=contents))
        before_close = repo.snapshot()
        conflict('RevisionConflict', repo.close_stage5, req, prepared)
        assert repo.snapshot() == before_close


def test_interrupt_before_switch_response_loss_and_same_key_content(baselines, monkeypatch):
    repo, req, context = reusing(baselines, 'interrupt')
    prepared = pipeline.prepare_stage5(repo, req)
    head = repo.read(context.head_ref)
    attempt = repo.load_attempt(req.run_id)
    missing_site = baselines[1]['normal'][0] / 'missing.yaml'
    old_terminal = pipeline.prepare_inputs(repo, RunRequest('w006-failed', 'precontext', 'create', str(missing_site)))
    old_closure = repo.read(old_terminal.closure_ref)
    old_record = repo.read(old_closure.run_record_ref)
    assert old_record.status == 'precontext_failure'
    before = repo.snapshot()

    def break_evaluator(*args):
        raise RuntimeError('transient T07 evaluator fault')

    with monkeypatch.context() as patch:
        patch.setattr(engine, 'evaluate_m1', break_evaluator)
        changed_report = pipeline.prepare_stage5(repo, req)
    assert changed_report.rules.issues and not prepared.rules.issues

    # The record was successfully constructed. A write failure aborts the
    # transaction; it must not create the exceptional no-RunRecord closure.
    store = repo._put

    def unavailable(contents, record):
        if isinstance(record, Stage5RunRecord):
            raise OSError('store run record')
        return store(contents, record)

    with monkeypatch.context() as patch:
        patch.setattr(repo, '_put', unavailable)
        with pytest.raises(OSError, match='store run record'):
            repo.close_stage5(req, prepared)
    assert repo.snapshot() == before and repo.replay_stage5(req) is None

    # A fault hook can re-enter the same process's RLock at the switch.
    # Its successful mutation must survive the competing outer publication.
    nested = RunRequest('nested', 'independent-lineage', 'create', str(missing_site))

    def reenter(point):
        if point == 'close_stage5.before_switch':
            repo.create_attempt(nested)

    with monkeypatch.context() as patch:
        patch.setattr(repo, '_fault_injector', reenter)
        conflict('RootConflict', repo.close_stage5, req, prepared)
    assert repo.load_attempt(nested.run_id).request == nested and repo.load_attempt(req.run_id) == attempt
    assert repo.replay_stage5(req) is None
    assert repo.snapshot().generation == before.generation + 1
    before = repo.snapshot()

    faults = {'close_stage5.before_switch': KeyboardInterrupt, 'close_stage5.after_switch': OSError}

    def inject(point):
        if point in faults:
            raise faults.pop(point)(point)

    monkeypatch.setattr(repo, '_fault_injector', inject)
    with pytest.raises(KeyboardInterrupt, match='before_switch'):
        repo.close_stage5(req, prepared)
    assert repo.snapshot() == before and repo.replay_stage5(req) is None
    with pytest.raises(OSError, match='after_switch'):
        repo.close_stage5(req, prepared)

    after = repo.snapshot()
    assert (after.generation, after.idempotency_count) == (before.generation + 1, before.idempotency_count + 1)
    closed = repo.load_attempt(req.run_id)
    assert (closed.phase, closed.revision, closed.context_ref) == ('stage5_closed', attempt.revision + 1, attempt.context_ref)
    closure = repo.read(closed.closure_ref)
    record = repo.read(closure.run_record_ref)
    assert record.status == 'no_change' and record.head_status_at_finalization == 'current'
    assert record.final_snapshot_ref == head.snapshot_ref and record.ordered_commit_ids == ()
    assert record.binding.context_ref == attempt.context_ref
    assert record.binding.target_ref == context.target_ref
    assert repo.read(record.planning_ref) == prepared.planning and repo.read(record.rule_ref) == prepared.rules
    assert record.run_id == req.run_id and head.snapshot_ref.run_id == 'normal'
    assert repo.read(attempt.context_ref).checkpoint_ref != repo.read(head.snapshot_ref).checkpoint_ref
    assert repo.read(head.event_ref).snapshot_ref == record.final_snapshot_ref
    assert repo.read_terminal(old_terminal.run_id) == old_terminal
    assert repo.read(old_terminal.closure_ref) == old_closure and repo.read(old_closure.run_record_ref) == old_record
    assert repo.read(old_record.failure_ref).stage == 'stage1'
    assert repo.read(head.target_ref).differences == () and repo.read(context.head_ref) == head
    assert repo.load_head(req.lineage_id) == context.head_ref and repo.read_terminal(req.run_id) is None
    conflict('IdempotencyConflict', repo.close_stage5, req, changed_report)
    conflict('IdempotencyConflict', pipeline.run_stage5, repo, replace(req, expected_revision=999))
    conflict('TransitionConflict', pipeline.run_stage5, repo, replace(req, idempotency_key='another'))
    assert repo.snapshot() == after

    # Retrying after response loss never reacquires inputs or repeats a check,
    # even if the live head has since moved away from this successful snapshot.
    def unexpected(*args, **kwargs):
        pytest.fail('replay entered Stage 4/5 preparation')

    monkeypatch.setattr(pipeline, 'prepare_stage5', unexpected)
    change_live_head(repo, req.lineage_id, baselines[1]['c13'][2].head_ref, monkeypatch)
    advanced = repo.snapshot()
    assert repo.replay_stage5(req) == repo.close_stage5(req, prepared) == pipeline.run_stage5(repo, req) == closure
    assert repo.snapshot() == advanced



def test_formal_report_must_belong_to_this_run_and_cover_every_obligation(baselines, monkeypatch):
    repo, req, context = reusing(baselines, 'report-reuse')
    _, original, _ = baselines[1]['normal']
    check_rules = constraints.check_rules
    old_view = pipeline.open_constraint_context(repo, original.run_id, original.context_ref)
    old_pass = check_rules(old_view)
    assert old_pass.all_required_passed and old_pass.version.head_ref == context.head_ref
    assert old_pass.version.context_ref != req.context_ref
    before = repo.snapshot()

    with monkeypatch.context() as patch:
        patch.setattr(constraints, 'check_rules', lambda view: old_pass)
        conflict('BindingConflict', pipeline.run_stage5, repo, req)
    assert before == repo.snapshot()

    # Model an incomplete response from the formal checker on the correct
    # version: one returned obligation is pending and another row is absent.
    def incomplete(view):
        report = check_rules(view)
        rows = tuple(replace(row, status='pending', observations=()) if row.rule.id == 'T05.contact_enclosure' else row
                     for row in report.checks if row.rule.id != 'T07.m1_spacing')
        return replace(report, checks=rows)

    monkeypatch.setattr(constraints, 'check_rules', incomplete)
    closure = pipeline.run_stage5(repo, req)
    record = repo.read(closure.run_record_ref)
    audit = repo.read(record.rule_ref)
    assert record.status == 'sealed_no_publication' and repo.read(record.failure_ref).stage == 'stage5'
    assert sum(row['status'] == 'pass' for row in audit.checks) == 8
    assert any(issue.code == 'RequiredRuleNotPassed' and 'T05.contact_enclosure' in issue.message for issue in audit.issues)
    assert any(issue.code == 'IncompleteRuleReport' and 'T07.m1_spacing' in issue.message for issue in audit.issues)
    assert repo.load_head(req.lineage_id) == old_pass.version.head_ref


def test_concurrent_close_accepts_one_key(baselines):
    repo, req, _ = reusing(baselines, 'race')
    requests = (req, replace(req, idempotency_key='second'))
    work = [(r, pipeline.prepare_stage5(repo, r)) for r in requests]
    gate = Barrier(2)
    before = repo.snapshot()

    def compete(pair):
        gate.wait(timeout=30)
        try:
            return repo.close_stage5(*pair)
        except RepositoryConflict as exc:
            assert exc.code == 'TransitionConflict'
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(compete, work))
    closure, = (reply for reply in replies if reply is not None)
    assert [repo.replay_stage5(r) for r in requests] == replies
    assert repo.read(repo.load_attempt(req.run_id).closure_ref) == closure
    after = repo.snapshot()
    assert (after.generation, after.idempotency_count) == (before.generation + 1, before.idempotency_count + 1)
    assert after.heads == before.heads


@pytest.mark.parametrize('lineage', ['normal', 'c13'])
def test_runrecord_freeze_failure_preserves_completed_work(baselines, monkeypatch, lineage):
    repo, req, context = reusing(baselines, 'freeze-' + lineage, lineage=lineage)
    prepared = pipeline.prepare_stage5(repo, req)

    def inject(point):
        if point == 'close_stage5.freeze':
            raise ArithmeticError('failed to freeze RunRecord')

    monkeypatch.setattr(repo, '_fault_injector', inject)
    closure = repo.close_stage5(req, prepared)
    assert closure == repo.read(repo.load_attempt(req.run_id).closure_ref) == pipeline.run_stage5(repo, req)
    assert closure.closure_kind == 'run_record_freeze_failure'
    freeze = repo.read(closure.freeze_failure_ref)
    assert (freeze.code, freeze.stage, freeze.causes[0].message) == (
        'RunRecordFreezeFailure', 'run_record_freeze', 'failed to freeze RunRecord')
    assert freeze.completed == closure.completed
    assert not any(r.kind == 'run_record' and r.run_id == req.run_id for r in repo.snapshot().content_refs)
    assert repo.read(closure.completed[0]) == prepared.planning
    if lineage == 'normal':
        assert closure.original_failure_ref is None
        assert len(closure.completed) == 2 and repo.read(closure.completed[1]) == prepared.rules
    else:
        assert len(closure.completed) == 1
        original = repo.read(closure.original_failure_ref)
        assert original.stage == 'stage4' and original.completed == closure.completed
    assert repo.load_head(lineage) == context.head_ref and repo.read(context.head_ref).eco_commits == ()


def test_failure_can_close_when_checked_head_has_been_superseded(baselines, monkeypatch):
    repo, req, context = reusing(baselines, 'superseded', lineage='c13')
    prepared = pipeline.prepare_stage5(repo, req)
    assert prepared.planning.issues and prepared.rules is None
    checked = repo.read(context.head_ref)
    advanced = baselines[1]['normal'][2].head_ref
    change_live_head(repo, req.lineage_id, advanced, monkeypatch)
    closure = repo.close_stage5(req, prepared)
    record = repo.read(closure.run_record_ref)
    assert (record.status, record.head_status_at_finalization) == ('sealed_no_publication', 'superseded')
    assert record.binding.head_ref == context.head_ref and record.final_snapshot_ref == checked.snapshot_ref
    assert record.rule_ref is None and record.ordered_commit_ids == ()
    assert repo.read(record.failure_ref).stage == 'stage4'
    assert repo.load_head(req.lineage_id) == advanced and repo.read(context.head_ref) == checked
