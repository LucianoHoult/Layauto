"""Whole-context and dependency-scoped neutral body witnesses.

The shared base comes from the actual reader. These direct neutral probes test
body arithmetic/completeness; they do not claim changed bytes authenticated.
"""
from __future__ import annotations

import pytest

from layauto_v2.derive.body_relations import evaluate_body
from layauto_v2.derive.channel_identity import build_channel_identity_draft
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord
from w014_cases import normal_capture


@pytest.fixture(scope='module')
def body_inputs():
    draft = normal_capture().value
    channels = build_channel_identity_draft(draft.local, draft.source, draft.channel_seeds, draft.derived)
    return channels, draft.annotation, draft.body_evidence


def evaluate(inputs, mutate):
    channels, annotation, original = inputs
    # JSON is only a convenient independent mutable copy of this JSON input.
    from w005_cases import read_json, FIXTURE
    value = read_json(FIXTURE / 'body/context.json')
    mutate(value)
    return evaluate_body(channels, annotation, EvidenceRecord('body', FrozenMap(value), original.sources))


def test_orphan_tap_is_audited_even_when_both_declared_device_paths_are_valid(body_inputs):
    def mutate(value):
        value['shapes'].append({'id': 'bad-orphan-tap', 'layer': 'BTAP_N', 'bbox': [-18, 92, -16, 94]})
    body, issues = evaluate(body_inputs, mutate)
    audit = next(row for row in body['tap_audits'] if row['tap_id'] == 'bad-orphan-tap')
    assert audit['status'] == 'violation'
    assert audit['body_candidates'] == audit['rail_candidates'] == ()
    assert any(issue.code == 'BodyUniqueMatchFailure' and issue.source.field == '/shapes/6' for issue in issues)
    assert {row['chain_status'] for row in body['paths']} == {'established'}


def test_unreferenced_opposite_body_overlap_is_not_hidden_by_valid_selected_chains(body_inputs):
    def mutate(value):
        value['shapes'].append({'id': 'opposite-extra', 'layer': 'BODY_N', 'bbox': [-20, 120, 0, 180]})
    body, issues = evaluate(body_inputs, mutate)
    assert any(row['domain'] == 'external' and row['n_id'] == 'opposite-extra'
               and row['positive_area_overlap'] is True for row in body['body_pair_audits'])
    assert any(issue.code == 'BodyOppositeTypeOverlap' for issue in issues)
    assert {row['rule_status'] for row in body['paths']} == {'violation'}


@pytest.mark.parametrize('identity,bounds', [
    ('BN.ext', [-20, 90, 0, 100]),
    ('MN.ext', [-20, 58, 0, 68]),
])
def test_corner_only_continuation_does_not_establish_a_body_chain(body_inputs, identity, bounds):
    def mutate(value):
        next(row for row in value['shapes'] if row['id'] == identity)['bbox'] = bounds
    body, issues = evaluate(body_inputs, mutate)
    path = next(row for row in body['paths'] if row['device_id']['name'] == 'MN0')
    assert path['chain_status'] == 'indeterminate'
    assert any(issue.code == 'BodyContinuationMismatch' for issue in issues)


def test_tap_edge_only_contact_is_not_positive_area(body_inputs):
    def mutate(value):
        next(row for row in value['shapes'] if row['id'] == 'TN.ext')['bbox'] = [-4, 58, 0, 62]
    body, issues = evaluate(body_inputs, mutate)
    audit = next(row for row in body['tap_audits'] if row['tap_id'] == 'TN.ext')
    assert audit['rail_candidates'] == ()
    assert any(issue.code == 'BodyUniqueMatchFailure' for issue in issues)


def test_one_device_wrong_local_body_keeps_other_device_proof(body_inputs):
    def mutate(value):
        value['associations'][0]['local_body'] = 'BP'
    body, issues = evaluate(body_inputs, mutate)
    paths = {row['device_id']['name']: row for row in body['paths']}
    assert paths['MN0']['chain_status'] == 'indeterminate'
    assert paths['MP0']['chain_status'] == 'established'
    assert tuple(row['name'] for row in paths['MP0']['observed_net_ids']) == ('VDD',)
    assert any(issue.code == 'BodyTypeMismatch' for issue in issues)


def test_global_wrong_top_does_not_retain_satisfied_rule_or_equal_claim(body_inputs):
    body, issues = evaluate(body_inputs, lambda value: value.__setitem__('top', 'WRONG_TOP'))
    assert any(issue.code == 'BodySourceBindingMismatch' for issue in issues)
    for path in body['paths']:
        assert path['chain_status'] == path['rule_status'] == path['claim_status'] == 'indeterminate'
        assert path['observed_net_ids'] == ()


