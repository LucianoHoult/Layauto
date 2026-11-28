"""Independent W025 oracle for the full-height vertical cut in the two sample drawings.

Run from the repository root with PYTHONPATH=.:tests/contracts:docs/tasks/W024.
The W024 review probe supplies an independent raw GDS reader and closed-interval
integer lattice search. Neither uses a product geometry or spacing function.
"""
import argparse
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pm_inputs import stage_gap
from review_probe import axis_measure, read_metal
from w005_cases import FIXTURE, read_json, rebind, write_json


def original_geometry(root, gds_path):
    site = json.loads((root / 'site_config.yaml').read_bytes())
    owners = json.loads((root / site['tech_ref']).read_bytes())['owners']
    layers = json.loads((root / owners['drawn']['path']).read_bytes())['layers']
    contract = json.loads((root / owners['formats']['path']).read_bytes())['unit_scale_contract']
    raw = gds_path.read_bytes()
    shapes = {}
    for layer in layers:
        name = layer['name']
        if name in ('LI', 'CUT', 'M1'):
            scale, shapes[name] = read_metal(raw, layer['stream_key'], contract)
            assert scale == 1
    (cut_offset, (_, cut)), = shapes['CUT'].items()
    # Key each resulting rectangle by its *drawn* offset and physical bounds.
    li = []
    for offset, (_, rect) in shapes['LI'].items():
        x, y, r, t = rect
        l, b, h, u = cut
        if l >= r or x >= h or b >= t or y >= u:
            li.append((offset, rect))
        else:
            assert x < l < h < r and b <= y < t <= u
            li.extend(((offset, (x, y, l, t)), (offset, (h, y, r, t))))
    m1 = [(offset, rect) for offset, (_, rect) in shapes['M1'].items()]
    return sha256(raw).hexdigest(), cut_offset, li, m1


def distances(operands):
    squared = {}
    for a, b in combinations(operands, 2):
        x, y, r, t = a[1]
        l, d, h, u = b[1]
        dx, shared_x = axis_measure(x, r, l, h)
        dy, shared_y = axis_measure(y, t, d, u)
        assert not (shared_x and shared_y)  # All pairs in these specimens are disjoint.
        squared[tuple(sorted((a, b)))] = dx * dx + dy * dy
    return squared


def check_specimen():
    root = FIXTURE / 'special/cut_islands'
    _, cut_offset, li, _ = original_geometry(FIXTURE, root / 'source.gds')
    assert cut_offset == 246 and [o for o, _ in li] == [182, 182, 310]
    spec = json.loads((root / 'spec.json').read_bytes())
    assert {a['schematic_net'] for a in spec['annotations']} == {'A'}
    assert {r for _, r in li} == {tuple(a['bbox_nm']) for a in spec['annotations']}
    expected = json.loads((root / 'oracle.json').read_bytes())
    assert sorted(distances(li).values()) == expected['all_pair_distance_squared_nm2']
    print('cut_islands LI', li, 'squared nm2', sorted(distances(li).values()))


