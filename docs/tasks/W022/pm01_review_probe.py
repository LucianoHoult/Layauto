"""Independent full-run, shifted-grid witnesses for PM-01."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.layer_checks import LayerInitializationChecks
from review_probe import read_rectangles
from w005_cases import copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection


def expected_cells(bounds, x_cells):
    """Clip the captured rectangle against explicitly enumerated half-open cells."""
    x0, y0, x1, y1 = bounds
    cells = {}
    for i in range(x_cells):
        left = 4 + 11 * i
        for j in range(12):
            bottom = -3 + 17 * j
            rect = max(x0, left), max(y0, bottom), min(x1, left + 11), min(y1, bottom + 17)
            if rect[0] < rect[2] and rect[1] < rect[3]:
                cells[i, j] = rect
    return cells


def run(parent, x_cells):
    root = copy_input(parent)
    select_projection(root)
    config = yaml.safe_load(Path(__file__).with_name('layer-discretization.synthetic.yaml').read_bytes())
    config['coordinate_projection']['layers']['POLY'] = {
        'projection': '2d_cells',
        'x_edges': {'offset_dbu': 4, 'pitch_dbu': 11, 'cells': x_cells},
        'y_edges': {'offset_dbu': -3, 'pitch_dbu': 17, 'cells': 12},
    }
    coordinate = root / COORDINATE_URI
    coordinate.write_text(yaml.safe_dump(config))
    rebind(root)
    gds_path = root / 'source.gds'
    stream = read_rectangles(gds_path)
    (offset, (_, _, bounds)), = [(off, rec) for off, rec in stream.items() if rec[:2] == (3, 0)]
    assert offset == 432 and bounds == (58, 10, 62, 190)

    repo = PublicationRepository()
    ready = prepare_inputs(repo, RunRequest('pm01-review', 'pm01-review', 'create', str(root / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    before = repo.snapshot()
    state = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=335))
    checks = LayerInitializationChecks(state)
    assert repo.snapshot() == before and ready.attempt.phase == 'unsealed'
    assert repo.load_attempt(ready.run_id) == ready.attempt and repo.read_terminal(ready.run_id) is None
    gate = checks.layers['POLY']
    source, = gate.sources
    assert (source.uri, source.sha256, source.byte_offset) == ('source.gds', hashlib.sha256(gds_path.read_bytes()).hexdigest(), offset)
    assert gate.gate_track_numbers_available is False
    assert not gate.drawn_issues and gate.lifecycle_passed and not gate.frame_issues
    assert gate.frame.rect.bounds == stream[112][2]
    coordinate_ref = gate.initialization.projection.declaration
    assert coordinate_ref.field == '/coordinate_projection/layers/POLY'
    assert coordinate_ref.sha256 == hashlib.sha256(coordinate.read_bytes()).hexdigest()

    fragments = state.occupancy.for_layer('POLY', view='drawn')
    assert all(f.source.record_source == source and f in state.occupancy.in_cell('POLY', *f.indices) for f in fragments)
    expected = expected_cells(bounds, x_cells)
    area = sum(f.rect.area for f in fragments)
    if x_cells == 6:
        assert len(fragments) == len(expected) == 24 and area == 720
        assert {f.indices: f.rect.bounds for f in fragments} == expected
        assert gate.initialization.availability == 'reconstructed'
        assert gate.projection_passed and checks.passed
    else:
        # The truncated domain still overlaps the original for 1 DBU in X.
        assert len(expected) == 12 and max(rect[2] for rect in expected.values()) == 59
        assert not fragments and not gate.projection_passed and not checks.passed
        diag, = gate.initialization.diagnostics
        assert diag.status == 'outside_range' and diag.source.record_source == source
        assert diag.source.rect.bounds == bounds and gate.initialization.availability == 'incomplete'

    others = {}
    for name, row in checks.layers.items():
        if name != 'POLY':
            assert row.passed and row.gate_track_numbers_available is None
            others[name] = tuple((f.view, f.indices, f.rect.bounds, f.source.record_source, f.region_ref, f.piece_ref)
                                 for f in state.occupancy.for_layer(name))
    assert len(others) == 14
    print('x_cells', x_cells, 'global', checks.passed, 'availability', gate.initialization.availability,
          'fragments', len(fragments), 'area', area, 'GDS_offset', offset)
    return others


if __name__ == '__main__':
    with TemporaryDirectory() as full, TemporaryDirectory() as narrow:
        assert run(Path(full), 6) == run(Path(narrow), 5)
