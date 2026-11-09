"""W011 real captures, complete independent crossing sets and scope witnesses."""
from __future__ import annotations

import builtins
import io
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.publication import InputsReady
from layauto_v2.normalization import build_effective_geometry, build_geometry, build_local_connectivity
from layauto_v2.normalization.channel_identity import build_channel_identity
from layauto_v2.normalization.channel_identity_codec import record_digest
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready
from layauto_v2.normalization.local_connectivity_codec import record_digest as local_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

from w005_cases import FIXTURE, apply_case, copy_input, inventory, read_json, rebind, without_cache
from w006_cases import caller_request
from w007_cases import ready_copy
from w009_cases import change_owner, rewrite_geometry
from w010_cases import append_records, build_local
from w011_cases import EXPECTED_CHANNELS, EXPECTED_FIN_Y, build, change_cdl, change_seeds


@pytest.fixture(scope='module')
def accepted():
    result = build()
    assert result.status == 'success', result.issues
    return result


def by_device(draft):
    return {association.device_id.name: next(row for row in draft.measurements
            if row.channel_ref == association.channel_ref) for association in draft.associations}


def channel_rect(draft, ref):
    return next(region.rectangles[0].bounds for record in draft.local.effective.records
                for region in record.regions if region.ref == ref)


def test_actual_direct_composition_is_pure_and_retains_original_inputs(monkeypatch):
    before = inventory(FIXTURE)
    local = build_local()
    identity = local_digest(local)
    def forbidden(*args, **kwargs):
        pytest.fail('W011 attempted acquisition or publication')
    with monkeypatch.context() as patch:
        for method in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_channel_identity(local)
    assert result.status == 'success' and not result.issues
    assert result.input is local and result.value.local is local.value
    assert result.completed == local.completed
    assert local_digest(local) == identity
    assert result.semantic.value.source == result.value.source
    assert result.semantic.value.target and result.semantic.value.net_seeds
    assert result.input.body_evidence is local.body_evidence
    assert inventory(FIXTURE) == before


