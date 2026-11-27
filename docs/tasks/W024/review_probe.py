"""Recompute the example's T07 evidence from source GDS bytes and selected owners."""
from __future__ import annotations

import argparse
import json
import struct
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[3] / 'tests/fixtures/w003_m1'
RULE = 'T07.m1_spacing'


def gds_records(raw):
    offset = index = 0
    while offset < len(raw):
        size, kind, dtype = struct.unpack_from('>HBB', raw, offset)
        assert 4 <= size <= len(raw) - offset and size % 2 == 0
        yield index, offset, kind, dtype, raw[offset + 4:offset + size]
        offset += size
        index += 1


def check_real8(encoded, nominal):
    # The two positive REAL8 scales must round to the selected nominal within half an ULP.
    assert not encoded[0] & 128 and encoded[1] >> 4
    quantum = Fraction(16) ** (encoded[0] - 64) / (1 << 56)
    value = int.from_bytes(encoded[1:], 'big') * quantum
    expected = Fraction(int(nominal['numerator']), int(nominal['denominator']))
    assert abs(value - expected) * 2 <= quantum
    return expected


def read_metal(raw, stream, contract):
    units = None
    shapes = {}
    boundary = None
    for index, offset, kind, dtype, data in gds_records(raw):
        if kind == 3:  # UNITS
            assert dtype == 5 and len(data) == 16
            check_real8(data[:8], contract['gds_units_first_nominal'])
            units = check_real8(data[8:], contract['nominal_tick_m']) * 10**9
        elif kind == 8:  # BOUNDARY
            assert boundary is None
            boundary = {'offset': offset, 'index': index}
        elif boundary is not None:
            if kind in (13, 14):  # LAYER, DATATYPE
                boundary[kind], = struct.unpack('>h', data)
            elif kind == 16:  # XY
                points = list(struct.iter_unpack('>ii', data))
                assert len(points) == 5 and points[0] == points[-1]
                xs, ys = zip(*points)
                xs, ys = sorted(set(xs)), sorted(set(ys))
                assert len(xs) == len(ys) == 2 and set(points) == set(product(xs, ys))
                boundary['bounds'] = (xs[0], ys[0], xs[1], ys[1])
            elif kind == 17:  # ENDEL
                if (boundary[13], boundary[14]) == (stream['layer'], stream['datatype']):
                    shapes[boundary['offset']] = (boundary['index'], boundary['bounds'])
                boundary = None
    assert units and boundary is None
    return units, shapes


def axis_measure(lo, hi, other_lo, other_hi):
    # For closed integer-endpoint intervals the exact minimum is attained at integer positions.
    left, right = range(lo, hi + 1), range(other_lo, other_hi + 1)
    return min(abs(x - y) for x in left for y in right), len(set(left).intersection(right))


