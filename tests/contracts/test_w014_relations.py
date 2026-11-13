"""Real W014 composition, source/observed separation, and located negatives."""
from __future__ import annotations

import builtins
from dataclasses import fields
from fractions import Fraction
import io
from pathlib import Path
import shutil

import pytest

from w005_cases import FIXTURE, inventory, without_cache
from w007_cases import ready_copy
from w009_cases import change_owner
from w010_cases import build_local
from w011_cases import change_cdl, change_seeds
from w013_cases import rewrite_net_response
from w014_cases import (EXPECTED_TERMINALS, build, failure_copy, neutral,
                        normal_capture, readback_capture, relation_map)


@pytest.fixture(scope='module')
def accepted():
    return normal_capture()


@pytest.fixture(scope='module')
def variant_base(tmp_path_factory):
    root = ready_copy(tmp_path_factory.mktemp('w014-neutral'))
    return root, build_local(root).value


@pytest.fixture
def variant(variant_base):
    root, local = variant_base
    shutil.rmtree(root / 'query', ignore_errors=True)
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    without_cache(root)
    return root, local


def net_names(values):
    return tuple(net.name for net in values)


def test_actual_eight_ordered_terminals_match_source_with_shared_gate_and_separate_body(accepted):
    draft, local = accepted.value, accepted.input.value
    rows = relation_map(draft)
    assert set(rows) == set(EXPECTED_TERMINALS) and len(rows) == len(draft.relations) == 8
    assert {(name, role): row.expected.net_id.name for (name, role), row in rows.items()} == EXPECTED_TERMINALS
    assert {(name, role): net_names(row.observed_net_ids)[0]
            for (name, role), row in rows.items()} == EXPECTED_TERMINALS
    assert all(row.status == 'equal' and row.expected.source.uri == 'source.cdl' for row in rows.values())
    assert all(row.expected.source.sha256 for row in rows.values())
    assert rows['MN0', 'G'].node_refs == rows['MP0', 'G'].node_refs
    assert len(rows['MN0', 'G'].node_refs) == 1
    assert rows['MN0', 'G'].target != rows['MP0', 'G'].target
    for (name, role), row in rows.items():
        assert row.node_refs and row.component_refs and row.annotation_target_refs
        if role == 'B':
            assert row.local_observed_net_ids == () and row.context_path is not None
        else:
            assert row.local_observed_net_ids == row.observed_net_ids
            assert row.context_path is None and row.evidence_refs
    assert len(local.nodes) == 14 and len(local.edges) == 8 and len(local.components) == 6
    assert draft.local is local
    assert len(draft.annotation.components) == 6
    unknown = [row for row in draft.annotation.components if row.status == 'unknown']
    assert len(unknown) == 2 and all(len(row.members) == 1 and row.observed_net_ids == () for row in unknown)
    assert sum(row.total_area for row in draft.annotation.coverage) == 35090
    assert sum(row.covered_area for row in draft.annotation.coverage) == 3170
    assert draft.comparison_status == draft.channel_comparison_status == draft.source_comparison_status == 'equal'
    assert not draft.differences and not draft.issues
    assert accepted.completed == accepted.input.completed
    assert accepted.body_evidence is accepted.input.body_evidence


def test_component_is_pure_and_cannot_publish_or_change_the_original_graph(accepted, monkeypatch):
    from layauto_v2.normalization import build_terminal_relations
    before = inventory(FIXTURE)
    local = accepted.input
    edges, components = local.value.edges, local.value.components
    def forbidden(*args, **kwargs):
        pytest.fail('W014 attempted acquisition or publication')
    with monkeypatch.context() as patch:
        for method in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_terminal_relations(local)
    assert result.status == 'success' and result.input is local
    assert local.value.edges is edges and local.value.components is components
    assert inventory(FIXTURE) == before
    for value in (result, result.value, *result.value.relations):
        assert not {'baseline', 'terminal', 'final_snapshot_id', 'body_complete', 'no_change'} & {
            field.name for field in fields(value)}


