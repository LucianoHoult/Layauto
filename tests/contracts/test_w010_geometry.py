"""Actual W005/W006 composition and independent exact local-graph witnesses."""
from __future__ import annotations

import builtins
import io
import random
from collections import Counter
from dataclasses import fields
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.geometry import Rect
from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, build_local_connectivity,
    from_parse_result, geometry_from_inputs_ready, normalize,
)
from layauto_v2.normalization.codec import record_digest as semantic_digest
from layauto_v2.normalization.effective_codec import record_digest as effective_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.local_connectivity import encloses_connector, same_layer_contact

from w005_cases import FIXTURE, apply_case, inventory, read_json
from w006_cases import caller_request
from w007_cases import query_only_rename, ready_copy
from w008_geometry_cases import edit_geometry
from w009_cases import change_owner, rewrite_geometry, special_input
from w010_cases import (
    append_records, arrangement_contact, arrangement_enclosure, build_effective,
    build_local, normal_node_names,
)


@pytest.fixture(scope='module')
def accepted():
    return build_local()


def test_actual_direct_chain_is_pure_and_retains_complete_prior_evidence(monkeypatch):
    before = inventory(FIXTURE)
    effective = build_effective()
    semantic = normalize(from_parse_result(effective.input.input.parse))
    semantic_before, effective_before = semantic_digest(semantic), effective_digest(effective)

    def forbidden(*args, **kwargs):
        pytest.fail('local connectivity must not acquire files or access repository')

    with monkeypatch.context() as patch:
        for method in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_local_connectivity(effective)
    assert result.status == 'success' and not result.issues
    assert result.input is effective and result.value.effective is effective.value
    assert result.completed == effective.completed
    assert result.body_evidence is effective.body_evidence
    assert effective_digest(effective) == effective_before
    assert semantic_digest(semantic) == semantic_before
    assert semantic.value.device_seeds and semantic.value.net_seeds
    assert len(result.value.effective.base.layout.records) == 40
    assert len(result.value.effective.base.fragments) == 41
    assert len(result.body_evidence.payload['shapes']) == 6
    tech = next(item for item in effective.completed if item.kind == 'tech')
    assert result.value.binding.rules.sources == (tech.sources[6],)
    assert result.value.binding.rules.payload == effective.input.input.value['tech']['rules']
    assert result.value.binding.physical.sources == (tech.sources[3],)
    assert result.value.binding.drawn.sources == (tech.sources[1],)
    assert inventory(FIXTURE) == before


def test_real_w006_readback_matches_direct_without_advancing_attempt(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    direct = build_local(root)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id='w010-real-composition'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)

    def forbidden(*args, **kwargs):
        pytest.fail('pure local graph composition attempted acquisition/publication')

    with monkeypatch.context() as patch:
        for method in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        patch.setattr(repository, 'read', forbidden)
        geometry = build_geometry(geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))
        effective = build_effective_geometry(geometry)
        result = build_local_connectivity(effective)
    assert result.status == 'success' and result.value == direct.value
    assert result.input is effective and result.input.input.input.readback is not None
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None


