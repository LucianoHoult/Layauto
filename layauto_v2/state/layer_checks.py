"""Read-only, prepublication layer checks over one assembled initial candidate."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import NamedTuple

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import (
    DrawnRecord, Rect, StreamLayerKey, UnitBinding, integer, mapping, sequence, text,
)
from layauto_v2.domain.results import EvidenceIssue
from .layout_store import LayoutDraft
from .mutation import LayerInitialization, ProposedInitialState

LIFECYCLE_OPERATOR = ('all preserve_drawn elements retain drawn signatures; frame_static also binds frame '
                      'signature; no prepublication_derived layer in this profile; operator DAG effective '
                      'geometry -> fragments -> contacts/body -> terminal graph -> mandatory rules')
_FRAME_RULE = {
    'exact_evaluator_ref': 'w003-toy-predicate/T01.frame/1',
    'scope': 'all non-frame drawn records', 'predicate': 'each bbox contained in sole BOUNDARY',
    'schema_version': 'w003-toy-rule/1', 'unit': 'nm', 'parameters': {'margin_nm': 0},
    'relation_basis': 'geometry_only', 'required_relation_assurance': 'none',
    'missing_context_policy': 'reject_indeterminate', 'required': True,
}


class DrawnSignature(NamedTuple):
    source: SourceRef
    top: str
    key: StreamLayerKey
    layer: str
    purpose: str
    rect: Rect

    @classmethod
    def from_record(cls, record: DrawnRecord) -> DrawnSignature:
        return cls(record.source, record.top, record.stream_key, record.layer, record.purpose, record.rect)


def source_signatures(gds: FrozenMap, source: SourceRef, drawn: FrozenMap,
                      units: UnitBinding) -> dict[str, list[DrawnSignature]]:
    """Read the captured stream elements and selected mapping, independently of layout.records."""
    layers = {}
    for value in sequence(drawn['layers']):
        declaration = mapping(value)
        stream = mapping(declaration['stream_key'])
        key = StreamLayerKey(text(stream['element']), integer(stream['layer']), integer(stream['datatype']))
        layers[key] = text(declaration['name']), text(declaration['purpose'])
    top = text(gds['top'])
    result: dict[str, list[DrawnSignature]] = defaultdict(list)
    for value in sequence(gds['elements']):
        row = mapping(value)
        key = StreamLayerKey(text(row['element']), integer(row['layer']), integer(row['datatype']))
        name, purpose = layers[key]
        bounds = (units.source_to_canonical(integer(v)) for v in sequence(row['bbox']))
        location = replace(source, byte_offset=integer(row['byte_offset']),
                           record_index=integer(row['record_index']))
        result[name].append(DrawnSignature(location, top, key, name, purpose, Rect(*bounds)))
    return result


def _drawn_issues(expected: list[DrawnSignature], records: list[DrawnRecord]) -> tuple[EvidenceIssue, ...]:
    source = Counter(expected)
    actual = Counter(DrawnSignature.from_record(record) for record in records)
    missing = (EvidenceIssue('binding', 'MissingDrawnRecord', 'captured signature missing from layer', s.source)
               for s in (source - actual).elements())
    extra = (EvidenceIssue('binding', 'UnexpectedDrawnRecord', 'unexpected drawn signature on layer', s.source)
             for s in (actual - source).elements())
    return (*missing, *extra)


def _frame_rule(rules: EvidenceRecord) -> tuple[SourceRef, tuple[EvidenceIssue, ...]]:
    for i, value in enumerate(sequence(rules.payload['rules'])):
        rule = mapping(value)
        if rule['id'] == 'T01.frame':
            ref = replace(rules.sources[0], field=f'/rules/{i}')
            issues = tuple(EvidenceIssue('unsupported', 'UnsupportedFrameRule', 'unsupported T01.frame field',
                                         replace(ref, field=f'/rules/{i}/{key}'))
                           for key, expected in _FRAME_RULE.items() if rule[key] != expected)
            return ref, issues
    ref = replace(rules.sources[0], field='/rules')
    return ref, (EvidenceIssue('config', 'MissingFrameRule', 'T01.frame is required', ref),)


def _bound_frame(layout: LayoutDraft, expected: dict[str, list[DrawnSignature]],
                 records: dict[str, list[DrawnRecord]]) -> tuple[DrawnRecord | None, tuple[EvidenceIssue, ...]]:
    # T01.frame/1 names the sole BOUNDARY. A different enclosing polygon is insufficient.
    roles = [p for p in layout.policies if p.declaration['role'] == 'boundary']
    if len(roles) != 1 or roles[0].name != 'BOUNDARY':
        ref = replace(layout.drawn.sources[0], field='/layers')
        return None, (EvidenceIssue('binding', 'FrameRoleMismatch', 'expected one BOUNDARY role', ref),)
    captured, actual = expected['BOUNDARY'], records['BOUNDARY']
    if len(captured) == len(actual) == 1 and captured[0] == DrawnSignature.from_record(actual[0]):
        return actual[0], ()
    ref = captured[0].source if captured else layout.gds.sources[0]
    return None, (EvidenceIssue('binding', 'FrameBindingMismatch', 'expected the sole captured BOUNDARY', ref),)


def _projection_issues(row: LayerInitialization) -> tuple[EvidenceIssue, ...]:
    kind = row.projection.projection
    if row.policy.projected and kind in ('missing_declaration', 'projection_none'):
        return (EvidenceIssue('config', 'RequiredProjectionUnavailable', f'initialize_layer_occupancy: {kind}',
                              row.projection.declaration),)
    return ()


@dataclass(frozen=True, slots=True)
class LayerCheck:
    """Projection counts, per-source diagnostics and gap fields remain on initialization."""
    initialization: LayerInitialization
    sources: tuple[SourceRef, ...]
    drawn_issues: tuple[EvidenceIssue, ...]
    lifecycle_issues: tuple[EvidenceIssue, ...]
    frame_issues: tuple[EvidenceIssue, ...]
    projection_issues: tuple[EvidenceIssue, ...]
    frame: DrawnRecord | None

    @property
    def lifecycle_passed(self) -> bool:
        needs_frame = self.initialization.policy.declaration['lifecycle'] == 'frame_static'
        return not (self.drawn_issues or self.lifecycle_issues or (needs_frame and self.frame_issues))

    @property
    def projection_passed(self) -> bool:
        return not self.projection_issues and self.initialization.availability != 'incomplete'

    @property
    def gate_track_numbers_available(self) -> bool | None:
        """Whether this gate layer has records, all on declared 1D tracks. None for other roles."""
        row = self.initialization
        if row.policy.declaration['role'] != 'gate':
            return None
        return (row.projection.projection == '1d_track' and row.projection.record_count > 0
                and row.drawn_reconstructed == row.projection.record_count)

    @property
    def passed(self) -> bool:
        return self.lifecycle_passed and not self.frame_issues and self.projection_passed


@dataclass(frozen=True, slots=True)
class LayerInitializationChecks:
    """Construct from the W021 candidate. All verdicts are derived; no IO or publication."""
    candidate: ProposedInitialState
    layers: Mapping[str, LayerCheck] = field(init=False)
    comparator: SourceRef = field(init=False)
    lifecycle_operator: SourceRef = field(init=False)
    frame_rule: SourceRef = field(init=False)

    def __post_init__(self) -> None:
        state = self.candidate
        if not isinstance(state, ProposedInitialState):
            raise TypeError('layer checks require a W021 candidate')
        layout = state.layout
        # W008 admits only its implemented geometry comparator; retain that exact field.
        comparator = replace(layout.formats.sources[0], field='/geometry_capability/comparator')
        physical = state.connectivity.binding.physical
        operator = replace(physical.sources[0], field='/operators/lifecycle~11')
        lifecycle_issues: tuple[EvidenceIssue, ...] = ()
        if mapping(physical.payload['operators']).get('lifecycle/1') != LIFECYCLE_OPERATOR:
            lifecycle_issues = (EvidenceIssue('unsupported', 'UnsupportedLifecycleOperator',
                                              'unsupported lifecycle/1 semantics', operator),)
        # The W005 owner schema requires lifecycle/1 in required_operator_refs.
        expected = source_signatures(layout.gds.payload, layout.gds.sources[0], layout.drawn.payload, layout.units)
        actual: dict[str, list[DrawnRecord]] = defaultdict(list)
        for record in layout.records:
            actual[record.layer].append(record)
        frame, binding_issues = _bound_frame(layout, expected, actual)
        rule, rule_issues = _frame_rule(state.rules)
        checked = {}
        for name, row in state.layers.items():
            policy = row.policy
            lifecycle = lifecycle_issues
            if policy.declaration['lifecycle'] not in ('preserve_drawn', 'frame_static'):
                lifecycle += (EvidenceIssue('unsupported', 'UnsupportedLifecycle', 'unsupported layer lifecycle',
                                            replace(policy.source, field=f'{policy.source.field}/lifecycle')),)
            frame_issues = binding_issues + rule_issues
            if frame is not None and not rule_issues:
                frame_issues += tuple(EvidenceIssue('binding', 'OutsideFrame', 'drawn record exceeds T01.frame',
                                                    record.source) for record in actual[name]
                                      if frame.rect.intersection(record.rect) != record.rect)
            # W018 takes exact disjoint intersections per source. W021 checked their
            # summed areas for every drawn record and every effective region piece.
            checked[name] = LayerCheck(row, tuple(s.source for s in expected[name]),
                                       _drawn_issues(expected[name], actual[name]), lifecycle, frame_issues,
                                       _projection_issues(row), frame)
        object.__setattr__(self, 'layers', MappingProxyType(checked))
        object.__setattr__(self, 'comparator', comparator)
        object.__setattr__(self, 'lifecycle_operator', operator)
        object.__setattr__(self, 'frame_rule', rule)

    @property
    def passed(self) -> bool:
        """True when all layer initialization obligations checked here are met."""
        return all(layer.passed for layer in self.layers.values())