def test_actual_caller_read_readback_keeps_attempt_checkpoint_and_empty_terminal():
    result, repository, ready, checkpoint, attempt = readback_capture()
    assert result.status == 'success'
    assert set(relation_map(result.value)) == set(EXPECTED_TERMINALS)
    assert all(row.status == 'equal' for row in result.value.relations)
    binding = result.value.capture_binding['readback']
    assert binding['run_id'] == ready.run_id
    assert binding['checkpoint_ref']['digest'] == ready.checkpoint_ref.digest
    assert binding['parse_ref']['digest'] == ready.parse_ref.digest
    assert binding['tool_ref']['digest'] == ready.tool_ref.digest
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.read_terminal(ready.run_id) is None


@pytest.mark.parametrize('case,code', [
    ('missing_body_context', 'RequiredBodyContextUnavailable'),
    ('missing_body_operator', 'RequiredBodyOperatorUnavailable'),
    ('body_wrong_binding', 'BodySourceBindingMismatch'),
])
def test_body_cases_rejected_by_reader_never_reach_w014(tmp_path, monkeypatch, case, code):
    from layauto_v2.importers import read_inputs
    import layauto_v2.normalization.terminal_relations as component
    root = failure_copy(tmp_path, case)
    def forbidden(*args, **kwargs):
        pytest.fail('reader-rejected case was sent to W014')
    monkeypatch.setattr(component, 'build_terminal_relations', forbidden)
    result = read_inputs(root / 'site_config.yaml')
    assert result.status == 'error' and result.value is None
    assert result.issues[0].code == code
    assert result.completed and result.sources
    assert result.issues[0].source.uri
    if case == 'missing_body_context':
        assert result.issues[0].source.sha256 is None
    else:
        assert result.issues[0].source.sha256 in {row.sha256 for row in result.sources}


@pytest.mark.parametrize('case,code', [
    ('body_wrong_type', 'BodyTypeMismatch'),
    ('body_disconnected', 'BodyContinuationMismatch'),
    ('body_ambiguous', 'BodyUniqueMatchFailure'),
    ('body_enclosure', 'BodyTapEnclosureFailure'),
    ('body_wrong_rail', 'BodyTargetRailMismatch'),
])
def test_existing_body_witnesses_reach_real_component_and_keep_diagnostics(tmp_path, case, code):
    root = failure_copy(tmp_path, case)
    result = build(root)
    assert result.status == 'error' and result.value is not None
    assert code in {issue.code for issue in result.issues}
    assert result.completed == result.input.completed
    assert all(issue.source.uri and issue.source.sha256 and issue.source.field for issue in result.issues)
    assert len(result.input.value.nodes) == 14 and len(result.input.value.edges) == 8
    assert len(result.input.value.components) == 6
    assert len(result.value.relations) == 8
    if case == 'body_wrong_rail':
        row = relation_map(result.value)['MN0', 'B']
        assert row.expected.net_id.name == 'VSS' and net_names(row.observed_net_ids) == ('VSS',)


@pytest.mark.parametrize('field,value', [
    ('electrical_connects', ['BODY_P', 'M1']),
    ('contact_predicate', 'corner_touch_is_contact'),
    ('enclosure_rule', 'T04.body'),
])
def test_external_btap_owner_declarations_are_consumed_at_w014_boundary(tmp_path, field, value):
    root = ready_copy(tmp_path)
    def mutate(owner):
        next(row for row in owner['layers'] if row['name'] == 'BTAP_N')[field] = value
    change_owner(root, 'drawn', mutate)
    result = build(root)
    assert result.status == 'error'
    assert result.completed == result.input.completed
    assert result.body_evidence is result.input.body_evidence
    issues = [issue for issue in result.issues if issue.category == 'unsupported']
    assert issues and any(issue.source.uri == 'tech/drawn.json'
                          and issue.source.field.endswith('/' + field) for issue in issues)