def test_normal_graph_matches_complete_independent_members_edges_and_geometry(accepted):
    draft = accepted.value
    oracle, spec = read_json(FIXTURE / 'oracle.json'), read_json(FIXTURE / 'spec.json')
    names = normal_node_names(draft, spec, oracle)
    assert len(names) == len(draft.nodes) == 14
    assert {frozenset(names[ref] for ref in component.members) for component in draft.components} == {
        frozenset(row['regions']) for row in oracle['components']}
    assert len(draft.components) == 6
    raw_names = {(row['layer'], tuple(row['bbox'])): row['id'] for row in spec['shapes']}
    actual_edges = []
    for edge in draft.edges:
        assert edge.kind == 'connector'
        connector = draft.effective.base.layout.record(edge.connector_id)
        actual_edges.append((raw_names[connector.layer, connector.rect.bounds],
                             frozenset(names[ref] for ref in edge.endpoints)))
    assert Counter(actual_edges) == Counter((row['connector'], frozenset(row['ends'])) for row in oracle['edges'])
    assert len(draft.edges) == 8 and len(draft.audits) == 16
    assert draft.local_enclosure_status == 'pass'
    assert all(audit.status == 'pass' and audit.margin_ticks == Fraction(1) for audit in draft.audits)
    assert {audit.connector_id for audit in draft.audits} == {edge.connector_id for edge in draft.edges}
    assert len([node for node in draft.nodes if node.layer == 'POLY']) == 1
    assert not any(node.region.role == 'channel' for node in draft.nodes)
    edge_sets = {frozenset(names[ref] for ref in edge.endpoints) for edge in draft.edges}
    assert not any(frozenset(pair) in edge_sets for pair in oracle['non_edges'])
    assert draft.binding.scope == 'local_flat_cell/1'
    forbidden = {'net_id', 'device_id', 'body_complete', 'baseline', 'terminal', 'no_change', 'final_snapshot_id'}
    for value in (draft, accepted, *draft.nodes, *draft.edges, *draft.components):
        assert not forbidden & {field.name for field in fields(value)}


@pytest.mark.parametrize('first,second,expected', [
    ((0, 0, 10, 10), (5, 5, 12, 13), True),
    ((0, 0, 10, 10), (10, 0, 20, 10), True),
    ((0, 0, 10, 10), (10, 4, 20, 6), True),
    ((0, 0, 10, 10), (4, 10, 6, 20), True),
    ((0, 0, 10, 10), (10, 10, 20, 20), False),
    ((0, 0, 10, 10), (11, 0, 20, 10), False),
    ((-30, -40, -20, -10), (-20, -30, -10, -20), True),
    ((-30, -40, -20, -10), (-20, -10, -10, 0), False),
    ((2**90, -2**90, 2**90 + 10, -2**90 + 10),
     (2**90 + 10, -2**90 + 4, 2**90 + 20, -2**90 + 6), True),
])
def test_same_layer_exact_hand_cases_independent_arrangement(first, second, expected):
    assert arrangement_contact((first,), (second,)) is expected
    assert same_layer_contact((Rect(*first),), (Rect(*second),)) is expected
    assert same_layer_contact((Rect(*second),), (Rect(*first),)) is expected


def test_seeded_rectangle_set_contacts_match_all_arrangement_atoms():
    rng = random.Random(10010)
    for _ in range(160):
        groups = []
        for _ in range(2):
            boxes = []
            for _ in range(rng.randrange(1, 5)):
                xs, ys = sorted(rng.sample(range(-12, 13), 2)), sorted(rng.sample(range(-12, 13), 2))
                boxes.append((xs[0], ys[0], xs[1], ys[1]))
            groups.append(tuple(boxes))
        expected = arrangement_contact(*groups)
        assert same_layer_contact(*(tuple(Rect(*box) for box in group) for group in groups)) is expected


@pytest.mark.parametrize('cover,connector,margin,expected', [
    (((0, 0, 10, 10),), (1, 1, 9, 9), Fraction(1), True),
    (((0, 0, 10, 10),), (1, 1, 9, 9), Fraction(3, 2), False),
    (((0, 0, 5, 10), (5, 0, 10, 10)), (2, 2, 8, 8), Fraction(1), True),
    (((0, 0, 4, 10), (4, 0, 6, 4), (4, 6, 6, 10), (6, 0, 10, 10)),
     (2, 2, 8, 8), Fraction(1), False),
    (((0, 0, 4, 10), (4, 0, 6, 4), (4, 6, 6, 10), (6, 0, 10, 10)),
     (1, 1, 3, 3), Fraction(1), True),
    (((-10, -10, 0, 0),), (-9, -9, -1, -1), Fraction(1), True),
    (((0, 0, 10, 10),), (1, 1, 9, 9), Fraction(1, 2), True),
    (((2**90, -2**90, 2**90 + 20, -2**90 + 20),),
     (2**90 + 2, -2**90 + 2, 2**90 + 18, -2**90 + 18), Fraction(2), True),
])
def test_exact_set_enclosure_hand_cases_not_bbox_or_single_piece(cover, connector, margin, expected):
    assert arrangement_enclosure(cover, connector, margin) is expected
    assert encloses_connector(tuple(Rect(*box) for box in cover), Rect(*connector), margin) is expected


