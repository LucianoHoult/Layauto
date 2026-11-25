"""Project one already authenticated Stage 2 result into transaction inputs."""
from __future__ import annotations

from collections import Counter, defaultdict
from types import MappingProxyType

from layauto_v2.domain.geometry import LayerPolicy
from layauto_v2.domain.regions import RegionRef
from layauto_v2.state.discrete_occupancy import DiscreteOccupancy, ProjectionDiagnostic
from layauto_v2.state.mutation import LayerInitialization, ProjectionGap, ProposedInitialState, TargetContext
from .stage2 import Stage2Facts


def _projection_gap(policy: LayerPolicy) -> ProjectionGap:
    if policy.declaration['role'] == 'gate':
        # Requirements for the gate-track operation, not a claim about its pitch.
        return ProjectionGap('initialize_gate_tracks', (
            'projection=1d_track', 'index_axis', 'pitch_nm or pitch_nm_ref',
            'first_centre.basis=lower_edge_plus_half_width',
            'first_centre.lower_edge_nm or lower_edge_nm_ref',
            'first_centre.width_nm or width_nm_ref', 'index_range_inclusive',
        ))
    return ProjectionGap('initialize_layer_occupancy', ('projection',))


def _layers(index: DiscreteOccupancy) -> dict[str, LayerInitialization]:
    effective = index.effective
    assert effective is not None  # W020 always projects the shared effective draft.
    counts: Counter[tuple[str, str]] = Counter()
    piece_area: Counter[RegionRef] = Counter()
    record_layers = {}
    # W018 intersects each source with disjoint cells (or one on-track strip).
    # Equality of exact areas therefore proves coverage for that source alone.
    for record in index.layout.records:
        record_layers[record.id] = record.layer
        drawn = index.for_record(record.id, view='drawn')
        if sum(f.rect.area for f in drawn) == record.rect.area:
            counts[record.layer, 'drawn'] += 1
        for fragment in index.for_record(record.id, view='effective'):
            assert fragment.piece_ref is not None
            piece_area[fragment.piece_ref] += fragment.rect.area
    for result in effective.records:
        layer = record_layers[result.record_id]
        for region in result.regions:
            for piece in region.pieces:
                counts[layer, 'pieces'] += 1
                if piece_area[piece.ref] == piece.rect.area:
                    counts[layer, 'effective'] += 1
    diagnostics: dict[str, list[ProjectionDiagnostic]] = defaultdict(list)
    for issue in index.diagnostics:
        diagnostics[issue.source.layer].append(issue)
    layers = {}
    for report in index.layers:
        name = report.layer
        policy = index.layout.policy(name)
        gap = _projection_gap(policy) if policy.projected and report.projection == 'missing_declaration' else None
        layers[name] = LayerInitialization(policy, report, counts[name, 'drawn'], counts[name, 'pieces'],
                                           counts[name, 'effective'], tuple(diagnostics[name]), gap)
    return layers


class _AssembledInitialState(ProposedInitialState):
    __slots__ = ()

    def __init__(self, facts: Stage2Facts) -> None:
        if type(facts) is not Stage2Facts:
            raise TypeError('candidate requires facts from one full Stage 2 assembly')
        terminal = facts.terminals.value
        assert terminal is not None
        semantic = facts.terminals.semantic_facts
        object.__setattr__(self, 'current', semantic.source)
        object.__setattr__(self, 'target_context', TargetContext(semantic.target, semantic.differences))
        object.__setattr__(self, 'occupancy', facts.occupancy)
        object.__setattr__(self, 'connectivity', terminal.local)
        object.__setattr__(self, 'annotation', terminal.annotation)
        object.__setattr__(self, 'terminals', terminal.relations)
        object.__setattr__(self, 'channel_observations', terminal.channel_observations)
        object.__setattr__(self, 'body', terminal.body)
        object.__setattr__(self, 'body_evidence', terminal.body_evidence)
        object.__setattr__(self, 'capture_binding', terminal.capture_binding)
        object.__setattr__(self, 'layers', MappingProxyType(_layers(facts.occupancy)))


def build_proposed_initial_state(facts: Stage2Facts) -> ProposedInitialState:
    return _AssembledInitialState(facts)
