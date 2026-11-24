"""Independent W019 review checks on temporary captures. Run from the checkout."""
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from layauto_v2.analysis import AnalysisRequest, OccupancyRequest, analyze_cell

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tests/support'), str(ROOT / 'tests/contracts')]
from analysis_inputs import load, rebind, write
from analysis_projection_inputs import COORDINATE, projected_manifest
from w005_cases import copy_input, rebind as rebind_site
from w018_cases import build_geometry_from_site, select_projection
from layauto_v2.normalization.projection import build_discrete_occupancy


def query(manifest, budget, effective=False):
    return analyze_cell(AnalysisRequest(manifest), occupancy=OccupancyRequest(budget, effective))


def wire_bounds(data, offset):
    assert data[offset:offset + 4] == b'\x00\x04\x08\x00'
    position = offset + 4
    while position < len(data):
        size, kind, _ = struct.unpack_from('>HBB', data, position)
        assert size >= 4 and kind != 17  # ENDEL
        if kind == 16:  # XY in signed stream coordinates
            points = list(struct.iter_unpack('>ii', data[position + 4:position + size]))
            assert len(points) == 5 and points[0] == points[-1]
            xs, ys = zip(*points)
            return min(xs), min(ys), max(xs), max(ys)
        position += size
    raise AssertionError('GDS record has no XY')


def main(root):
    manifest = projected_manifest(root)
    assert not (root / 'body/context.json').exists()
    data = (root / 'source.gds').read_bytes()
    owner = root / COORDINATE
    raw_owner = owner.read_bytes()
    good = query(manifest, 68, True)
    assert good.request_status == 'completed' and good.external_body.status == 'not_selected'
    index = good.occupancy.value
    table = index.model.layers
    assert index.layout is good.local.facets.drawn.value.layout
    assert index.effective is good.local.facets.effective.value
    assert index.model.coordinate_source.sha256 == sha256(raw_owner).hexdigest()
    drawn = [fragment for fragment in index.fragments if fragment.view == 'drawn']
    assert len(drawn) == 48 and len(index.fragments) == 68
    for fragment in drawn:
        loc = fragment.source.record_source
        assert (loc.uri, loc.sha256) == ('source.gds', sha256(data).hexdigest())
        x0, y0, x1, y1 = wire_bounds(data, loc.byte_offset)
        if fragment.layer in ('LI', 'M1'):
            dx, dy = {'M1': (16, 20), 'LI': (20, 10)}[fragment.layer]
            i, j = fragment.indices
            x0, y0 = max(x0, i * dx), max(y0, j * dy)
            x1, y1 = min(x1, (i + 1) * dx), min(y1, (j + 1) * dy)
        else:
            assert fragment.layer == 'FIN' and fragment.indices == ((y0 + y1 - 50) // 20,)
        assert fragment.rect.bounds == (x0, y0, x1, y1)
    wire, = index.in_cell('M1', 2, 2, view='drawn')
    assert wire_bounds(data, 2352) == (0, 48, 45, 58)
    assert wire.source.record_source.byte_offset == 2352
    assert wire.rect.area == 130 and table['M1'].cell_bounds(2, 2).bounds == (32, 40, 48, 60)
    # Make an independent W018 full-run receipt with byte-identical selected
    # owners. The legacy and the analysis header have different contracts.
    full_site = copy_input(root)
    select_projection(full_site)
    (full_site / 'tech.json').write_bytes((root / 'tech.json').read_bytes())
    rebind_site(full_site)
    full = build_discrete_occupancy(build_geometry_from_site(full_site), fragment_budget=48)
    assert full.model == index.model
    assert full.value.fragments == tuple(drawn)
    print('48 drawn fragments agree with source XY and W018 full-run entry; combined=68')

    config = load(manifest)
    config['external_body'] = {'kind': 'synthetic_context', 'uri': 'absent.json'}
    write(manifest, config)
    rebind(root)
    missing = query(manifest, 68, True)
    assert missing.request_status == 'rejected' and missing.external_body.status == 'error'
    assert missing.occupancy.value.fragments == index.fragments
    assert missing.local.receipt_ref != good.local.receipt_ref
    limited = query(manifest, 67, True)
    assert limited.occupancy.status == 'resource_limit' and limited.occupancy.required_fragments == 68
    assert limited.occupancy.value is None and limited.occupancy.exceeded_at.piece_ref is not None
    print('missing selected body preserves all 68 fragments; budget 67 locates effective piece')

    # Same actual stream with a second coordinate owner. Only the new call
    # sees pitch=15. Its x=45 endpoint lies exactly on the new right edge.
    changed = yaml.safe_load(raw_owner)
    changed['coordinate_projection']['layers']['M1']['x_edges']['pitch_dbu'] = 15
    write(owner, changed)
    stale = query(manifest, 100)
    assert stale.local is None and stale.occupancy.status == 'not_evaluated'
    assert stale.occupancy.issues[0].code == 'ClosureHashMismatch'
    rebind(root)
    current = query(manifest, 100).occupancy.value
    assert current.model.model_id != index.model.model_id
    expected = [((0, 2), 15), ((1, 2), 15), ((2, 2), 15)]
    assert [(f.indices, f.rect.x1 - f.rect.x0) for f in current.for_record(wire.record_id)] == expected
    assert current.in_cell('M1', 3, 2) == ()
    with ExitStack() as stack:
        for name in ('read_bytes', 'open', 'resolve'):
            stack.enter_context(patch.object(Path, name, side_effect=AssertionError('lookup performed IO')))
        assert [f.rect.x1 - f.rect.x0 for f in index.for_record(wire.record_id)] == [16, 16, 13]
        assert index.in_cell('M1', 2, 2, view='drawn')[0] is wire
    print('stale binding rejected; rebound pitch=15 yields 15/15/15; old index retains 16/16/13')


if __name__ == '__main__':
    with TemporaryDirectory() as temp:
        main(Path(temp))