def verify(summary):
    case = summary['run']
    assert case in ('normal', 'c14')
    replacements = {}
    if case == 'c14':
        cases = json.loads((FIXTURE / 'failures/cases.json').read_bytes())['cases']
        replacements = next(c['replacement_files'] for c in cases if c['original_id'] == 'C14')

    def read(uri):
        path = FIXTURE / ('failures/' + replacements[uri] if uri in replacements else uri)
        return path.read_bytes()

    site = json.loads(read('site_config.yaml'))
    owners = json.loads(read(site['tech_ref']))['owners']
    header = json.loads(read(site['inputs']['query_header']))
    closure = {entry['uri']: entry['sha256'] for entry in header['closure']['entries']}

    def owner(name):
        uri = owners[name]['path']
        data = read(uri)
        assert sha256(data).hexdigest() == closure[uri]
        return json.loads(data)

    rules = owner('rules')
    declared = rules['rules']
    idx, row = next((i, r) for i, r in enumerate(declared) if r['id'] == RULE)
    threshold = row['parameters']['min_distance_nm']
    t07 = summary['T07']
    threshold_source = t07['threshold_source']
    uri = owners['rules']['path']
    assert (threshold_source['uri'], threshold_source['sha256'], threshold_source['field']) == (
        uri, closure[uri], f'/rules/{idx}/parameters/min_distance_nm')
    assert (summary['rule_owner']['uri'], summary['rule_owner']['sha256'], summary['owner_schema']) == (
        uri, closure[uri], rules['schema_version'])
    assert t07['threshold_nm'] == threshold and summary['mandatory_policy'] == rules['mandatory_rule_policy']

    gds_uri = site['inputs']['gds']
    raw = read(gds_uri)
    sha = sha256(raw).hexdigest()
    assert header['layout'] == {'uri': gds_uri, 'sha256': sha}
    layer, = (x for x in owner('drawn')['layers'] if x['name'] == 'M1')
    contract = owner('formats')['unit_scale_contract']
    scale, shapes = read_metal(raw, layer['stream_key'], contract)
    by_pair = {}
    for (a, (_, first)), (b, (_, second)) in combinations(shapes.items(), 2):
        ax, ay, ar, at = first
        bx, by, br, bt = second
        dx, x_shared = axis_measure(ax, ar, bx, br)
        dy, y_shared = axis_measure(ay, at, by, bt)
        squared = (dx**2 + dy**2) * scale**2
        contact = x_shared and y_shared and (x_shared > 1 or y_shared > 1)
        status = 'same_layer_contact' if contact else 'violation' if squared < threshold**2 else 'pass'
        by_pair[(a, b)] = (squared, status, dx, dy)
    closest = min(by_pair, key=lambda p: by_pair[p][0])
    squared, status, dx, dy = by_pair[closest]
    violations = sum(result[1] == 'violation' for result in by_pair.values())
    rule_status = 'violation' if violations else 'pass'
    assert (t07['pair_count'], t07['violation_count'], t07['status']) == (len(by_pair), violations, rule_status)
    nearest = t07['nearest']
    canonical = contract['canonical_tick_nm']
    assert (nearest['dx_dbu'] * canonical, nearest['dy_dbu'] * canonical) == (dx * scale, dy * scale)
    assert (nearest['status'], nearest['distance_squared_nm2'], nearest['nm_per_dbu']) == (status, squared, canonical)
    assert nearest['distance_nm'] >= 0 and nearest['distance_nm'] ** 2 == squared
    assert sorted(w['byte_offset'] for w in nearest['records']) == list(closest)
    for w in nearest['records']:
        index, bounds = shapes[w['byte_offset']]
        assert (w['record_index'], w['uri'], w['sha256']) == (index, gds_uri, sha)
        assert [x * canonical for x in w['rect_dbu']] == [x * scale for x in bounds]
    expected = [dict(r, status=rule_status if r['id'] == RULE else 'pending', pointer=f'/rules/{i}')
                for i, r in enumerate(declared)]
    assert summary['rules'] == expected and summary['version'] == 0 and summary['phase'] == 'sealed_open'
    print(case, 'gds', sha, 'rules', closure[uri], 'pair squared nm²', [int(r[0]) for r in by_pair.values()],
          'closest', closest, 'violations', violations)
    return {pair: (values[0], values[1]) for pair, values in by_pair.items()}


def compare_published(expected):
    # This adapter only obtains the measurements under review. The oracle above uses raw files.
    from tempfile import TemporaryDirectory
    from types import SimpleNamespace

    from layauto_v2.constraints import check_m1_spacing
    from layauto_v2.pipeline import open_constraint_context, publish_stage2
    from layauto_v2.repository import PublicationRepository
    from w023_cases import capture
    from w024_cases import stage

    repo = PublicationRepository()
    contexts = {}
    for case, pairs in expected.items():
        with TemporaryDirectory() as directory:
            root = stage(Path(directory), case)
            _, request = capture(repo, root, case, lineage=case, budget=400)
            publish_stage2(repo, request)
        before = repo.snapshot()
        ctx = open_constraint_context(repo, case, repo.load_attempt(case).context_ref)
        result = check_m1_spacing(ctx).for_rule(RULE)
        actual = {tuple(sorted((p.first.source.byte_offset, p.second.source.byte_offset))):
                  (p.distance_squared_nm2, p.status) for p in result.pairs}
        assert len(result.pairs) == len(pairs) and actual == pairs
        assert repo.snapshot() == before
        contexts[case] = ctx

    normal, c14 = contexts['normal'], contexts['c14']
    crossed = SimpleNamespace(version=normal.version, catalog=normal.catalog,
                              physical=normal.physical, snapshot=c14.snapshot)
    try:
        wrong = check_m1_spacing(crossed)
    except TypeError as exc:
        assert 'published ConstraintContext' in str(exc)
        print('crossed context rejected:', exc)
    else:
        failure = wrong.for_rule(RULE)
        raise AssertionError(f'{wrong.version.snapshot_ref.id} accepted C14 with {failure.status}, '
                             f'{failure.violations[0].distance_nm} nm')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('example_json', type=Path)
    parser.add_argument('--published', action='store_true', help='publish both cases and compare every pair')
    args = parser.parse_args()
    summaries = json.loads(args.example_json.read_bytes())
    assert [s['run'] for s in summaries] == ['normal', 'c14']
    expected_pairs = {result['run']: verify(result) for result in summaries}
    if args.published:
        compare_published(expected_pairs)
