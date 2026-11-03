"""W009 independent geometry mathematics and actual captured-input composition."""
from __future__ import annotations

import builtins
import io
import random
from collections import Counter
from dataclasses import fields, replace
from pathlib import Path

import pytest

from layauto_v2.domain.geometry import Rect
from layauto_v2.domain.publication import InputsReady
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization.codec import record_digest as semantic_digest
from layauto_v2.normalization.effective import build_effective_geometry
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import record_digest as geometry_digest
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready, geometry_from_parse_result
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.regions import slab_difference

from w005_cases import FIXTURE, inventory
from w006_cases import caller_request
from w007_cases import query_only_rename, read, ready_copy
from w008_geometry_cases import edit_geometry
from w009_cases import (
    area, change_owner, hand_channel_partition, independent_difference, region_boxes,
    rewrite_geometry, special_input,
)


def build(root=FIXTURE):
    geometry = build_geometry(geometry_from_parse_result(read(root)))
    assert geometry.status == 'success', geometry.issues
    result = build_effective_geometry(geometry)
    assert result.status == 'success', result.issues
    assert result.value is not None
    return result


@pytest.fixture(scope='module')
def accepted():
    return build()


def no_extra_claims(value):
    forbidden = {'physical_edges', 'components', 'net_id', 'device_id', 'baseline',
                 'no_change', 'terminal', 'coordinate_ref', 'final_snapshot_id',
                 'deployment_disposition', 'extraction_equal', 'body_complete'}
    assert not forbidden & {field.name for field in fields(value)}


def test_actual_w005_chain_preserves_hand_geometry_sources_and_prior_facts_without_io(monkeypatch):
    before = inventory(FIXTURE)
    parsed = read(FIXTURE)
    semantic = normalize(from_parse_result(parsed))
    semantic_before = semantic_digest(semantic)
    geometry = build_geometry(geometry_from_parse_result(parsed))
    geometry_before = geometry_digest(geometry)

    def forbidden(*args, **kwargs):
        pytest.fail('effective geometry must consume captured data without IO')

    with monkeypatch.context() as patch:
        for name in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, name, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_effective_geometry(geometry)
    assert result.status == 'success' and not result.issues
    draft = result.value
    assert draft.base is geometry.value
    assert result.input is geometry
    assert result.completed == parsed.completed
    assert result.body_evidence is geometry.body_evidence
    assert geometry_digest(geometry) == geometry_before
    assert semantic_digest(semantic) == semantic_before
    assert semantic.value.device_seeds and semantic.value.net_seeds
    assert len(draft.base.layout.records) == 40
    assert len(draft.base.fragments) == 41
    assert len(draft.records) == 5  # Three LI and two independently traced OD records.
    physical_ref = next(record for record in parsed.completed if record.kind == 'tech').sources[3]
    assert draft.physical.sources == (physical_ref,)
    assert draft.physical.payload == parsed.value['tech']['physical']
    channels, terminals = [], []
    for raw in draft.base.layout.records:
        if raw.layer not in ('OD', 'LI'):
            continue
        derived = draft.for_record(raw.id)
        assert derived.record_id == raw.id
        assert derived.unit_ref == raw.unit_ref
        assert derived.operator_ref == draft.operators.ref
        if raw.layer == 'LI':
            assert derived.operation == 'cut' and not derived.contributors
            assert region_boxes(derived) == (raw.rect.bounds,)
        else:
            roles = hand_channel_partition(derived, raw.rect.bounds)
            channels.extend(box.bounds for box in roles['channel'].rectangles)
            terminals.extend((role, roles[role].rectangles[0].bounds) for role in ('S', 'D'))
            assert all(region.owner_id == raw.id for region in derived.regions)
            assert len(derived.contributors) == 1
            gate = draft.base.layout.record(derived.contributors[0])
            assert gate.layer == 'POLY' and gate.rect.bounds == (58, 10, 62, 190)
        for region in derived.regions:
            assert region.unit_ref == raw.unit_ref
            assert region.operator_ref == draft.operators.ref
            assert all(piece.region_ref == region.ref for piece in region.pieces)
    assert sorted(channels) == [(58, 20, 62, 70), (58, 110, 62, 180)]
    assert set(terminals) == {('S', (20, 20, 58, 70)), ('D', (62, 20, 100, 70)),
                              ('S', (20, 110, 58, 180)), ('D', (62, 110, 100, 180))}
    for value in (result, draft, *draft.records):
        no_extra_claims(value)
    assert inventory(FIXTURE) == before


