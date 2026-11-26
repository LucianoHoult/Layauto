"""Run both W022 captures from real files and print the prepublication evidence."""
import json
import platform
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import tracemalloc

from layauto_v2.state.layer_checks import LayerInitializationChecks
from w022_cases import assemble, sample


def location(ref):
    return {key: value for key, value in asdict(ref).items() if value is not None}


def run(parent, complete):
    state, repo, before = assemble(sample(parent, complete=complete), 312 if complete else 68)
    tracemalloc.start()
    start = perf_counter()
    checks = LayerInitializationChecks(state)
    elapsed = perf_counter() - start
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert repo.snapshot() == before and checks.candidate is state
    assert checks.passed == complete

    layers = {}
    index = state.occupancy
    for name, result in checks.layers.items():
        row = result.initialization
        layers[name] = {
            'passed': result.passed,
            'drawn_offsets': [s.byte_offset for s in result.sources],
            'drawn_matches': not result.drawn_issues,
            'lifecycle': row.policy.declaration['lifecycle'],
            'lifecycle_passed': result.lifecycle_passed,
            'policy_field': row.policy.source.field,
            'frame_passed': not result.frame_issues,
            'frame_offset': result.frame.source.byte_offset,
            'projection': row.projection.projection,
            'coordinate_field': row.projection.declaration.field,
            'availability': row.availability, 'projection_passed': result.projection_passed,
            'drawn_reconstructed': row.drawn_reconstructed,
            'effective_pieces': row.effective_pieces, 'effective_reconstructed': row.effective_reconstructed,
            'fragments': dict(Counter(f.view for f in index.for_layer(name))),
            'projection_issues': [i.code for i in result.projection_issues],
            'gap': asdict(row.gap) if row.gap else None,
        }
    m1, = index.in_cell('M1', 2, 2, view='drawn')
    gate = None
    if complete:
        poly, = index.in_cell('POLY', -3, view='drawn')
        gate = {'index': -3, 'centre_nm': int(index.model.layers['POLY'].centre(-3)),
                'rect_dbu': poly.rect.bounds, 'source_offset': poly.source.record_source.byte_offset}
    delta, = state.target_context.differences
    frame = checks.layers['BOUNDARY'].frame
    return {
        'passed': checks.passed, 'layers': layers, 'gds': location(state.layout.gds.sources[0]),
        'coordinate': location(index.model.coordinate_source), 'model_id': index.model.model_id,
        'drawn_owner': location(state.layout.drawn.sources[0]), 'comparator': location(checks.comparator),
        'lifecycle_operator': location(checks.lifecycle_operator), 'frame_rule': location(checks.frame_rule),
        'frame_dbu': frame.rect.bounds, 'frame_identity': frame.id.sha256,
        'attempt': repo.load_attempt('w022').ref.id, 'attempt_phase': repo.load_attempt('w022').phase,
        'checkpoint': repo.load_checkpoint('w022').ref.id, 'repository_unchanged': repo.snapshot() == before,
        'poly_track': gate, 'm1_cell_2_2': {'rect_dbu': m1.rect.bounds, 'area_dbu2': m1.rect.area,
                                            'source_offset': m1.source.record_source.byte_offset},
        'unknown_fragments': sum(f.status == 'unknown' for f in state.annotation.fragments),
        'unknown_conductor_policy': state.uncovered_conductor_policy,
        'body': {'source': location(state.body_evidence.sources[0]), 'lvs': state.body['lvs_status'],
                 'local_graph_union': state.body['local_graph_union']},
        'target_delta': [delta.operand_ref.name, delta.axis, delta.semantic_before.lexeme, delta.semantic_after.lexeme],
        'first_check': {'seconds_with_tracemalloc': elapsed, 'retained_python_bytes': retained,
                        'peak_python_bytes': peak},
    }


if __name__ == '__main__':
    report = {'python': platform.python_version(), 'platform': platform.platform()}
    for name in ('w018', 'w022'):
        with TemporaryDirectory() as directory:
            report[name] = run(Path(directory), name == 'w022')
    print(json.dumps(report, indent=2, ensure_ascii=False))