def test_actual_w006_readback_preserves_unsealed_attempt_and_direct_result(tmp_path, monkeypatch):
    root = ready_copy(tmp_path)
    direct = build(root)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(root, run_id='w011-readback'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    local = build_local_connectivity(build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))))
    def forbidden(*args, **kwargs):
        pytest.fail('W011 attempted acquisition or repository read')
    with monkeypatch.context() as patch:
        patch.setattr(repository, 'read', forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        for method in ('open', 'read_bytes', 'read_text', 'resolve'):
            patch.setattr(Path, method, forbidden)
        result = build_channel_identity(local)
    assert result.status == 'success' and result.value == direct.value
    assert result.input.input.input.input.readback is not None
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None


def test_normal_result_matches_all_independent_crossings_and_retains_18_fin(accepted):
    draft = accepted.value
    spec, oracle = read_json(FIXTURE / 'spec.json'), read_json(FIXTURE / 'oracle.json')
    names = {tuple(row['bbox']): row['id'] for row in spec['shapes'] if row['layer'] == 'FIN'}
    records = draft.local.effective.base.layout.records
    fins = {row.id: row for row in records if row.layer == 'FIN'}
    assert len(fins) == 18 and len(draft.associations) == 2
    measurements = by_device(draft)
    for name, measurement in measurements.items():
        assert channel_rect(draft, measurement.channel_ref) == EXPECTED_CHANNELS[name]
        assert measurement.length_nm == 4 and measurement.count == len(EXPECTED_FIN_Y[name])
        assert {row.fin_id for row in measurement.evaluations} == set(fins)
        crossings = [row for row in measurement.evaluations if row.status == 'qualified']
        expected_boxes = {(58, lo, 62, hi) for lo, hi in EXPECTED_FIN_Y[name]}
        assert {row.crossing.bounds for row in crossings} == expected_boxes
        assert all(row.width_nm == 2 and row.source == fins[row.fin_id].source for row in crossings)
        hand = next(row for row in oracle['crossings'] if row['device'] == name)
        assert {names[fins[row.fin_id].rect.bounds] for row in crossings} == set(hand['fin_ids'])
        assert all(row.width_nm == 2 for row in measurement.evaluations)
    assert sum(row.status == 'qualified' for measurement in draft.measurements for row in measurement.evaluations) == 12
    assert len(draft.comparisons) == 16  # NFIN/L per channel, plus every observed FIN width.
    assert draft.comparison_status == 'equal' and not draft.differences
    assert all(row.full_coverage and row.coverage_fraction == 1 for row in draft.associations)
    assert len(draft.local.components) == 6 and len(draft.local.edges) == 8
    assert draft.local.local_enclosure_status == 'pass'


def test_existing_extraction_mismatch_is_actual_four_against_source_five(tmp_path):
    root = copy_input(tmp_path)
    apply_case(root, 'extraction_mismatch')
    without_cache(root)
    result = build(root)
    assert result.status == 'success'
    rows = by_device(result.value)
    assert rows['MN0'].count == 4 and rows['MP0'].count == 7
    touching = [row for row in rows['MN0'].evaluations if row.status == 'touch']
    assert any(result.value.local.effective.base.layout.record(row.fin_id).rect.bounds == (10, 64, 110, 66)
               for row in touching)
    differences = result.value.differences
    assert len(differences) == 1
    assert differences[0].axis == 'fins_per_finger'
    assert differences[0].measured == 4 and differences[0].declared.exact == 5
    assert result.value.comparison_status == 'mismatch'


def test_source_l_and_w_mismatches_are_all_retained_and_target_is_separate(tmp_path):
    root = ready_copy(tmp_path)
    change_cdl(root, 'source', 'L=4n W=2n', 'L=5n W=3n')
    result = build(root)
    assert result.status == 'success'
    assert {row.count for row in result.value.measurements} == {5, 7}
    differences = result.value.differences
    assert len(differences) == 14
    assert sum(row.axis == 'channel_length' for row in differences) == 2
    assert sum(row.axis == 'fin_width' for row in differences) == 12
    assert all(row.measured == Fraction(4 if row.axis == 'channel_length' else 2, 10**9)
               for row in differences)
    assert result.semantic.value.differences


def test_target_only_multiple_axes_do_not_change_source_geometry(tmp_path, accepted):
    root = ready_copy(tmp_path)
    change_cdl(root, 'target', 'NFIN=5 NF=1 M=1 L=4n W=2n VT=toy',
               'NFIN=3 NF=1 M=1 L=6n W=3n VT=toy')
    result = build(root)
    assert result.status == 'success' and result.value.comparison_status == 'equal'
    assert not result.value.differences and len(result.semantic.value.differences) == 3
    assert {name: row.count for name, row in by_device(result.value).items()} == {'MN0': 5, 'MP0': 7}
    assert [(row.axis, row.measured) for row in result.value.comparisons] == [
        (row.axis, row.measured) for row in accepted.value.comparisons]


@pytest.mark.parametrize('boxes,coverage', [
    (((58, 20, 62, 40),), Fraction(2, 5)),
    (((58, 20, Fraction(121, 2), 70),), Fraction(5, 8)),
    (((58, 20, 62, 45), (58, 45, 62, 70)), Fraction(1)),
    (((58, 20, 62, 50), (58, 40, 62, 70)), Fraction(1)),
])
def test_unique_partial_and_multiple_same_identity_seeds_keep_exact_coverage(tmp_path, boxes, coverage):
    root = ready_copy(tmp_path)
    change_seeds(root, 'Q17', boxes)
    result = build(root)
    assert result.status == 'success'
    association = next(row for row in result.value.associations if row.device_id.name == 'MN0')
    assert association.coverage_fraction == coverage and association.full_coverage is (coverage == 1)
    assert len(association.seed_refs) == len(boxes)
    locations = [row for row in result.value.locations if row.seed_ref in association.seed_refs]
    assert len(locations) == len(boxes) and all(len(row.intersections) == 1 for row in locations)
    assert by_device(result.value)['MN0'].count == 5
    assert len(result.semantic.value.net_seeds) == 8


@pytest.mark.parametrize('case', ('missing', 'outside', 'ambiguous', 'conflict', 'split_identity', 'extra_channel'))
def test_all_seeds_devices_and_channels_participate_without_fallback(tmp_path, case):
    root = ready_copy(tmp_path)
    if case == 'missing': change_seeds(root, 'Q17', ())
    elif case == 'outside': change_seeds(root, 'Q17', ((58, 70, 62, 80),))
    elif case == 'ambiguous': change_seeds(root, 'Q17', ((58, 20, 62, 180),))
    elif case == 'conflict': change_seeds(root, 'Q93', ((58, 20, 62, 70),))
    elif case == 'split_identity': change_seeds(root, 'Q17', ((58, 20, 62, 70), (58, 110, 62, 180)))
    else: append_records(root, [('OD', (200, 20, 280, 70)), ('POLY', (238, 10, 242, 80))])
    result = build(root)
    assert result.status == 'error' and result.value is not None and result.issues
    assert all(issue.source is not None for issue in result.issues)
    assert result.completed == result.input.completed
    assert len(result.value.measurements) == (3 if case == 'extra_channel' else 2)
    if case == 'ambiguous':
        assert any(len(row.intersections) == 2 for row in result.value.locations)
    if case == 'split_identity':
        assert len(result.value.seeds) == 3


@pytest.mark.parametrize('extra,kind', [((10, 24, 110, 26), 'duplicate'), ((10, 25, 110, 27), 'overlap')])
def test_unproven_duplicate_or_overlapping_fin_never_claims_valid_count(tmp_path, extra, kind):
    root = ready_copy(tmp_path)
    append_records(root, [('FIN', extra)])
    result = build(root)
    assert result.status == 'error' and result.value is not None
    rows = by_device(result.value)
    assert rows['MN0'].count is None and rows['MP0'].count == 7
    assert rows['MN0'].unresolved_relations and result.value.fin_relations
    assert any(row.relation == kind for row in result.value.fin_relations)
    assert len([row for row in result.value.local.effective.base.layout.records if row.layer == 'FIN']) == 19
    assert any(row.axis == 'channel_length' and row.device_id.name == 'MN0' for row in result.value.comparisons)
    assert any(row.axis == 'fin_width' and row.device_id.name == 'MN0' for row in result.value.comparisons)
    assert not any(row.axis == 'fins_per_finger' and row.device_id.name == 'MN0' for row in result.value.comparisons)
    if kind == 'duplicate':
        from dataclasses import replace
        from layauto_v2.normalization.channel_identity_codec import decode_record, encode_record
        assert decode_record(encode_record(result.value.fin_relations[0])) == result.value.fin_relations[0]
        assert decode_record(encode_record(result)) == result
        with pytest.raises(ValueError): replace(result, status='success', issues=())
        with pytest.raises(ValueError): replace(result.value, fin_relations=(), issues=())


def test_duplicate_fin_outside_channels_is_retained_without_poisoning_counts(tmp_path):
    root = ready_copy(tmp_path)
    append_records(root, [('FIN', (10, 194, 110, 196))])
    result = build(root)
    assert result.status == 'success' and result.value.fin_relations
    assert {row.count for row in result.value.measurements} == {5, 7}


def test_partial_crossing_preserves_unknown_count_and_all_decidable_l_w(tmp_path):
    root = ready_copy(tmp_path)
    append_records(root, [('FIN', (59, 27, 110, 29))])
    result = build(root)
    assert result.status == 'error'
    row = by_device(result.value)['MN0']
    assert row.count is None and any(item.status == 'partial' for item in row.evaluations)
    assert row.length_nm == 4
    assert sum(item.axis == 'fin_width' and item.device_id.name == 'MN0' for item in result.value.comparisons) >= 5


def test_same_long_fin_crosses_channels_at_two_distinct_x_ranges(tmp_path):
    root = ready_copy(tmp_path)
    rewrite_geometry(root, replace_layers={'FIN': ((10, 24, 250, 26),)},
                     append=(('OD', (180, 20, 260, 70)), ('POLY', (208, 10, 212, 80))))
    result = build(root)
    assert result.status == 'error'  # The third channel lacks an identity, retained explicitly.
    matching = [row for row in result.value.measurements if row.count == 1]
    assert len(matching) == 2
    crossings = [next(item for item in row.evaluations if item.status == 'qualified') for row in matching]
    assert len({item.fin_id for item in crossings}) == 1
    assert {item.crossing.bounds for item in crossings} == {(58, 24, 62, 26), (208, 24, 212, 26)}


def test_zero_crossing_does_not_claim_width_was_verified(tmp_path):
    root = ready_copy(tmp_path)
    rewrite_geometry(root, replace_layers={'FIN': ((10, 194, 110, 196),)})
    result = build(root)
    assert result.status == 'success'
    assert all(row.count == 0 for row in result.value.measurements)
    assert not any(row.axis == 'fin_width' for row in result.value.comparisons)
    assert result.value.comparison_status != 'equal'


def test_record_reordering_changes_provenance_but_not_crossing_semantics(tmp_path, accepted):
    root = ready_copy(tmp_path)
    rewrite_geometry(root, reverse=True)
    result = build(root)
    assert result.status == 'success'
    def summary(draft):
        return {name: (row.count, row.length_nm, sorted(item.crossing.bounds for item in row.evaluations
                 if item.status == 'qualified')) for name, row in by_device(draft).items()}
    assert summary(result.value) == summary(accepted.value)
    assert result.value.local.ref != accepted.value.local.ref


def test_original_t05_violation_and_body_scope_remain_visible(tmp_path):
    root = ready_copy(tmp_path)
    apply_case(root, 'via_enclosure')
    local = build_local(root)
    identity = local_digest(local)
    result = build_channel_identity(local)
    assert result.status == 'success' and result.value.comparison_status == 'equal'
    assert result.value.local.local_enclosure_status == 'violation'
    assert result.value.local.audits == local.value.audits and result.value.local.edges == local.value.edges
    assert result.input.body_evidence == local.body_evidence
    assert local_digest(local) == identity


@pytest.mark.parametrize('owner,field,value', [
    ('physical', 'effective_fin_operator', 'foreign'),
    ('physical', 'qualification', 'positive overlap only'),
    ('derived', 'trim_operator', 'identity'),
    ('derived', 'annotation_match_tolerance_nm', 1),
])
def test_consumed_operator_changes_fail_at_located_component_boundary(tmp_path, owner, field, value):
    root = ready_copy(tmp_path)
    def mutate(document):
        target = document['fin_count_profile'] if owner == 'physical' else document['derived_registry'][0]
        target[field] = value
    change_owner(root, owner, mutate)
    result = build(root)
    assert result.status == 'error' and result.value is None and result.issues
    assert result.completed == result.input.completed


def test_unconsumed_t02_profile_numbers_are_retained_without_claiming_rule_execution(tmp_path):
    root = ready_copy(tmp_path)
    change_owner(root, 'physical', lambda doc: doc['fin_count_profile'].__setitem__('fin_pitch_nm', 11))
    result = build(root)
    assert result.status == 'success' and {row.count for row in result.value.measurements} == {5, 7}
    assert result.input.value.binding.physical.payload['fin_count_profile']['fin_pitch_nm'] == 11


@pytest.mark.parametrize('active,channel,fin,expected', [
    ((20, 20, 100, 70), (58, 20, 62, 70), (10, 24, 110, 26), 'qualified'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (58, 20, 62, 22), 'qualified'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (58, 68, 62, 70), 'qualified'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (59, 24, 110, 26), 'partial'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (10, 19, 110, 21), 'partial'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (10, 18, 110, 20), 'touch'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (10, 18, 58, 20), 'touch'),
    ((20, 20, 100, 70), (58, 20, 62, 70), (100, 24, 110, 26), 'outside'),
    ((2**90, -2**90, 2**90 + 100, -2**90 + 50),
     (2**90 + 38, -2**90, 2**90 + 42, -2**90 + 50),
     (2**90 - 10, -2**90 + 4, 2**90 + 110, -2**90 + 6), 'qualified'),
])
def test_exact_fin_geometry_against_independent_open_atom_witnesses(accepted, active, channel, fin, expected):
    from dataclasses import replace
    from layauto_v2.domain.geometry import Rect
    from layauto_v2.derive.fin_count import evaluate_fins
    from w011_cases import independent_fin_verdict
    assert independent_fin_verdict(active, channel, fin) == expected
    graph = accepted.value.local
    layout = graph.effective.base.layout
    original_channel = next(region for row in graph.effective.records for region in row.regions
                            if region.role == 'channel')
    active_record = layout.record(original_channel.owner_id)
    fin_record = next(row for row in layout.records if row.layer == 'FIN')
    def neutral_rectangle(record, bounds):
        x0, y0, x1, y1 = bounds
        points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))
        preserved = dict(record.preservation, xy=points, bbox=bounds)
        return replace(record, rect=Rect(*bounds), raw_xy=points, preservation=preserved)
    active_record = neutral_rectangle(active_record, active)
    fin_record = neutral_rectangle(fin_record, fin)
    region = replace(original_channel, rectangles=(Rect(*channel),))
    measurements, relations, issues = evaluate_fins((region,), (active_record, fin_record), 1,
                                                   accepted.value.binding_ref)
    assert len(measurements) == 1 and not relations
    row = measurements[0]
    assert row.evaluations[0].status == expected
    assert row.count == (None if expected == 'partial' else int(expected == 'qualified'))
    assert bool(issues) is (expected == 'partial')
    assert row.length_nm == channel[2] - channel[0]
    assert row.evaluations[0].width_nm == fin[3] - fin[1]


