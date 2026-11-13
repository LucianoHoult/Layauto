"""W013 real receipt composition against independent local-only expectations."""
from __future__ import annotations

import builtins
from dataclasses import fields, replace
from fractions import Fraction
import io
from pathlib import Path
import shutil

import pytest

from w005_cases import FIXTURE, inventory, read_json, rebind, without_cache
from w007_cases import ready_copy
from w010_cases import build_local, normal_node_names
from w013_cases import (DIRECT_AREAS, DIRECT_TARGET_NETS, LOCAL_COMPONENTS,
                        TARGET_AREAS, independent_areas, neutral, normal_capture,
                        readback_capture, rewrite_net_response)


@pytest.fixture(scope='module')
def accepted():
    return normal_capture()


@pytest.fixture(scope='module')
def variant_base(tmp_path_factory):
    root = ready_copy(tmp_path_factory.mktemp('w013-neutral'))
    return root, build_local(root).value


@pytest.fixture
def variant(variant_base):
    root, local = variant_base
    # The same temporary URI and unchanged GDS/tech owners make compact spatial
    # tests comparable without rebuilding a complete W010 receipt per query.
    shutil.rmtree(root / 'query', ignore_errors=True)
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    without_cache(root)
    return root, local


def ln(draft):
    target = next(target for target in draft.targets
                  if target.target_id.layer == 'LI' and target.drawn_rectangle.bounds == (28, 30, 34, 55))
    fragments = tuple(row for row in draft.fragments if row.target_ref == target.ref)
    return target, fragments


def test_actual_direct_result_keeps_complete_local_graph_and_independent_net_projection(accepted):
    draft, local = accepted.value, accepted.input.value
    names = normal_node_names(local, read_json(FIXTURE / 'spec.json'), read_json(FIXTURE / 'oracle.json'))
    assert len(draft.targets) == len(local.nodes) == 14
    assert len(local.edges) == 8 and len(local.components) == len(draft.components) == 6
    targets = {target.ref: target for target in draft.targets}
    assert {target.node_ref for target in draft.targets} == {node.ref for node in local.nodes}
    assert len(targets) == 14

    evidence = {row.ref: row for row in draft.evidence}
    assert len(evidence) == len(draft.matches) == 8
    assert {row.query_key.identity: (row.net_id.name, row.query_key.index)
            for row in draft.evidence} == {
                'n_a': ('A', '1'), 'n_y': ('Y', '2'),
                'n_lo': ('VSS', '3'), 'n_hi': ('VDD', '4')}
    direct = {}
    for fragment in draft.fragments:
        name = names[targets[fragment.target_ref].node_ref]
        assert fragment.validity == 'source_evidence'
        if fragment.status == 'annotated':
            assert len(fragment.net_ids) == len(fragment.evidence_refs) == 1
            direct[name] = fragment.net_ids[0].name
            assert evidence[fragment.evidence_refs[0]].net_id == fragment.net_ids[0]
        else:
            assert fragment.status == 'unknown' and fragment.net_ids == fragment.evidence_refs == ()
    assert direct == DIRECT_TARGET_NETS
    assert len(draft.fragments) == 14
    assert all(row.status == 'matched' and not row.trimmed and not row.unmatched
               and not row.multiple_candidates for row in draft.matches)

    actual = {}
    for row in draft.components:
        members = frozenset(names[member] for member in row.members)
        actual[members] = row.observed_net_ids[0].name if row.observed_net_ids else None
        assert row.status == ('associated' if row.observed_net_ids else 'unknown')
        expected_direct = {ref for ref in row.target_refs
                           if names[targets[ref].node_ref] in DIRECT_TARGET_NETS}
        assert set(row.directly_covered_targets) == expected_direct
    assert actual == LOCAL_COMPONENTS
    # Four OD terminal regions have component associations, but zero direct
    # query coverage. External body rail associations do not label local BODY.
    assert set(names.values()) - set(direct) == {'ON.S', 'ON.D', 'OP.S', 'OP.D', 'BN', 'BP'}
    assert all(names[targets[ref].node_ref] not in ('BN', 'BP')
               for row in draft.components for ref in row.directly_covered_targets)


