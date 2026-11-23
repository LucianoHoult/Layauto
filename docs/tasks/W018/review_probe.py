"""Compare product fragments to individual DBU squares from the two captured streams."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from runpy import run_path
import sys
from tempfile import TemporaryDirectory

import yaml

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/contracts')]
from layauto_v2.normalization import build_effective_geometry
from layauto_v2.normalization.projection import build_discrete_occupancy
from w005_cases import copy_input, without_cache
from w009_cases import special_input
from w018_cases import SAMPLE, build_geometry_from_site, select_projection

# The W017 independent reviewer already implemented a small GDS byte/UNITS
# reader. Test helpers above only bind files and invoke the product.
old_review = run_path(str(ROOT / 'docs/tasks/W017/review/recompute.py'))
squares = old_review['pixels']
table = old_review['document']('tech/drawn.json')['layers']
stream_names = {(row['stream_key']['layer'], row['stream_key']['datatype']): row['name']
                for row in table}


def read_stream(name):
    return old_review['gds_rectangles'](name, stream_names, (Fraction(1, 1000), Fraction(1, 10**9)))


def main_capture(site):
    select_projection(site)
    geometry = build_geometry_from_site(site)
    occupancy = build_discrete_occupancy(geometry, fragment_budget=48).value
    assert occupancy is not None
    stream = read_stream('source.gds')
    counts = Counter(name for name, _, _ in stream)
    assert {row.layer: row.record_count for row in occupancy.layers} == {
        name: counts[name] for name in stream_names.values()}
    layers = yaml.safe_load(SAMPLE.read_bytes())['coordinate_projection']['layers']
    profile = old_review['document']('tech/physical.json')['fin_count_profile']
    expected = defaultdict(set)
    for layer, bounds, offset in stream:
        if layer == 'FIN':
            centre = Fraction(bounds[1] + bounds[3], 2)
            index = (centre - profile['fin_lower_edge_offset_nm']
                     - Fraction(profile['fin_width_nm'], 2)) / profile['fin_pitch_nm']
            assert index.denominator == 1
            expected[offset, (int(index),)] = squares(bounds)
        elif layer in ('M1', 'LI'):
            px, py = (layers[layer][k]['pitch_dbu'] for k in ('x_edges', 'y_edges'))
            for x, y in squares(bounds):
                expected[offset, (x // px, y // py)].add((x, y))
    actual = {}
    for fragment in occupancy.fragments:
        key = fragment.source.record_source.byte_offset, fragment.indices
        assert key not in actual
        assert fragment in occupancy.for_record(fragment.record_id)
        assert fragment in occupancy.in_cell(fragment.layer, *fragment.indices)
        actual[key] = squares(fragment.rect.bounds)
    assert actual == expected
    print('main', len(stream), 'records,', len(expected), 'source/cell pairs,',
          sum(len(coverage) for coverage in actual.values()), 'DBU²')


def islands(site):
    without_cache(site)
    special_input(site)

    def grid(model):
        li = model['layers']['LI']
        li['x_edges'].update(pitch_dbu=32, cells=5)
        li['y_edges'].update(pitch_dbu=16, cells=13)

    select_projection(site, mutate=grid)
    geometry = build_geometry_from_site(site)
    effective = build_effective_geometry(geometry)
    occupancy = build_discrete_occupancy(geometry, fragment_budget=5, effective=effective).value
    raw, = occupancy.in_cell('LI', 4, 1, view='drawn')
    lobes = occupancy.in_cell('LI', 4, 1, view='effective')
    stream = read_stream('special/cut_islands/source.gds')
    cut, = [(bounds, offset) for layer, bounds, offset in stream if layer == 'CUT']
    drawn, = [bounds for layer, bounds, offset in stream if offset == raw.source.record_source.byte_offset]
    actual = Counter(pixel for fragment in lobes for pixel in squares(fragment.rect.bounds))
    assert actual == Counter(squares(drawn) - squares(cut[0]))
    assert {geometry.layout.record(c).source.byte_offset for f in lobes for c in f.contributors} == {cut[1]}
    assert len({f.region_ref for f in lobes}) == len({f.piece_ref for f in lobes}) == 2
    assert all(f.record_id == raw.record_id for f in lobes)
    print('islands', raw.source.record_source.byte_offset, cut[1], sorted(f.rect.bounds for f in lobes))


def extreme_owner(site):
    def exact(model):
        centre = model['layers']['FIN']['first_centre']
        del centre['width_nm_ref'], centre['lower_edge_nm_ref']
        centre['lower_edge_nm'] = {'numerator': '1', 'denominator': str(10**2200)}
        centre['width_nm'] = {'numerator': '1', 'denominator': str(10**2200 + 1)}

    select_projection(site, mutate=exact)
    geometry = build_geometry_from_site(site)
    occupancy = build_discrete_occupancy(geometry, fragment_budget=30).value
    assert len(occupancy.fragments) == 30
    assert sum(d.status == 'unsupported_strip' for d in occupancy.diagnostics) == 18
    print('R1', len(occupancy.fragments), 'grid fragments, 18 unsupported strips')


if __name__ == '__main__':
    for case in (main_capture, islands, extreme_owner):
        with TemporaryDirectory() as temp:
            case(copy_input(Path(temp)))
