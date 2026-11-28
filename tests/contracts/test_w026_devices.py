"""Device rule contrasts through the complete read-only entry point."""
from shutil import copyfile

import pytest

from layauto_v2.normalization.stage2 import Stage2AssemblyError
from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE, rebind, sha
from w011_cases import change_cdl
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
    drain, = (obs for obs in row.observations if obs.status == 'violation')
    assert drain.kind == 'terminal_relation' and drain.object_ids[:2] == ('MN0', 'D')
    assert drain.facts['observed_nets'] == ('Y',) and drain.facts['declared_net'] == 'VDD'
    assert drain.facts['component_ids'] and drain.facts['domain'] == 'local_components'
    assert drain.sources[0].uri == 'source.cdl' and drain.sources[0].line == 3
    assert any(source.uri.startswith('query/raw') for source in drain.sources)
    body = [obs for obs in row.observations if obs.facts.get('role') == 'B']
    assert {obs.facts['observed_nets'] for obs in body} == {('VSS',), ('VDD',)}
    assert all(obs.status == 'pass' and obs.facts['domain'] == 'external_body_path' for obs in body)
    assert report.for_rule('T04.body').status == 'pass'