def test_exact_body_rail_anchor_does_not_hide_partial_conflicting_net_evidence(tmp_path):
    from w007_cases import ready_copy
    from w010_cases import build_local
    from w013_cases import rewrite_net_response
    from w014_cases import neutral, relation_map
    root = ready_copy(tmp_path)
    local = build_local(root).value
    rewrite_net_response(root, 'n_hi', [('toy_li', (28, 130, 34, 155)),
                                      ('toy_m1', (0, 148, 45, 158)),
                                      ('toy_m1', (0, 48, 10, 58))])
    draft = neutral(root, local)
    relation = relation_map(draft)['MN0', 'B']
    assert relation.status == 'conflict'
    assert {net.name for net in relation.observed_net_ids} == {'VSS', 'VDD'}
    assert relation.context_path['claim_status'] == 'conflict'
    assert relation.context_path['rule_status'] == 'indeterminate'
    assert len(relation.context_path['evidence_refs']) >= 2


def test_changed_gate_owner_is_rejected_by_w009_before_terminal_relations(tmp_path):
    from w007_cases import ready_copy, read
    from w009_cases import change_owner
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, geometry_from_parse_result,
    )
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda owner: owner['device_extraction_contract'].__setitem__(
        'gate_operator', 'gate connects source and drain'))
    geometry = build_geometry(geometry_from_parse_result(read(root)))
    assert geometry.status == 'success'
    result = build_effective_geometry(geometry)
    assert result.status == 'error'
    assert result.input is geometry and result.completed == geometry.completed
    assert any(issue.category == 'unsupported' and issue.code == 'UnsupportedRegionOperator'
               and issue.source.uri == 'tech/physical.json'
               and issue.source.field == '/device_extraction_contract/gate_operator' for issue in result.issues)


def test_positive_edges_outside_actual_frame_are_not_context_continuations(tmp_path):
    from w005_cases import read_json, rebind, write_json
    from w007_cases import ready_copy
    from w009_cases import rewrite_geometry
    from w014_cases import build
    root = ready_copy(tmp_path)
    rewrite_geometry(root, replace_layers={
        'BODY_N': [(-10, 0, 120, 90)], 'BODY_P': [(-10, 100, 120, 200)],
        'M1': [(-10, 48, 45, 58), (-10, 148, 45, 158), (50, 90, 75, 98), (80, 90, 110, 98)],
    })
    body = read_json(root / 'body/context.json')
    for row in body['local_bindings']:
        if row['layer'] in ('BODY_N', 'BODY_P', 'M1'):
            row['bbox'][0] = -10
    for row in body['shapes']:
        if row['layer'] in ('BODY_N', 'BODY_P', 'M1'):
            row['bbox'][2] = -10
        elif row['layer'] in ('BTAP_N', 'BTAP_P'):
            row['bbox'][0], row['bbox'][2] = -18, -14
    write_json(root / 'body/context.json', body)
    rebind(root)
    result = build(root)
    assert result.status == 'error' and result.value is not None
    assert any(issue.code == 'BodyContinuationMismatch' for issue in result.issues)
    paths = {row['device_id']['name']: row for row in result.value.body['paths']}
    assert paths['MN0']['body_edge_length_nm'] == 90
    assert paths['MP0']['body_edge_length_nm'] == 100
    assert all(row['rail_edge_length_nm'] == 10 and row['chain_status'] == 'indeterminate'
               for row in paths.values())


def test_actual_local_opposite_body_overlap_is_a_rule_violation_without_erasing_contact(tmp_path):
    from w005_cases import rebind
    from w007_cases import ready_copy
    from w009_cases import rewrite_geometry
    from w014_cases import build, change_body
    root = ready_copy(tmp_path)
    rewrite_geometry(root, replace_layers={'BODY_N': [(0, 0, 120, 130)]})
    def bind_actual_body(value):
        next(row for row in value['local_bindings'] if row['layer'] == 'BODY_N')['bbox'] = [0, 0, 120, 130]
    change_body(root, bind_actual_body)
    rebind(root)
    result = build(root)
    assert result.status == 'error' and result.value is not None
    assert any(issue.code == 'BodyOppositeTypeOverlap' for issue in result.issues)
    assert any(row['domain'] == 'local' and row['positive_area_overlap'] is True
               for row in result.value.body['body_pair_audits'])
    assert all(path['chain_status'] == 'established' and path['rule_status'] == 'violation'
               for path in result.value.body['paths'])
    assert result.value.comparison_status == 'equal'
    assert result.value.source_comparison_status == 'indeterminate'
