"""Publish with a declared coordinate on an empty layer and check exact readback."""
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, publish_stage2
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.layer_checks import LayerInitializationChecks
from w005_cases import rebind, write_json
from w018_cases import COORDINATE_URI
from w023_cases import capture, sample


def run(parent, exponent):
    root = sample(parent)
    owner = root / COORDINATE_URI
    config = yaml.safe_load(owner.read_bytes())
    d = 10**exponent
    first = {'basis': 'lower_edge_plus_half_width',
             'lower_edge_nm': {'numerator': '1', 'denominator': str(d)},
             'width_nm': {'numerator': '1', 'denominator': str(d + 1)}}
    config['coordinate_projection']['layers']['BTAP_N'] = {
        'projection': '1d_track', 'index_axis': 'y', 'pitch_nm': 10,
        'first_centre': first, 'index_range_inclusive': [0, 17]}
    write_json(owner, config)
    rebind(root)
    repo = PublicationRepository()
    ready, request = capture(repo, root, 'pm-w023')
    before = repo.snapshot()
    state = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=312))
    checks = LayerInitializationChecks(state)
    axis = state.occupancy.model.layers['BTAP_N']
    expected = Fraction(1, d) + Fraction(1, 2 * (d + 1))
    assert axis.centre(0) == expected
    assert checks.passed and len(checks.layers) == 15 and len(state.occupancy.fragments) == 312
    assert checks.layers['BTAP_N'].initialization.availability == 'no_local_records'
    assert before == repo.snapshot()
    print('exponent', exponent, 'configuration_bytes', owner.stat().st_size,
          'all_layers_pass', checks.passed, 'fragments', len(state.occupancy.fragments),
          'centre_denominator_bits', expected.denominator.bit_length(), flush=True)
    del state, checks, axis
    try:
        context = publish_stage2(repo, request)
    except Exception as exc:
        attempt = repo.load_attempt(ready.run_id)
        print(type(exc).__name__, str(exc), 'head', repo.load_head('L'), 'attempt', attempt.phase,
              attempt.revision, 'repository_unchanged', before == repo.snapshot(), flush=True)
        raise
    snapshot = repo.read(repo.read(context.head_ref).snapshot_ref)
    result = snapshot.state['coordinates']['axes']['BTAP_N']
    assert result['first_centre_nm'] == expected
    assert repo.load_attempt(ready.run_id).phase == 'sealed_open'
    print('version', snapshot.version, 'exact coordinate readback', True, flush=True)


if __name__ == '__main__':
    import sys
    with TemporaryDirectory() as tmp:
        run(Path(tmp), int(sys.argv[1]))
