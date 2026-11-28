"""Device rule contrasts through the complete read-only entry point."""
from shutil import copyfile

import pytest

from layauto_v2.normalization.stage2 import Stage2AssemblyError
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE, rebind, sha, without_cache
from w010_cases import append_records
from w011_cases import change_cdl
from w013_cases import rewrite_net_response
from w023_cases import capture, sample
from w026_cases import inspect_published, stage_rules


def test_correct_count_wrong_target_length(tmp_path):
    root = sample(tmp_path, c13=True)
    _, report, _ = inspect_published(root, 'length')
    row = report.for_rule('T03.recognition')
    assert row.status == 'violation', row.issue
    mismatch, = (obs for obs in row.observations if obs.status == 'violation')
    assert mismatch.kind == 'device_parameter' and mismatch.object_ids[0] == 'MN0'
    assert mismatch.facts['circuit'] == 'target' and mismatch.facts['axis'] == 'channel_length'
    assert mismatch.facts['declared'] == 5 and mismatch.facts['measured'] == (4,)
    assert mismatch.sources[0].uri == 'target.cdl' and mismatch.sources[0].line == 3
    counts = [obs for obs in row.observations if obs.kind == 'qualified_fins']
    assert {obs.object_ids[0]: obs.facts['qualified_count'] for obs in counts} == {'MN0': 5, 'MP0': 7}


def test_wrong_external_rail_rejected_at_terminal_assembly(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    copyfile(FIXTURE / 'failures/body_wrong_rail/body/context.json', root / 'body/context.json')
    rebind(root)
    repo = PublicationRepository()
    _, request = capture(repo, root, 'rail', lineage='rail', budget=400)
    with pytest.raises(Stage2AssemblyError) as rejected:
        publish_stage2(repo, request)
    assert rejected.value.stage == 'terminal_relations'
    issue, = (i for i in rejected.value.result.issues if i.code == 'BodyTargetRailMismatch')
    assert issue.source.uri == 'body/context.json' and issue.source.field == '/associations/0/expected_semantic_rail'
    assert issue.source.sha256 == sha(root / issue.source.uri) and repo.load_head('rail') is None


def test_declared_drain_contrasted_with_observed_component(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    change_cdl(root, 'source', 'MN0 Y A VSS', 'MN0 VDD A VSS')
    change_cdl(root, 'target', 'MN0   Y A VSS', 'MN0   VDD A VSS')
    _, report, _ = inspect_published(root, 'drain')
    row = report.for_rule('T08.terminal_graph')
    assert row.status == 'violation', row.issue
    failures = {obs.kind: obs for obs in row.observations if obs.status == 'violation'}
    drain = failures['terminal_relation']
    # The new drain expectation also requires a connection to MP0.S on VDD.
    vdd = failures['local_net_connectivity']
    assert vdd.facts['declared_net'] == 'VDD'
    assert {(pin['device'], pin['role']) for pin in vdd.facts['terminals']} == {('MN0', 'D'), ('MP0', 'S')}
    assert drain.object_ids[:2] == ('MN0', 'D')
    assert drain.facts['observed_nets'] == ('Y',) and drain.facts['declared_net'] == 'VDD'
    assert drain.facts['component_ids'] and drain.facts['domain'] == 'local_components'
    assert drain.sources[0].uri == 'source.cdl' and drain.sources[0].line == 3
    assert any(source.uri.startswith('query/raw') for source in drain.sources)
    body = [obs for obs in row.observations if obs.facts.get('role') == 'B']
    assert {obs.facts['observed_nets'] for obs in body} == {('VSS',), ('VDD',)}
    assert all(obs.status == 'pass' and obs.facts['domain'] == 'external_body_path' for obs in body)
    assert report.for_rule('T04.body').status == 'pass'


def test_local_gate_and_drain_connections_on_normal_cell(normal_rules):
    _, report, _ = normal_rules
    assert report.all_required_passed
    terminals = report.for_rule('T08.terminal_graph')
    groups = {obs.facts['declared_net']: obs for obs in terminals.observations
              if obs.kind == 'local_net_connectivity'}
    assert set(groups) == {'A', 'Y'}
    for net, role in (('A', 'G'), ('Y', 'D')):
        obs = groups[net]
        assert obs.status == 'pass'
        component, = obs.facts['component_ids']
        assert {(pin['device'], pin['role'], pin['component_ids']) for pin in obs.facts['terminals']} == {
            ('MN0', role, (component,)), ('MP0', role, (component,))}
    body = [obs for obs in terminals.observations if obs.facts.get('role') == 'B']
    assert {obs.object_ids[0] for obs in body} == {'MN0', 'MP0'}
    assert all(obs.facts['domain'] == 'external_body_path' for obs in body)


def test_cut_between_output_drains_breaks_the_required_connection(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    append_records(root, [('CUT', (83, 78, 91, 81))])
    ctx, report, _ = inspect_published(root, 'open-output')
    assert not report.all_required_passed
    assert [row.rule.id for row in report.checks if row.status != 'pass'] == ['T08.terminal_graph']
    row = report.for_rule('T08.terminal_graph')
    assert row.status == 'violation', row.issue
    failure, = (obs for obs in row.observations if obs.status == 'violation')
    assert failure.kind == 'local_net_connectivity' and failure.facts['declared_net'] == 'Y'
    pins = {(pin['device'], pin['role']): pin for pin in failure.facts['terminals']}
    assert set(pins) == {('MN0', 'D'), ('MP0', 'D')}

    # Resolve each W014 drain's W010 nodes directly against the published graph.
    # Both retain the expected name in W013, so a name-only check would pass.
    graph = ctx.snapshot.state['connectivity']['components']
    resolved = set()
    for relation in ctx.snapshot.state['terminals']:
        target = relation['target']
        key = target['device_id']['name'], target['role']
        if key not in pins:
            continue
        pin = pins[key]
        nodes = {ref['sha256'] for ref in relation['node_refs']}
        assert nodes and set(pin['node_ids']) == nodes
        component, = [component for component, members in graph.items() if nodes <= set(members)]
        assert pin['component_ids'] == (component,)
        resolved.add(component)
        individual, = (o for o in row.observations if o.kind == 'terminal_relation' and o.object_ids[:2] == key)
        assert individual.status == 'pass' and individual.facts['observed_nets'] == ('Y',)
    assert len(resolved) == 2 and set(failure.facts['component_ids']) == resolved

    sources = failure.sources
    assert {s.line for s in sources if s.uri == 'source.cdl' and s.sha256 == sha(root / s.uri)} == {3, 4}
    assert {s.field for s in sources if s.uri == ctx.version.snapshot_ref.id
            and s.sha256 == ctx.version.snapshot_ref.digest} >= {'/connectivity/components/' + c for c in resolved}
    assert row.rule.location('relation_basis') in sources
    assert any(s.uri.startswith('query/raw/') and s.sha256 == sha(root / s.uri) for s in sources)
    islands, = (o for o in report.for_rule('T10.coverage').observations if o.kind == 'separate_label_islands')
    assert islands.facts['net']['name'] == 'Y' and set(islands.object_ids) == resolved


def test_missing_gate_net_evidence_keeps_t08_indeterminate(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    without_cache(root)
    rewrite_net_response(root, 'n_a', ())
    ctx, report, _ = inspect_published(root, 'missing-gate-net')
    row = report.for_rule('T08.terminal_graph')
    assert row.status == 'indeterminate' and row.policy_action == 'indeterminate_then_reject'
    assert row.issue.code == 'UnobservedTerminalNet'
    assert row.issue.source.uri == ctx.version.snapshot_ref.id and not report.all_required_passed
