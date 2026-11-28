"""Directed W026 observations on captured whole-cell inputs."""
import pytest

from docs.tasks.W022.review_probe import read_rectangles
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from layauto_v2.transactions.initialization import InitializationRejected
from w005_cases import sha
from w008_geometry_cases import blocks, edit_geometry
from w013_cases import rewrite_net_response
from w023_cases import capture
from w026_cases import inspect_published, stage_rules
from w025_cases import stage_spacing


def test_normal_frame_fin_and_marker(normal_rules):
    _, report, _ = normal_rules
    frame, fins, coverage = (report.for_rule(k) for k in ('T01.frame', 'T02.fin_grid', 'T10.coverage'))
    assert frame.status == fins.status == coverage.status == 'pass'
    assert len(frame.observations) == 39
    rail, = (o for o in frame.observations if o.facts['bbox_dbu'] == (0, 48, 45, 58))
    assert rail.facts['side_margins_nm'] == (0, 48, 115, 142)
    assert rail.sources[0].uri == 'source.gds' and rail.sources[-1].field == '/rules/0/parameters/margin_nm'
    strips = sorted((o for o in fins.observations if o.kind == 'fin_strip'), key=lambda o: o.facts['track'])
    assert len(strips) == 18
    for i, strip in enumerate(strips):
        assert (strip.facts['lower_nm'], strip.facts['width_nm'], strip.facts['pitch_nm']) == (24 + 10*i, 2, 10)
        assert strip.facts['pitch_from_previous_nm'] == (10 if i else None)
        assert strip.facts['phase_residual_nm'] == 0
        assert strip.facts['track'] == i and strip.sources[0].byte_offset is not None
    marker, = (o for o in coverage.observations if o.kind == 'drawn_coverage' and o.facts['layer'] == 'MARKER')
    assert marker.facts['raw_retained'] and marker.status == 'disclosed' and not marker.facts['has_conductor_node']
    assert marker.sources[0].byte_offset == 2608


def test_missing_edge_track_and_extra_unannotated_marker(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    path = root / 'source.gds'
    offset, = (k for k, v in read_rectangles(path).items() if v[2] == (10, 194, 110, 196))
    prefix, elements, suffix = blocks(path.read_bytes())
    position = len(prefix)
    for i, element in enumerate(elements):
        if position == offset:
            del elements[i]
            break
        position += len(element)
    else:
        pytest.fail('last FIN element not found')
    path.write_bytes(prefix + b''.join(elements) + suffix)
    edit_geometry(root, append=[('MARKER', (149, 160, 152, 166))])
    _, report, _ = inspect_published(root, 'missing-fin')
    check = report.for_rule('T02.fin_grid')
    assert check.status == 'violation'
    failure, = (o for o in check.observations if o.status == 'violation')
    assert failure.kind == 'fin_sequence' and failure.facts['missing_ranges'] == ((17, 17),)
    assert failure.sources[0].field == '/coordinate_projection/layers/FIN'
    coverage = report.for_rule('T10.coverage')
    markers = [o for o in coverage.observations if o.kind == 'drawn_coverage' and o.facts['layer'] == 'MARKER']
    assert coverage.status == 'pass'
    assert {m.facts['bbox_dbu'] for m in markers} == {(145, 180, 150, 185), (149, 160, 152, 166)}
    assert all(m.status == 'disclosed' and m.facts['has_conductor_node'] is False for m in markers)


def test_outside_frame_rejected_at_stage2(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    edit_geometry(root, append=[('MARKER', (159, 10, 161, 12))])
    repo = PublicationRepository()
    _, request = capture(repo, root, 'outside', budget=400)
    before = repo.snapshot()
    with pytest.raises(InitializationRejected) as error:
        publish_stage2(repo, request)
    issue, = error.value.checks.layers['MARKER'].frame_issues
    assert (issue.code, issue.source.uri, issue.source.sha256, issue.source.byte_offset) == (
        'OutsideFrame', 'source.gds', sha(root / 'source.gds'), 2672)
    assert repo.snapshot() == before and repo.load_head('L') is None


def test_same_label_islands_keep_their_physical_components(tmp_path):
    root = stage_spacing(tmp_path, 2)
    rewrite_net_response(root, 'n_a', [('toy_poly', (58, 10, 62, 190)),
                                       ('toy_m1', (50, 90, 75, 98)), ('toy_li', (130, 20, 150, 24))])
    _, report, _ = inspect_published(root, 'labelled-islands')
    check = report.for_rule('T10.coverage')
    assert check.status == 'pass', check.issue
    islands, = (o for o in check.observations if o.kind == 'separate_label_islands')
    assert islands.status == 'disclosed' and islands.facts['net']['name'] == 'A'
    assert len(set(islands.object_ids)) == 3
    assert any(s.uri == 'query/raw/net_shapes_n_a.txt' for s in islands.sources)
    assert islands.sources[-1].field == '/rules/9/parameters/disconnected_label_policy'
