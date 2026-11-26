"""Independent comparison with original GDS stream positions, integer XY and explicit axes."""
import json
import struct
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2, prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.layer_checks import LayerInitializationChecks
from w005_cases import copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection


def read_rectangles(source):
    """Return stream keys and bounding boxes indexed by their actual BOUNDARY byte offset."""
    data = source.read_bytes()
    cursor = 0
    records = {}
    while cursor < len(data):
        length, kind, _ = struct.unpack_from('>HBB', data, cursor)
        if kind == 8:
            start = cursor
        elif kind == 13:
            layer, = struct.unpack_from('>h', data, cursor + 4)
        elif kind == 14:
            datatype, = struct.unpack_from('>h', data, cursor + 4)
        elif kind == 16:
            points = tuple(struct.iter_unpack('>ii', data[cursor + 4:cursor + length]))
            xs, ys = zip(*points)
            records[start] = layer, datatype, (min(xs), min(ys), max(xs), max(ys))
        cursor += length
    return records


def run(parent, narrow):
    root = copy_input(parent)
    select_projection(root)
    coordinate = root / COORDINATE_URI
    copyfile(Path(__file__).with_name('layer-discretization.synthetic.yaml'), coordinate)
    config = yaml.safe_load(coordinate.read_bytes())
    layers = config['coordinate_projection']['layers']
    if narrow:
        layers['M1']['x_edges']['cells'] = 2
        coordinate.write_text(yaml.safe_dump(config))
    rebind(root)
    source = read_rectangles(root / 'source.gds')
    by_name = {d['name']: d['stream_key'] for d in json.loads((root / 'tech/drawn.json').read_bytes())['layers']}
    repo = PublicationRepository()
    ready = prepare_inputs(repo, RunRequest('review', 'review', 'create', str(root / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    before = repo.snapshot()
    state = build_proposed_initial_state(assemble_stage2(repo, ready, fragment_budget=312))
    checks = LayerInitializationChecks(state)
    assert repo.snapshot() == before and checks.candidate is state
    assert set(checks.layers) == set(by_name) and checks.passed == (not narrow)
    for name, result in checks.layers.items():
        key = by_name[name]
        offsets = sorted(off for off, (l, d, _) in source.items() if (l, d) == (key['layer'], key['datatype']))
        assert sorted(ref.byte_offset for ref in result.sources) == offsets
        assert not result.drawn_issues and result.lifecycle_passed and not result.frame_issues
        assert result.frame.source.byte_offset == 112 and result.frame.rect.bounds == source[112][2]
    axis = layers['POLY']
    first = axis['first_centre']
    centre = config['coordinate_projection']['frame_origin_nm'][0] + first['lower_edge_nm'] + first['width_nm'] // 2
    track = axis['index_range_inclusive'][0]
    strip, = state.occupancy.in_cell('POLY', track)
    assert track == -3 and centre == 60 and state.occupancy.model.layers['POLY'].centre(track) == centre
    assert strip.source.record_source.byte_offset == 432 and strip.rect.bounds == source[432][2]

    edge = layers['M1']['x_edges']
    end = edge['offset_dbu'] + edge['cells'] * edge['pitch_dbu']
    outside = sorted(off for off, (l, _, rect) in source.items() if l == by_name['M1']['layer'] and rect[2] > end)
    m1 = checks.layers['M1']
    assert sorted(d.source.record_source.byte_offset for d in m1.initialization.diagnostics
                  if d.status == 'outside_range') == outside
    if narrow:
        assert end == 32 and outside == [2352, 2416, 2480, 2544]
        assert not m1.projection_passed and m1.initialization.drawn_reconstructed == 0
        assert [name for name, row in checks.layers.items() if not row.passed] == ['M1']
    else:
        fragment, = state.occupancy.in_cell('M1', 2, 2, view='drawn')
        x0, y0, x1, y1 = source[2352][2]
        height = layers['M1']['y_edges']['pitch_dbu']
        rect = max(x0, 2 * edge['pitch_dbu']), max(y0, 2 * height), min(x1, 3 * edge['pitch_dbu']), min(y1, 3 * height)
        assert rect == fragment.rect.bounds == (32, 48, 45, 58)
        assert fragment.rect.area == (rect[2] - rect[0]) * (rect[3] - rect[1]) == 130
    print('passed', checks.passed, 'layers', len(checks.layers), 'GDS', len(source),
          'gate', (track, centre), 'M1_end', end, 'outside_offsets', outside)


if __name__ == '__main__':
    for narrow in (False, True):
        with TemporaryDirectory() as directory:
            run(Path(directory), narrow)