def test_real_w006_readback_matches_direct_chain_and_does_not_advance_attempt(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id='w009-actual-composition'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse = repository.read(ready.parse_ref)
    tool = repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    direct = build(root)
    semantic = normalize(from_parse_result(parse.result))
    semantic_before = semantic_digest(semantic)

    def forbidden(*args, **kwargs):
        pytest.fail('pure W008/W009 composition cannot acquire, access repository or publish')

    with monkeypatch.context() as patch:
        for method in ('open', 'read_bytes', 'read_text', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        patch.setattr(repository, 'read', forbidden)
        geometry = build_geometry(geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))
        result = build_effective_geometry(geometry)
    assert result.status == 'success'
    assert result.value == direct.value
    assert result.input.input.readback is not None
    assert semantic_digest(semantic) == semantic_before
    assert repository.load_attempt(ready.run_id) == attempt
    assert attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None


@pytest.mark.parametrize('target,cuts,expected_area', [
    ((0, 0, 10, 10), (), 100),
    ((0, 0, 10, 10), ((3, 3, 7, 7),), 84),
    ((0, 0, 10, 10), ((4, -1, 6, 11),), 80),
    ((0, 0, 10, 10), ((-1, 4, 11, 6),), 80),
    ((0, 0, 10, 10), ((4, -1, 6, 11), (-1, 4, 11, 6)), 64),
    ((0, 0, 10, 10), ((2, 2, 6, 8), (4, 4, 8, 9)), 64),
    ((0, 0, 10, 10), ((3, 3, 7, 7), (3, 3, 7, 7)), 84),
    ((0, 0, 10, 10), ((3, 3, 5, 7), (5, 3, 7, 7)), 84),
    ((0, 0, 10, 10), ((10, 0, 15, 10), (10, 10, 20, 20)), 100),
    ((0, 0, 10, 10), ((20, 20, 30, 30),), 100),
    ((0, 0, 10, 10), ((-1, -1, 11, 11),), 0),
    ((0, 0, 10, 10), ((0, 5, 5, 10), (5, 0, 10, 5)), 50),
    ((-20, -30, -10, -10), ((-17, -40, -13, -5),), 120),
    ((2**80, -2**80, 2**80 + 20, -2**80 + 30),
     ((2**80 + 5, -2**80 + 10, 2**80 + 15, -2**80 + 20),), 500),
])
def test_exact_difference_hand_cases_and_independent_finite_arrangement(target, cuts, expected_area):
    result = slab_difference(Rect(*target), [Rect(*cut) for cut in cuts])
    bounds = tuple(rect.bounds for rect in result)
    assert bounds == tuple(sorted(bounds))
    assert independent_difference(target, cuts, bounds) == expected_area
    assert result == slab_difference(Rect(*target), [Rect(*cut) for cut in reversed(cuts)])


def test_difference_canonical_output_ignores_redundant_cut_partition_and_order():
    target = Rect(0, 0, 20, 20)
    whole = (Rect(4, 3, 16, 17),)
    fractured = (Rect(4, 3, 10, 17), Rect(10, 3, 16, 17),
                  Rect(7, 5, 14, 12), Rect(4, 3, 10, 17))
    expected = slab_difference(target, whole)
    assert slab_difference(target, fractured) == expected
    assert slab_difference(target, reversed(fractured)) == expected
    independent_difference(target.bounds, tuple(rect.bounds for rect in fractured),
                           tuple(rect.bounds for rect in expected))


def test_seeded_differences_have_no_missing_or_extra_coverage():
    rng = random.Random(9009)
    for _ in range(70):
        xs, ys = sorted(rng.sample(range(-12, 13), 2)), sorted(rng.sample(range(-12, 13), 2))
        target = (xs[0], ys[0], xs[1], ys[1])
        cuts = []
        for _ in range(rng.randrange(0, 9)):
            x, y = sorted(rng.sample(range(-15, 16), 2)), sorted(rng.sample(range(-15, 16), 2))
            cuts.append((x[0], y[0], x[1], y[1]))
        result = slab_difference(Rect(*target), [Rect(*cut) for cut in cuts])
        independent_difference(target, cuts, tuple(rect.bounds for rect in result))


def test_existing_cut_islands_has_exact_two_pieces_and_retains_remote_record(tmp_path):
    root = ready_copy(tmp_path)
    special_input(root)
    result = build(root)
    draft = result.value
    assert draft.base.layout.top == 'CUT_ISLANDS_SYNTH'
    assert len(draft.base.layout.records) == 4
    assert len(draft.base.fragments) == 3
    assert len(draft.records) == 2
    branch = next(record for record in draft.base.layout.records if record.layer == 'LI' and record.rect.x0 == 130)
    raw_branch = draft.base.for_record(branch.id)
    assert len(raw_branch) == 1 and raw_branch[0].rect.bounds == (130, 20, 150, 24)
    derived = draft.for_record(branch.id)
    assert len(derived.regions) == 2
    assert region_boxes(derived) == ((130, 20, 139, 24), (141, 20, 150, 24))
    assert sum(area(box) for box in region_boxes(derived)) == 72
    cut = draft.base.layout.record(derived.contributors[0])
    assert cut.layer == 'CUT' and cut.rect.bounds == (139, 18, 141, 26)
    independent_difference(branch.rect.bounds, (cut.rect.bounds,), region_boxes(derived))
    remote = next(record for record in draft.base.layout.records if record.layer == 'LI' and record.rect.x0 == 50)
    assert region_boxes(draft.for_record(remote.id)) == ((50, 20, 60, 24),)
    assert draft.for_record(remote.id).contributors == ()
    assert not any(record.rect.bounds in region_boxes(derived) for record in draft.base.layout.records)


@pytest.mark.parametrize('cuts,expected_area,regions', [
    (((203, 203, 207, 207),), 84, 1),  # Hole remains in one locally connected region.
    (((200, 205, 205, 210), (205, 200, 210, 205)), 50, 2),  # Point contact never merges.
    (((199, 199, 211, 211),), 0, 0),
    (((210, 200, 220, 210), (210, 210, 220, 220)), 100, 1),
])
def test_actual_cut_geometry_holes_point_contacts_empty_and_untouched(tmp_path, cuts, expected_area, regions):
    root = ready_copy(tmp_path)
    rewrite_geometry(root, append=[('LI', (200, 200, 210, 210))] + [('CUT', cut) for cut in cuts])
    draft = build(root).value
    target = next(record for record in draft.base.layout.records if record.layer == 'LI' and record.rect.x0 == 200)
    derived = draft.for_record(target.id)
    assert len(derived.regions) == regions
    assert independent_difference(target.rect.bounds, cuts, region_boxes(derived)) == expected_area
    expected_contributors = {record.id for record in draft.base.layout.records
                             if record.layer == 'CUT' and record.rect.intersection(target.rect) is not None}
    assert set(derived.contributors) == expected_contributors
    assert len(draft.base.for_record(target.id)) > 0
    assert all(region.owner_id == target.id for region in derived.regions)


def test_duplicate_targets_and_cuts_retain_every_record_identity(tmp_path):
    root = ready_copy(tmp_path)
    target = (200, 200, 220, 210)
    cut = (207, 199, 213, 211)
    rewrite_geometry(root, append=[('LI', target), ('LI', target), ('CUT', cut), ('CUT', cut)])
    draft = build(root).value
    targets = [record for record in draft.base.layout.records if record.layer == 'LI' and record.rect.bounds == target]
    assert len(targets) == 2 and targets[0].id != targets[1].id
    cut_ids = {record.id for record in draft.base.layout.records if record.layer == 'CUT'}
    assert len(cut_ids) == 2
    results = [draft.for_record(record.id) for record in targets]
    for derived in results:
        assert set(derived.contributors) == cut_ids
        assert region_boxes(derived) == ((200, 200, 207, 210), (213, 200, 220, 210))
        independent_difference(target, (cut, cut), region_boxes(derived))
    assert {region.ref for region in results[0].regions}.isdisjoint(region.ref for region in results[1].regions)


def test_hole_public_constructor_rejects_bbox_filling_missing_and_extra_coverage(tmp_path):
    root = ready_copy(tmp_path)
    target = (200, 200, 210, 210)
    rewrite_geometry(root, append=[('LI', target), ('CUT', (203, 203, 207, 207))])
    draft = build(root).value
    raw = next(record for record in draft.base.layout.records if record.layer == 'LI' and record.rect.bounds == target)
    derived = draft.for_record(raw.id)
    assert len(derived.regions) == 1
    region = derived.regions[0]
    assert tuple(rect.bounds for rect in region.rectangles) == (
        (200, 200, 203, 210), (203, 200, 207, 203),
        (203, 207, 207, 210), (207, 200, 210, 210))
    wrong_covers = (
        (Rect(*target),),  # Area and coverage grow by filling the actual hole.
        (region.rectangles[0],),  # An individually legal rectangle omits most valid coverage.
        (Rect(199, 200, 203, 210),) + region.rectangles[1:],  # A canonical connected cover adds a foreign band.
    )
    for wrong_cover in wrong_covers:
        # These are valid neutral connected/canonical regions on their own.
        wrong_region = replace(region, rectangles=wrong_cover)
        wrong_result = replace(derived, regions=(wrong_region,))
        with pytest.raises(ValueError):
            replace(draft, records=tuple(wrong_result if row.record_id == raw.id else row for row in draft.records))


@pytest.mark.parametrize('gates,code', [
    ((), 'AmbiguousGateStripe'),  # No gate.
    (((100, 10, 104, 190),), 'AmbiguousGateStripe'),  # Edge contact only.
    (((100, 70, 104, 100),), 'AmbiguousGateStripe'),  # A single corner contact.
    (((58, 10, 62, 190), (78, 10, 82, 190)), 'AmbiguousGateStripe'),
    (((58, 30, 62, 60),), 'UnsupportedTerminalSplit'),  # Interior hole leaves one residual.
    (((10, 40, 110, 44),), 'UnsupportedTerminalSplit'),  # Top/bottom split is not left/right.
    (((20, 10, 24, 190),), 'UnsupportedTerminalSplit'),  # No left terminal.
    (((96, 10, 100, 190),), 'UnsupportedTerminalSplit'),  # No right terminal.
    (((10, 10, 110, 190),), 'UnsupportedTerminalSplit'),  # Channel consumes all active.
])
def test_actual_gate_profile_rejects_absent_ambiguous_or_nonterminal_splits(tmp_path, gates, code):
    root = ready_copy(tmp_path)
    # A single active isolates the intended failure: another OD lacking a gate
    # must not hide a partial-height or incorrectly oriented split rejection.
    rewrite_geometry(root, replace_layers={'OD': ((20, 20, 100, 70),), 'POLY': gates})
    parsed = read(root)
    geometry = build_geometry(geometry_from_parse_result(parsed))
    result = build_effective_geometry(geometry)
    assert result.status == 'error' and result.value is None
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == code
    assert issue.source.uri == 'source.gds'
    assert issue.source.byte_offset is not None and issue.source.record_index is not None
    assert issue.source.field
    assert result.completed == parsed.completed
    assert result.input is geometry
    assert result.body_evidence == geometry.body_evidence


def test_third_active_and_duplicate_geometry_are_not_device_name_or_count_oracles(tmp_path):
    root = ready_copy(tmp_path)
    extra_active = (120, 20, 150, 70)
    rewrite_geometry(root, append=[('OD', extra_active), ('OD', (20, 20, 100, 70)),
                                  ('POLY', (133, 10, 137, 80)), ('POLY', (58, 10, 62, 190))])
    draft = build(root).value
    active_records = [record for record in draft.base.layout.records if record.layer == 'OD']
    assert len(active_records) == 4
    assert Counter(region.role for row in draft.records for region in row.regions)['channel'] == 4
    for active in active_records:
        derived = draft.for_record(active.id)
        roles = hand_channel_partition(derived, active.rect.bounds)
        expected = (133, 20, 137, 70) if active.rect.bounds == extra_active else (58, active.rect.y0, 62, active.rect.y1)
        assert roles['channel'].rectangles[0].bounds == expected
        assert len(derived.contributors) == (1 if active.rect.bounds == extra_active else 2)


def test_gds_reorder_and_query_renames_preserve_geometry_multiset_semantics(tmp_path):
    first_root = ready_copy(tmp_path / 'first')
    second_root = ready_copy(tmp_path / 'second')
    additions = [('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 141, 26)),
                 ('CUT', (139, 18, 141, 26))]
    rewrite_geometry(first_root, append=additions)
    rewrite_geometry(second_root, append=additions, reverse=True)
    query_only_rename(second_root)
    first, second = build(first_root), build(second_root)
    assert first.value.semantic_digest == second.value.semantic_digest
    assert first.value.ref != second.value.ref  # Different source positions/bytes retain distinct provenance.
    assert len(first.value.records) == len(second.value.records)
    assert Counter((record.layer, record.rect.bounds) for record in first.value.base.layout.records) == Counter(
        (record.layer, record.rect.bounds) for record in second.value.base.layout.records)


def test_negative_translation_uses_exact_active_and_gate_coordinates(tmp_path):
    root = ready_copy(tmp_path)
    edit_geometry(root, translate=(-1000, -2000), vertices=True, reorder=True)
    draft = build(root).value
    for record in draft.base.layout.records:
        if record.layer == 'OD':
            roles = hand_channel_partition(draft.for_record(record.id), record.rect.bounds)
            assert roles['channel'].rectangles[0].bounds == (-942, record.rect.y0, -938, record.rect.y1)
    assert draft.base.layout.units.canonical_tick_nm == 1


@pytest.mark.parametrize('section,key,wrong,field', [
    ('fin_count_profile', 'recognized_channel_operator', 'bbox_overlap_or_point_contact',
     '/fin_count_profile/recognized_channel_operator'),
    ('device_extraction_contract', 'sd_policy', 'swap freely; top is S and bottom D',
     '/device_extraction_contract/sd_policy'),
    ('device_extraction_contract', 'gate_operator', 'connect OD source and drain as conductor',
     '/device_extraction_contract/gate_operator'),
    ('operators', 'rectangle_set_difference/1', 'subtract only a bbox of all cuts',
     '/operators/rectangle_set_difference~11'),
    ('operators', 'terminal_split/1', 'union OD source and drain', '/operators/terminal_split~11'),
])
def test_same_named_consumed_operator_with_wrong_semantics_is_located_rejection(tmp_path, section, key, wrong, field):
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda document: document[section].__setitem__(key, wrong))
    parsed = read(root)  # W005 accepts this versioned textual field; W009 must interpret it explicitly.
    geometry = build_geometry(geometry_from_parse_result(parsed))
    result = build_effective_geometry(geometry)
    assert result.status == 'error' and result.value is None
    assert len(result.issues) == 1
    assert result.issues[0].code == 'UnsupportedRegionOperator'
    assert result.issues[0].source.uri == 'tech/physical.json'
    assert result.issues[0].source.field == field
    physical_source = next(source for source in parsed.sources if source.uri == 'tech/physical.json')
    assert result.issues[0].source.sha256 == physical_source.sha256
    assert result.completed == parsed.completed


@pytest.mark.parametrize('layer,role', [('OD', 'gate'), ('POLY', 'interconnect'),
                                        ('LI', 'gate'), ('CUT', 'marker')])
def test_all_four_consumed_drawn_roles_are_checked_before_role_filtering(tmp_path, layer, role):
    root = ready_copy(tmp_path)
    def mutate(document):
        row = next(row for row in document['layers'] if row['name'] == layer)
        row['role'] = role
        if layer == 'CUT':
            # Keep the earlier grammar valid: non-cut roles cannot retain cut fields.
            del row['cut_target']
            del row['effective_geometry_operator']
    change_owner(root, 'drawn', mutate)
    geometry = build_geometry(geometry_from_parse_result(read(root)))
    result = build_effective_geometry(geometry)
    assert result.status == 'error'
    assert result.issues[0].code == 'UnsupportedRegionOperator'
    assert result.issues[0].source.uri == 'tech/drawn.json'
    assert result.issues[0].source.field.endswith('/role')


@pytest.mark.parametrize('key,wrong', [('cut_target', 'M1'),
                                     ('effective_geometry_operator', 'same_layer_contact/1')])
def test_declared_cut_target_and_executable_operator_are_checked(tmp_path, key, wrong):
    root = ready_copy(tmp_path)
    def mutate(document):
        next(row for row in document['layers'] if row['name'] == 'CUT')[key] = wrong
    change_owner(root, 'drawn', mutate)
    geometry = build_geometry(geometry_from_parse_result(read(root)))
    result = build_effective_geometry(geometry)
    assert result.status == 'error' and result.value is None
    assert result.issues[0].source.uri == 'tech/drawn.json'
    assert result.issues[0].source.field.endswith('/' + key)


@pytest.mark.parametrize('section,key,wrong', [
    ('fin_count_profile', 'id', 'toy_fin_crossing/2'),
    ('fin_count_profile', 'fin_representation', 'undeclared_dynamic_fins'),
    ('fin_count_profile', 'effective_active_operator', 'identity_M1'),
    ('device_extraction_contract', 'id', 'toy_device_terminal_context/3'),
    ('operators', 'delete', 'terminal_split/1'),
])
def test_existing_reader_profile_and_missing_operator_failures_are_preserved(tmp_path, section, key, wrong):
    root = ready_copy(tmp_path)
    def mutate(document):
        if key == 'delete':
            del document[section][wrong]
        else:
            document[section][key] = wrong
    change_owner(root, 'physical', mutate)
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'error' and parsed.value is None
    assert parsed.issues[0].source.uri == 'tech/physical.json'
    assert parsed.issues[0].code in ('InvalidSchema', 'RequiredOperatorUnavailable')


def test_unconsumed_contact_semantics_are_retained_without_claiming_execution(tmp_path):
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda document: document['operators'].__setitem__(
        'same_layer_contact/1', 'future contact definition; deliberately not executed by W009'))
    draft = build(root).value
    assert draft.physical.payload['operators']['same_layer_contact/1'].startswith('future contact')
    consumed_operator_fields = {field for field in draft.operators.consumed if field.startswith('/operators/')}
    assert consumed_operator_fields == {'/operators/rectangle_set_difference~11', '/operators/terminal_split~11'}