def test_seeded_fractional_enclosure_matches_complete_exact_target_atoms():
    rng = random.Random(10105)
    for _ in range(100):
        cover = []
        for _ in range(rng.randrange(1, 7)):
            xs, ys = sorted(rng.sample(range(-7, 8), 2)), sorted(rng.sample(range(-7, 8), 2))
            cover.append((xs[0], ys[0], xs[1], ys[1]))
        xs, ys = sorted(rng.sample(range(-6, 7), 2)), sorted(rng.sample(range(-6, 7), 2))
        target, margin = (xs[0], ys[0], xs[1], ys[1]), Fraction(rng.randrange(1, 5), rng.randrange(1, 5))
        assert encloses_connector(tuple(Rect(*box) for box in cover), Rect(*target), margin) is arrangement_enclosure(cover, target, margin)


def test_cut_islands_preserve_three_isolated_components_zero_edges(tmp_path):
    root = ready_copy(tmp_path)
    special_input(root)
    draft = build_local(root).value
    assert len(draft.nodes) == len(draft.components) == 3
    assert draft.edges == draft.audits == ()
    assert {tuple(rect.bounds for rect in node.region.rectangles) for node in draft.nodes} == {
        ((50, 20, 60, 24),), ((130, 20, 139, 24),), ((141, 20, 150, 24),)}
    assert all(len(component.members) == 1 for component in draft.components)


def test_existing_via_enclosure_failure_retains_physical_edge_and_separate_violation(tmp_path):
    root = ready_copy(tmp_path)
    apply_case(root, 'via_enclosure')
    result = build_local(root)
    draft = result.value
    connector = next(record for record in draft.effective.base.layout.records
                     if record.layer == 'VIA0' and record.rect.bounds == (33, 50, 37, 54))
    edges = [edge for edge in draft.edges if edge.connector_id == connector.id]
    assert len(edges) == 1 and len(draft.edges) == 8
    audits = [audit for audit in draft.audits if audit.connector_id == connector.id]
    assert {(audit.layer, audit.status) for audit in audits} == {('LI', 'violation'), ('M1', 'pass')}
    assert draft.local_enclosure_status == 'violation'
    assert set(edges[0].endpoints) == {audit.node_ref for audit in audits}
    assert len(draft.components) == 6


@pytest.mark.parametrize('extra', [
    [('LI', (28, 30, 34, 55))],  # A second source record counts separately.
    [('LI', (30, 35, 36, 60))],  # Same-layer connected candidates remain two regions.
    [('LI', (32, 41, 35, 45))],  # One barely overlapping side fails enclosure; cannot filter it away.
])
def test_connector_counts_independent_regions_before_components_or_enclosure(tmp_path, extra):
    root = ready_copy(tmp_path)
    append_records(root, extra)
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.value is None
    assert result.issues[0].code == 'AmbiguousConnectorEndpoint'
    assert result.issues[0].source.uri == 'source.gds' and result.issues[0].source.field
    assert result.completed == effective.completed and result.input is effective


@pytest.mark.parametrize('bounds', [(110, 50, 114, 54), (34, 50, 38, 54), (34, 55, 38, 59)])
def test_connector_missing_edge_only_and_corner_only_side_are_not_positive_area(tmp_path, bounds):
    root = ready_copy(tmp_path)
    rewrite_geometry(root, replace_layers={'VIA0': (bounds,)})
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.value is None
    assert result.issues[0].code == 'AmbiguousConnectorEndpoint'
    assert result.completed == effective.completed


