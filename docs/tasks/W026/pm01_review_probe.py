"""Two independent Y cuts, one between the drain contacts and one beyond both."""
from pathlib import Path
from tempfile import TemporaryDirectory

from docs.tasks.W022.review_probe import read_rectangles
from w005_cases import sha
from w010_cases import append_records
from w026_cases import inspect_published, stage_rules


def reachable(graph, start):
    neighbours = {key: set() for key in graph['nodes']}
    for edge in graph['edges'].values():
        a, b = (endpoint['sha256'] for endpoint in edge['endpoints'])
        neighbours[a].add(b)
        neighbours[b].add(a)
    visited = set()
    pending = [start]
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(neighbours[node] - visited)
    return visited


def inspect(root, run, lower_y, connected):
    gds = root / 'source.gds'
    raw = read_rectangles(gds)
    assert raw[1776][2] == (84, 30, 90, 165)
    assert [raw[i][2] for i in (1904, 2032)] == [(85, 40, 89, 44), (85, 140, 89, 144)]
    assert raw[2224][2] == (85, 92, 89, 96)
    bbox = (83, lower_y, 91, lower_y + 4)
    append_records(root, [('CUT', bbox)])
    changed = read_rectangles(gds)
    cut_offset, = changed.keys() - raw.keys()
    assert changed[cut_offset][2] == bbox and all(changed[k] == v for k, v in raw.items())
    cdl = root / 'source.cdl'
    devices = {line.split()[0]: n for n, line in enumerate(cdl.read_text().splitlines(), 1)
               if line.startswith('M') and line.split()[1] == 'Y'}
    assert set(devices) == {'MN0', 'MP0'}

    ctx, report, _ = inspect_published(root, run)
    state = ctx.snapshot.state
    graph = state['connectivity']
    drains = {}
    for row in state['terminals']:
        target = row['target']
        name = target['device_id']['name']
        if name in devices and target['role'] == 'D':
            node, = (ref['sha256'] for ref in row['node_refs'])
            component, = (ref['sha256'] for ref in row['component_refs'])
            drains[name] = node, component
            assert reachable(graph, node) == set(graph['components'][component])
    mn, mp = drains['MN0'], drains['MP0']
    assert (mp[0] in reachable(graph, mn[0])) == connected
    assert (mn[1] == mp[1]) == connected

    t08 = report.for_rule('T08.terminal_graph')
    y, = (o for o in t08.observations if o.kind == 'local_net_connectivity' and o.facts['declared_net'] == 'Y')
    located = {(t['device'], t['role']): (t['node_ids'], t['component_ids']) for t in y.facts['terminals']}
    assert located == {(name, 'D'): ((node,), (comp,)) for name, (node, comp) in drains.items()}
    assert {(s.sha256, s.line) for s in y.sources if s.uri == 'source.cdl'} == {
        (sha(cdl), line) for line in devices.values()}
    for _, component in drains.values():
        assert any(s.uri == ctx.version.snapshot_ref.id and s.field == '/connectivity/components/' + component
                   for s in y.sources)
    assert y.status == ('pass' if connected else 'violation')
    b_terms = [o for o in t08.observations if o.kind == 'terminal_relation' and o.facts['role'] == 'B']
    assert len(b_terms) == 2 and all(o.facts['domain'] == 'external_body_path' and o.status == 'pass' for o in b_terms)
    t10 = report.for_rule('T10.coverage')
    islands, = (o for o in t10.observations if o.kind == 'separate_label_islands' and o.facts['net']['name'] == 'Y')
    assert t10.status == 'pass' and islands.status == 'disclosed' and len(set(islands.object_ids)) == 2
    assert {mn[1], mp[1]} <= set(islands.object_ids)
    assert report.for_rule('T06.li_spacing').status == 'pass'
    assert len(report.checks) == 10
    assert {c.rule.id: c.status for c in report.checks if c.status != 'pass'} == (
        {} if connected else {'T08.terminal_graph': 'violation'})
    assert report.all_required_passed == connected
    print(run, 'CUT', bbox, 'T08', t08.status, 'Y drains', {name: component for name, (_, component) in drains.items()},
          'Y islands', len(islands.object_ids), 'all_required_passed', report.all_required_passed)


if __name__ == '__main__':
    for name, y0, still_connected in (('between-drains', 112, False), ('beyond-drains', 151, True)):
        with TemporaryDirectory() as tmp:
            inspect(stage_rules(Path(tmp), 'normal'), name, y0, still_connected)
