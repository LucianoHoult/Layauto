"""Stage real files in temporary directories. All transformations precede W006 capture."""
from pathlib import Path
from shutil import copyfile

from layauto_v2.domain.publication import InputsReady, RunRequest, Stage2Request
from layauto_v2.pipeline import prepare_inputs
from w005_cases import apply_case, copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE


def sample(parent: Path, *, c13=False):
    root = copy_input(parent)
    if c13:
        apply_case(root, 'unsupported_target')
    select_projection(root)
    copyfile(COMPLETE, root / COORDINATE_URI)
    rebind(root)
    return root


def capture(repo, root, run, *, head=None, lineage='L', budget=312):
    ready = prepare_inputs(repo, RunRequest(run, lineage, 'create-' + run,
                                           str(root / 'site_config.yaml'), expected_state_head=head))
    assert isinstance(ready, InputsReady), ready
    return ready, Stage2Request.from_ready(ready, idempotency_key='publish-' + run, fragment_budget=budget)