def test_duplicate_connectors_keep_each_record_and_audit_without_adding_conductors(tmp_path, accepted):
    root = ready_copy(tmp_path)
    append_records(root, [('VIA0', (29, 50, 33, 54))])
    draft = build_local(root).value
    assert len(draft.nodes) == 14 and len(draft.components) == 6
    assert len(draft.edges) == 9 and len(draft.audits) == 18
    duplicates = [record for record in draft.effective.base.layout.records
                  if record.layer == 'VIA0' and record.rect.bounds == (29, 50, 33, 54)]
    assert len(duplicates) == 2 and duplicates[0].id != duplicates[1].id
    assert duplicates[0].source != duplicates[1].source
    matching = [edge for edge in draft.edges if edge.connector_id in {record.id for record in duplicates}]
    assert len(matching) == 2 and matching[0].endpoints == matching[1].endpoints
    assert Counter(audit.connector_id for audit in draft.audits)[duplicates[0].id] == 2
    assert Counter(audit.connector_id for audit in draft.audits)[duplicates[1].id] == 2


def test_cut_new_boundary_preserves_exact_contact_and_unique_region_count(tmp_path):
    root = ready_copy(tmp_path)
    append_records(root, [('LI', (200, 200, 220, 210)), ('CUT', (207, 199, 213, 205)),
                          ('LI', (220, 203, 225, 207))])
    draft = build_local(root).value
    raw = [record for record in draft.effective.base.layout.records if record.layer == 'LI' and record.rect.x0 >= 200]
    refs = {node.ref for node in draft.nodes if node.region.owner_id in {record.id for record in raw}}
    assert len(refs) == 2
    matching = [edge for edge in draft.edges if set(edge.endpoints) == refs]
    assert len(matching) == 1 and matching[0].kind == 'same_layer'
    first = next(node for node in draft.nodes if node.region.owner_id == next(record.id for record in raw if record.rect.x0 == 200))
    assert len(first.region.rectangles) > 1
    axes = next(layer for layer in draft.effective.base.partition.layers if layer.layer == 'LI')
    # CUT's x=207/213 and y=205 need not be pre-existing drawn LI axes.
    assert 207 not in axes.xs and 213 not in axes.xs


@pytest.mark.parametrize('hole,connector,status', [
    ((207, 207, 213, 213), (202, 202, 206, 206), 'pass'),  # Expanded right/top exactly touch hole boundary.
    ((207, 207, 213, 213), (203, 203, 207, 207), 'violation'),
    ((207, 207, 213, 213), (202, 204, 218, 206), 'pass'),  # Expanded box spans several pieces.
    ((207, 207, 213, 213), (202, 202, 218, 218), 'violation'),  # bbox encloses; actual hole remains.
])
def test_actual_multi_piece_li_enclosure_uses_exact_set_not_bbox(tmp_path, hole, connector, status):
    root = ready_copy(tmp_path)
    append_records(root, [('LI', (200, 200, 220, 220)), ('CUT', hole),
                          ('M1', (198, 198, 222, 222)), ('VIA0', connector)])
    draft = build_local(root).value
    record = next(record for record in draft.effective.base.layout.records
                  if record.layer == 'VIA0' and record.rect.bounds == connector)
    assert len([edge for edge in draft.edges if edge.connector_id == record.id]) == 1
    audit = next(audit for audit in draft.audits if audit.connector_id == record.id and audit.layer == 'LI')
    assert audit.status == status
    node = next(node for node in draft.nodes if node.ref == audit.node_ref)
    assert len(node.region.rectangles) > 1
    assert encloses_connector(node.region.rectangles, record.rect, Fraction(1)) is (status == 'pass')


