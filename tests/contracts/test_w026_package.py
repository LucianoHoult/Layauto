"""Assertions on real single-publication W026 inputs and the original witness bytes."""
from collections import Counter

import pytest

from docs.tasks.W022.review_probe import read_rectangles
from layauto_v2.constraints import check_m1_spacing, check_spacing
from layauto_v2.normalization.stage2 import Stage2AssemblyError
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import read_json, sha
from w023_cases import capture
from w026_cases import inspect_published, stage_rules


T05, T06, T07 = 'T05.contact_enclosure', 'T06.li_spacing', 'T07.m1_spacing'


def margins(outer, inner):
    return inner[0] - outer[0], inner[1] - outer[1], outer[2] - inner[2], outer[3] - inner[3]


def assert_legacy_rows(ctx, report):
    spacing = check_spacing(ctx)
    metal = check_m1_spacing(ctx)
    assert report.for_rule(T06) == spacing.for_rule(T06)
    assert report.for_rule(T07) == spacing.for_rule(T07) == metal.for_rule(T07)
    assert all(c.status == 'pending' for c in spacing.checks if c.rule.id not in (T06, T07))
    assert all(c.status == 'pending' for c in metal.checks if c.rule.id != T07)


def collect_causes(root, ctx, report, case):
    # Equality at one nanometre is accepted. Check connector sides against the
    # test's independent stream reader and raw body JSON even on a violation.
    t05 = report.for_rule(T05)
    local = [o for o in t05.observations if o.kind == 'local_enclosure']
    external = [o for o in t05.observations if o.kind == 'external_enclosure']
    assert Counter(o.facts['connector_layer'] for o in local) == {'CONTACT': 8, 'VIA0': 6, 'GCONTACT': 2}
    assert Counter(o.object_ids[0] for o in external) == {'TN.ext': 2, 'TP.ext': 2}
    assert {o.facts['side'] for o in external} == {'body', 'rail'}
    assert all(o.facts['threshold_nm'] == 1 for o in local + external)
    assert t05.rule.location('parameters/enclosure_nm').field == '/rules/4/parameters/enclosure_nm'

    stream = read_rectangles(root / 'source.gds')
    via, = (o for o in local if o.sources[0].byte_offset == 2096 and o.facts['side_layer'] == 'LI')
    assert via.sources[1].byte_offset == 1648
    assert via.sources[0].sha256 == via.sources[1].sha256 == sha(root / 'source.gds')
    actual = margins(stream[1648][2], stream[2096][2])
    assert tuple(via.facts['margins_nm']) == actual
    assert min(actual) == (-3 if case in ('via_enclosure', 'combined') else 1)
    edge = ctx.snapshot.state['connectivity']['edges'][via.facts['edge_id']]
    assert edge['connector_id'] == via.object_ids[0] and len(edge['endpoints']) == 2
    assert min(stream[1648][2][2], stream[2096][2][2]) - max(stream[1648][2][0], stream[2096][2][0]) > 0
    assert (via.status == 'violation') == (min(actual) < 1)
    assert [o for o in local + external if o.status == 'violation'] == ([via] if min(actual) < 1 else [])

    body = read_json(root / 'body/context.json')
    shapes = {s['id']: s['bbox'] for s in body['shapes']}
    rail, = (o for o in external if o.object_ids[0] == 'TN.ext' and o.facts['side'] == 'rail')
    rail_margins = margins(shapes['MN.ext'], shapes['TN.ext'])
    assert tuple(rail.facts['margins_nm']) == rail_margins
    assert min(rail_margins) == (1 if case == 'external_equality' else 2)
    assert rail.sources[0].uri == 'body/context.json' and rail.sources[0].field == '/shapes/4'
    assert rail.sources[1].field == '/shapes/2'
    assert rail.sources[0].sha256 == rail.sources[1].sha256 == sha(root / 'body/context.json')
    assert ctx.snapshot.state['body']['local_graph_union'] is False

    metal = report.for_rule(T07)
    closest = min(metal.pairs, key=lambda p: p.distance_squared_nm2)
    pair_offsets = tuple(sorted([closest.first.source.byte_offset, closest.second.source.byte_offset]))
    assert pair_offsets == (2480, 2544)
    assert closest.distance_nm == stream[2544][2][0] - stream[2480][2][2]
    assert closest.distance_nm == (4 if case in ('c14', 'combined') else 5)
    assert closest.first.source.sha256 == closest.second.source.sha256 == via.sources[0].sha256
    assert report.for_rule(T06).status == 'pass' and closest.status == metal.status
    return ((via.facts['side_layer'], via.sources[0].byte_offset, via.sources[1].byte_offset,
             min(actual), via.facts['threshold_nm']), (pair_offsets, closest.distance_nm, metal.threshold_nm))


