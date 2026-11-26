"""Temporary, explicitly rebound W022 fixture selections for tests and evidence."""
from pathlib import Path
from shutil import copyfile

from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import apply_case, rebind
from w007_cases import ready_copy
from w018_cases import COORDINATE_URI, select_projection

COMPLETE = Path(__file__).resolve().parents[2] / 'docs/tasks/W022/layer-discretization.synthetic.yaml'


def sample(parent, *, complete):
    root = ready_copy(parent)
    apply_case(root, 'unsupported_target')
    select_projection(root)
    if complete:
        copyfile(COMPLETE, root / COORDINATE_URI)
        rebind(root)
    return root


def assemble(root, budget):
    repo = PublicationRepository()
    request = RunRequest('w022', 'lineage', 'create', str(root / 'site_config.yaml'))
    ready = prepare_inputs(repo, request)
    assert isinstance(ready, InputsReady), ready
    before = repo.snapshot()
    candidate = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=budget))
    assert repo.snapshot() == before
    return candidate, repo, before