def test_actual_coverage_denominator_and_marker_classification_match_hand_arithmetic(accepted):
    draft = accepted.value
    coverage = {row.layer: row for row in draft.coverage}
    assert sum((row.total_area for row in coverage.values()), Fraction()) == 35090
    assert sum((row.covered_area for row in coverage.values()), Fraction()) == 3170
    assert sum((row.uncovered_area for row in coverage.values()), Fraction()) == 31920
    assert sum(row.drawn_shape_count for row in coverage.values()) == 40
    assert sum(row.target_count for row in coverage.values()) == 14
    for layer, total in TARGET_AREAS.items():
        row = coverage[layer]
        assert row.total_area == total and row.covered_area == DIRECT_AREAS.get(layer, 0)
        assert row.covered_area + row.uncovered_area == row.total_area
        assert row.conflict_area == row.component_conflict_area == 0
        assert row.unit == 'nm2' and row.denominator == 'local_target_multiset_area'
        assert row.source_refs
    classes = draft.classifications
    assert len(classes) == 40 and len({row.record_id for row in classes}) == 40
    markers = [row for row in classes if row.classification == 'marker']
    assert len(markers) == 1 and markers[0].layer == 'MARKER'
    assert markers[0].rectangle.bounds == (145, 180, 150, 185)
    assert markers[0].rectangle.area == 25 and markers[0].cell_coordinates == ()
    assert len([row for row in classes if row.classification == 'backdrop']) == 18
    assert coverage['MARKER'].target_count == 0 and coverage['MARKER'].total_area == 0
    assert draft.binding.scope == 'source_evidence_local_net_annotation/1'
    assert draft.binding.validity == 'source_evidence'


def test_builder_performs_no_new_acquisition_or_publication(accepted, monkeypatch):
    from layauto_v2.normalization.net_annotation import build_net_annotation
    local = accepted.input
    before = inventory(FIXTURE)
    edges, components = local.value.edges, local.value.components
    def forbidden(*args, **kwargs):
        pytest.fail('network annotation attempted file acquisition or publication')
    with monkeypatch.context() as patch:
        for method in ('open', 'read_text', 'read_bytes', 'resolve'):
            patch.setattr(Path, method, forbidden)
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(io, 'open', forbidden)
        result = build_net_annotation(local)
    assert result.status == 'success' and result.input is local
    assert result.completed == local.completed and result.body_evidence is local.body_evidence
    assert local.value.edges is edges and local.value.components is components
    assert inventory(FIXTURE) == before
    for value in (result, result.value, *result.value.components):
        assert not {'baseline', 'terminal', 'body_complete', 'no_change', 'final_snapshot_id'} & {
            field.name for field in fields(value)}


def test_readback_run_owner_is_retained_and_attempt_stays_unsealed():
    result, repository, ready, checkpoint, attempt = readback_capture()
    assert result.status == 'success'
    row = result.value.binding.capture_binding['readback']
    assert row['run_id'] == ready.run_id
    assert row['checkpoint_ref']['digest'] == ready.checkpoint_ref.digest
    assert row['parse_ref']['digest'] == ready.parse_ref.digest
    assert row['tool_ref']['digest'] == ready.tool_ref.digest
    assert all(evidence.query_key.query_run_id == 'w004.synthetic.query.2'
               for evidence in result.value.evidence)
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.read_terminal(ready.run_id) is None