def assert_rows(report, failures):
    assert len(report.checks) == 10
    assert tuple(c.rule.id for c in report.checks) == tuple(r.id for r in report.catalog.rules)
    for i, row in enumerate(report.checks):
        assert row.status == ('violation' if row.rule.id in failures else 'pass'), (row.rule.id, row.issue)
        assert row.rule.source.sha256 == report.catalog.source.sha256
        assert row.rule.source.field == f'/rules/{i}'
        if row.rule.id not in (T06, T07):
            assert row.observations and all(o.sources for o in row.observations)


def test_normal_and_four_contrasts(normal_rules, tmp_path):
    normal, report, _ = normal_rules
    assert_rows(report, set())
    assert_legacy_rows(normal, report)
    # Recreate only the input files for the independent byte-level checks.
    root = stage_rules(tmp_path / 'normal-bytes', 'normal')
    normal_via, normal_metal = collect_causes(root, normal, report, 'normal')
    local = tuple(o for o in report.for_rule(T05).observations if o.kind == 'local_enclosure')

    causes = {}
    for case, failures in [('via_enclosure', {T05}), ('external_equality', set()),
                           ('c14', {T07}), ('combined', {T05, T07})]:
        root = stage_rules(tmp_path / case, case)
        ctx, report, _ = inspect_published(root, case)
        assert_rows(report, failures)
        assert_legacy_rows(ctx, report)
        causes[case] = collect_causes(root, ctx, report, case)
        if case == 'external_equality':
            assert tuple(o for o in report.for_rule(T05).observations if o.kind == 'local_enclosure') == local
    assert causes['external_equality'] == (normal_via, normal_metal)
    assert causes['combined'] == (causes['via_enclosure'][0], causes['c14'][1])


def test_cut_gap_from_real_effective_pieces(tmp_path):
    root = stage_rules(tmp_path, 'cut_gap')
    ctx, report, _ = inspect_published(root, 'cut_gap')
    assert_rows(report, {T06})
    assert_legacy_rows(ctx, report)
    pair, = report.for_rule(T06).violations
    assert pair.distance_squared_nm2 == 1 and pair.threshold_nm == 2
    assert pair.first.source.byte_offset == pair.second.source.byte_offset == 2672
    assert pair.first.region_id != pair.second.region_id
    cut, = pair.first.cuts
    assert pair.first.cuts == pair.second.cuts and cut.source.byte_offset == 2736
    assert cut.source.sha256 == sha(root / 'source.gds')


def test_touching_external_rail_refused_before_publication(tmp_path):
    repo = PublicationRepository()
    root = stage_rules(tmp_path, 'body_enclosure')
    body = root / 'body/context.json'
    shapes = {s['id']: s['bbox'] for s in read_json(body)['shapes']}
    assert min(margins(shapes['MN.ext'], shapes['TN.ext'])) == 0
    _, request = capture(repo, root, 'zero', lineage='zero', budget=400)
    before = repo.snapshot()
    with pytest.raises(Stage2AssemblyError) as refused:
        publish_stage2(repo, request)
    assert refused.value.stage == 'terminal_relations'
    issue, = (i for i in refused.value.result.issues if i.code == 'BodyTapEnclosureFailure')
    assert (issue.source.uri, issue.source.field) == ('body/context.json', '/shapes/4')
    assert issue.source.sha256 == sha(body)
    assert repo.snapshot() == before and repo.load_head('zero') is None