def compare_published(root, digest, cut_offset, li, m1, threshold):
    from layauto_v2.constraints import check_m1_spacing, check_spacing
    from layauto_v2.pipeline import open_constraint_context, publish_stage2
    from layauto_v2.repository import PublicationRepository
    from w023_cases import capture

    rule_path = root / 'tech/rules.json'
    if threshold == 3:
        owner = read_json(rule_path)
        row, = (r for r in owner['rules'] if r['id'] == 'T06.li_spacing')
        row['parameters']['min_distance_nm'] = 3
        row['predicate'] = row['predicate'].replace('>=2', '>=3')
        write_json(rule_path, owner)
        rebind(root)
    rule_digest = sha256(rule_path.read_bytes()).hexdigest()
    run = 'review'
    repo = PublicationRepository()
    _, request = capture(repo, root, run, budget=400)
    publish_stage2(repo, request)
    attempt = repo.load_attempt(run)
    before = repo.snapshot()
    ctx = open_constraint_context(repo, run, attempt.context_ref)
    report = check_spacing(ctx)
    single = check_m1_spacing(ctx)
    assert single.for_rule('T06.li_spacing').status == 'pending'
    assert single.for_rule('T07.m1_spacing') == report.for_rule('T07.m1_spacing')
    assert sum(c.status == 'pending' for c in report.checks) == 8
    for rule_id, operands, limit, field in (
        ('T06.li_spacing', li, threshold, '/rules/5/parameters/min_distance_nm'),
        ('T07.m1_spacing', m1, 5, '/rules/6/parameters/min_distance_nm'),
    ):
        expected = distances(operands)
        check = report.for_rule(rule_id)
        assert len(check.pairs) == len(expected) and check.threshold_nm == limit
        ref = check.rule.location('parameters/min_distance_nm')
        assert (ref.sha256, ref.field) == (rule_digest, field)
        for pair in check.pairs:
            ends = []
            for side in (pair.first, pair.second):
                assert side.source.sha256 == digest
                offset = side.source.byte_offset
                ends.append((offset, side.rect.bounds))
                if rule_id == 'T06.li_spacing':
                    geo = ctx.snapshot.state['geometry']
                    assert side.region_id in geo['effective_by_record'][side.record_id]['region_ids']
                    assert geo['pieces'][side.piece_id]['rect'] == side.rect.bounds
                    assert geo['pieces'][side.piece_id]['region_ref']['sha256'] == side.region_id
                    assert geo['regions'][side.region_id]['owner_id'] == side.record_id
                    assert [(cut.source.sha256, cut.source.byte_offset) for cut in side.cuts] == (
                        [(digest, cut_offset)] if offset == 2672 else [])
            sq = expected.pop(tuple(sorted(ends)))
            assert pair.distance_squared_nm2 == sq
            assert pair.status == ('violation' if sq < limit ** 2 else 'pass')
        assert not expected
        print(rule_id, 'threshold', limit, 'verified pairs', len(check.pairs), 'violations', len(check.violations))
    assert repo.load_attempt(run) == attempt and repo.snapshot() == before


def check_notch():
    """Distinguish a 4 nm effective gap from the 2 nm drawn-box gap."""
    from layauto_v2.constraints import check_spacing
    from layauto_v2.pipeline import open_constraint_context, publish_stage2
    from layauto_v2.repository import PublicationRepository
    from w010_cases import append_records
    from w023_cases import capture
    from w024_cases import stage

    with TemporaryDirectory() as directory:
        root = stage(Path(directory), 'normal')
        append_records(root, [('LI', (130, 20, 150, 24)), ('CUT', (139, 22, 151, 26)),
                              ('LI', (144, 26, 148, 28))])
        repo = PublicationRepository()
        _, request = capture(repo, root, 'review-notch', budget=420)
        publish_stage2(repo, request)
        attempt = repo.load_attempt('review-notch')
        ctx = open_constraint_context(repo, attempt.run_id, attempt.context_ref)
        check = check_spacing(ctx).for_rule('T06.li_spacing')
        nearest = min(check.pairs, key=lambda p: p.distance_squared_nm2)
        assert sorted(map(len, check.operands)) == [1, 1, 1, 1, 2]
        assert len(check.pairs) == 10 and check.status == 'pass'
        assert {s.source.byte_offset for s in (nearest.first, nearest.second)} == {2672, 2800}
        assert {s.rect.bounds for s in (nearest.first, nearest.second)} == {
            (139, 20, 150, 22), (144, 26, 148, 28)}
        assert nearest.distance_squared_nm2 == 16 and nearest.distance_nm == 4
        print('notch nearest', nearest.first.rect.bounds, nearest.second.rect.bounds, 'squared nm2', 16)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', action='store_true', help='also compare all pairs from three sealed snapshots')
    parser.add_argument('--notch', action='store_true', help='also publish and check an L-shaped region')
    args = parser.parse_args()
    check_specimen()
    for gap, threshold in ((2, 2), (1, 2), (2, 3)):
        with TemporaryDirectory() as directory:
            root = stage_gap(Path(directory), gap)
            digest, cut, li, metal = original_geometry(root, root / 'source.gds')
            squared, m1_squared = distances(li), distances(metal)
            assert cut == 2736 and len(squared) == 10 and min(squared.values()) == gap ** 2
            assert min(m1_squared.values()) == 25 and len(m1_squared) == 6
            print('gap', gap, 'GDS', digest, 'LI', li, 'squared nm2', list(squared.values()),
                  'M1 squared nm2', list(m1_squared.values()))
            if args.published:
                compare_published(root, digest, cut, li, metal, threshold)
    if args.notch:
        check_notch()
