"""Compact proposed annotation table; immutable and independent of publication."""
from __future__ import annotations

from dataclasses import dataclass, fields
from fractions import Fraction
from typing import cast

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.identifiers import NetId
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, digest
from layauto_v2.domain.geometry import mapping, sequence
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.net_annotation import (
    VERSION, AnnotationBinding, AnnotationFragment, AnnotationIssue, AnnotationRef,
    LayerCoverage, MatchEvidence, NET_TYPES, NetComponentSummary, NetEvidence,
    RecordClassification, TargetEvidence, _value, area, canonical_cover, difference,
    intersections, policy_for, records, validate_members,
)
from layauto_v2.domain.regions import validate_closed_graph


def _same(a: object, b: object) -> bool:
    return canonical_bytes(_value(a)) == canonical_bytes(_value(b))


def _boundary(a: object, b: object) -> bool:
    from layauto_v2.domain.channel_identity import RationalRect
    if type(a) is not RationalRect or type(b) is not RationalRect:
        raise ValueError('boundary relation requires exact rational rectangles')
    width, height = min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
    return width >= 0 and height >= 0 and (width == 0 or height == 0)


@dataclass(frozen=True)
class AnnotationDraft:
    binding: AnnotationBinding
    evidence: tuple[NetEvidence, ...]
    targets: tuple[TargetEvidence, ...]
    matches: tuple[MatchEvidence, ...]
    fragments: tuple[AnnotationFragment, ...]
    coverage: tuple[LayerCoverage, ...]
    components: tuple[NetComponentSummary, ...]
    classifications: tuple[RecordClassification, ...]
    issues: tuple[AnnotationIssue, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION or type(self.binding) is not AnnotationBinding:
            raise ValueError('invalid annotation draft schema/binding')
        for name, cls in (('evidence', NetEvidence), ('targets', TargetEvidence), ('matches', MatchEvidence),
                          ('fragments', AnnotationFragment), ('coverage', LayerCoverage), ('components', NetComponentSummary),
                          ('classifications', RecordClassification), ('issues', AnnotationIssue)):
            object.__setattr__(self, name, records(getattr(self, name), cls, name))
        validate_closed_graph(self, DRAFT_TYPES)
        for field in fields(self):
            validate_members(getattr(self, field.name))
        self._validate_inputs()
        self._validate_matches()
        self._validate_fragments()
        self._validate_components()
        self._validate_coverage()
        self._validate_issues()

    def _validate_inputs(self) -> None:
        b = self.binding
        if tuple(seed.ref for seed in self.evidence) != b.evidence_refs:
            raise ValueError('annotation evidence table omitted/duplicated retained seeds')
        if len({seed.record['record_id'] for seed in self.evidence}) != len(self.evidence):
            raise ValueError('annotation repeats a source seed record identity')
        keys = {(seed.query_key.header_id, seed.query_key.query_run_id, seed.query_key.database_id) for seed in self.evidence}
        if len(keys) > 1 or any(seed.net_id.cell != b.source_cell for seed in self.evidence):
            raise ValueError('annotation evidence mixes runs/database/source cells')
        joins: dict[object, object] = {}
        reverse: dict[object, object] = {}
        names: dict[object, object] = {}
        indices: dict[object, object] = {}
        for seed in self.evidence:
            previous = joins.setdefault(seed.query_key, seed.net_id)
            prior_key = reverse.setdefault(seed.net_id, seed.query_key)
            prior_name = names.setdefault(seed.query_key.identity, seed.query_key)
            prior_index = indices.setdefault(seed.query_key.index, seed.query_key)
            if previous != seed.net_id or prior_key != seed.query_key or prior_name != seed.query_key or prior_index != seed.query_key:
                raise ValueError('annotation query identity conflicts with source net')
        allowed = {(item['uri'], item['sha256']) for item in (mapping(row) for row in sequence(b.capture_binding['sources']))}
        def sources(value: object) -> None:
            if type(value) is SourceRef:
                if (value.uri, value.sha256) not in allowed:
                    raise ValueError('annotation source belongs to another capture')
            elif type(value) is FrozenMap:
                if 'sha256' in value and ('uri' in value or 'path' in value):
                    if (value.get('uri', value.get('path')), value['sha256']) not in allowed:
                        raise ValueError('annotation provenance belongs to another capture')
                for child in value.values():
                    sources(child)
            elif type(value) is tuple:
                for child in value:
                    sources(child)
        sources((b.source_ref,) + b.derived.sources + b.drawn.sources)
        for seed in self.evidence:
            sources((seed.record, seed.identity_provenance))
        for row in self.classifications:
            sources(row.source)
        if self.targets != tuple(sorted(self.targets, key=lambda row: row.ref.sha256)) or len({row.ref for row in self.targets}) != len(self.targets):
            raise ValueError('annotation targets require canonical unique identities')
        topology = {member: component.ref for component in b.topology for member in component.members}
        if {target.node_ref for target in self.targets} != set(topology) or len(self.targets) != len(topology):
            raise ValueError('annotation targets do not completely cover original local nodes')
        for target in self.targets:
            if (target.target_id.binding_ref != b.ref or target.component_ref != topology[target.node_ref]
                    or target.tick_nm != b.tick_nm or target.node.region.unit_ref != b.unit_ref):
                raise ValueError('annotation target belongs to another binding/component/unit')
        if tuple(row.record_id for row in self.classifications) != b.drawn_record_ids:
            raise ValueError('annotation classification omitted/duplicated original drawn records')
        drawn = {row.record_id: row for row in self.classifications}
        registry = {str(mapping(row)['name']): mapping(row) for row in sequence(b.drawn.payload['layers'])}
        target_records = {target.target_id.record_id for target in self.targets}
        for row in self.classifications:
            declaration = registry.get(row.layer)
            if declaration is None or row.role != declaration['role']:
                raise ValueError('classification does not preserve drawn layer role')
            expected = ('target_conductor' if row.role in ('diffusion', 'interconnect', 'gate', 'body') else 'connector' if row.role in ('contact', 'via', 'body_contact')
                        else 'cut' if row.role == 'cut' else 'backdrop' if row.role == 'fin' else 'boundary' if row.role == 'boundary'
                        else 'marker' if row.role == 'marker' else 'auxiliary')
            if row.classification != expected:
                raise ValueError('classification changes drawn role/conductor meaning')
        if not target_records <= set(drawn):
            raise ValueError('annotation target has no drawn record backlink')
        for target in self.targets:
            row = drawn[target.target_id.record_id]
            if row.layer != target.target_id.layer or not _same(row.rectangle, target.drawn_rectangle) or not _same(row.source, target.source):
                raise ValueError('annotation target differs from original drawn classification/source')

    def _validate_matches(self) -> None:
        if tuple(match.evidence_ref for match in self.matches) != self.binding.evidence_refs:
            raise ValueError('annotation matches omit or reorder source evidence')
        targets = {target.ref: target for target in self.targets}
        for seed, match in zip(self.evidence, self.matches):
            policy = policy_for(self.binding, seed)
            if canonical_bytes(policy) != canonical_bytes(match.policy):
                raise ValueError('match policy does not belong to retained tech owners')
            if not policy['supported']:
                expected = 'ambiguous' if str(policy['reason']).startswith('ambiguous') else 'unsupported'
                if match.status != expected or match.intersections or match.boundary_targets or match.trimmed or match.unmatched != (seed.rectangle,):
                    raise ValueError('unsupported match must preserve all source geometry as unknown evidence')
                continue
            selected = tuple(target for target in self.targets if target.target_id.layer == policy['target_layer'])
            expected_hits = {target.ref: intersections((seed.rectangle,), target.rectangles) for target in selected}
            expected_hits = {key: value for key, value in expected_hits.items() if value}
            actual_hits = {hit.target_ref: hit.rectangles for hit in match.intersections}
            if not _same(tuple(sorted(expected_hits.items(), key=lambda item: item[0].sha256)), tuple(sorted(actual_hits.items(), key=lambda item: item[0].sha256))):
                raise ValueError('match intersections differ from complete exact target intersections')
            expected_boundary = tuple(sorted((target.ref for target in selected if target.ref not in expected_hits and any(_boundary(seed.rectangle, rect) for rect in target.rectangles)), key=lambda item: item.sha256))
            if match.boundary_targets != expected_boundary:
                raise ValueError('match omits or invents boundary-only candidates')
            covered = canonical_cover(tuple(rect for hit in match.intersections for rect in hit.rectangles))
            trimmed: tuple[RationalRect, ...] = ()
            if policy['trim_operator'] == 'cut_effective_intersection':
                drawn = canonical_cover(tuple(row.rectangle for row in self.classifications if row.layer == policy['target_layer']))
                effective = canonical_cover(tuple(rect for target in selected for rect in target.rectangles))
                trimmed = intersections((seed.rectangle,), difference(drawn, effective))
            unmatched = difference((seed.rectangle,), canonical_cover(covered + trimmed))
            expected_status = 'unmatched' if not match.intersections else 'partial' if unmatched else 'matched'
            if match.trimmed != trimmed or match.unmatched != unmatched or match.status != expected_status:
                raise ValueError('match trimming/unmatched/status loses exact evidence')
            if any(reference not in targets for reference in match.boundary_targets):
                raise ValueError('match references a foreign boundary target')

    def _validate_fragments(self) -> None:
        if self.fragments != tuple(sorted(self.fragments, key=lambda row: row.ref.sha256)) or len({row.ref for row in self.fragments}) != len(self.fragments):
            raise ValueError('annotation fragments require unique canonical identities')
        seeds = {seed.ref: seed for seed in self.evidence}
        valid_targets = {target.ref for target in self.targets}
        if any(fragment.target_ref not in valid_targets for fragment in self.fragments):
            raise ValueError('annotation fragment references foreign target')
        for target in self.targets:
            rows = tuple(row for row in self.fragments if row.target_ref == target.ref)
            rectangles = tuple(rect for row in rows for rect in row.rectangles)
            if canonical_cover(rectangles) != canonical_cover(target.rectangles) or area(rectangles) != area(target.rectangles):
                raise ValueError('annotation fragments do not partition complete target coverage')
            signatures = [row.evidence_refs for row in rows]
            if len(set(signatures)) != len(signatures):
                raise ValueError('same target/evidence signature must have one canonical fragment cover')
            for row in rows:
                expected_refs = []
                for match in self.matches:
                    covered = tuple(rect for hit in match.intersections if hit.target_ref == target.ref for rect in hit.rectangles)
                    overlap = intersections(row.rectangles, covered)
                    if overlap:
                        if difference(row.rectangles, covered):
                            raise ValueError('annotation fragment crosses an evidence boundary')
                        expected_refs.append(match.evidence_ref)
                expected = tuple(sorted(expected_refs, key=lambda item: item.sha256))
                nets = tuple(sorted({seeds[item].net_id for item in expected}, key=lambda item: item.id))
                if row.evidence_refs != expected or row.net_ids != nets:
                    raise ValueError('annotation fragment omits or invents net/source evidence')

    def _validate_components(self) -> None:
        if tuple(row.component_ref for row in self.components) != tuple(component.ref for component in self.binding.topology):
            raise ValueError('component summary omitted/merged/reordered physical components')
        for topology, row in zip(self.binding.topology, self.components):
            targets = tuple(target for target in self.targets if target.component_ref == topology.ref)
            target_refs = tuple(sorted((target.ref for target in targets), key=lambda item: item.sha256))
            fragments = tuple(fragment for fragment in self.fragments if fragment.target_ref in set(target_refs) and fragment.evidence_refs)
            nets = tuple(sorted({net for fragment in fragments for net in fragment.net_ids}, key=lambda item: item.id))
            evidence = tuple(sorted({ref for fragment in fragments for ref in fragment.evidence_refs}, key=lambda item: item.sha256))
            direct = tuple(sorted({fragment.target_ref for fragment in fragments}, key=lambda item: item.sha256))
            if row.members != topology.members or row.target_refs != target_refs or row.observed_net_ids != nets or row.evidence_refs != evidence or row.directly_covered_targets != direct:
                raise ValueError('component summary differs from direct region evidence; inference is not coverage')

    def _validate_coverage(self) -> None:
        layers = tuple(sorted({row.layer for row in self.classifications}))
        if tuple(row.layer for row in self.coverage) != layers:
            raise ValueError('coverage omits/reorders a drawn layer')
        conflict_components = {row.component_ref for row in self.components if row.status == 'conflict'}
        for row in self.coverage:
            drawn = tuple(item for item in self.classifications if item.layer == row.layer)
            targets = tuple(item for item in self.targets if item.target_id.layer == row.layer)
            target_refs = {target.ref for target in targets}
            fragments = tuple(item for item in self.fragments if item.target_ref in target_refs)
            total = sum((area(target.rectangles) for target in targets), Fraction())
            covered = sum((item.area_nm2 for item in fragments if item.evidence_refs), Fraction())
            conflict = sum((item.area_nm2 for item in fragments if item.status == 'conflict'), Fraction())
            conflict_targets = {target.ref for target in targets if target.component_ref in conflict_components}
            component_area = sum((item.area_nm2 for item in fragments if item.target_ref in conflict_targets and item.evidence_refs), Fraction())
            expected_refs = tuple(sorted({ref for item in fragments for ref in item.evidence_refs}, key=lambda item: item.sha256))
            expected_sources = tuple(sorted({item.source for item in drawn}, key=lambda source: canonical_bytes({'uri': source.uri, 'sha': source.sha256, 'record': source.record_index})))
            if ((row.drawn_shape_count, row.cell_count, row.target_count) != (len(drawn), len({cell for item in drawn for cell in item.cell_coordinates}), len(targets))
                    or (row.total_area, row.covered_area, row.uncovered_area, row.conflict_area, row.component_conflict_area) != (total, covered, total - covered, conflict, component_area)
                    or row.evidence_refs != expected_refs or not _same(row.source_refs, expected_sources)):
                raise ValueError('layer coverage loses target multiplicity, gaps, conflict or sources')

    def _validate_issues(self) -> None:
        if self.issues != tuple(sorted(self.issues, key=lambda row: row.ref.sha256)) or len({row.ref for row in self.issues}) != len(self.issues):
            raise ValueError('annotation issues require canonical unique order')
        targets = {target.ref: target for target in self.targets}
        evidence = {seed.ref: seed for seed in self.evidence}
        expected: list[AnnotationIssue] = []
        for match in self.matches:
            if match.status in ('unsupported', 'ambiguous'):
                code = 'AmbiguousNetMapping' if match.status == 'ambiguous' else 'UnsupportedNetAnnotationPolicy'
                seed = evidence[match.evidence_ref]
                issue = EvidenceIssue('unsupported', code, 'network evidence policy cannot be interpreted: ' + str(match.policy['reason']), seed.source)
                expected.append(AnnotationIssue(issue, (), (), (seed.ref,), (seed.net_id,)))
        for fragment in self.fragments:
            if fragment.status == 'conflict':
                target = targets[fragment.target_ref]
                issue = EvidenceIssue('binding', 'ConflictingRegionNets', 'one exact local region fragment has multiple canonical net identities', target.source)
                expected.append(AnnotationIssue(issue, (target.ref,), (target.component_ref,), fragment.evidence_refs, fragment.net_ids))
        for row in self.components:
            if row.status == 'conflict':
                issue = EvidenceIssue('binding', 'ConflictingComponentNets', 'one original local physical component has multiple canonical net identities', targets[row.target_refs[0]].source)
                expected.append(AnnotationIssue(issue, row.target_refs, (row.component_ref,), row.evidence_refs, row.observed_net_ids))
        if not _same(self.issues, tuple(sorted(expected, key=lambda item: item.ref.sha256))):
            raise ValueError('annotation issues omit or invent conflicts, severity, locations or source evidence')

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('draft', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'type': 'AnnotationDraft', 'fields': {field.name: _value(getattr(self, field.name)) for field in fields(self)}})


DRAFT_TYPES = NET_TYPES + (AnnotationDraft,)