def test_same_captured_source_admission_failure_stays_located_and_preserves_completed_facts(tmp_path):
    from layauto_v2.normalization import normalize
    from layauto_v2.normalization.net_annotation import build_net_annotation
    root = ready_copy(tmp_path)
    path = root / 'source.cdl'
    path.write_text(path.read_text().replace('NF=1', 'NF=2', 1))
    rebind(root)
    local = build_local(root)
    original = normalize(local.input.input.input.semantic_input)
    assert original.status == 'error'
    assert len(original.issues) == 1 and original.issues[0].code == 'UnsupportedFingerCount'
    assert original.issues[0].category == 'unsupported' and original.issues[0].source.uri == 'source.cdl'
    result = build_net_annotation(local)
    assert result.status == 'error' and result.value is None
    assert [(row.category, row.code, row.message, row.source) for row in result.issues] == [
        (row.category, row.code, row.message, row.source) for row in original.issues]
    assert result.completed == local.completed
    assert result.input is local and result.body_evidence is local.body_evidence


def test_neutral_partial_same_net_overlap_retains_both_sources_without_double_coverage(variant):
    root, local = variant
    rewrite_net_response(root, 'n_lo', [('toy_li', (28, 30, 31, 55)),
                                      ('toy_li', (30, 30, 33, 55)),
                                      ('toy_m1', (0, 48, 45, 58))])
    draft = neutral(root, local)
    target, rows = ln(draft)
    assert sum(row.area_nm2 for row in rows if row.evidence_refs) == 125
    assert sum(row.area_nm2 for row in rows if not row.evidence_refs) == 25
    assert len(rows) == 4
    overlap = next(row for row in rows if len(row.evidence_refs) == 2)
    assert overlap.area_nm2 == 25 and {net.name for net in overlap.net_ids} == {'VSS'}
    assert overlap.status == 'annotated' and not draft.issues
    coverage = next(row for row in draft.coverage if row.layer == 'LI')
    assert (coverage.total_area, coverage.covered_area, coverage.uncovered_area, coverage.conflict_area) == (1110, 1085, 25, 0)
    assert draft.binding.local_ref == local.ref
    assert tuple(row.component_ref for row in draft.components) == tuple(row.ref for row in local.components)
    expected = independent_areas(((28, 30, 34, 55),),
                                 [('VSS', (28, 30, 31, 55)), ('VSS', (30, 30, 33, 55))])
    assert expected == {'total': 150, 'covered': 125, 'uncovered': 25, 'conflict': 0}
    assert target.component_ref in {row.component_ref for row in draft.components}


@pytest.mark.parametrize('box,covered,unmatched,status,boundary_count', [
    ((34, 30, 35, 55), 0, 25, 'unmatched', 1),
    ((34, 55, 35, 56), 0, 1, 'unmatched', 1),
    ((120, 30, 125, 35), 0, 25, 'unmatched', 0),
    ((27, 30, 30, 55), 50, 25, 'partial', 0),
    ((28, 30, Fraction(679, 20), 55), Fraction(595, 4), 0, 'matched', 0),
])
def test_neutral_zero_area_unmatched_and_fractional_query_evidence_is_exact(
        variant, box, covered, unmatched, status, boundary_count):
    root, local = variant
    rewrite_net_response(root, 'n_lo', [('toy_li', box), ('toy_m1', (0, 48, 45, 58))])
    draft = neutral(root, local)
    target, rows = ln(draft)
    seed = next(row for row in draft.evidence if row.query_key.identity == 'n_lo'
                and row.record['derived_layer'] == 'toy_li')
    match = next(row for row in draft.matches if row.evidence_ref == seed.ref)
    assert seed.record['quality'] == 'exact' and seed.rectangle.bounds == tuple(Fraction(v) for v in box)
    assert sum(row.area_nm2 for row in rows if row.evidence_refs) == covered
    assert sum(row.area_nm2 for row in rows if not row.evidence_refs) == 150 - covered
    assert sum((row.area for row in match.unmatched), Fraction()) == unmatched
    assert match.trimmed == () and match.status == status
    assert len(match.boundary_targets) == boundary_count
    if boundary_count:
        assert target.ref in match.boundary_targets and match.intersections == ()


