"""Measure first construction and print a small witness from a W003/C13 capture."""
import json
from pathlib import Path
import platform
import resource
import sys
import tracemalloc
from tempfile import TemporaryDirectory
from time import perf_counter

from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository


def run(parent):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tests/contracts'))
    from w005_cases import apply_case
    from w007_cases import ready_copy
    from w018_cases import select_projection

    root = ready_copy(parent)
    apply_case(root, 'unsupported_target')
    select_projection(root)
    repo = PublicationRepository()
    ready = prepare_inputs(repo, RunRequest('w021-example', 'w021', 'create', str(root / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    start = perf_counter()
    facts = assemble_stage2(repo, ready, fragment_budget=68)
    assembly_s = perf_counter() - start
    tracemalloc.start()
    start = perf_counter()
    state = build_proposed_initial_state(facts)
    candidate_s = perf_counter() - start
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    delta, = state.target_context.differences
    report = {
        'python': platform.python_version(), 'platform': platform.platform(),
        'assembly_seconds': assembly_s, 'candidate_seconds_traced': candidate_s,
        'candidate_retained_python_bytes': retained, 'candidate_peak_python_bytes': peak,
        'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * (1 if sys.platform == 'darwin' else 1024),
        'attempt_before': ready.attempt.ref.id, 'attempt_after': repo.load_attempt(ready.run_id).ref.id,
        'checkpoint': ready.checkpoint_ref.id, 'terminal': repo.read_terminal(ready.run_id),
        'model_id': state.occupancy.model.model_id, 'canonical_tick_nm': state.layout.units.canonical_tick_nm,
        'li_cell_dbu2': [f.rect.area for f in state.occupancy.in_cell('LI', 1, 3, view='effective')],
        'delta': [delta.operand_ref.name, delta.axis, delta.semantic_before.lexeme, delta.semantic_after.lexeme],
        'layers': {name: {'records': row.projection.record_count, 'lifecycle': row.policy.declaration['lifecycle'],
                          'projection': row.projection.projection, 'availability': row.availability,
                          'drawn_reconstructed': row.drawn_reconstructed,
                          'effective_reconstructed': row.effective_reconstructed,
                          'effective_pieces': row.effective_pieces}
                   for name, row in state.layers.items()},
    }
    return report


if __name__ == '__main__':
    with TemporaryDirectory() as directory:
        print(json.dumps(run(Path(directory)), indent=2))
