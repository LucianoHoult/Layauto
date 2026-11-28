"""Full-cell T06/T07 observations on separately bound and published snapshots."""
import json
import struct

import pytest

from layauto_v2.constraints import check_m1_spacing, check_spacing
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import read_json, rebind, write_json
from w010_cases import append_records
from w023_cases import capture
from w025_cases import stage_spacing


T06, T07 = 'T06.li_spacing', 'T07.m1_spacing'


def published_query(root):
    repo = PublicationRepository()
    run = 'spacing'
    _, request = capture(repo, root, run, lineage=run, budget=400)
    publish_stage2(repo, request)
    attempt = repo.load_attempt(run)
    before = repo.snapshot()
    ctx = open_constraint_context(repo, run, attempt.context_ref)
    report = check_spacing(ctx)
    assert report.version == ctx.version and report.version.version == 0
    assert report.catalog == ctx.catalog
    t07 = report.for_rule(T07)
    assert t07.status == 'pass' and min(p.distance_squared_nm2 for p in t07.pairs) == 25
    assert check_m1_spacing(ctx).for_rule(T07) == t07
    assert tuple(c.rule.id for c in report.checks) == tuple(r.id for r in ctx.catalog.rules)
    assert [c.status for c in report.checks if c.rule.id not in (T06, T07)] == ['pending'] * 8
    assert repo.load_attempt(run) == attempt and attempt.phase == 'sealed_open'
    assert repo.snapshot() == before
    files = {s.uri: s for s in repo.read(ctx.version.tool_ref).sources}
    return ctx, files, report.for_rule(T06)


def gds_bounds(gds, offset):
    assert gds.data[offset:offset + 4] == b'\x00\x04\x08\x00'
    xy = struct.unpack_from('>10i', gds.data, offset + 20)
    assert xy[:2] == xy[-2:]
    return min(xy[::2]), min(xy[1::2]), max(xy[::2]), max(xy[1::2])


@pytest.mark.parametrize(('gap', 'threshold'), [(2, 2), (1, 2), (2, 3)])
def test_published_full_cell_spacing(tmp_path, gap, threshold):
    root = stage_spacing(tmp_path, gap, threshold)
    ctx, files, check = published_query(root)
    gds, rules = files['source.gds'], files['tech/rules.json']
    # Both equality and changed-threshold cases must use the original 2 nm GDS bytes.
    if gap == 2:
        assert gds.sha256 == '7d25599e5deb32ff67c4f5b7ac3b9b84fa931b56131170494ff659fc25fadec3'
    if threshold == 3:
        assert rules.sha256 == '65c8ecd3bc0c168f6e5d505561d6467a57dc38f5f9409684bd834dbe956a647d'
    row = json.loads(rules.data)['rules'][5]
    assert check.rule.location('parameters/min_distance_nm') == rules.ref(field='/rules/5/parameters/min_distance_nm')
    assert (check.rule.id, row['unit'], row['parameters']['min_distance_nm'], check.threshold_nm) == (T06, 'nm', threshold, threshold)
    assert check.status == ('pass' if gap >= threshold else 'violation')
    closest = min(check.pairs, key=lambda p: p.distance_squared_nm2)
    assert (closest.distance_nm, closest.dx_dbu, closest.dy_dbu) == (gap, gap, 0)
    assert check.violations == (() if gap >= threshold else (closest,))

    geo = ctx.snapshot.state['geometry']
    left, right = sorted((closest.first, closest.second), key=lambda w: w.rect.x0)
    assert (left.rect.bounds, right.rect.bounds) == ((130, 20, 139, 24), (139 + gap, 20, 150, 24))
    assert left.region_id != right.region_id and left.record_id == right.record_id
    assert left.piece_id != right.piece_id and left.source == right.source
    assert left.source.byte_offset == 2672 and gds_bounds(gds, 2672) == (130, 20, 150, 24)
    assert left.cuts == right.cuts
    cut, = left.cuts
    assert cut.source.byte_offset == 2736 and (cut.source.uri, cut.source.sha256) == (gds.uri, gds.sha256)
    assert gds_bounds(gds, 2736) == cut.rect.bounds == (139, 18, 139 + gap, 26)
    assert geo['records'][cut.record_id]['layer'] == 'CUT'
    fragments = [f for f in ctx.snapshot.state['occupancy'] if f['view'] == 'effective' and f['record_id'] == left.record_id]
    assert {f['indices'] for f in fragments} == {(4, 1)}
    assert {f['rect'] for f in fragments} == {left.rect.bounds, right.rect.bounds}

    # Each unordered region pair occurs once. Identify the old LI by its GDS
    # offset and the two islands by their distinct X bounds at a shared offset.
    distances = {}
    for pair in check.pairs:
        locations = []
        for w in (pair.first, pair.second):
            owner = geo['records'][w.record_id]
            assert owner['layer'] == 'LI' and owner['rect'] == gds_bounds(gds, w.source.byte_offset)
            assert (w.source.uri, w.source.sha256) == (gds.uri, gds.sha256)
            assert w.region_id in geo['effective_by_record'][w.record_id]['region_ids']
            region = geo['regions'][w.region_id]
            assert (region['owner_id'], region['contributors']) == (w.record_id, tuple(c.record_id for c in w.cuts))
            piece = geo['pieces'][w.piece_id]
            assert piece['region_ref']['sha256'] == w.region_id and piece['rect'] == w.rect.bounds
            name = {1648: 'A', 1712: 'B', 1776: 'C', 2672: 'L' if w.rect.x0 == 130 else 'R'}[w.source.byte_offset]
            locations.append(name)
        distances[''.join(sorted(locations))] = pair.distance_squared_nm2
    assert len(check.pairs) == 10
    assert distances == {
        'AB': 75**2, 'AC': 50**2, 'BC': 50**2, 'LR': gap**2,
        'AL': 96**2 + 6**2, 'AR': (105 + gap)**2 + 6**2,
        'BL': 96**2 + 106**2, 'BR': (105 + gap)**2 + 106**2,
        'CL': 40**2 + 6**2, 'CR': (49 + gap)**2 + 6**2,
    }


