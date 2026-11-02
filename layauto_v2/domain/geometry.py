"""Exact drawn-geometry values. No IO, technology lattice or topology inference.

A neutral record proves internal consistency, not authenticity of its evidence.
The normalization boundary authenticates that evidence against captured bytes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, fields
from fractions import Fraction
from typing import Literal, cast

from .codec import FrozenMap, Value, digest, freeze_map, rational
from .evidence import EvidenceRecord, SourceRef

VERSION = 'layauto-geometry/1'
GEOMETRY_COMPARATOR = ('multiset(element,layer,datatype,exact_integer_bbox) and top identity; '
                       'source-record backlinks retained; no byte equality requirement')
RefKind = Literal['unit', 'layer_policy', 'layout', 'base_partition', 'base_occupancy']


def integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError('geometry requires an exact integer, not bool/float')
    return value


def text(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError('geometry requires nonempty text')
    value.encode('utf-8')
    return value


def mapping(value: object) -> FrozenMap:
    if type(value) is not FrozenMap:
        raise ValueError('geometry requires an immutable map')
    return value


def sequence(value: object) -> tuple[Value, ...]:
    if type(value) is not tuple:
        raise ValueError('geometry requires an immutable sequence')
    return cast('tuple[Value, ...]', value)


def version(value: str) -> None:
    if value != VERSION:
        raise ValueError('unsupported geometry schema version')


def source_value(value: SourceRef) -> FrozenMap:
    if type(value) is not SourceRef or value.sha256 is None:
        raise ValueError('geometry requires a captured source reference')
    return FrozenMap({field.name: getattr(value, field.name) for field in fields(value)})


def evidence_value(value: EvidenceRecord) -> FrozenMap:
    if type(value) is not EvidenceRecord:
        raise ValueError('expected geometry evidence')
    return FrozenMap({'kind': value.kind, 'payload': value.payload,
                      'sources': tuple(source_value(ref) for ref in value.sources),
                      'parser_version': value.parser_version, 'schema_version': value.schema_version})


def _sha(value: str) -> None:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('geometry identity requires lowercase SHA-256')


@dataclass(frozen=True)
class GeometryRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if self.kind not in ('unit', 'layer_policy', 'layout', 'base_partition', 'base_occupancy'):
            raise ValueError('unknown geometry reference kind')
        _sha(self.sha256)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


@dataclass(frozen=True)
class GeometryRecordId:
    sha256: str

    def __post_init__(self) -> None:
        _sha(self.sha256)


@dataclass(frozen=True)
class OccupantFragmentId:
    sha256: str

    def __post_init__(self) -> None:
        _sha(self.sha256)


@dataclass(frozen=True)
class Rect:
    """Positive-area rectangle in exact integer DBU; half-open for indexing."""
    x0: int
    y0: int
    x1: int
    y1: int

    def __post_init__(self) -> None:
        for coordinate in self.bounds:
            integer(coordinate)
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError('rectangle must have positive area')

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        return self.x0, self.y0, self.x1, self.y1

    @property
    def area(self) -> int:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def intersection(self, other: Rect) -> Rect | None:
        if type(other) is not Rect:
            raise ValueError('intersection requires an exact rectangle')
        x0, y0, x1, y1 = max(self.x0, other.x0), max(self.y0, other.y0), min(self.x1, other.x1), min(self.y1, other.y1)
        return Rect(x0, y0, x1, y1) if x0 < x1 and y0 < y1 else None


@dataclass(frozen=True)
class StreamLayerKey:
    element: str
    layer: int
    datatype: int

    def __post_init__(self) -> None:
        if self.element != 'BOUNDARY' or not 0 <= integer(self.layer) <= 32767 or not 0 <= integer(self.datatype) <= 32767:
            raise ValueError('outside the BOUNDARY stream-key subset')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'element': self.element, 'layer': self.layer, 'datatype': self.datatype})


@dataclass(frozen=True)
class UnitBinding:
    """Preserved verified scale evidence; never performs source quantization."""
    contract: FrozenMap
    encoded: FrozenMap
    source: SourceRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        object.__setattr__(self, 'contract', freeze_map(self.contract))
        object.__setattr__(self, 'encoded', freeze_map(self.encoded))
        source_value(self.source)
        if set(self.contract) != {'id', 'nominal_tick_m', 'nominal_user_unit_m', 'canonical_tick_nm',
                                  'gds_units_first_nominal', 'encoding', 'equivalence', 'geometry_quantization',
                                  'source_tick_policy', 'output_xy_range', 'output_nominal_selection', 'nominal_source'}:
            raise ValueError('unknown or missing unit contract fields')
        if set(self.encoded) != {'contract', 'user_units_per_tick', 'metres_per_tick'} or self.encoded['contract'] != self.contract['id']:
            raise ValueError('unit contract and encoding disagree')
        if self.nominal_tick_m <= 0 or self.canonical_tick_nm <= 0:
            raise ValueError('unit scales must be positive')
        first = rational(self.contract['gds_units_first_nominal'])
        if first <= 0 or self.nominal_tick_m / first != rational(self.contract['nominal_user_unit_m']):
            raise ValueError('inconsistent nominal unit ratio')
        for name, nominal in (('user_units_per_tick', first), ('metres_per_tick', self.nominal_tick_m)):
            record = mapping(self.encoded[name])
            if set(record) != {'raw', 'exact', 'nominal', 'encoding_delta', 'ulp', 'byte_offset', 'record_index'}:
                raise ValueError('unknown or missing unit encoding fields')
            if type(record['raw']) is not bytes or len(record['raw']) != 8:
                raise ValueError('unit encoding must retain eight REAL8 bytes')
            if any(type(record[key]) is not Fraction for key in ('exact', 'nominal', 'encoding_delta', 'ulp')):
                raise ValueError('unit encoding requires exact rational values')
            exact, delta, ulp = cast(Fraction, record['exact']), cast(Fraction, record['encoding_delta']), cast(Fraction, record['ulp'])
            if record['nominal'] != nominal or exact <= 0 or ulp <= 0 or exact - nominal != delta or abs(delta) > ulp / 2:
                raise ValueError('unit binding values disagree')
            if integer(record['byte_offset']) < 0 or integer(record['record_index']) < 0:
                raise ValueError('invalid unit source position')

    @property
    def nominal_tick_m(self) -> Fraction:
        return rational(self.contract['nominal_tick_m'])

    @property
    def canonical_tick_nm(self) -> int:
        return integer(self.contract['canonical_tick_nm'])

    @property
    def ref(self) -> GeometryRef:
        return GeometryRef('unit', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'contract': self.contract,
                          'encoded': self.encoded, 'source': source_value(self.source)})

    def source_to_nm(self, tick: int) -> Fraction:
        return integer(tick) * self.nominal_tick_m * 1_000_000_000

    def nm_to_canonical(self, nm: Fraction | int) -> int:
        if type(nm) not in (Fraction, int):
            raise ValueError('physical coordinate must be exact')
        coordinate = Fraction(nm) / self.canonical_tick_nm
        if coordinate.denominator != 1:
            raise ValueError('source coordinate is not exactly representable in canonical DBU')
        return coordinate.numerator

    def source_to_canonical(self, tick: int) -> int:
        return self.nm_to_canonical(self.source_to_nm(tick))

    def canonical_to_nm(self, tick: int) -> Fraction:
        return Fraction(integer(tick) * self.canonical_tick_nm)

    def canonical_to_source(self, tick: int) -> int:
        value = self.canonical_to_nm(tick) / (self.nominal_tick_m * 1_000_000_000)
        if value.denominator != 1:
            raise ValueError('canonical coordinate has no exact source tick')
        return value.numerator


@dataclass(frozen=True)
class LayerPolicy:
    declaration: FrozenMap
    source: SourceRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        object.__setattr__(self, 'declaration', freeze_map(self.declaration))
        source_value(self.source)
        required = {'name', 'stream_key', 'purpose', 'tier', 'role', 'lifecycle', 'edit_policy',
                    'projection_kind', 'derived_layer_refs'}
        optional = {'cut_target', 'effective_geometry_operator', 'electrical_connects', 'contact_predicate', 'enclosure_rule'}
        if not required <= set(self.declaration) or not set(self.declaration) <= required | optional:
            raise ValueError('unknown or missing layer policy fields')
        for key in ('name', 'purpose', 'tier', 'role', 'lifecycle', 'edit_policy', 'projection_kind'):
            text(self.declaration[key])
        stream = mapping(self.declaration['stream_key'])
        if set(stream) != {'element', 'layer', 'datatype'}:
            raise ValueError('unknown or missing stream key fields')
        StreamLayerKey(text(stream['element']), integer(stream['layer']), integer(stream['datatype']))
        if self.declaration['tier'] not in ('A', 'B', 'C1', 'C2') or self.declaration['projection_kind'] not in ('none', 'exact_fragment_rectangles'):
            raise ValueError('unsupported layer tier/projection')

    @property
    def name(self) -> str:
        return text(self.declaration['name'])

    @property
    def projected(self) -> bool:
        return self.declaration['projection_kind'] == 'exact_fragment_rectangles'

    @property
    def ref(self) -> GeometryRef:
        return GeometryRef('layer_policy', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'declaration': self.declaration, 'source': source_value(self.source)})


def record_identity(source: SourceRef, top: str) -> GeometryRecordId:
    source_value(source)
    if source.byte_offset is None or source.record_index is None:
        raise ValueError('drawn record requires a located BOUNDARY source')
    return GeometryRecordId(digest({'schema': 'layauto-drawn-record-id/1', 'source': source_value(source), 'top': text(top)}))


@dataclass(frozen=True)
class DrawnRecord:
    id: GeometryRecordId
    top: str
    stream_key: StreamLayerKey
    layer: str
    purpose: str
    source: SourceRef
    raw_xy: tuple[tuple[int, int], ...]
    rect: Rect
    unit_ref: GeometryRef
    policy_ref: GeometryRef
    preservation: FrozenMap
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        for value in (self.top, self.layer, self.purpose):
            text(value)
        if type(self.id) is not GeometryRecordId or self.id != record_identity(self.source, self.top):
            raise ValueError('drawn record identity differs from its source position')
        if type(self.rect) is not Rect or type(self.stream_key) is not StreamLayerKey:
            raise ValueError('invalid drawn geometry value')
        if type(self.unit_ref) is not GeometryRef or self.unit_ref.kind != 'unit' or type(self.policy_ref) is not GeometryRef or self.policy_ref.kind != 'layer_policy':
            raise ValueError('drawn record requires typed unit/layer policy refs')
        if not isinstance(self.raw_xy, (tuple, list)):
            raise ValueError('drawn XY must be a sequence')
        points: list[tuple[int, int]] = []
        for pair in self.raw_xy:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError('drawn XY requires coordinate pairs')
            points.append((integer(pair[0]), integer(pair[1])))
        object.__setattr__(self, 'raw_xy', tuple(points))
        if len(points) != 5 or points[0] != points[-1] or len(set(points[:-1])) != 4:
            raise ValueError('drawn record must retain a closed four-corner rectangle')
        if any((a[0] == b[0]) == (a[1] == b[1]) for a, b in zip(points, points[1:])):
            raise ValueError('drawn record has a diagonal or zero-length edge')
        xs, ys = {p[0] for p in points}, {p[1] for p in points}
        if len(xs) != 2 or len(ys) != 2:
            raise ValueError('drawn polygon is not an exact rectangle')
        object.__setattr__(self, 'preservation', freeze_map(self.preservation))
        expected_keys = {'element', 'layer', 'datatype', 'canonical_layer', 'xy', 'bbox', 'byte_offset',
                         'record_index', 'xy_byte_offset', 'xy_record_index', 'byte_length'}
        row = self.preservation
        if set(row) != expected_keys:
            raise ValueError('invalid preserved BOUNDARY evidence fields')
        if (row['xy'] != self.raw_xy or row['bbox'] != (min(xs), min(ys), max(xs), max(ys))
                or row['canonical_layer'] != self.layer or row['byte_offset'] != self.source.byte_offset
                or row['record_index'] != self.source.record_index
                or any(row[key] != self.stream_key.to_value()[key] for key in ('element', 'layer', 'datatype'))):
            raise ValueError('drawn geometry disagrees with its preservation record')
        for key in ('byte_offset', 'record_index', 'xy_byte_offset', 'xy_record_index', 'byte_length'):
            if integer(row[key]) < 0:
                raise ValueError('negative drawn record position/length')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'id': self.id.sha256, 'top': self.top,
                          'stream_key': self.stream_key.to_value(), 'layer': self.layer, 'purpose': self.purpose,
                          'source': source_value(self.source), 'raw_xy': self.raw_xy, 'rect': self.rect.bounds,
                          'unit_ref': self.unit_ref.to_value(), 'policy_ref': self.policy_ref.to_value(),
                          'preservation': self.preservation})
