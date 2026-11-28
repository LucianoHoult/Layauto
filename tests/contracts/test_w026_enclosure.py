"""An actual CUT through VN's LI partner leaves a hole inside a connected region."""
from w010_cases import append_records, arrangement_enclosure
from w026_cases import inspect_published, stage_rules


def test_published_region_hole_preserves_edge_but_fails_enclosure(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    hole = (31, 52, 32, 53)
    append_records(root, [('CUT', hole)])
    ctx, report, _ = inspect_published(root, 'hole')
    check = report.for_rule('T05.contact_enclosure')
    assert check.status == 'violation', check.issue
    failure, = (o for o in check.observations if o.status == 'violation')
    assert (failure.kind, failure.facts['connector_layer'], failure.facts['side_layer']) == (
        'local_enclosure', 'VIA0', 'LI')
    cells = failure.facts['region_rectangles_dbu']
    via = failure.facts['connector_rect_dbu']
    assert via == (29, 50, 33, 54) and len(cells) > 1
    envelope = (min(r[0] for r in cells), min(r[1] for r in cells),
                max(r[2] for r in cells), max(r[3] for r in cells))
    assert arrangement_enclosure([envelope], via, 1) and not arrangement_enclosure(cells, via, 1)
    assert failure.facts['margins_nm'] is None  # A bbox margin would hide the hole.
    assert len(failure.facts['candidate_node_ids']) == 1
    assert failure.facts['edge_id'] in ctx.snapshot.state['connectivity']['edges']
    cut_id, = failure.facts['contributors']
    cut = ctx.snapshot.state['geometry']['records'][cut_id]
    assert cut['rect'] == hole and cut['layer'] == 'CUT'
    assert cut['source']['byte_offset'] == failure.sources[-1].byte_offset