def test_sealed_unsupported_li_scope_preserves_other_rules(tmp_path):
    root = stage_spacing(tmp_path, 2)
    path = root / 'tech/rules.json'
    rules = read_json(path)
    rules['rules'][5]['scope'] = 'only annotated LI regions'
    write_json(path, rules)
    rebind(root)
    ctx, files, check = published_query(root)
    assert check.status == 'indeterminate' and check.pairs == ()
    assert check.policy_action == ctx.catalog.mandatory_policy['missing_operator_or_context']
    assert check.issue.code == 'UnsupportedRuleDeclaration' and 'scope' in check.issue.message
    assert check.issue.source == files['tech/rules.json'].ref(field='/rules/5/scope')


def test_published_l_shaped_li_uses_nearest_piece(tmp_path):
    root = stage_spacing(tmp_path, 2)
    append_records(root, [
        ('LI', (130, 48, 150, 54)), ('CUT', (139, 50, 155, 56)), ('LI', (146, 57, 148, 59)),
    ])
    ctx, _, check = published_query(root)
    assert check.status == 'pass' and len(check.pairs) == 21  # seven regions
    pair, = (p for p in check.pairs if {p.first.source.byte_offset, p.second.source.byte_offset} == {2800, 2928})
    arm, neighbor = sorted((pair.first, pair.second), key=lambda w: w.source.byte_offset)
    region = ctx.snapshot.state['geometry']['regions'][arm.region_id]
    assert region['rectangles'] == ((130, 48, 139, 54), (139, 48, 150, 50))
    # Drawing bounds are just 3 nm apart. The actual lower arm is 7 nm away.
    assert (arm.rect.bounds, neighbor.rect.bounds) == ((139, 48, 150, 50), (146, 57, 148, 59))
    assert (pair.dx_dbu, pair.dy_dbu, pair.distance_nm) == (0, 7, 7)
    assert len(arm.cuts) == 1 and arm.cuts[0].source.byte_offset == 2864 and neighbor.cuts == ()
