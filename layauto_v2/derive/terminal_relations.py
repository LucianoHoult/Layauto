"""Read-only terminal aggregation sharing one authenticated local input chain.

Neutral construction proves internal consistency. Captured-input trust belongs
to normalization; neither this draft nor its comparisons publish layout state.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Literal, cast

from layauto_v2.annotation.net_regions import build_net_annotation_draft
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.domain.circuit import SemanticCircuitDraft, semantic_value
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import evidence_value, mapping, sequence
from layauto_v2.domain.identifiers import DeviceId, NetId, identity_value
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.net_annotation import AnnotationRef, NetEvidence
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.terminal_relations import (
    ROLES, SCOPE, VERSION, TERMINAL_TYPES, SupportStatus, TerminalRef, TerminalRelation,
    TerminalTarget, _value, problem, records, validate_terminal_graph,
)
from layauto_v2.state.annotation import AnnotationDraft, DRAFT_TYPES as ANNOTATION_TYPES
from layauto_v2.state.local_connectivity import LocalConnectivityDraft
from .channel_identity import (
    ChannelIdentityDraft, DRAFT_TYPES as CHANNEL_TYPES, build_channel_identity_draft,
)
from .body_relations import evaluate_body


def _capture_sources(value: object, allowed: set[tuple[str, str | None]], *, raw_locations: bool) -> None:
    """Close actual SourceRefs and the query/source field-operand locations."""
    seen: set[int] = set()

    def visit(item: object) -> None:
        if item is None or type(item) in (str, int, bool, bytes):
            return
        if id(item) in seen:
            return
        seen.add(id(item))
        if type(item) is SourceRef:
            source = item
            if (source.uri, source.sha256) not in allowed:
                raise ValueError('terminal provenance belongs to another captured source set')
        elif type(item) is FrozenMap:
            row = item
            if raw_locations and 'sha256' in row and ('uri' in row or 'path' in row):
                if (row.get('uri', row.get('path')), row['sha256']) not in allowed:
                    raise ValueError('terminal field operand belongs to another capture')
            for child in row.values():
                visit(child)
        elif type(item) is tuple:
            for child in item:
                visit(child)
        elif is_dataclass(item):
            for member in fields(item):
                visit(getattr(item, member.name))

    visit(value)


def _require(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
             channel_seeds: tuple[ChannelSeed, ...], net_evidence: tuple[NetEvidence, ...],
             derived: EvidenceRecord, body_evidence: EvidenceRecord, capture_binding: FrozenMap) -> None:
    validate_terminal_graph((local, source, channel_seeds, net_evidence, derived,
                             body_evidence, capture_binding), DRAFT_TYPES)
    if (type(local) is not LocalConnectivityDraft or type(source) is not SemanticCircuitDraft
            or type(body_evidence) is not EvidenceRecord or body_evidence.kind != 'body'
            or len(body_evidence.sources) != 2):
        raise ValueError('terminal relations require one local/source chain and two-source body evidence')
    if type(capture_binding) is not FrozenMap:
        raise ValueError('terminal relations require the immutable captured source binding')
    allowed: set[tuple[str, str | None]] = {
        (str(mapping(row)['uri']), cast(str, mapping(row)['sha256']))
        for row in sequence(capture_binding['sources'])}
    # Raw body source_gds URI is a document binding, possibly relative. Its
    # interpretation belongs to evaluate_body; actual retained SourceRefs close
    # here without treating that raw spelling as a fresh captured selection.
    _capture_sources((local, derived, body_evidence.sources), allowed, raw_locations=False)
    _capture_sources((source, channel_seeds, net_evidence), allowed, raw_locations=True)
    gds_sources = local.effective.base.layout.gds.sources
    if (len(gds_sources) != 1
            or (body_evidence.sources[1].uri, body_evidence.sources[1].sha256)
            != (gds_sources[0].uri, gds_sources[0].sha256)
            or body_evidence.sources[0].uri == body_evidence.sources[1].uri):
        raise ValueError('body source roles do not bind its document followed by the actual local GDS')
    query_keys = tuple(row.query_key for row in channel_seeds) + tuple(row.query_key for row in net_evidence)
    query_runs = {(key.header_id, key.query_run_id, key.database_id) for key in query_keys}
    if len(query_runs) > 1:
        raise ValueError('terminal device/net evidence mixes query run or database identities')
    selected = next((cell for cell in source.cells if cell.id == source.selected_cell), None)
    if selected is None:
        raise ValueError('terminal source has no selected cell')
    for device in selected.devices:
        if tuple(terminal.role for terminal in device.terminals) != ROLES:
            raise problem(device.terminals[0].source if device.terminals else source.preservation.sources[0],
                          '/source_admission/terminal_order',
                          'source device must retain exactly one ordered D/G/S/B terminal',
                          'IncompleteSourceTerminalSet')


def _binding(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
             channel_seeds: tuple[ChannelSeed, ...], net_evidence: tuple[NetEvidence, ...],
             derived: EvidenceRecord, body_evidence: EvidenceRecord, capture_binding: FrozenMap) -> TerminalRef:
    return TerminalRef('binding', digest({
        'schema': VERSION, 'scope': SCOPE, 'local_ref': local.ref.to_value(),
        'source_semantics': semantic_value(source), 'source_preservation': evidence_value(source.preservation),
        'source_profile': source.profile_id, 'source_dialect': source.dialect,
        'selected_source_cell': identity_value(source.selected_cell),
        'channel_seeds': tuple(seed.to_value() for seed in channel_seeds),
        'net_evidence': tuple(seed.to_value() for seed in net_evidence),
        'derived': evidence_value(derived), 'body_evidence': evidence_value(body_evidence),
        'capture_binding': capture_binding,
    }))


def _body_paths(body: FrozenMap) -> tuple[FrozenMap, ...]:
    return tuple(mapping(item) for item in sequence(body['paths']))


def _body_ref(path: FrozenMap, name: str, choices: tuple[LocalRef, ...]) -> tuple[LocalRef, ...]:
    value = path.get(name)
    if value is None:
        return ()
    matches = tuple(item for item in choices if item.to_value() == value)
    if len(matches) != 1:
        raise ValueError('body path retains a foreign or ambiguous local physical reference')
    return matches


def _observed(path: FrozenMap, source: SemanticCircuitDraft) -> tuple[NetId, ...]:
    nets = tuple(net.id for cell in source.cells if cell.id == source.selected_cell for net in cell.nets)
    result: list[NetId] = []
    for value in sequence(path['observed_net_ids']):
        matches = tuple(net for net in nets if identity_value(net) == value)
        if len(matches) != 1:
            raise ValueError('body path observed net has no unique source identity')
        result.append(matches[0])
    observed = tuple(sorted(set(result), key=lambda item: item.id))
    if len(observed) != len(result):
        raise ValueError('body path repeats an observed net identity')
    return observed


def _relations(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
               channels: ChannelIdentityDraft, annotation: AnnotationDraft,
               body: FrozenMap, binding_ref: TerminalRef) -> tuple[TerminalRelation, ...]:
    selected = next(cell for cell in source.cells if cell.id == source.selected_cell)
    by_device = {row.device_id: row.channel_ref for row in channels.associations}
    topology = {row.channel_ref: row for row in channels.topology}
    summaries = {row.component_ref: row for row in annotation.components}
    all_nodes = tuple(node.ref for node in local.nodes)
    all_components = tuple(component.ref for component in local.components)
    rows: list[TerminalRelation] = []
    paths = _body_paths(body)
    for device in selected.devices:
        channel = by_device.get(device.id)
        physical = None if channel is None else topology.get(channel)
        path_matches = tuple(path for path in paths if path['device_id'] == identity_value(device.id))
        if len(path_matches) != 1:
            raise ValueError('body paths must retain exactly one row per source device')
        path = path_matches[0]
        for expected in device.terminals:
            role = expected.role
            node_refs: tuple[LocalRef, ...] = ()
            component_refs: tuple[LocalRef, ...] = ()
            support: SupportStatus = 'indeterminate'
            observed: tuple[NetId, ...] = ()
            context: FrozenMap | None = None
            extra_evidence: tuple[AnnotationRef, ...] = ()
            if role == 'B':
                context = path
                node_refs = _body_ref(path, 'local_body_node_ref', all_nodes)
                component_refs = _body_ref(path, 'local_body_component_ref', all_components)
                observed = _observed(path, source)
                support = 'established' if path['chain_status'] == 'established' and channel is not None else 'indeterminate'
                evidence_choices = tuple(row.ref for row in annotation.evidence)
                extra_evidence = tuple(reference for reference in evidence_choices
                                       if any(reference.to_value() == value for value in sequence(path['evidence_refs'])))
                if len(extra_evidence) != len(sequence(path['evidence_refs'])):
                    raise ValueError('body path evidence does not close to the common annotation input')
            elif physical is not None:
                if role == 'D':
                    node_refs, component_refs = (physical.drain_node,), (physical.drain_component,)
                elif role == 'S':
                    node_refs, component_refs = (physical.source_node,), (physical.source_component,)
                else:
                    node_refs, component_refs = physical.gate_nodes, physical.gate_components
                support = 'established'
            node_refs = tuple(sorted(set(node_refs), key=lambda item: item.sha256))
            component_refs = tuple(sorted(set(component_refs), key=lambda item: item.sha256))
            target_refs = tuple(sorted((target.ref for target in annotation.targets if target.node_ref in node_refs),
                                       key=lambda item: item.sha256))
            local_nets = tuple(sorted({net for component in component_refs
                                       for net in summaries[component].observed_net_ids}, key=lambda item: item.id))
            evidence = tuple(sorted({ref for component in component_refs for ref in summaries[component].evidence_refs}
                                    | set(extra_evidence), key=lambda item: item.sha256))
            if role != 'B':
                observed = local_nets
            rows.append(TerminalRelation(TerminalTarget(binding_ref, device.id, role), expected, channel,
                         node_refs, component_refs, target_refs, local_nets, evidence, context, observed, support))
    return tuple(rows)


@dataclass(frozen=True)
class TerminalRelationsDraft:
    local: LocalConnectivityDraft
    source: SemanticCircuitDraft
    channel_seeds: tuple[ChannelSeed, ...]
    net_evidence: tuple[NetEvidence, ...]
    derived: EvidenceRecord
    body_evidence: EvidenceRecord
    capture_binding: FrozenMap
    schema_version: str = VERSION
    binding_ref: TerminalRef = field(init=False)
    channel_observations: FrozenMap = field(init=False)
    annotation: AnnotationDraft = field(init=False)
    body: FrozenMap = field(init=False)
    relations: tuple[TerminalRelation, ...] = field(init=False)
    issues: tuple[EvidenceIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported terminal draft schema')
        object.__setattr__(self, 'channel_seeds', records(self.channel_seeds, ChannelSeed, 'channel seeds'))
        object.__setattr__(self, 'net_evidence', records(self.net_evidence, NetEvidence, 'net evidence'))
        _require(self.local, self.source, self.channel_seeds, self.net_evidence, self.derived,
                 self.body_evidence, self.capture_binding)
        channels = build_channel_identity_draft(self.local, self.source, self.channel_seeds, self.derived)
        annotation = build_net_annotation_draft(self.local, self.source, self.net_evidence,
                                                 self.derived, self.capture_binding)
        body, body_issues = evaluate_body(channels, annotation, self.body_evidence)
        validate_terminal_graph((body, body_issues))
        binding = _binding(self.local, self.source, self.channel_seeds, self.net_evidence, self.derived,
                           self.body_evidence, self.capture_binding)
        relations = _relations(self.local, self.source, channels, annotation, body, binding)
        object.__setattr__(self, 'binding_ref', binding)
        object.__setattr__(self, 'channel_observations', channels.to_value())
        object.__setattr__(self, 'annotation', annotation)
        object.__setattr__(self, 'body', body)
        object.__setattr__(self, 'relations', relations)
        object.__setattr__(self, 'issues', channels.issues + tuple(row.issue for row in annotation.issues) + body_issues)
        validate_terminal_graph(self, DRAFT_TYPES)

    @property
    def comparison_status(self) -> Literal['equal', 'mismatch', 'indeterminate']:
        if any(row.status == 'mismatch' for row in self.relations):
            return 'mismatch'
        if not self.relations or any(row.status != 'equal' for row in self.relations):
            return 'indeterminate'
        return 'equal'

    @property
    def channel_comparison_status(self) -> Literal['equal', 'mismatch', 'indeterminate']:
        return cast(Literal['equal', 'mismatch', 'indeterminate'],
                    mapping(self.channel_observations['coverage'])['source_comparison'])

    @property
    def source_comparison_status(self) -> Literal['equal', 'mismatch', 'indeterminate']:
        if 'mismatch' in (self.comparison_status, self.channel_comparison_status):
            return 'mismatch'
        if self.issues or 'indeterminate' in (self.comparison_status, self.channel_comparison_status):
            return 'indeterminate'
        return 'equal'

    @property
    def differences(self) -> tuple[FrozenMap, ...]:
        rows = tuple(mapping(row) for row in sequence(self.channel_observations['comparisons']))
        return tuple(row for row in rows
                     if mapping(row['fields'])['measured'] != mapping(mapping(row['fields'])['declared'])['exact'])

    @property
    def terminal_differences(self) -> tuple[TerminalRelation, ...]:
        return tuple(row for row in self.relations if row.status == 'mismatch')

    @property
    def coverage(self) -> FrozenMap:
        return FrozenMap({'scope': SCOPE, 'roles': ROLES,
            'source_device_count': len(self.relations) // len(ROLES), 'terminal_count': len(self.relations),
            'terminal_comparison': self.comparison_status, 'channel_comparison': self.channel_comparison_status,
            'source_comparison': self.source_comparison_status,
            'inherited_local_enclosure_status': self.local.local_enclosure_status,
            'local_graph_union': False, 'physical_pin_access_established': False,
            'production_matched_body_evidence': self.body_evidence.payload['production_matched_body_evidence'],
            'lvs_status': self.body_evidence.payload['lvs_status'],
            'deferred': ('complete_model_VT_extraction', 'other_mandatory_rules',
                         'production_U06', 'baseline_no_change_Stage6')})

    @property
    def ref(self) -> TerminalRef:
        return TerminalRef('draft', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        validate_terminal_graph(self, DRAFT_TYPES)
        return FrozenMap({'schema': self.schema_version, 'binding_ref': self.binding_ref.to_value(),
            'channel_observations': self.channel_observations, 'annotation': self.annotation.to_value(),
            'body': self.body, 'relations': tuple(row.to_value() for row in self.relations),
            'issues': tuple(_value(issue) for issue in self.issues), 'coverage': self.coverage})


DRAFT_TYPES = TERMINAL_TYPES + CHANNEL_TYPES + ANNOTATION_TYPES + (TerminalRelationsDraft,)


def build_terminal_relations_draft(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
                                  channel_seeds: tuple[ChannelSeed, ...], net_evidence: tuple[NetEvidence, ...],
                                  derived: EvidenceRecord, body_evidence: EvidenceRecord,
                                  capture_binding: FrozenMap) -> TerminalRelationsDraft:
    return TerminalRelationsDraft(local, source, channel_seeds, net_evidence, derived,
                                   body_evidence, capture_binding)