def test_neutral_direct_region_conflict_keeps_all_nets_and_sources(variant):
    root, local = variant
    rewrite_net_response(root, 'n_a', [('toy_poly', (58, 10, 62, 190)),
                                     ('toy_m1', (50, 90, 75, 98)),
                                     ('toy_li', (30, 30, 33, 55))])
    draft = neutral(root, local)
    target, rows = ln(draft)
    conflicts = [row for row in rows if row.status == 'conflict']
    assert len(conflicts) == 1 and conflicts[0].area_nm2 == 75
    assert {net.name for net in conflicts[0].net_ids} == {'A', 'VSS'}
    assert len(conflicts[0].evidence_refs) == 2
    assert {row.issue.code for row in draft.issues} == {'ConflictingRegionNets', 'ConflictingComponentNets'}
    summary = next(row for row in draft.components if row.component_ref == target.component_ref)
    assert summary.status == 'conflict' and {net.name for net in summary.observed_net_ids} == {'A', 'VSS'}
    coverage = {row.layer: row for row in draft.coverage}
    assert coverage['LI'].conflict_area == 75 and coverage['LI'].component_conflict_area == 150
    assert coverage['M1'].conflict_area == 0 and coverage['M1'].component_conflict_area == 450
    assert draft.binding.local_ref == local.ref and len(draft.components) == 6
    original = draft.issues[0]
    for replacement in (replace(original.issue, source=replace(original.issue.source, uri='foreign.gds')),
                        replace(original.issue, message='altered explanation'),
                        replace(original.issue, category='unsupported')):
        forged = replace(original, issue=replacement)
        with pytest.raises(ValueError):
            replace(draft, issues=(forged,) + draft.issues[1:])


def test_neutral_disjoint_labels_in_one_physical_component_still_report_conflict(variant):
    root, local = variant
    rewrite_net_response(root, 'n_a', [('toy_poly', (58, 10, 62, 190)),
                                     ('toy_m1', (50, 90, 75, 98)),
                                     ('toy_li', (28, 30, 30, 55))])
    rewrite_net_response(root, 'n_lo', [('toy_li', (32, 30, 34, 55)),
                                      ('toy_m1', (0, 48, 45, 58))])
    draft = neutral(root, local)
    target, rows = ln(draft)
    assert not any(row.status == 'conflict' for row in rows)
    assert sum(row.area_nm2 for row in rows if row.evidence_refs) == 100
    assert {row.issue.code for row in draft.issues} == {'ConflictingComponentNets'}
    summary = next(row for row in draft.components if row.component_ref == target.component_ref)
    assert {net.name for net in summary.observed_net_ids} == {'A', 'VSS'}
    coverage = next(row for row in draft.coverage if row.layer == 'LI')
    assert coverage.conflict_area == 0 and coverage.component_conflict_area == 100


def test_neutral_declared_nonzero_tolerance_is_retained_as_unsupported(variant):
    from w009_cases import change_owner
    root, local = variant
    def mutate(owner):
        next(row for row in owner['derived_registry'] if row['id'] == 'toy_li')['annotation_match_tolerance_nm'] = 1
    change_owner(root, 'derived', mutate)
    draft = neutral(root, local)
    seeds = {row.ref: row for row in draft.evidence}
    matches = [row for row in draft.matches if seeds[row.evidence_ref].record['derived_layer'] == 'toy_li']
    assert len(matches) == 3
    assert all(row.status == 'unsupported' and row.intersections == ()
               and row.unmatched == (seeds[row.evidence_ref].rectangle,)
               and row.policy['declaration']['annotation_match_tolerance_nm'] == 1 for row in matches)
    coverage = next(row for row in draft.coverage if row.layer == 'LI')
    assert coverage.covered_area == 0 and coverage.uncovered_area == 1110
    assert len(draft.issues) == 3
    assert all(row.issue.code == 'UnsupportedNetAnnotationPolicy' for row in draft.issues)


