"""Check the normal cell and three independent faults on the merged Stage 3 entry."""
from pathlib import Path
from tempfile import TemporaryDirectory

from docs.tasks.W022.review_probe import read_rectangles
from docs.tasks.W026.pm01_review_probe import reachable
from w010_cases import append_records
from w026_cases import inspect_published, stage_rules


def inspect(parent: Path, with_faults: bool) -> None:
    source = stage_rules(parent, 'combined' if with_faults else 'normal')
    if with_faults:
        append_records(source, [('CUT', (83, 78, 91, 81))])
    raw = read_rectangles(source / 'source.gds')
    li, via = raw[1648][2], raw[2096][2]
    margin = min(via[0] - li[0], via[1] - li[1], li[2] - via[2], li[3] - via[3])
    metal_gap = raw[2544][2][0] - raw[2480][2][2]
    assert (margin, metal_gap) == ((-3, 4) if with_faults else (1, 5))

    run = 'pm-three' if with_faults else 'pm-normal'
    ctx, report, times = inspect_published(source, run)
    expected = {'T05.contact_enclosure', 'T07.m1_spacing', 'T08.terminal_graph'} if with_faults else set()
    assert len(report.checks) == 10
    assert all(row.status == ('violation' if row.rule.id in expected else 'pass') for row in report.checks)
    assert report.all_required_passed == (not with_faults)
    vn, = (o for o in report.for_rule('T05.contact_enclosure').observations
           if o.kind == 'local_enclosure' and o.facts['side_layer'] == 'LI'
           and o.sources[0].byte_offset == 2096)
    assert min(vn.facts['margins_nm']) == margin
    closest = min(report.for_rule('T07.m1_spacing').pairs, key=lambda p: p.distance_squared_nm2)
    assert closest.distance_nm == metal_gap
    drains, = (o for o in report.for_rule('T08.terminal_graph').observations
               if o.kind == 'local_net_connectivity' and o.facts['declared_net'] == 'Y')
    terminals = {t['device']: t for t in drains.facts['terminals'] if t['role'] == 'D'}
    assert set(terminals) == {'MN0', 'MP0'}
    start, = terminals['MN0']['node_ids']
    end, = terminals['MP0']['node_ids']
    connected = end in reachable(ctx.snapshot.state['connectivity'], start)
    assert connected == (not with_faults)
    assert drains.status == ('pass' if connected else 'violation')
    print(run, 'version', ctx.version.version, 'violations', sorted(expected), 'VN/LI nm', margin,
          'M1 gap nm', metal_gap, 'drains connected', connected, 'check seconds', times['check_s'])


if __name__ == '__main__':
    for faults in (False, True):
        with TemporaryDirectory() as tmp:
            inspect(Path(tmp), faults)
