"""Review probe: malformed exception messages still use the freeze closure."""
import json

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.publication import RunRequest, StageFailure, ToolRunResult
from layauto_v2.repository import PublicationRepository

class BadText:
    def __str__(self):
        raise ValueError('diagnostic string conversion failed')

for error in (RuntimeError(BadText()), RuntimeError('\ud800')):
    def inject(point):
        if point == 'finalize.freeze':
            raise error
    repository = PublicationRepository(fault_injector=inject)
    request = RunRequest('run', 'lineage', 'key', '/fixture/site')
    repository.create_attempt(request)
    tool = ToolRunResult('run', 'tool', (), ())
    failure = StageFailure('run', 'read', 'MissingInput', 'site absent', SourceRef('site'))
    checkpoint = repository.record_audits(
        'run', expected_revision=0, idempotency_key='audit', tool=tool, parse=None,
        evidence=(), failure=failure)
    try:
        result = repository.finalize_precontext_failure(checkpoint.finalize_request)
    except BaseException as caught:
        outcome = {'raised':type(caught).__name__}
    else:
        closure = repository.read(result.closure_ref)
        outcome = {'result':type(result).__name__, 'closure_kind':closure.closure_kind,
                   'preserved_original':closure.failure_ref == checkpoint.failure_ref}
    outcome['terminal'] = repository.read_terminal('run') is not None
    outcome['closure_count'] = sum(ref.kind == 'closure' for ref in repository.snapshot().content_refs)
    print(json.dumps(outcome))
