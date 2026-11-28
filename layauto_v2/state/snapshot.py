"""Freeze the checked Stage 2 owners into exact values for repository readback."""
from __future__ import annotations

from dataclasses import fields, is_dataclass

from layauto_v2.domain.circuit import SemanticCircuitDraft
from layauto_v2.domain.codec import FrozenMap, Value, freeze
from layauto_v2.domain.geometry import source_value
from .layer_checks import LayerInitializationChecks
from .mutation import ProposedInitialState


def _fields(value: object) -> FrozenMap:
    """Preserve declared DTO fields, including exact operands, lexemes and locations."""
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError('expected a Stage 2 value record')
    return FrozenMap({f.name: _value(getattr(value, f.name)) for f in fields(value)})


def _value(value: object) -> Value:
    if isinstance(value, FrozenMap):
        return value
    if isinstance(value, tuple):
        return tuple(_value(v) for v in value)
    if is_dataclass(value):
        return _fields(value)
    return freeze(value)


def current_value(circuit: SemanticCircuitDraft) -> FrozenMap:
    return _fields(circuit)


def target_values(candidate: ProposedInitialState) -> tuple[FrozenMap, tuple[FrozenMap, ...]]:
    target = candidate.target_context
    return _fields(target.target), tuple(_fields(d) for d in target.differences)


def _geometry(candidate: ProposedInitialState) -> FrozenMap:
    layout = candidate.layout
    effective = candidate.connectivity.effective
    regions = {region.ref.sha256: region for row in effective.records for region in row.regions}
    regions.update((n.region.ref.sha256, n.region) for n in candidate.connectivity.nodes)
    return FrozenMap({
        'top': layout.top, 'units': layout.units.to_value(),
        'records': {r.id.sha256: r.to_value() for r in layout.records},
        'effective_by_record': {r.record_id.sha256: {
            'operation': r.operation, 'contributors': tuple(c.sha256 for c in r.contributors),
            'region_ids': tuple(region.ref.sha256 for region in r.regions)} for r in effective.records},
        'regions': {key: region.to_value() for key, region in regions.items()},
        'pieces': {p.ref.sha256: p.to_value() for region in regions.values() for p in region.pieces},
    })


def _annotation(candidate: ProposedInitialState) -> FrozenMap:
    annotation = candidate.annotation
    return FrozenMap({
        'validity': annotation.binding.validity, 'scope': annotation.binding.scope,
        'binding_id': annotation.binding.ref.sha256,
        'unknown_conductor_policy': candidate.uncovered_conductor_policy,
        'rules_source': source_value(candidate.rules.sources[0]),
        'targets': {t.ref.sha256: {'id': _fields(t.target_id), 'node': t.node_ref.sha256,
                                   'component': t.component_ref.sha256, 'source': source_value(t.source)}
                    for t in annotation.targets},
        'fragments': {f.ref.sha256: _fields(f) for f in annotation.fragments},
        'evidence': {e.ref.sha256: _fields(e) for e in annotation.evidence},
        'matches': tuple(_fields(m) for m in annotation.matches),
        'coverage': tuple(_fields(c) for c in annotation.coverage),
        'classifications': tuple(_fields(c) for c in annotation.classifications),
        'components': tuple(_fields(c) for c in annotation.components),
        'issues': tuple(_fields(i) for i in annotation.issues),
    })


def snapshot_state(checks: LayerInitializationChecks) -> FrozenMap:
    if not checks.passed:
        raise ValueError('snapshot requires complete layer checks')
    c = checks.candidate
    index, graph = c.occupancy, c.connectivity
    model = index.model
    return FrozenMap({
        'current': current_value(c.current), 'semantic_assurance': 'committed_unverified',
        'geometry': _geometry(c),
        'coordinates': {'model_id': model.model_id, 'unit_id': model.unit_ref.sha256,
                        'tech_bundle': source_value(model.tech_sources[0]),
                        'tech_owners': tuple(source_value(s) for s in model.tech_sources[1:]),
                        'origin_nm': model.frame_origin_nm,
                        'axes': {k: _value(v) for k, v in model.layers.items()}},
        'layers': {name: {'policy': row.initialization.policy.to_value(),
                          'projection': _fields(row.initialization.projection),
                          'availability': row.initialization.availability,
                          'drawn_reconstructed': row.initialization.drawn_reconstructed,
                          'effective_reconstructed': row.initialization.effective_reconstructed,
                          'gate_track_numbers_available': row.gate_track_numbers_available}
                   for name, row in checks.layers.items()},
        'checks': {'comparator': source_value(checks.comparator), 'frame_rule': source_value(checks.frame_rule),
                   'lifecycle_operator': source_value(checks.lifecycle_operator)},
        'occupancy': tuple({'view': f.view, 'layer': f.layer, 'record_id': f.record_id.sha256,
                            'indices': f.indices, 'rect': f.rect.bounds,
                            'region_id': None if f.region_ref is None else f.region_ref.sha256,
                            'piece_id': None if f.piece_ref is None else f.piece_ref.sha256}
                           for f in index.fragments),
        'connectivity': {'scope': graph.binding.scope, 'operators': graph.binding.consumed,
                         'binding_id': graph.binding.ref.sha256,
                         'nodes': {n.ref.sha256: {'layer': n.layer, 'region_id': n.region.ref.sha256}
                                   for n in graph.nodes},
                         'edges': {e.ref.sha256: e.to_value() for e in graph.edges},
                         'components': {g.ref.sha256: tuple(m.sha256 for m in g.members)
                                        for g in graph.components},
                         'enclosure': tuple(a.to_value() for a in graph.audits)},
        'annotation': _annotation(c), 'terminals': tuple(_fields(t) for t in c.terminals),
        'channels': c.channel_observations, 'body': c.body,
        'body_sources': tuple(source_value(s) for s in c.body_evidence.sources),
    })
