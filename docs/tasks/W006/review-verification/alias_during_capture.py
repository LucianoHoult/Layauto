"""Review probe: retarget one selected symlink after its first successful read."""
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.publication import RunRequest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

fixture = Path(__file__).resolve().parents[4] / 'tests/fixtures/w003_m1'
with tempfile.TemporaryDirectory(prefix='w006-review-') as tmp:
    root = Path(tmp) / 'input'
    shutil.copytree(fixture, root)
    selected = root / 'source.cdl'
    first = root / 'source-first.cdl'
    second = root / 'source-second.cdl'
    selected.rename(first)
    shutil.copyfile(first, second)
    selected.symlink_to(first.name)
    original = Path.read_bytes
    reads = []
    def changing_read(path):
        data = original(path)
        reads.append(str(path))
        if path == first:
            selected.unlink()
            selected.symlink_to(second.name)
        return data
    repository = PublicationRepository()
    request = RunRequest('alias-run', 'alias-lineage', 'create', str(root / 'site_config.yaml'))
    try:
        with patch.object(Path, 'read_bytes', changing_read):
            result = prepare_inputs(repository, request)
        outcome = {'returned': type(result).__name__}
    except Exception as exc:
        outcome = {'raised': type(exc).__name__, 'message': str(exc)}
    outcome['phase'] = repository.load_attempt(request.run_id).phase
    outcome['checkpoint'] = repository.load_checkpoint(request.run_id) is not None
    outcome['terminal'] = repository.read_terminal(request.run_id) is not None
    outcome['cdl_reads'] = [Path(x).name for x in reads if x.endswith('.cdl')]
    print(json.dumps(outcome, indent=2))