@pytest.mark.parametrize('field,value', [
    ('coordinates', 'scaled parent coordinates without a transform'),
    ('geometry_scope', 'unbound external geometry anywhere'),
])
def test_body_profile_changes_are_not_silently_interpreted(tmp_path, field, value):
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda owner: owner['body_context_profile'].__setitem__(field, value))
    result = build(root)
    assert result.status == 'error'
    assert result.completed == result.input.completed
    assert result.body_evidence is result.input.body_evidence
    assert any(issue.category == 'unsupported' and issue.source.uri == 'tech/physical.json'
               and '/body_context_profile/' in issue.source.field for issue in result.issues)


def test_source_admission_failure_retains_w007_issue_and_completed_capture_without_a_draft(tmp_path):
    from layauto_v2.normalization import normalize
    root = ready_copy(tmp_path)
    change_cdl(root, 'source', 'TOY_N NFIN=5 NF=1', 'TOY_N NFIN=5 NF=2')
    result = build(root)
    original = normalize(result.input.input.input.input.semantic_input)
    assert original.status == result.status == 'error'
    assert result.value is None
    assert [issue.code for issue in result.issues] == ['UnsupportedFingerCount']
    assert [(issue.category, issue.code, issue.message, issue.source) for issue in result.issues] == [
        (issue.category, issue.code, issue.message, issue.source) for issue in original.issues]
    assert result.completed == result.input.completed
    assert result.body_evidence is result.input.body_evidence
    assert result.semantic_facts == original.completed


def test_source_terminal_mismatch_keeps_actual_observation_and_never_swaps_sd(variant):
    root, local = variant
    change_cdl(root, 'source', 'MN0 Y A VSS VSS TOY_N', 'MN0 VDD A VSS VSS TOY_N')
    draft = neutral(root, local)
    rows = relation_map(draft)
    drain = rows['MN0', 'D']
    assert drain.expected.net_id.name == 'VDD'
    assert net_names(drain.local_observed_net_ids) == net_names(drain.observed_net_ids) == ('Y',)
    assert drain.status == 'mismatch' and rows['MN0', 'S'].status == 'equal'
    assert draft.comparison_status == draft.source_comparison_status == 'mismatch'
    assert len(draft.relations) == 8 and len(draft.local.components) == 6


def test_source_body_expectation_is_not_the_context_observed_rail(variant):
    root, local = variant
    change_cdl(root, 'source', 'MN0 Y A VSS VSS TOY_N', 'MN0 Y A VSS VDD TOY_N')
    draft = neutral(root, local)
    row = relation_map(draft)['MN0', 'B']
    assert row.expected.net_id.name == 'VDD' and row.local_observed_net_ids == ()
    assert net_names(row.observed_net_ids) == ('VSS',) and row.status == 'mismatch'


def test_missing_query_evidence_keeps_both_shared_gate_terminals_unknown(variant):
    root, local = variant
    rewrite_net_response(root, 'n_a', ())
    draft = neutral(root, local)
    rows = relation_map(draft)
    for name in ('MN0', 'MP0'):
        assert rows[name, 'G'].observed_net_ids == () and rows[name, 'G'].status == 'unknown'
        assert rows[name, 'G'].expected.net_id.name == 'A'
        assert rows[name, 'D'].status == rows[name, 'S'].status == 'equal'
    assert draft.comparison_status == 'indeterminate'


def test_conflicting_shared_gate_nets_keep_both_identities_and_w013_gaps(variant):
    root, local = variant
    rewrite_net_response(root, 'n_lo', [('toy_li', (28, 30, 34, 55)),
                                      ('toy_m1', (0, 48, 45, 58)),
                                      ('toy_poly', (58, 10, 62, 190))])
    draft = neutral(root, local)
    rows = relation_map(draft)
    for name in ('MN0', 'MP0'):
        assert set(net_names(rows[name, 'G'].observed_net_ids)) == {'A', 'VSS'}
        assert rows[name, 'G'].status == 'conflict'
    assert any(issue.code == 'ConflictingComponentNets' for issue in draft.issues)
    assert any(row.conflict_area > 0 for row in draft.annotation.coverage)
    assert relation_map(draft)['MN0', 'B'].status == 'equal'
    assert len(draft.local.components) == 6 and len(draft.local.edges) == 8