def test_additional_fin_role_declaration_is_not_silently_ignored(tmp_path):
    root = ready_copy(tmp_path)
    def mutate(document):
        import copy
        layer = copy.deepcopy(next(row for row in document['layers'] if row['name'] == 'FIN'))
        layer['name'], layer['stream_key']['layer'] = 'FIN_EXTRA', 99
        document['layers'].append(layer)
    change_owner(root, 'drawn', mutate)
    result = build(root)
    assert result.status == 'error' and result.value is None
    assert result.issues[0].code == 'UnsupportedChannelOperator'
    assert result.issues[0].source.uri == 'tech/drawn.json'


@pytest.mark.parametrize('failure', ('admission', 'identity'))
def test_w007_unsupported_admission_is_retained_without_false_channel_success(tmp_path, failure):
    root = ready_copy(tmp_path)
    if failure == 'admission':
        change_cdl(root, 'source', 'NF=1', 'NF=2')
    else:
        path = root / 'query/raw/iXref.temp'
        path.write_text(path.read_text().replace('MN0', 'UNDECLARED'))
        rebind(root)
    result = build(root)
    assert result.status == 'error' and result.value is None
    assert result.semantic.status == 'error' and result.semantic.issues
    assert [row.code for row in result.issues] == [row.code for row in result.semantic.issues]
    assert result.completed == result.input.completed


