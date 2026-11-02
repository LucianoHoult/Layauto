"""CR-02 recheck: empty standard exception messages need a nonempty fallback."""
import json
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.publication import RunRequest, StageFailure, ToolRunResult
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

fixture = Path(__file__).resolve().parents[4] / 'tests/fixtures/w003_m1/site_config.yaml'
repository = PublicationRepository()
request = RunRequest('empty-parse', 'lineage', 'key', str(fixture))
with patch.object(reader, 'parse_query', side_effect=RuntimeError()):
    try:
        result = prepare_inputs(repository, request)
    except Exception as exc:
        print(json.dumps({'boundary':'parse', 'raised':type(exc).__name__, 'message':str(exc)}))
    else:
        print(json.dumps({'boundary':'parse', 'result':type(result).__name__, 'terminal':repository.read_terminal(request.run_id) is not None}))

for boundary in ('create.before_switch', 'finalize.freeze'):
    def inject(point):
        if point == boundary:
            raise RuntimeError()
    repository = PublicationRepository(fault_injector=inject)
    request = RunRequest('empty-repo', 'lineage', 'key', '/fixture/site')
    try:
        if boundary == 'create.before_switch':
            result = prepare_inputs(repository, request)
        else:
            repository.create_attempt(request)
            checkpoint = repository.record_audits('empty-repo', expected_revision=0, idempotency_key='audit',
                tool=ToolRunResult('empty-repo','tool',(),()),parse=None,evidence=(),
                failure=StageFailure('empty-repo','read','MissingInput','absent',SourceRef('site')))
            result = repository.finalize_precontext_failure(checkpoint.finalize_request)
    except Exception as exc:
        print(json.dumps({'boundary':boundary, 'raised':type(exc).__name__, 'message':str(exc)}))
    else:
        print(json.dumps({'boundary':boundary, 'result':type(result).__name__}))
