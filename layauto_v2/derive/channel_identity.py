"""Self-reconstructing neutral channel identity and FIN analysis draft.

Captured-input authentication belongs to normalization. This aggregate retains
all local topology/audits and source evidence without publishing state.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from typing import Literal, cast

from layauto_v2.annotation.channel_identity import locate_channels
from layauto_v2.domain.channel_identity import (
    CHANNEL_TYPES, SCOPE, VERSION, ChannelAssociation, ChannelMeasurement, ChannelRef, ChannelSeed,
    ChannelTopology, FinRelation, ParameterComparison, SeedLocation, problem, records,
)
from layauto_v2.domain.circuit import (
    Cell, Device, Membership, Net, Parameter, SemanticCircuitDraft, Terminal, semantic_value,
)
from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, evidence_value, mapping, sequence
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId, QueryKey, identity_value
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.regions import ExactRegion, RegionRef, validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.state.local_connectivity import DRAFT_TYPES as LOCAL_DRAFT_TYPES, LocalConnectivityDraft
from layauto_v2.tech.schema import SchemaError, validate_payload
from .fin_count import evaluate_fins

CONSUMED_PROFILE = FrozenMap({
    'id': 'toy_fin_crossing/1',
    'fin_representation': 'explicit_static_fin_plus_active_window',
    'effective_fin_operator': 'identity',
    'effective_active_operator': 'identity_OD',
    'recognized_channel_operator': 'positive_area_OD_intersect_POLY_with_exactly_one_gate_stripe_per_active',
    'qualification': 'FIN intersects full channel x span and is fully contained in active y interval; partial fin is unsupported, never rounded',
    'count': 'distinct qualified FIN rectangles for each recognized channel, grouped by the one-to-one device identity join',
    'finger_count_required': 1, 'multiplicity_required': 1,
})
CONSUMED_DERIVED = FrozenMap({
    'target_layer': 'POLY', 'carries': ('device_id',), 'accepted_geometry_kinds': ('rectangle',),
    'quality': 'exact', 'annotation_match_tolerance_nm': 0,
    'trim_operator': 'recognized_channel_intersection', 'conflict_policy': 'reject_ambiguous',
})
_SOURCE_TYPES = (CellId, DeviceId, NetId, QueryKey, Parameter, Terminal, Membership, Device, Net,
                 Cell, SemanticCircuitDraft, EvidenceRecord, SourceRef)


def _rebuild(value: object) -> object:
    """Reconstruct semantic leaves as well as aggregates, without IO/codecs."""
    if type(value) is tuple:
        return tuple(_rebuild(item) for item in value)
    if any(type(value) is cls for cls in _SOURCE_TYPES) and is_dataclass(value):
        constructor = cast(Callable[..., object], type(value))
        return constructor(**{field.name: _rebuild(getattr(value, field.name)) for field in fields(value)})
    return value


def _require(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
             seeds: tuple[ChannelSeed, ...], derived: EvidenceRecord) -> None:
    if type(local) is not LocalConnectivityDraft or type(source) is not SemanticCircuitDraft:
        raise ValueError('channel draft requires local graph and source circuit')
    validate_closed_graph((local, source, seeds, derived), DRAFT_TYPES)
    if _rebuild(source) != source:
        raise ValueError('source circuit is not completely reconstructible')
    if LocalConnectivityDraft(local.effective, local.binding, local.nodes, local.edges,
                              local.audits, local.components, local.schema_version) != local:
        raise ValueError('local graph is not completely reconstructible')
    if (type(derived) is not EvidenceRecord or derived.kind != 'derived' or len(derived.sources) != 1
            or derived.sources[0].sha256 is None):
        raise ValueError('channel draft requires a single-source derived owner')
    for seed in seeds:
        if ChannelSeed(seed.device_id, seed.query_key, seed.record, seed.identity_provenance, seed.schema_version) != seed:
            raise ValueError('seed is not completely reconstructible')
    if len({seed.record['record_id'] for seed in seeds}) != len(seeds) or len({seed.ref for seed in seeds}) != len(seeds):
        raise ValueError('duplicate seed record identity')
    query_runs = {(seed.query_key.header_id, seed.query_key.query_run_id, seed.query_key.database_id) for seed in seeds}
    if len(query_runs) > 1:
        raise ValueError('seeds mix query capture identities')
    by_device: dict[DeviceId, tuple[QueryKey, FrozenMap]] = {}
    by_query: dict[QueryKey, DeviceId] = {}
    for seed in seeds:
        pair = (seed.query_key, seed.identity_provenance)
        if seed.device_id in by_device and by_device[seed.device_id] != pair:
            raise ValueError('one device has inconsistent identity evidence')
        if seed.query_key in by_query and by_query[seed.query_key] != seed.device_id:
            raise ValueError('query identity maps to more than one source device')
        by_device[seed.device_id], by_query[seed.query_key] = pair, seed.device_id


def _owners(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
            seeds: tuple[ChannelSeed, ...], derived: EvidenceRecord) -> None:
    physical = local.binding.physical
    drawn = local.binding.drawn
    for owner, kind in ((physical, 'physical'), (drawn, 'drawn'), (derived, 'derived')):
        schema_error: SchemaError | None = None
        try:
            validate_payload(owner.payload, kind)
        except SchemaError as exc:
            schema_error = exc
        if schema_error is not None:
            # Construct outside the handler: an unexpected diagnostic failure
            # must not acquire this handled input error as its implicit context.
            raise problem(owner.sources[0], schema_error.path or '/',
                          'invalid channel policy owner: ' + str(schema_error)) from schema_error
    profile = mapping(physical.payload['fin_count_profile'])
    for key, expected in CONSUMED_PROFILE.items():
        if profile.get(key) != expected:
            raise problem(physical.sources[0], '/fin_count_profile/' + key, 'unsupported consumed FIN counting semantics')
    extraction = mapping(physical.payload['device_extraction_contract'])
    for key, expected in (('id', 'toy_device_terminal_context/2'), ('cardinality', 'one_to_one'),
                          ('device_reduction', 'forbidden'), ('mapping_missing_or_ambiguous', 'typed_fail'),
                          ('sd_policy', 'left connected component of OD minus channel is S, right is D; ordered terminals, swap unsupported')):
        if extraction.get(key) != expected:
            raise problem(physical.sources[0], '/device_extraction_contract/' + key, 'unsupported device-channel grouping')
    rows = tuple(mapping(row) for row in sequence(drawn.payload['layers']))
    fins = tuple((index, row) for index, row in enumerate(rows) if row.get('name') == 'FIN')
    if len(fins) != 1:
        raise problem(drawn.sources[0], '/layers', 'FIN layer must resolve uniquely')
    index, fin = fins[0]
    for key, expected in (('role', 'fin'), ('purpose', 'drawing')):
        if fin.get(key) != expected:
            raise problem(drawn.sources[0], f'/layers/{index}/{key}', 'unsupported FIN layer semantics')
    for index, row in enumerate(rows):
        if row.get('role') == 'fin' and row.get('name') != 'FIN':
            raise problem(drawn.sources[0], f'/layers/{index}/role',
                          'additional FIN layer is outside the identity-FIN profile subset')
    registry = tuple(mapping(row) for row in sequence(derived.payload['derived_registry']))
    for seed in seeds:
        matches = tuple((index, row) for index, row in enumerate(registry) if row.get('id') == seed.record['derived_layer'])
        if len(matches) != 1:
            raise problem(derived.sources[0], '/derived_registry', 'device seed registry must resolve uniquely')
        index, declaration = matches[0]
        for key, expected in CONSUMED_DERIVED.items():
            if declaration.get(key) != expected:
                raise problem(derived.sources[0], f'/derived_registry/{index}/{key}', 'unsupported consumed seed localization policy')
        if seed.identity_provenance['sd_swap'] is not False:
            raise problem(derived.sources[0], f'/derived_registry/{index}', 'ordered toy terminals do not support query S/D swap')
    selected = next(cell for cell in source.cells if cell.id == source.selected_cell)
    models = mapping(physical.payload['models'])
    for device in selected.devices:
        model = models.get(device.model)
        if type(model) is not FrozenMap:
            raise problem(physical.sources[0], '/models', 'source model has no parameter mapping')
        axes = mapping(model['parameter_axes'])
        if any(axes.get(parameter.token) != parameter.axis for parameter in device.parameters):
            raise problem(physical.sources[0], '/models/' + device.model + '/parameter_axes', 'source canonical axes differ from model mapping')
        parameters = {parameter.axis: parameter for parameter in device.parameters}
        for axis in ('fins_per_finger', 'channel_length', 'fin_width', 'finger_count', 'multiplicity'):
            if axis not in parameters:
                raise problem(physical.sources[0], '/models/' + device.model, 'source lacks required measured/admission axis')
        for axis in ('finger_count', 'multiplicity'):
            parameter = parameters[axis]
            if parameter.unit != 'count' or parameter.exact != Fraction(1):
                raise problem(parameter.source, '/source_admission/' + axis, 'single-finger one-to-one source requires NF=M=1')


def _binding(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
             seeds: tuple[ChannelSeed, ...], derived: EvidenceRecord) -> ChannelRef:
    return ChannelRef('binding', digest({'schema': VERSION, 'scope': SCOPE,
        'local_ref': local.ref.to_value(), 'source_semantics': semantic_value(source),
        'source_evidence': evidence_value(source.preservation),
        'seeds': tuple(seed.to_value() for seed in seeds), 'derived': evidence_value(derived),
        'unit_ref': local.effective.base.layout.units.ref.to_value(),
        'consumed_profile': CONSUMED_PROFILE, 'consumed_derived': CONSUMED_DERIVED}))


def _topology(local: LocalConnectivityDraft, channels: tuple[ExactRegion, ...],
              binding_ref: ChannelRef) -> tuple[ChannelTopology, ...]:
    nodes = {node.region.ref: node.ref for node in local.nodes}
    components = {member: component.ref for component in local.components for member in component.members}
    result = []
    for channel in channels:
        terminal = local.effective.for_record(channel.owner_id)
        source_node, drain_node = nodes[terminal.regions[1].ref], nodes[terminal.regions[2].ref]
        gates = tuple(sorted((node.ref for node in local.nodes if node.layer == 'POLY'
                              and node.region.owner_id in channel.contributors), key=lambda ref: ref.sha256))
        gate_components = tuple(sorted({components[gate] for gate in gates}, key=lambda ref: ref.sha256))
        result.append(ChannelTopology(channel.ref, gates, gate_components, source_node, components[source_node],
                                       drain_node, components[drain_node], binding_ref))
    return tuple(result)


def _comparisons(source: SemanticCircuitDraft, associations: tuple[ChannelAssociation, ...],
                 measurements: tuple[ChannelMeasurement, ...], binding_ref: ChannelRef
                 ) -> tuple[ParameterComparison, ...]:
    devices = {device.id: device for cell in source.cells if cell.id == source.selected_cell for device in cell.devices}
    measured = {measurement.channel_ref: measurement for measurement in measurements}
    result: list[ParameterComparison] = []
    for association in associations:
        parameters = {parameter.axis: parameter for parameter in devices[association.device_id].parameters}
        measurement = measured[association.channel_ref]
        values: list[tuple[Literal['fins_per_finger', 'channel_length', 'fin_width'], Fraction, GeometryRecordId | None]] = [
            ('channel_length', measurement.length_nm / 1_000_000_000, None)]
        if measurement.count is not None:
            values.append(('fins_per_finger', Fraction(measurement.count), None))
        # Width is independently measurable even when independence/count is not.
        # Partial crossings likewise retain their actual drawn FIN width.
        values.extend(('fin_width', item.width_nm / 1_000_000_000, item.fin_id)
                      for item in measurement.evaluations if item.crossing is not None)
        result.extend(ParameterComparison(association.device_id, association.channel_ref, axis, value,
                      parameters[axis], fin_id, binding_ref) for axis, value, fin_id in values)
    return tuple(result)


Analysis = tuple[tuple[SeedLocation, ...], tuple[ChannelAssociation, ...], tuple[ChannelTopology, ...],
                 tuple[ChannelMeasurement, ...], tuple[FinRelation, ...], tuple[ParameterComparison, ...],
                 tuple[EvidenceIssue, ...]]


def _analyze(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
             seeds: tuple[ChannelSeed, ...], derived: EvidenceRecord) -> Analysis:
    _require(local, source, seeds, derived)
    _owners(local, source, seeds, derived)
    binding_ref = _binding(local, source, seeds, derived)
    channels = tuple(record.regions[0] for record in local.effective.records if record.operation == 'terminal')
    layout = local.effective.base.layout
    selected = next(cell for cell in source.cells if cell.id == source.selected_cell)
    channel_sources = tuple(layout.record(channel.owner_id).source for channel in channels)
    locations, associations, location_issues = locate_channels(selected.devices, channels, seeds,
            layout.units.canonical_tick_nm, binding_ref, channel_sources)
    measurements, relations, fin_issues = evaluate_fins(channels, layout.records, layout.units.canonical_tick_nm, binding_ref)
    return (locations, associations, _topology(local, channels, binding_ref), measurements, relations,
            _comparisons(source, associations, measurements, binding_ref), location_issues + fin_issues)


@dataclass(frozen=True)
class ChannelIdentityDraft:
    local: LocalConnectivityDraft
    source: SemanticCircuitDraft
    seeds: tuple[ChannelSeed, ...]
    derived: EvidenceRecord
    locations: tuple[SeedLocation, ...]
    associations: tuple[ChannelAssociation, ...]
    topology: tuple[ChannelTopology, ...]
    measurements: tuple[ChannelMeasurement, ...]
    fin_relations: tuple[FinRelation, ...]
    comparisons: tuple[ParameterComparison, ...]
    issues: tuple[EvidenceIssue, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported channel draft schema')
        for name, cls in (('seeds', ChannelSeed), ('locations', SeedLocation), ('associations', ChannelAssociation),
                          ('topology', ChannelTopology), ('measurements', ChannelMeasurement), ('fin_relations', FinRelation),
                          ('comparisons', ParameterComparison), ('issues', EvidenceIssue)):
            object.__setattr__(self, name, records(getattr(self, name), cls, name))
        validate_closed_graph(self, DRAFT_TYPES)
        expected = _analyze(self.local, self.source, self.seeds, self.derived)
        actual = self.locations, self.associations, self.topology, self.measurements, self.fin_relations, self.comparisons, self.issues
        if actual != expected:
            raise ValueError('channel draft omitted/added/altered localization, geometry, topology, comparisons or issues')

    @property
    def binding_ref(self) -> ChannelRef:
        return _binding(self.local, self.source, self.seeds, self.derived)

    @property
    def ref(self) -> ChannelRef:
        return ChannelRef('draft', digest(self.to_value()))

    @property
    def differences(self) -> tuple[ParameterComparison, ...]:
        return tuple(item for item in self.comparisons if item.status == 'mismatch')

    @property
    def comparison_status(self) -> Literal['equal', 'mismatch', 'indeterminate']:
        if self.differences:
            return 'mismatch'
        if (not self.measurements or self.issues or len(self.associations) != len(self.measurements)
                or any(item.count is None or not item.crossings for item in self.measurements)):
            return 'indeterminate'
        return 'equal'

    @property
    def coverage(self) -> FrozenMap:
        return FrozenMap({'scope': SCOPE, 'measured_axes': ('fins_per_finger', 'channel_length', 'fin_width'),
            'consumed_profile': CONSUMED_PROFILE, 'consumed_derived': CONSUMED_DERIVED,
            'association_is_full_region_annotation': False, 'source_comparison': self.comparison_status,
            'inherited_local_enclosure_status': self.local.local_enclosure_status,
            'unmeasured_width_channels': tuple(item.channel_ref.to_value() for item in self.measurements
                                              if not any(fin.crossing is not None for fin in item.evaluations)),
            'deferred': ('complete_net_body_model_VT_matching', 'T02_and_all_mandatory_rules',
                         'manufacturing_coordinates', 'production_U06', 'baseline_no_change_Stage6')})

    @property
    def semantic_digest(self) -> str:
        layout = self.local.effective.base.layout
        channel_boxes = {item.channel_ref: layout.record(item.active_id).rect.bounds for item in self.measurements}
        fin_boxes = {record.id: record.rect.bounds for record in layout.records if record.layer == 'FIN'}
        locations = tuple(FrozenMap({'device': identity_value(seed.device_id), 'seed_rect': seed.rectangle.bounds,
                           'candidates': tuple(sorted(((channel_boxes[item.channel_ref], item.intersection.bounds,
                                                         item.coverage_fraction) for item in location.intersections), key=canonical_bytes))})
                          for location in self.locations for seed in self.seeds if seed.ref == location.seed_ref)
        measurements = tuple(FrozenMap({'active': channel_boxes[item.channel_ref], 'length_nm': item.length_nm,
                         'count': item.count, 'fins': tuple(sorted(((fin_boxes[fin.fin_id], fin.status,
                             None if fin.crossing is None else fin.crossing.bounds, fin.width_nm) for fin in item.evaluations), key=canonical_bytes))}) for item in self.measurements)
        comparisons = tuple(FrozenMap({'device': identity_value(item.device_id), 'active': channel_boxes[item.channel_ref],
                           'axis': item.axis, 'measured': item.measured, 'declared': item.declared.exact,
                           'fin': None if item.fin_id is None else fin_boxes[item.fin_id]}) for item in self.comparisons)
        return digest({'schema': VERSION, 'scope': SCOPE, 'local_semantic': self.local.semantic_digest,
                       'source_semantics': semantic_value(self.source),
                       'locations': tuple(sorted(locations, key=canonical_bytes)),
                       'measurements': tuple(sorted(measurements, key=canonical_bytes)),
                       'comparisons': tuple(sorted(comparisons, key=canonical_bytes))})

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'binding_ref': self.binding_ref.to_value(),
            'locations': tuple(item.to_value() for item in self.locations),
            'associations': tuple(item.to_value() for item in self.associations),
            'topology': tuple(item.to_value() for item in self.topology),
            'measurements': tuple(item.to_value() for item in self.measurements),
            'fin_relations': tuple(item.to_value() for item in self.fin_relations),
            'comparisons': tuple(item.to_value() for item in self.comparisons),
            'issues': tuple(FrozenMap({'category': item.category, 'code': item.code, 'message': item.message,
                                      'source': evidence_value(EvidenceRecord('issue', FrozenMap({}), (item.source,)))}) for item in self.issues),
            'coverage': self.coverage})


DRAFT_TYPES = CHANNEL_TYPES + LOCAL_DRAFT_TYPES + _SOURCE_TYPES + (ChannelIdentityDraft,)


def build_channel_identity_draft(local: LocalConnectivityDraft, source: SemanticCircuitDraft,
                                 seeds: tuple[ChannelSeed, ...], derived: EvidenceRecord) -> ChannelIdentityDraft:
    snapshot = records(seeds, ChannelSeed, 'seeds')
    return ChannelIdentityDraft(local, source, snapshot, derived, *_analyze(local, source, snapshot, derived))