def test_actual_geometry_length_and_width_are_not_backfilled_from_profile_or_cdl(tmp_path):
    root = ready_copy(tmp_path)
    fins = [tuple(row['bbox']) for row in read_json(FIXTURE / 'spec.json')['shapes'] if row['layer'] == 'FIN']
    index = fins.index((10, 24, 110, 26))
    fins[index] = (10, 24, 110, 27)
    rewrite_geometry(root, replace_layers={'FIN': tuple(fins), 'POLY': ((58, 10, 63, 190),)})
    result = build(root)
    assert result.status == 'success'
    assert {name: row.count for name, row in by_device(result.value).items()} == {'MN0': 5, 'MP0': 7}
    assert all(row.length_nm == 5 for row in result.value.measurements)
    assert len(result.value.differences) == 3
    lengths = [row for row in result.value.differences if row.axis == 'channel_length']
    widths = [row for row in result.value.differences if row.axis == 'fin_width']
    assert len(lengths) == 2 and all(row.measured == Fraction(5, 10**9) and row.declared.exact == Fraction(4, 10**9)
                                    for row in lengths)
    assert len(widths) == 1 and widths[0].measured == Fraction(3, 10**9)
    assert widths[0].declared.exact == Fraction(2, 10**9) and widths[0].device_id.name == 'MN0'
    assert all(row.coverage_fraction == Fraction(4, 5) for row in result.value.associations)