def test_absent_exact_body_rail_query_is_unknown_even_when_local_component_has_a_net(variant):
    root, local = variant
    rewrite_net_response(root, 'n_lo', [('toy_li', (28, 30, 34, 55))])
    draft = neutral(root, local)
    rows = relation_map(draft)
    assert net_names(rows['MN0', 'S'].observed_net_ids) == ('VSS',)
    assert rows['MN0', 'B'].observed_net_ids == ()
    assert rows['MN0', 'B'].status in ('unknown', 'indeterminate')
    assert rows['MP0', 'B'].status == 'equal'


def test_req01_fractional_rail_mismatch_is_not_rounded_or_hidden_by_component_consensus(variant):
    root, local = variant
    rewrite_net_response(root, 'n_lo', [('toy_li', (28, 30, 34, 55)),
                                      ('toy_m1', (0, 48, Fraction(901, 20), 58))])
    draft = neutral(root, local)
    evidence = next(row for row in draft.annotation.evidence
                    if row.query_key.identity == 'n_lo' and row.record['derived_layer'] == 'toy_m1')
    assert evidence.rectangle.x1 == Fraction(901, 20) and evidence.rectangle.x1 != 45
    rows = relation_map(draft)
    assert net_names(rows['MN0', 'S'].observed_net_ids) == ('VSS',)
    assert any(issue.code == 'BodyTargetRailMismatch' for issue in draft.issues)
    assert rows['MN0', 'B'].status != 'equal'


def test_target_only_intent_changes_do_not_change_source_terminal_observations(tmp_path):
    root = ready_copy(tmp_path)
    change_cdl(root, 'target', 'VT=toy W=2n L=4n M=1 NF=1 NFIN=5',
               'VT=toy W=3n L=6n M=1 NF=1 NFIN=3')
    result = build(root)
    assert result.status == 'success'
    assert result.value.comparison_status == result.value.source_comparison_status == 'equal'
    assert len(result.semantic_facts.differences) == 3
    assert {(name, role): net_names(row.observed_net_ids)[0]
            for (name, role), row in relation_map(result.value).items()} == EXPECTED_TERMINALS


def test_existing_fin_mismatch_stays_four_against_source_five_despite_eight_equal_terminals(tmp_path):
    root = failure_copy(tmp_path, 'extraction_mismatch')
    result = build(root)
    assert result.status == 'success'
    draft = result.value
    assert len(draft.relations) == 8 and all(row.status == 'equal' for row in draft.relations)
    assert draft.comparison_status == 'equal'
    assert draft.channel_comparison_status == draft.source_comparison_status == 'mismatch'
    assert len(draft.differences) == 1
    difference = draft.differences[0]['fields']
    assert difference['axis'] == 'fins_per_finger' and difference['measured'] == 4
    assert difference['declared']['exact'] == 5
    assert sum(row.total_area for row in draft.annotation.coverage) == 34634
    assert sum(row.covered_area for row in draft.annotation.coverage) == 3170


def test_missing_channel_identity_still_emits_all_four_source_targets(variant):
    root, local = variant
    change_seeds(root, 'Q17', ())
    draft = neutral(root, local)
    rows = relation_map(draft)
    assert set(rows) == set(EXPECTED_TERMINALS) and len(draft.relations) == 8
    assert draft.issues
    assert all(rows['MN0', role].status == 'indeterminate' for role in ('D', 'G', 'S', 'B'))
    assert all(rows['MP0', role].status == 'equal' for role in ('D', 'G', 'S', 'B'))


def test_cr02_reader_accepted_unknown_lvs_status_is_preserved_in_relation_coverage(variant):
    from w014_cases import change_body
    root, local = variant
    change_body(root, lambda body: body.__setitem__('lvs_status', 'unknown'))
    # neutral() reads actual changed bytes and rebuilds all non-geometry facts;
    # the unchanged local graph shares the same source/tech capture identities.
    draft = neutral(root, local)
    assert draft.body_evidence.payload['lvs_status'] == 'unknown'
    assert draft.coverage['lvs_status'] == 'unknown'
    assert draft.comparison_status == 'equal'
    assert len(draft.relations) == 8
