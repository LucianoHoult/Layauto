"""PM combination on normal W003 inputs with two explicit coordinate owners."""

from collections import Counter
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from layauto_v2.state.layer_checks import LayerInitializationChecks
from w005_cases import rebind
from w007_cases import ready_copy
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE, assemble


def check(complete: bool) -> None:
    with TemporaryDirectory() as directory:
        root = ready_copy(Path(directory))
        select_projection(root)
        if complete:
            copyfile(COMPLETE, root / COORDINATE_URI)
            rebind(root)
        state, repo, before = assemble(root, 312 if complete else 68)
        checks = LayerInitializationChecks(state)
        assert len(checks.layers) == 15 and len(state.layout.records) == 40
        assert not state.target_context.differences
        gate = checks.layers['POLY']
        assert gate.lifecycle_passed and gate.sources[0].byte_offset == 432
        assert checks.passed is complete and gate.gate_track_numbers_available is complete
        counts = Counter(f.view for f in state.occupancy.fragments)
        if complete:
            assert counts == {'drawn': 220, 'effective': 92}
            assert state.occupancy.model.layers['POLY'].centre(-3) == 60
        else:
            assert sum(not row.passed for row in checks.layers.values()) == 10
            issue, = gate.projection_issues
            assert issue.code == 'RequiredProjectionUnavailable'
            assert issue.source.uri == COORDINATE_URI
            assert issue.source.field == '/coordinate_projection/layers/POLY'
        tip, = state.occupancy.in_cell('M1', 2, 2)
        assert tip.rect.area == 130 and tip.source.record_source.byte_offset == 2352
        attempt = repo.load_attempt('w022')
        assert (attempt.phase, attempt.revision) == ('unsealed', 1)
        assert repo.snapshot() == before and repo.read_terminal('w022') is None
        print('complete', complete, 'passed', checks.passed, 'fragments', dict(counts),
              'M1', tip.rect.area, 'target_differences', len(state.target_context.differences),
              attempt.phase, attempt.revision)


if __name__ == '__main__':
    check(True)
    check(False)