def test_neutral_real_xref_renumber_and_rename_do_not_replace_semantic_identity(variant):
    from w007_cases import query_only_rename
    root, local = variant
    renames = query_only_rename(root)
    draft = neutral(root, local)
    identities = {row.query_key.identity: (row.net_id.name, row.query_key.index)
                  for row in draft.evidence}
    assert identities == {renames['n_a']: ('A', '4'), renames['n_y']: ('Y', '3'),
                           renames['n_lo']: ('VSS', '2'), renames['n_hi']: ('VDD', '1')}
    assert all(row.query_key.query_run_id == 'alternate.query.run' for row in draft.evidence)
    assert sum(row.covered_area for row in draft.coverage) == 3170
    assert len(draft.targets) == 14 and len(draft.components) == 6 and not draft.issues


def test_neutral_cut_islands_keep_three_A_components_and_distinguish_trim_from_unmatched(tmp_path):
    from w010_cases import append_records
    root = ready_copy(tmp_path)
    append_records(root, [('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 141, 26))])
    rewrite_net_response(root, 'n_a', [('toy_poly', (58, 10, 62, 190)),
                                     ('toy_m1', (50, 90, 75, 98)),
                                     ('toy_li', (130, 20, 152, 24))])
    local = build_local(root).value
    draft = neutral(root, local)
    assert len(local.nodes) == len(draft.targets) == 16
    assert len(local.edges) == 8 and len(local.components) == len(draft.components) == 8
    islands = [row for row in draft.targets if row.target_id.layer == 'LI'
               and row.drawn_rectangle.bounds == (130, 20, 150, 24)]
    assert len(islands) == 2 and len({row.target_id.region_ref for row in islands}) == 2
    assert {tuple(rect.bounds for rect in row.rectangles) for row in islands} == {
        ((130, 20, 139, 24),), ((141, 20, 150, 24),)}
    assert len({row.component_ref for row in islands}) == 2
    a_components = [row for row in draft.components if {net.name for net in row.observed_net_ids} == {'A'}]
    assert len(a_components) == 3
    seed = next(row for row in draft.evidence if row.query_key.identity == 'n_a'
                and row.record['derived_layer'] == 'toy_li')
    match = next(row for row in draft.matches if row.evidence_ref == seed.ref)
    assert match.multiple_candidates and len(match.intersections) == 2
    assert sum(rect.area for hit in match.intersections for rect in hit.rectangles) == 72
    assert tuple(rect.bounds for rect in match.trimmed) == ((139, 20, 141, 24),)
    assert tuple(rect.bounds for rect in match.unmatched) == ((150, 20, 152, 24),)
    assert match.status == 'partial' and not draft.issues


def test_neutral_duplicate_occupants_share_a_candidate_cell_without_losing_record_multiplicity(tmp_path):
    from w010_cases import append_records
    root = ready_copy(tmp_path)
    append_records(root, [('M1', (130, 20, 150, 24)), ('M1', (130, 20, 150, 24))])
    rewrite_net_response(root, 'n_a', [('toy_poly', (58, 10, 62, 190)),
                                     ('toy_m1', (50, 90, 75, 98)),
                                     ('toy_m1', (130, 20, 150, 24))])
    local = build_local(root).value
    draft = neutral(root, local)
    occupants = [row for row in draft.targets if row.target_id.layer == 'M1'
                 and row.drawn_rectangle.bounds == (130, 20, 150, 24)]
    assert len(occupants) == 2 and len({row.target_id.record_id for row in occupants}) == 2
    assert len({row.ref for row in occupants}) == 2
    classes = [row for row in draft.classifications if row.record_id in {row.target_id.record_id for row in occupants}]
    assert set(classes[0].cell_coordinates) & set(classes[1].cell_coordinates)
    coverage = next(row for row in draft.coverage if row.layer == 'M1')
    assert coverage.total_area == coverage.covered_area == 1500  # 1340 + 2*80
    assert coverage.conflict_area == 0
    assert len(local.nodes) == 16 and len(local.edges) == 9 and len(local.components) == 7
    assert len(draft.components) == 7
