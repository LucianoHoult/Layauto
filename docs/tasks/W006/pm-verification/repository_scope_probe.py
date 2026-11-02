from dataclasses import replace
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceFile, EvidenceRecord
from layauto_v2.domain.results import EvidenceIssue, ParseResult
from layauto_v2.domain.publication import AcquisitionEvent, ToolRunResult, StageFailure, RunRequest, RunRecordFreezeFailureClosure
from layauto_v2.domain.publication_codec import content_ref, encode_record, decode_record
from layauto_v2.repository import PublicationRepository, RepositoryConflict


def checkpoint(repo, run='probe'):
    req = RunRequest(run, 'lineage', 'create-' + run, '/fixture/site.yaml')
    repo.create_attempt(req)
    source = SourceFile('site.yaml', b'{"captured": true}')
    event = AcquisitionEvent(source.uri, '/fixture/site.yaml', 'read', 'success', source.sha256)
    tool = ToolRunResult(run, run + ':tool', (source,), (event,))
    evidence = EvidenceRecord('config', FrozenMap({'captured': True}), (source.ref(),))
    issue = EvidenceIssue('parse', 'ProbeInputFailure', 'original failure', source.ref(line=1))
    parsed = ParseResult('error', None, (issue,), (evidence,), (source,), tool.tool_run_id)
    return repo.record_audits(run, expected_revision=0, idempotency_key='audit-' + run,
                             tool=tool, parse=parsed, evidence=(evidence,),
                             failure=StageFailure(run, 'parse', issue.code, issue.message, issue.source))


def reject_without_mutation(repo, code, operation):
    before = repo.snapshot()
    try:
        operation()
    except RepositoryConflict as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError('invalid operation was accepted')
    assert repo.snapshot() == before

# All changed finalization refs must still match the published frozen decision.
repo = PublicationRepository()
cp = checkpoint(repo)
reject_without_mutation(repo, 'RefConflict',
                        lambda: repo.finalize_precontext_failure(replace(cp.finalize_request, completed=())))
reject_without_mutation(repo, 'CheckpointConflict',
                        lambda: repo.finalize_precontext_failure(replace(cp.finalize_request, idempotency_key='other')))
reject_without_mutation(repo, 'RefConflict',
                        lambda: repo.read(replace(cp.failure_ref, digest='0' * 64)))
try:
    replace(cp.finalize_request, failure_ref=replace(cp.failure_ref, run_id='other'))
except ValueError:
    pass
else:
    raise AssertionError('cross-run finalization ref reached repository')
for ref in repo.snapshot().content_refs:
    record = repo.read(ref)
    assert decode_record(encode_record(record)) == record
    assert content_ref(record) == ref
print('PASS ref/hash/run guards reject without repository mutation; all stored records roundtrip')

# Fail before or after root switch and retry the exact published request.
for point in ('finalize.before_switch', 'finalize.after_switch'):
    fired = set()
    def inject(value, point=point):
        if value == point and value not in fired:
            fired.add(value)
            raise OSError('response/storage fault')
    repo = PublicationRepository(fault_injector=inject)
    cp = checkpoint(repo)
    before = repo.snapshot()
    try:
        repo.finalize_precontext_failure(cp.finalize_request)
    except OSError:
        pass
    else:
        raise AssertionError('fault injection did not execute')
    if point.endswith('before_switch'):
        assert repo.snapshot() == before and repo.read_terminal('probe') is None
    else:
        assert repo.snapshot().generation == before.generation + 1
        assert repo.read_terminal('probe') is not None
    result = repo.finalize_precontext_failure(cp.finalize_request)
    after = repo.snapshot()
    assert result.deployment_disposition == 'reject'
    assert repo.finalize_precontext_failure(cp.finalize_request) == result
    assert repo.snapshot() == after
    assert after.generation == before.generation + 1
    for ref in after.content_refs:
        assert content_ref(repo.read(ref)) == ref
print('PASS before-switch failure publishes nothing; after-switch response loss replays one atomic publication')

class HostileError(RuntimeError):
    def __str__(self):
        raise KeyboardInterrupt('diagnostic formatting interrupt')

for error in (RuntimeError(), RuntimeError('\ud800'), HostileError()):
    def inject(value, error=error):
        if value == 'finalize.freeze':
            raise error
    repo = PublicationRepository(fault_injector=inject)
    cp = checkpoint(repo)
    result = repo.finalize_precontext_failure(cp.finalize_request)
    closure = repo.read(result.closure_ref)
    assert type(closure) is RunRecordFreezeFailureClosure
    assert closure.failure_ref == cp.failure_ref
    failure = repo.read(closure.failure_ref)
    freeze_failure = repo.read(closure.freeze_failure_ref)
    assert failure.message == 'original failure'
    assert freeze_failure.causes
    assert freeze_failure.message
    assert not any(ref.kind == 'run_record' for ref in repo.snapshot().content_refs)
    assert repo.read_terminal('probe') == result
    assert decode_record(encode_record(freeze_failure)) == freeze_failure
print('PASS empty/surrogate/hostile freeze exception preserves original failure and valid no-RunRecord closure')

original_interrupt = KeyboardInterrupt('freeze interrupt')
fired = set()
def inject(value):
    if value == 'finalize.freeze' and value not in fired:
        fired.add(value)
        raise original_interrupt
repo = PublicationRepository(fault_injector=inject)
cp = checkpoint(repo)
before = repo.snapshot()
try:
    repo.finalize_precontext_failure(cp.finalize_request)
except KeyboardInterrupt as caught:
    assert caught is original_interrupt
else:
    raise AssertionError('interrupt swallowed')
assert repo.snapshot() == before
assert repo.read_terminal('probe') is None
result = repo.finalize_precontext_failure(cp.finalize_request)
assert repo.read(result.closure_ref).closure_kind == 'with_run_record'
print('PASS original freeze interrupt propagates without half-publication; frozen request remains retryable')
