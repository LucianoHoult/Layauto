"""Pure exact network evidence overlay; never changes geometry or physical edges."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction
from typing import TYPE_CHECKING, cast

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.circuit import (
    Cell, Device, Membership, Net, Parameter, SemanticCircuitDraft, Terminal, semantic_value,
)
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, mapping, sequence
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId, QueryKey
from layauto_v2.domain.net_annotation import (
    AnnotationBinding, AnnotationFragment, AnnotationIssue, AnnotationRef, AnnotationTargetId,
    LayerCoverage, MatchEvidence, NET_TYPES, NetComponentSummary, NetEvidence, RecordClassification, TargetEvidence,
    TargetIntersection, area, canonical_cover, difference, intersections, policy_for, problem, records, validate_annotation_graph,
)
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.derive.net_annotation import summarize_components
from layauto_v2.state.local_connectivity import DRAFT_TYPES as LOCAL_TYPES, LocalConnectivityDraft
from layauto_v2.tech.schema import SchemaError, validate_payload

if TYPE_CHECKING:
    from layauto_v2.state.annotation import AnnotationDraft

_SOURCE_TYPES = (CellId, DeviceId, NetId, QueryKey, Parameter, Terminal, Membership,
                 Device, Net, Cell, SemanticCircuitDraft, EvidenceRecord, SourceRef)


def _rebuild(value: object) -> object:
    if type(value) is tuple:
        return tuple(_rebuild(item) for item in value)
    if any(type(value) is cls for cls in _SOURCE_TYPES) and is_dataclass(value):
        constructor = cast(Callable[..., object], type(value))
        return constructor(**{field.name: _rebuild(getattr(value, field.name)) for field in fields(value)})
    return value


def _boundary(a: RationalRect, b: RationalRect) -> bool:
    width, height = min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
    return width >= 0 and height >= 0 and (width == 0 or height == 0)


def match_evidence(binding: AnnotationBinding, evidence: tuple[NetEvidence, ...],
                   targets: tuple[TargetEvidence, ...], classifications: tuple[RecordClassification, ...] = ()) -> tuple[MatchEvidence, ...]:
    matches: list[MatchEvidence] = []
    for seed in evidence:
        policy = policy_for(binding, seed)
        if not policy['supported']:
            status = 'ambiguous' if str(policy['reason']).startswith('ambiguous') else 'unsupported'
            matches.append(MatchEvidence(seed.ref, (), (), (), (seed.rectangle,), policy, status))
            continue
        candidates = tuple(target for target in targets if target.target_id.layer == policy['target_layer'])
        hits = tuple(TargetIntersection(target.ref, pieces) for target in candidates
                     if (pieces := intersections((seed.rectangle,), target.rectangles)))
        boundary = tuple(sorted((target.ref for target in candidates if not intersections((seed.rectangle,), target.rectangles)
                                and any(_boundary(seed.rectangle, rect) for rect in target.rectangles)), key=lambda item: item.sha256))
        all_hits = canonical_cover(tuple(rect for hit in hits for rect in hit.rectangles))
        trimmed: tuple[RationalRect, ...] = ()
        if policy['trim_operator'] == 'cut_effective_intersection':
            drawn = canonical_cover(tuple(row.rectangle for row in classifications if row.layer == policy['target_layer'])
                                    + tuple(target.drawn_rectangle for target in candidates))
            effective = canonical_cover(tuple(rect for target in candidates for rect in target.rectangles))
            trimmed = intersections((seed.rectangle,), difference(drawn, effective))
        unmatched = difference((seed.rectangle,), canonical_cover(all_hits + trimmed))
        status = 'unmatched' if not hits else 'partial' if unmatched else 'matched'
        matches.append(MatchEvidence(seed.ref, tuple(sorted(hits, key=lambda item: item.target_ref.sha256)), boundary,
                                     trimmed, unmatched, policy, status))
    return tuple(matches)


def fragment_targets(evidence: tuple[NetEvidence, ...], targets: tuple[TargetEvidence, ...],
                     matches: tuple[MatchEvidence, ...]) -> tuple[AnnotationFragment, ...]:
    net_by_ref = {seed.ref: seed.net_id for seed in evidence}
    result: list[AnnotationFragment] = []
    for target in targets:
        hit_rows = tuple((match.evidence_ref, hit.rectangles) for match in matches for hit in match.intersections if hit.target_ref == target.ref)
        boxes = target.rectangles + tuple(rect for _, rects in hit_rows for rect in rects)
        xs, ys = sorted({v for rect in boxes for v in (rect.x0, rect.x1)}), sorted({v for rect in boxes for v in (rect.y0, rect.y1)})
        groups: dict[tuple[AnnotationRef, ...], list[RationalRect]] = {}
        for x0, x1 in zip(xs, xs[1:]):
            for y0, y1 in zip(ys, ys[1:]):
                atom = RationalRect(x0, y0, x1, y1)
                if not intersections((atom,), target.rectangles):
                    continue
                refs = tuple(sorted((seed_ref for seed_ref, rects in hit_rows if intersections((atom,), rects)), key=lambda item: item.sha256))
                groups.setdefault(refs, []).append(atom)
        for refs, rects in groups.items():
            nets = tuple(sorted({net_by_ref[item] for item in refs}, key=lambda item: item.id))
            status = 'unknown' if not nets else 'annotated' if len(nets) == 1 else 'conflict'
            result.append(AnnotationFragment(target.ref, canonical_cover(tuple(rects)), refs, nets, status))
    return tuple(sorted(result, key=lambda item: item.ref.sha256))


def layer_coverage(binding: AnnotationBinding, targets: tuple[TargetEvidence, ...],
                   fragments: tuple[AnnotationFragment, ...], classifications: tuple[RecordClassification, ...],
                   components: tuple[NetComponentSummary, ...]) -> tuple[LayerCoverage, ...]:
    conflict_components = {component.component_ref for component in components if component.status == 'conflict'}
    result: list[LayerCoverage] = []
    for layer in sorted({row.layer for row in classifications}):
        drawn = tuple(row for row in classifications if row.layer == layer)
        selected = tuple(target for target in targets if target.target_id.layer == layer)
        refs = {target.ref for target in selected}
        rows = tuple(row for row in fragments if row.target_ref in refs)
        total = sum((area(target.rectangles) for target in selected), Fraction())
        covered = sum((row.area_nm2 for row in rows if row.evidence_refs), Fraction())
        conflict = sum((row.area_nm2 for row in rows if row.status == 'conflict'), Fraction())
        conflicted_targets = {target.ref for target in selected if target.component_ref in conflict_components}
        component_area = sum((row.area_nm2 for row in rows if row.target_ref in conflicted_targets and row.evidence_refs), Fraction())
        sources = tuple(sorted({row.source for row in drawn}, key=lambda source: canonical_bytes({'uri': source.uri, 'sha': source.sha256, 'record': source.record_index})))
        evidence_refs = tuple(sorted({item for row in rows for item in row.evidence_refs}, key=lambda item: item.sha256))
        cells = {cell for row in drawn for cell in row.cell_coordinates}
        result.append(LayerCoverage(layer, len(drawn), len(cells), len(selected), total, covered, total - covered,
                                    conflict, component_area, sources, evidence_refs))
    return tuple(result)


def annotation_issues(evidence: tuple[NetEvidence, ...], targets: tuple[TargetEvidence, ...],
                      matches: tuple[MatchEvidence, ...], fragments: tuple[AnnotationFragment, ...],
                      components: tuple[NetComponentSummary, ...]) -> tuple[AnnotationIssue, ...]:
    seeds = {seed.ref: seed for seed in evidence}
    by_target = {target.ref: target for target in targets}
    issues: list[AnnotationIssue] = []
    for match in matches:
        if match.status in ('unsupported', 'ambiguous'):
            seed = seeds[match.evidence_ref]
            code = 'AmbiguousNetMapping' if match.status == 'ambiguous' else 'UnsupportedNetAnnotationPolicy'
            located = EvidenceIssue('unsupported', code, 'network evidence policy cannot be interpreted: ' + str(match.policy['reason']), seed.source)
            issues.append(AnnotationIssue(located, (), (), (seed.ref,), (seed.net_id,)))
    for fragment in fragments:
        if fragment.status == 'conflict':
            target = by_target[fragment.target_ref]
            located = EvidenceIssue('binding', 'ConflictingRegionNets', 'one exact local region fragment has multiple canonical net identities', target.source)
            issues.append(AnnotationIssue(located, (target.ref,), (target.component_ref,), fragment.evidence_refs, fragment.net_ids))
    for component in components:
        if component.status == 'conflict':
            refs = component.target_refs
            source = by_target[refs[0]].source
            located = EvidenceIssue('binding', 'ConflictingComponentNets', 'one original local physical component has multiple canonical net identities', source)
            issues.append(AnnotationIssue(located, refs, (component.component_ref,),
                                          component.evidence_refs, component.observed_net_ids))
    return tuple(sorted(issues, key=lambda item: item.ref.sha256))


def overlay(binding: AnnotationBinding, evidence: tuple[NetEvidence, ...], targets: tuple[TargetEvidence, ...],
            classifications: tuple[RecordClassification, ...]) -> tuple[tuple[MatchEvidence, ...], tuple[AnnotationFragment, ...], tuple[LayerCoverage, ...], tuple[NetComponentSummary, ...], tuple[AnnotationIssue, ...]]:
    matches = match_evidence(binding, evidence, targets, classifications)
    fragments = fragment_targets(evidence, targets, matches)
    components = summarize_components(binding, targets, fragments)
    coverage = layer_coverage(binding, targets, fragments, classifications, components)
    issues = annotation_issues(evidence, targets, matches, fragments, components)
    return matches, fragments, coverage, components, issues


def build_net_annotation_draft(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
                               net_evidence: tuple[NetEvidence, ...], derived: EvidenceRecord,
                               capture_binding: FrozenMap) -> AnnotationDraft:
    # Imports at the boundary avoid a state-to-algorithm dependency.
    from layauto_v2.state.annotation import AnnotationDraft
    if type(local) is not LocalConnectivityDraft or type(source) is not SemanticCircuitDraft:
        raise ValueError('network annotation requires a local graph and source semantics')
    validate_annotation_graph((local, source, net_evidence, derived, capture_binding), LOCAL_TYPES + NET_TYPES + _SOURCE_TYPES)
    if _rebuild(source) != source or replace(local) != local:
        raise ValueError('network annotation input is not completely reconstructible')
    evidence = tuple(sorted(records(net_evidence, NetEvidence, 'net evidence'), key=lambda item: item.ref.sha256))
    for owner, kind in ((derived, 'derived'), (local.binding.drawn, 'drawn')):
        if type(owner) is not EvidenceRecord or owner.kind != kind or len(owner.sources) != 1:
            raise ValueError('network annotation owner has a different role')
        try:
            validate_payload(owner.payload, kind)
        except SchemaError as exc:
            raise problem(owner.sources[0], exc.path or '/', 'unsupported network annotation owner: ' + str(exc)) from exc
    layout = local.effective.base.layout
    binding = AnnotationBinding(local.ref, local.effective.ref, layout.ref, layout.units.ref,
                                local.effective.base.partition.ref, layout.units.canonical_tick_nm, layout.top,
                                source.selected_cell, digest(semantic_value(source)), source.preservation.sources[0], derived, local.binding.drawn,
                                local.components, tuple(sorted((row.id for row in layout.records), key=lambda item: item.sha256)), tuple(seed.ref for seed in evidence), capture_binding)
    source_nets = {net.id for cell in source.cells if cell.id == source.selected_cell for net in cell.nets}
    if any(seed.net_id not in source_nets for seed in evidence):
        raise ValueError('network evidence references a foreign source net')
    components = {member: component.ref for component in local.components for member in component.members}
    drawn = {row.id: row for row in layout.records}
    targets = tuple(sorted((TargetEvidence(AnnotationTargetId(binding.ref, node.layer, node.region.owner_id, node.region.ref),
                    node, components[node.ref], RationalRect(*(Fraction(value * binding.tick_nm) for value in drawn[node.region.owner_id].rect.bounds)),
                    drawn[node.region.owner_id].source, binding.tick_nm) for node in local.nodes), key=lambda target: target.ref.sha256))
    target_records = {target.target_id.record_id for target in targets}
    classifications: list[RecordClassification] = []
    roles = {str(row['name']): str(row['role']) for row in (mapping(item) for item in sequence(binding.drawn.payload['layers']))}
    for row in layout.records:
        role = roles[row.layer]
        classification = ('target_conductor' if role in ('diffusion', 'interconnect', 'gate', 'body') else 'connector' if role in ('contact', 'via', 'body_contact')
                          else 'cut' if role == 'cut' else 'backdrop' if role == 'fin' else 'boundary' if role == 'boundary'
                          else 'marker' if role == 'marker' else 'auxiliary')
        cells = tuple(sorted({(fragment.cell.x, fragment.cell.y) for fragment in local.effective.base.fragments if fragment.record_id == row.id}))
        classifications.append(RecordClassification(row.id, row.layer, role, classification,
            RationalRect(*(Fraction(value * binding.tick_nm) for value in row.rect.bounds)), row.source, cells))
    classified = tuple(sorted(classifications, key=lambda row: row.record_id.sha256))
    matches, fragments, coverage, summaries, issues = overlay(binding, evidence, targets, classified)
    return AnnotationDraft(binding, evidence, targets, matches, fragments, coverage, summaries, classified, issues)
