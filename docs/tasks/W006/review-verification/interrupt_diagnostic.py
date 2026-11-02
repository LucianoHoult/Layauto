"""Review probe: diagnostics must never replace the original interruption."""
import json
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.publication import RunRequest
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

class BadMessage:
    def __str__(self):
        raise RuntimeError('diagnostic formatter failed')

fixture = Path(__file__).resolve().parents[4] / 'tests/fixtures/w003_m1/site_config.yaml'
for index, original in enumerate((SystemExit(BadMessage()), KeyboardInterrupt('\ud800'))):
    repository = PublicationRepository()
    request = RunRequest(f'interrupt-{index}', 'lineage', 'key', str(fixture))
    def broken_parser(*args, **kwargs):
        raise original
    with patch.object(reader, 'parse_query', broken_parser):
        try:
            prepare_inputs(repository, request)
        except BaseException as caught:
            print(json.dumps({'original_type':type(original).__name__,
                              'caught_type':type(caught).__name__,
                              'same_object':caught is original,
                              'checkpoint':repository.load_checkpoint(request.run_id) is not None,
                              'terminal':repository.read_terminal(request.run_id) is not None}))
