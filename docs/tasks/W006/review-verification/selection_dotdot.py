"""Review probe: normpath must not stand in for captured path identity."""
import json
import shutil
import tempfile
from pathlib import Path

from layauto_v2.domain.publication import RunRequest, Selection, InputsReady
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

fixture = Path(__file__).resolve().parents[4] / 'tests/fixtures/w003_m1'
with tempfile.TemporaryDirectory(prefix='w006-selection-review-') as tmp:
    root = Path(tmp) / 'input'
    shutil.copytree(fixture, root)
    (root / 'external/child').mkdir(parents=True)
    (root / 'external/source.cdl').write_bytes(b'not the acquired source')
    (root / 'link').symlink_to('external/child', target_is_directory=True)
    declared = 'link/../source.cdl'
    repository = PublicationRepository()
    request = RunRequest('selection-run','lineage','key',str(root / 'site_config.yaml'),
                         raw_input_selections=(Selection(declared),))
    result = prepare_inputs(repository, request)
    outcome = {'result':type(result).__name__,
               'declared_resolves':str((root / declared).resolve().relative_to(root)),
               'selected_bytes':(root / declared).read_bytes().decode()}
    if isinstance(result, InputsReady):
        tool = repository.read(result.tool_ref)
        outcome['read_uris']=[source.uri for source in tool.sources if source.uri.endswith('.cdl')]
        outcome['declared_uri_was_read']=any(event.uri == declared for event in tool.events)
    else:
        checkpoint = repository.load_checkpoint(request.run_id)
        failure = repository.read(checkpoint.failure_ref)
        outcome['failure_code'] = failure.code
        outcome['failure_uri'] = failure.source.uri
        outcome['disposition'] = result.deployment_disposition
    print(json.dumps(outcome, indent=2))
