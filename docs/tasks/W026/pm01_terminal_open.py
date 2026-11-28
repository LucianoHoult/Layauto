"""Reproduce the Y drain open on an actual published W026 cell."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from docs.tasks.W022.review_probe import read_rectangles
from w010_cases import append_records
from w026_cases import inspect_published, stage_rules


def inspect(root: Path, expect_fixed: bool) -> None:
    gds = root / 'source.gds'
    original = read_rectangles(gds)
    assert original[1776][2] == (84, 30, 90, 165)
    append_records(root, [('CUT', (83, 78, 91, 81))])
    changed = read_rectangles(gds)
    assert all(changed[offset] == value for offset, value in original.items())
    offset, = changed.keys() - original.keys()
    assert changed[offset][2] == (83, 78, 91, 81)
    ctx, report, _ = inspect_published(root, 'pm-output-cut')
    # Use the stored W014 rows for the topology assertion, independently of
    # how Stage 3 presents this fault after the fix.
    drains = {}
    for relation in ctx.snapshot.state['terminals']:
        terminal = relation['target']
        if terminal['role'] == 'D':
            name = terminal['device_id']['name']
            component, = relation['component_refs']
            drains[name] = component['sha256']
    assert set(drains) == {'MN0', 'MP0'} and drains['MN0'] != drains['MP0']
    li = report.for_rule('T06.li_spacing')
    assert li.status == 'pass' and min(p.distance_squared_nm2 for p in li.pairs) == 9
    coverage = report.for_rule('T10.coverage')
    islands, = (o for o in coverage.observations if o.kind == 'separate_label_islands')
    assert coverage.status == 'pass' and islands.facts['net']['name'] == 'Y'
    assert set(islands.object_ids) == set(drains.values())
    terminals = report.for_rule('T08.terminal_graph')
    failures = [r.rule.id for r in report.checks if r.status != 'pass']
    print('GDS CUT offset', offset, 'LI gap 3 nm; Y drain components', drains)
    print('T08', terminals.status, 'T10', coverage.status, 'all_required_passed', report.all_required_passed)
    if expect_fixed:
        assert failures == ['T08.terminal_graph'] and terminals.status == 'violation'
        assert not report.all_required_passed
    else:
        assert not failures and report.all_required_passed, 'the original false pass was not reproduced'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-fixed', action='store_true')
    args = parser.parse_args()
    with TemporaryDirectory() as tmp:
        inspect(stage_rules(Path(tmp), 'normal'), args.expect_fixed)
