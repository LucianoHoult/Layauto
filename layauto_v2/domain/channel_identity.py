"""Closed neutral evidence and measurements for finite channel attribution.

These immutable values establish representation consistency, not capture trust,
complete annotation, device extraction, or published state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass, replace
from fractions import Fraction
from typing import Literal, TypeVar, cast

from .codec import FrozenMap, Value, digest, rational
from .circuit import Parameter
from .evidence import EvidenceRecord, SourceRef
from .geometry import GeometryRecordId, GeometryRef, Rect, mapping, sequence, source_value
from .identifiers import CellId, DeviceId, QueryKey, identity_value
from .local_connectivity import LocalRef
from .regions import RegionRef, validate_closed_graph
from .results import EvidenceIssue

VERSION = 'layauto-channel-identity/1'
SCOPE = 'local_channel_identity_fin_measurement/1'
RefKind = Literal['binding', 'seed', 'location', 'association', 'topology', 'evaluation',
                  'relation', 'measurement', 'comparison', 'draft']
T = TypeVar('T')


def records(value: object, cls: type[T], name: str) -> tuple[T, ...]:
    """Snapshot native caller collections once, before inspecting their members."""
    if type(value) is not tuple and type(value) is not list:
        raise ValueError('invalid channel collection: ' + name)
    copied = tuple(value)
    if any(type(item) is not cls for item in copied):
        raise ValueError('invalid channel collection: ' + name)
    return copied


def _fraction(value: object, *, positive: bool = False) -> None:
    if type(value) is not Fraction:
        raise ValueError('channel values require exact Fraction scalars')
    validate_closed_graph(value)
    if positive and value <= 0:
        raise ValueError('channel dimension must be positive')


def _version(value: object) -> None:
    if type(value) is not str or value != VERSION:
        raise ValueError('unsupported channel identity schema')


def _ref(value: object, cls: type[object], kind: str) -> None:
    if type(value) is not cls or getattr(value, 'kind', None) != kind:
        raise ValueError('incorrect typed channel reference')


def _common(value: object) -> None:
    _version(getattr(value, 'schema_version'))
    validate_closed_graph(value, CHANNEL_TYPES)


def _value(value: object) -> Value:
    if any(type(value) is cls for cls in _NEW_TYPES) and is_dataclass(value):
        return FrozenMap({'type': type(value).__name__,
                          'fields': {field.name: _value(getattr(value, field.name)) for field in fields(value)}})
    if type(value) in (CellId, DeviceId, QueryKey):
        return identity_value(cast(CellId | DeviceId | QueryKey, value))
    if type(value) is GeometryRecordId:
        return FrozenMap({'geometry_record_id': value.sha256})
    if type(value) is Rect:
        return value.bounds
    if type(value) in (GeometryRef, RegionRef, LocalRef):
        return cast(GeometryRef | RegionRef | LocalRef, value).to_value()
    if type(value) is SourceRef:
        return source_value(value)
    if type(value) is Parameter:
        return FrozenMap({'axis': value.axis, 'token': value.token, 'exact': value.exact,
                          'unit': value.unit, 'lexeme': value.lexeme,
                          'source': source_value(value.source), 'field_evidence': value.field_evidence})
    if type(value) is tuple:
        return tuple(_value(item) for item in value)
    if value is None or type(value) in (str, int, bool, bytes, Fraction, FrozenMap):
        return cast(Value, value)
    raise ValueError('foreign channel value')


class ChannelProblem(ValueError):
    """Only expected unsupported owner policies abort draft construction."""

    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def problem(source: SourceRef, field: str, message: str,
            code: str = 'UnsupportedChannelOperator') -> ChannelProblem:
    return ChannelProblem(EvidenceIssue('unsupported', code, message, replace(source, field=field)))


@dataclass(frozen=True)
class ChannelRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in ('binding', 'seed', 'location', 'association',
                'topology', 'evaluation', 'relation', 'measurement', 'comparison', 'draft'):
            raise ValueError('unknown channel reference kind')
        if type(self.sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.sha256) is None:
            raise ValueError('channel reference requires lowercase SHA-256')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


class _Record:
    def to_value(self) -> FrozenMap:
        return cast(FrozenMap, _value(self))


@dataclass(frozen=True)
class RationalRect(_Record):
    x0: Fraction
    y0: Fraction
    x1: Fraction
    y1: Fraction

    def __post_init__(self) -> None:
        for value in self.bounds:
            _fraction(value)
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError('rational rectangle requires positive area')

    @property
    def bounds(self) -> tuple[Fraction, Fraction, Fraction, Fraction]:
        return self.x0, self.y0, self.x1, self.y1

    @property
    def area(self) -> Fraction:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def intersection(self, other: RationalRect) -> RationalRect | None:
        if type(other) is not RationalRect:
            raise ValueError('intersection requires a rational rectangle')
        x0, y0 = max(self.x0, other.x0), max(self.y0, other.y0)
        x1, y1 = min(self.x1, other.x1), min(self.y1, other.y1)
        return RationalRect(x0, y0, x1, y1) if x0 < x1 and y0 < y1 else None


@dataclass(frozen=True)
class ChannelSeed(_Record):
    device_id: DeviceId
    query_key: QueryKey
    record: FrozenMap
    identity_provenance: FrozenMap
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.device_id) is not DeviceId or type(self.query_key) is not QueryKey:
            raise ValueError('channel seed requires typed device/query identities')
        _common(self)
        if type(self.record) is not FrozenMap or type(self.identity_provenance) is not FrozenMap:
            raise ValueError('channel seed requires closed immutable evidence')
        row = self.record
        required = {'record_id', 'derived_layer', 'geometry_kind', 'quality', 'vertices_nm', 'bbox_nm',
                    'unit', 'precision', 'metadata_opaque', 'section_header_opaque', 'field_sources',
                    'layout_instance', 'schematic_instance'}
        if set(row) != required or self.query_key.kind != 'device':
            raise ValueError('invalid channel seed fields')
        if (row['layout_instance'] != self.query_key.identity or row['schematic_instance'] != self.device_id.name
                or row['geometry_kind'] != 'rectangle' or row['quality'] != 'exact' or row['unit'] != 'nm'
                or type(row['precision']) is not int or row['precision'] <= 0):
            raise ValueError('unsupported or inconsistent seed identity/geometry')
        for key in ('record_id', 'derived_layer', 'section_header_opaque'):
            if type(row[key]) is not str or not row[key]:
                raise ValueError('seed requires exact nonempty text')
        provenance = self.identity_provenance
        if (set(provenance) != {'layout_instance', 'schematic_instance', 'sd_swap', 'field_sources'}
                or provenance['layout_instance'] != self.query_key.identity
                or provenance['schematic_instance'] != self.device_id.name
                or type(provenance['sd_swap']) is not bool
                or set(mapping(provenance['field_sources'])) != {'layout_instance', 'schematic_instance', 'sd_swap'}
                or set(mapping(row['field_sources'])) != required - {'field_sources'}):
            raise ValueError('seed requires complete matching xref/field provenance')
        box = mapping(row['bbox_nm'])
        if set(box) != {'x_min', 'y_min', 'x_max', 'y_max'}:
            raise ValueError('invalid seed rectangle fields')
        expected = self.rectangle
        vertices = tuple(mapping(point) for point in sequence(row['vertices_nm']))
        if len(vertices) != 4 or any(set(point) != {'x', 'y'} for point in vertices):
            raise ValueError('invalid seed vertices')
        coords = tuple((rational(point['x']), rational(point['y'])) for point in vertices)
        if (set(coords) != {(expected.x0, expected.y0), (expected.x0, expected.y1),
                            (expected.x1, expected.y0), (expected.x1, expected.y1)}
                or any((a[0] == b[0]) == (a[1] == b[1]) for a, b in zip(coords, (*coords[1:], coords[0])))):
            raise ValueError('seed polygon differs from exact rectangle')

    @property
    def rectangle(self) -> RationalRect:
        box = mapping(self.record['bbox_nm'])
        return RationalRect(*(rational(box[key]) for key in ('x_min', 'y_min', 'x_max', 'y_max')))

    @property
    def ref(self) -> ChannelRef:
        return ChannelRef('seed', digest(self.to_value()))


@dataclass(frozen=True)
class SeedIntersection(_Record):
    seed_ref: ChannelRef
    channel_ref: RegionRef
    intersection: RationalRect
    coverage_fraction: Fraction
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _ref(self.seed_ref, ChannelRef, 'seed')
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        if type(self.intersection) is not RationalRect:
            raise ValueError('seed intersection requires exact rational geometry')
        _fraction(self.coverage_fraction, positive=True)
        if self.coverage_fraction > 1:
            raise ValueError('seed intersection coverage exceeds channel')
        _common(self)


@dataclass(frozen=True)
class SeedLocation(_Record):
    seed_ref: ChannelRef
    intersections: tuple[SeedIntersection, ...]
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _ref(self.seed_ref, ChannelRef, 'seed')
        _ref(self.binding_ref, ChannelRef, 'binding')
        object.__setattr__(self, 'intersections', records(self.intersections, SeedIntersection, 'intersections'))
        if (len({item.channel_ref for item in self.intersections}) != len(self.intersections)
                or any(item.seed_ref != self.seed_ref or item.binding_ref != self.binding_ref for item in self.intersections)):
            raise ValueError('seed location has duplicate or foreign intersections')
        _common(self)


@dataclass(frozen=True)
class ChannelAssociation(_Record):
    device_id: DeviceId
    channel_ref: RegionRef
    seed_refs: tuple[ChannelRef, ...]
    coverage: tuple[RationalRect, ...]
    coverage_fraction: Fraction
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.device_id) is not DeviceId:
            raise ValueError('association requires typed semantic identity')
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        object.__setattr__(self, 'seed_refs', records(self.seed_refs, ChannelRef, 'seed refs'))
        object.__setattr__(self, 'coverage', records(self.coverage, RationalRect, 'coverage'))
        if not self.seed_refs or len(set(self.seed_refs)) != len(self.seed_refs) or not self.coverage:
            raise ValueError('association requires complete distinct seed evidence and coverage')
        for ref in self.seed_refs:
            _ref(ref, ChannelRef, 'seed')
        _fraction(self.coverage_fraction, positive=True)
        if self.coverage_fraction > 1:
            raise ValueError('association coverage exceeds channel')
        _common(self)

    @property
    def full_coverage(self) -> bool:
        return self.coverage_fraction == 1


@dataclass(frozen=True)
class ChannelTopology(_Record):
    channel_ref: RegionRef
    gate_nodes: tuple[LocalRef, ...]
    gate_components: tuple[LocalRef, ...]
    source_node: LocalRef
    source_component: LocalRef
    drain_node: LocalRef
    drain_component: LocalRef
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        object.__setattr__(self, 'gate_nodes', records(self.gate_nodes, LocalRef, 'gate nodes'))
        object.__setattr__(self, 'gate_components', records(self.gate_components, LocalRef, 'gate components'))
        if (not self.gate_nodes or len(set(self.gate_nodes)) != len(self.gate_nodes)
                or not self.gate_components or len(set(self.gate_components)) != len(self.gate_components)):
            raise ValueError('topology must retain distinct gate nodes/components')
        for node in (*self.gate_nodes, self.source_node, self.drain_node):
            _ref(node, LocalRef, 'node')
        for component in (*self.gate_components, self.source_component, self.drain_component):
            _ref(component, LocalRef, 'component')
        _common(self)


@dataclass(frozen=True)
class FinEvaluation(_Record):
    fin_id: GeometryRecordId
    channel_ref: RegionRef
    status: Literal['outside', 'touch', 'qualified', 'partial']
    crossing: Rect | None
    width_nm: Fraction
    source: SourceRef
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.fin_id) is not GeometryRecordId or type(self.source) is not SourceRef:
            raise ValueError('FIN evaluation requires original record provenance')
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        if type(self.status) is not str or self.status not in ('outside', 'touch', 'qualified', 'partial'):
            raise ValueError('invalid FIN qualification')
        if ((self.status in ('qualified', 'partial') and type(self.crossing) is not Rect)
                or (self.status in ('outside', 'touch') and self.crossing is not None)):
            raise ValueError('FIN crossing disagrees with qualification')
        _fraction(self.width_nm, positive=True)
        _common(self)


@dataclass(frozen=True)
class FinRelation(_Record):
    left_id: GeometryRecordId
    right_id: GeometryRecordId
    relation: Literal['duplicate', 'overlap']
    intersection: Rect
    channel_refs: tuple[RegionRef, ...]
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if (type(self.left_id) is not GeometryRecordId or type(self.right_id) is not GeometryRecordId
                or self.left_id.sha256 >= self.right_id.sha256 or type(self.intersection) is not Rect):
            raise ValueError('FIN relation requires distinct ordered records and exact overlap')
        if type(self.relation) is not str or self.relation not in ('duplicate', 'overlap'):
            raise ValueError('invalid FIN geometric relation')
        object.__setattr__(self, 'channel_refs', records(self.channel_refs, RegionRef, 'affected channels'))
        if len(set(self.channel_refs)) != len(self.channel_refs):
            raise ValueError('duplicate affected channel')
        for channel in self.channel_refs:
            _ref(channel, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        _common(self)

    @property
    def ref(self) -> ChannelRef:
        return ChannelRef('relation', digest(self.to_value()))


@dataclass(frozen=True)
class ChannelMeasurement(_Record):
    channel_ref: RegionRef
    active_id: GeometryRecordId
    length_nm: Fraction
    evaluations: tuple[FinEvaluation, ...]
    count: int | None
    unresolved_relations: tuple[ChannelRef, ...]
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        if type(self.active_id) is not GeometryRecordId:
            raise ValueError('channel measurement requires active record identity')
        _fraction(self.length_nm, positive=True)
        object.__setattr__(self, 'evaluations', records(self.evaluations, FinEvaluation, 'FIN evaluations'))
        object.__setattr__(self, 'unresolved_relations', records(self.unresolved_relations, ChannelRef, 'unresolved FIN relations'))
        if len({item.fin_id for item in self.evaluations}) != len(self.evaluations):
            raise ValueError('duplicate FIN evaluation')
        if any(item.channel_ref != self.channel_ref or item.binding_ref != self.binding_ref for item in self.evaluations):
            raise ValueError('measurement contains foreign FIN evaluations')
        for ref in self.unresolved_relations:
            _ref(ref, ChannelRef, 'relation')
        expected = None if self.unresolved_relations or any(item.status == 'partial' for item in self.evaluations) else sum(item.status == 'qualified' for item in self.evaluations)
        if (self.count is not None and type(self.count) is not int) or self.count != expected:
            raise ValueError('FIN count differs from the complete qualified/unsupported evidence')
        _common(self)

    @property
    def crossings(self) -> tuple[FinEvaluation, ...]:
        return tuple(item for item in self.evaluations if item.status == 'qualified')


@dataclass(frozen=True)
class ParameterComparison(_Record):
    device_id: DeviceId
    channel_ref: RegionRef
    axis: Literal['fins_per_finger', 'channel_length', 'fin_width']
    measured: Fraction
    declared: Parameter
    fin_id: GeometryRecordId | None
    binding_ref: ChannelRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.device_id) is not DeviceId or type(self.declared) is not Parameter:
            raise ValueError('comparison requires source device and parameter evidence')
        _ref(self.channel_ref, RegionRef, 'region')
        _ref(self.binding_ref, ChannelRef, 'binding')
        if type(self.axis) is not str or self.axis not in ('fins_per_finger', 'channel_length', 'fin_width'):
            raise ValueError('unsupported finite measured parameter axis')
        _fraction(self.measured)
        if self.measured < 0 or self.declared.axis != self.axis or type(self.declared.exact) is not Fraction:
            raise ValueError('comparison differs from its canonical source axis')
        if (self.axis == 'fins_per_finger' and self.measured.denominator != 1
                or self.axis != 'fins_per_finger' and self.measured <= 0):
            raise ValueError('measured count must be integral and dimensions positive')
        expected_unit = 'count' if self.axis == 'fins_per_finger' else 'metres'
        if self.declared.unit != expected_unit:
            raise ValueError('comparison requires canonical source units')
        if ((self.axis == 'fin_width' and type(self.fin_id) is not GeometryRecordId)
                or (self.axis != 'fin_width' and self.fin_id is not None)):
            raise ValueError('width comparison requires exactly one FIN record')
        _common(self)

    @property
    def status(self) -> Literal['equal', 'mismatch']:
        return 'equal' if self.measured == self.declared.exact else 'mismatch'


_NEW_TYPES = (ChannelRef, RationalRect, ChannelSeed, SeedIntersection, SeedLocation, ChannelAssociation,
              ChannelTopology, FinEvaluation, FinRelation, ChannelMeasurement, ParameterComparison)
CHANNEL_TYPES = _NEW_TYPES + (CellId, DeviceId, QueryKey, GeometryRecordId, GeometryRef, Rect, RegionRef,
                             LocalRef, SourceRef, EvidenceRecord, EvidenceIssue, Parameter)