def test_record_order_query_names_change_provenance_not_topology_semantics(tmp_path):
    first, second = ready_copy(tmp_path / 'first'), ready_copy(tmp_path / 'second')
    extra = [('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 141, 26)), ('VIA0', (29, 50, 33, 54))]
    rewrite_geometry(first, append=extra)
    rewrite_geometry(second, append=extra, reverse=True)
    query_only_rename(second)
    a, b = build_local(first).value, build_local(second).value
    assert a.semantic_digest == b.semantic_digest and a.ref != b.ref
    assert len(a.nodes) == len(b.nodes) and len(a.edges) == len(b.edges)


def test_negative_translation_keeps_graph_membership_and_exact_geometry(tmp_path, accepted):
    root = ready_copy(tmp_path)
    edit_geometry(root, translate=(-1000, -2000), vertices=True, reorder=True)
    draft = build_local(root).value
    assert len(draft.nodes) == 14 and len(draft.edges) == 8 and len(draft.components) == 6
    assert all(rect.x1 < 0 and rect.y1 < 0 for node in draft.nodes for rect in node.region.rectangles)
    assert draft.local_enclosure_status == 'pass'


@pytest.mark.parametrize('operator', ['same_layer_contact/1', 'cross_layer_contact/1'])
def test_consumed_physical_contact_semantics_must_match_supported_version(tmp_path, operator):
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda owner: owner['operators'].__setitem__(operator, 'union by labels and bboxes'))
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedLocalContactOperator'
    assert result.issues[0].source.uri == 'tech/physical.json'
    assert result.completed == effective.completed


@pytest.mark.parametrize('layer,key,value', [
    ('VIA0', 'electrical_connects', ['OD', 'M1']),
    ('CONTACT', 'contact_predicate', 'bbox_touch'),
    ('GCONTACT', 'enclosure_rule', 'T04.body'),
    ('M1', 'purpose', 'annotation'),
])
def test_consumed_drawn_policy_is_not_inferred_from_names(tmp_path, layer, key, value):
    root = ready_copy(tmp_path)
    def mutate(owner):
        next(row for row in owner['layers'] if row['name'] == layer)[key] = value
    change_owner(root, 'drawn', mutate)
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedLocalContactOperator'
    assert result.issues[0].source.uri == 'tech/drawn.json'


@pytest.mark.parametrize('key,value', [
    ('predicate', 'bbox containment'), ('scope', 'all layers and external context merged'),
    ('parameters', {'enclosure_nm': 2}),
])
def test_local_t05_semantics_are_explicitly_checked(tmp_path, key, value):
    root = ready_copy(tmp_path)
    def mutate(owner):
        next(row for row in owner['rules'] if row['id'] == 'T05.contact_enclosure')[key] = value
    change_owner(root, 'rules', mutate)
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedLocalContactOperator'
    assert result.issues[0].source.uri == 'tech/rules.json'


@pytest.mark.parametrize('layer', ['BTAP_N', 'BTAP_P'])
def test_nonempty_local_body_connector_is_located_unsupported(tmp_path, layer):
    root = ready_copy(tmp_path)
    append_records(root, [(layer, (2, 2, 6, 6))])
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedLocalBodyContact'
    assert result.issues[0].source.uri == 'source.gds'
    assert result.completed == effective.completed


@pytest.mark.parametrize('owner,kind,key,value', [
    ('rules', 'T05.contact_enclosure', 'required', False),
    ('rules', 'T05.contact_enclosure', 'missing_context_policy', 'defer'),
    ('rules', 'T05.contact_enclosure', 'relation_basis', 'same_component'),
    ('rules', 'T05.contact_enclosure', 'exact_evaluator_ref', 'w004-toy-predicate/T05.contact_enclosure/3'),
    ('drawn', 'BODY_N', 'role', 'interconnect'),
    ('drawn', 'M1', 'role', 'gate'),
])
def test_existing_reader_contract_rejects_invalid_schema_before_local_graph(tmp_path, owner, kind, key, value):
    from layauto_v2.importers import read_inputs
    root = ready_copy(tmp_path)
    def mutate(document):
        collection, identity = ('rules', 'id') if owner == 'rules' else ('layers', 'name')
        next(row for row in document[collection] if row[identity] == kind)[key] = value
    change_owner(root, owner, mutate)
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'error' and parsed.value is None
    # The body profile owns body layer typing; selected context associations
    # separately check that their local rail points to an interconnect layer.
    expected_uri = ('body/context.json' if kind == 'M1' else
                    'tech/physical.json' if owner == 'drawn' else 'tech/' + owner + '.json')
    assert parsed.issues[0].source.uri == expected_uri


def test_overlapping_layers_without_declared_connector_do_not_gain_cross_layer_edge(tmp_path):
    root = ready_copy(tmp_path)
    append_records(root, [('LI', (200, 200, 210, 210)), ('M1', (200, 200, 210, 210))])
    draft = build_local(root).value
    extras = [node for node in draft.nodes if node.region.rectangles[0].x0 == 200]
    assert {node.layer for node in extras} == {'LI', 'M1'}
    refs = {node.ref for node in extras}
    assert not any(set(edge.endpoints) == refs for edge in draft.edges)
    assert {component.members[0] for component in draft.components if len(component.members) == 1} >= refs


def test_located_endpoint_error_roundtrips_without_false_success(tmp_path):
    from dataclasses import replace
    from layauto_v2.normalization.local_connectivity_codec import decode_record, encode_record, record_digest
    root = ready_copy(tmp_path)
    append_records(root, [('LI', (28, 30, 34, 55))])
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.value is None
    assert result.input is effective and result.completed == effective.completed
    wire = encode_record(result)
    rebuilt = decode_record(wire)
    assert rebuilt == result and encode_record(rebuilt) == wire
    assert record_digest(rebuilt) == record_digest(result)
    with pytest.raises(ValueError):
        replace(result, status='success', issues=())
    with pytest.raises(ValueError):
        replace(result, issues=())


def test_coverage_discloses_local_execution_and_retains_unconsumed_owner_semantics(tmp_path, accepted):
    root = ready_copy(tmp_path)
    spacing, lifecycle = 'future independent spacing interpretation', 'future independent lifecycle interpretation'
    def mutate(owner):
        owner['operators']['spacing/1'] = spacing
        owner['operators']['lifecycle/1'] = lifecycle
    change_owner(root, 'physical', mutate)
    draft = build_local(root).value
    assert draft.binding.physical.payload['operators']['spacing/1'] == spacing
    assert draft.binding.physical.payload['operators']['lifecycle/1'] == lifecycle
    coverage = draft.coverage
    assert coverage['scope'] == 'local_flat_cell/1'
    assert set(coverage['executed_contact_operators']) == {'same_layer_contact/1', 'cross_layer_contact/1'}
    assert set(coverage['executed_rules']) == {'T05.contact_enclosure:local CONTACT,VIA0,GCONTACT sides only'}
    assert {'body_context/2', 'spacing/1', 'lifecycle/1'} <= set(coverage['unconsumed_operator_refs'])
    assert {'external_body_and_BTAP', 'complete_T05_and_mandatory_rule_set',
            'manufacturing_coordinates_and_region_occupancy', 'FIN_device_extraction',
            'semantic_net_join_and_annotation', 'lifecycle', 'baseline_publication',
            'no_change_terminal_and_Stage6'} <= set(coverage['deferred'])
    assert draft.semantic_digest == accepted.value.semantic_digest


def test_unknown_conductive_role_cannot_be_silently_ignored(tmp_path):
    root = ready_copy(tmp_path)
    def mutate(owner):
        next(row for row in owner['layers'] if row['name'] == 'MARKER')['role'] = 'interconnect'
    change_owner(root, 'drawn', mutate)
    effective = build_effective(root)
    result = build_local_connectivity(effective)
    assert result.status == 'error' and result.issues[0].code == 'UnsupportedLocalContactOperator'
    assert result.issues[0].source.uri == 'tech/drawn.json'
