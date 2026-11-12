"""Exact, immutable local network annotation values; no capture or topology owner."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields, is_dataclass, replace
from fractions import Fraction
from math import gcd
import re
from typing import Literal, TypeVar, cast

from .channel_identity import RationalRect, _field_locations
from .codec import FrozenMap, Value, canonical_bytes, digest, rational
from .evidence import EvidenceRecord, SourceRef
from .geometry import GeometryRecordId, GeometryRef, Rect, mapping, sequence, source_value
from .identifiers import CellId, NetId, QueryKey
from .local_connectivity import ContactComponent, ContactNode, LocalRef
from .regions import ExactRegion, RegionRef
from .results import EvidenceIssue
from .source_location import ref_from_location

VERSION = 'layauto-net-annotation/1'
SCOPE = 'source_evidence_local_net_annotation/1'
RefKind = Literal['binding', 'evidence', 'target', 'match', 'fragment', 'coverage', 'component', 'classification', 'issue', 'draft']
T = TypeVar('T')


def validate_annotation_graph(value: object, record_types: tuple[type[object], ...] = ()) -> None:
    """Inspect original retained storage before any map iteration or copying.

    FrozenMap's public constructor is defensive, but a forged exact shell is
    not automatically an immutable value. Only native tuple backing and unique
    native text keys are admitted. Active-path detection rejects cycles while
    context-sensitive memoization permits shared immutable DAGs.
    """
    active: set[int] = set()
    complete: set[tuple[int, bool]] = set()

    def check(item: object, value_only: bool) -> None:
        cls = type(item)
        if item is None or cls is bool or cls is int or cls is str or cls is bytes:
            return
        if cls is Fraction:
            exact = cast(Fraction, item)
            numerator, denominator = exact.numerator, exact.denominator
            if (type(numerator) is not int or type(denominator) is not int
                    or denominator <= 0 or gcd(abs(numerator), denominator) != 1):
                raise ValueError('annotation fraction requires reduced native integer components')
            return
        is_map = cls is FrozenMap
        is_tuple = cls is tuple
        if not is_map and not is_tuple:
            if value_only or not any(cls is allowed for allowed in record_types) or not is_dataclass(item):
                raise ValueError('foreign or mutable value in annotation graph')
        identity = id(item)
        if identity in active:
            raise ValueError('cyclic value in annotation graph')
        context = identity, value_only
        if context in complete:
            return
        active.add(identity)
        try:
            if is_map:
                try:
                    backing = object.__getattribute__(item, '_entries')
                except AttributeError as exc:
                    raise ValueError('annotation map is missing immutable backing') from exc
                if type(backing) is not tuple:
                    raise ValueError('annotation map backing requires a native immutable tuple')
                seen: set[str] = set()
                for pair in backing:
                    if type(pair) is not tuple or len(pair) != 2:
                        raise ValueError('annotation map entries require native key/value tuples')
                    key, child = pair
                    if type(key) is not str or key in seen:
                        raise ValueError('annotation map keys require unique exact text')
                    seen.add(key)
                    check(child, True)
            elif is_tuple:
                for child in cast(tuple[object, ...], item):
                    check(child, value_only)
            else:
                assert is_dataclass(item)
                for field in fields(item):
                    try:
                        child = object.__getattribute__(item, field.name)
                    except AttributeError as exc:
                        raise ValueError('annotation record is missing a retained field') from exc
                    check(child, False)
        finally:
            active.remove(identity)
        complete.add(context)

    check(value, False)


def records(value: object, cls: type[T], name: str) -> tuple[T, ...]:
    if type(value) is not tuple and type(value) is not list:
        raise ValueError('invalid annotation collection: ' + name)
    copied = tuple(value)
    if any(type(item) is not cls for item in copied):
        raise ValueError('invalid annotation collection: ' + name)
    return copied


def text(value: object) -> None:
    if type(value) is not str or not value:
        raise ValueError('annotation requires exact nonempty text')
    value.encode('utf-8')


def sha(value: object) -> None:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('annotation requires lowercase SHA-256')


def fraction(value: object, *, nonnegative: bool = True) -> None:
    if type(value) is not Fraction:
        raise ValueError('annotation requires exact Fraction')
    validate_annotation_graph(value)
    if nonnegative and value < 0:
        raise ValueError('negative annotation measure')


def ref(value: object, cls: type[object], kind: str) -> None:
    if type(value) is not cls:
        raise ValueError('incorrect typed annotation reference')
    validate_annotation_graph(value, (cls,))
    if getattr(value, 'kind', None) != kind:
        raise ValueError('incorrect typed annotation reference')


def _value(value: object) -> Value:
    if any(type(value) is cls for cls in NET_TYPES) and is_dataclass(value):
        return FrozenMap({'type': type(value).__name__, 'fields': {
            field.name: _value(getattr(value, field.name)) for field in fields(value)}})
    if type(value) is tuple:
        return tuple(_value(item) for item in value)
    if value is None or type(value) in (str, int, bool, bytes, Fraction, FrozenMap):
        return cast(Value, value)
    raise ValueError('foreign annotation value')


def validate_members(value: object) -> None:
    if type(value) is tuple:
        for item in value:
            validate_members(item)
    elif any(type(value) is cls for cls in NET_TYPES) and is_dataclass(value):
        for field in fields(value):
            validate_members(getattr(value, field.name))
        constructor = cast(Callable[..., object], type(value))
        rebuilt = constructor(**{field.name: getattr(value, field.name) for field in fields(value)})
        if canonical_bytes(_value(rebuilt)) != canonical_bytes(_value(value)):
            raise ValueError('annotation member differs from validated reconstruction')


def common(value: object) -> None:
    version = getattr(value, 'schema_version')
    if type(version) is not str or version != VERSION:
        raise ValueError('unsupported net annotation schema')
    validate_annotation_graph(value, NET_TYPES)
    if not is_dataclass(value):
        raise ValueError('annotation requires a dataclass record')
    for field in fields(value):
        validate_members(getattr(value, field.name))


def ordered_refs(value: object, kind: str) -> tuple[AnnotationRef, ...]:
    result = records(value, AnnotationRef, kind + ' references')
    for item in result:
        ref(item, AnnotationRef, kind)
    if result != tuple(sorted(set(result), key=lambda item: item.sha256)):
        raise ValueError('annotation references require canonical unique order')
    return result


def canonical_cover(rectangles: tuple[RationalRect, ...]) -> tuple[RationalRect, ...]:
    """Unique disjoint x-slab union in exact physical nm."""
    xs = sorted({x for rect in rectangles for x in (rect.x0, rect.x1)})
    opened: dict[tuple[Fraction, Fraction], RationalRect] = {}
    result: list[RationalRect] = []
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((rect.y0, rect.y1) for rect in rectangles if rect.x0 <= left and right <= rect.x1)
        merged: list[tuple[Fraction, Fraction]] = []
        for low, high in intervals:
            if merged and low <= merged[-1][1]:
                merged[-1] = merged[-1][0], max(merged[-1][1], high)
            else:
                merged.append((low, high))
        updated: dict[tuple[Fraction, Fraction], RationalRect] = {}
        for low, high in merged:
            previous = opened.pop((low, high), None)
            updated[low, high] = RationalRect(left if previous is None else previous.x0, low, right, high)
        result.extend(opened.values())
        opened = updated
    result.extend(opened.values())
    return tuple(sorted(result, key=lambda rect: rect.bounds))


def cover(value: object) -> tuple[RationalRect, ...]:
    result = records(value, RationalRect, 'exact cover')
    for item in result:
        validate_annotation_graph(item, (RationalRect,))
        replace(item)
    if result != canonical_cover(result):
        raise ValueError('annotation rectangles require canonical disjoint cover')
    return result


def intersections(a: tuple[RationalRect, ...], b: tuple[RationalRect, ...]) -> tuple[RationalRect, ...]:
    return canonical_cover(tuple(piece for left in a for right in b if (piece := left.intersection(right)) is not None))


def difference(a: tuple[RationalRect, ...], b: tuple[RationalRect, ...]) -> tuple[RationalRect, ...]:
    result: list[RationalRect] = []
    for target in a:
        cuts = tuple(piece for rect in b if (piece := target.intersection(rect)) is not None)
        xs = sorted({target.x0, target.x1} | {x for cut in cuts for x in (cut.x0, cut.x1)})
        for left, right in zip(xs, xs[1:]):
            cursor = target.y0
            for low, high in sorted((cut.y0, cut.y1) for cut in cuts if cut.x0 <= left and right <= cut.x1):
                if cursor < low:
                    result.append(RationalRect(left, cursor, right, low))
                cursor = max(cursor, high)
            if cursor < target.y1:
                result.append(RationalRect(left, cursor, right, target.y1))
    return canonical_cover(tuple(result))


def area(rectangles: tuple[RationalRect, ...]) -> Fraction:
    return sum((rect.area for rect in rectangles), Fraction())


class AnnotationProblem(ValueError):
    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def problem(source: SourceRef, field: str, message: str,
            code: str = 'UnsupportedNetAnnotationOperator') -> AnnotationProblem:
    return AnnotationProblem(EvidenceIssue('unsupported', code, message, replace(source, field=field)))


@dataclass(frozen=True)
class AnnotationRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in ('binding', 'evidence', 'target', 'match', 'fragment', 'coverage', 'component', 'classification', 'issue', 'draft'):
            raise ValueError('unknown annotation reference kind')
        sha(self.sha256)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


class _Record:
    def to_value(self) -> FrozenMap:
        validate_annotation_graph(self, NET_TYPES)
        return cast(FrozenMap, _value(self))


def _seed_operands(row: FrozenMap, identity: FrozenMap) -> None:
    locations, xref = _field_locations(row), _field_locations(identity)
    layout, schematic, index = xref['lvs_name'], xref['schematic_name'], xref['lvs_index']
    if (len(layout) != 2 or len(schematic) != 1 or len(index) != 1
            or layout[0]['lexeme'] != identity['lvs_name'] or layout[1]['lexeme'] != identity['lvs_name']
            or schematic[0]['lexeme'] != identity['schematic_name'] or index[0] != layout[1]
            or layout[0].get('token_0based') != 1 or schematic[0].get('token_0based') != 3
            or tuple(layout[0].get(k) for k in ('path', 'sha256', 'line_1based'))
            != tuple(schematic[0].get(k) for k in ('path', 'sha256', 'line_1based'))):
        raise ValueError('net xref operands disagree')
    line = index[0].get('line_1based')
    if type(line) is not int or line < 4 or identity['lvs_index'] != str(line - 3):
        raise ValueError('net index is not its captured NET NAMES ordinal')
    for name in ('lvs_name', 'lvs_index', 'schematic_name'):
        operands = locations[name]
        if len(operands) != len(xref[name]) + 1 or operands[1:] != xref[name] or operands[0]['lexeme'] != row['lvs_name']:
            raise ValueError('net seed omits or changes identity source operands')
    if not (locations['lvs_name'][0] == locations['lvs_index'][0] == locations['schematic_name'][0]):
        raise ValueError('net seed identity operands require one query request')
    for name in ('record_id', 'section_header_opaque'):
        if len(locations[name]) != 1 or locations[name][0]['lexeme'] != row[name]:
            raise ValueError('net seed literal differs from source operand')
    metadata = row['metadata_opaque']
    if type(metadata) is not tuple or any(type(item) is not str for item in metadata) or tuple(loc['lexeme'] for loc in locations['metadata_opaque']) != metadata:
        raise ValueError('net seed metadata differs from source operands')
    vertices, layers = locations['vertices_nm'], locations['derived_layer']
    if len(vertices) != 10 or len(layers) != 2 or layers[0]['lexeme'] != row['derived_layer']:
        raise ValueError('net seed geometry source operands incomplete')
    precision, geometry = vertices[0], vertices[-1]
    coords = vertices[1:-1]
    if (precision['lexeme'] != str(row['precision']) or locations['bbox_nm'] != vertices
            or locations['precision'] != (precision, geometry) or locations['unit'] != (precision, geometry)
            or locations['geometry_kind'] != (*coords, layers[1]) or locations['quality'] != (*coords, layers[1])):
        raise ValueError('net seed geometry fields omit source operands')
    registry = mapping(layers[1]['lexeme'])
    if registry.get('id') != row['derived_layer'] or registry.get('quality') != row['quality']:
        raise ValueError('net seed registry source differs from record')
    actual = tuple(mapping(point) for point in sequence(row['vertices_nm']))
    for i in range(4):
        y, x = coords[i * 2:i * 2 + 2]
        xy: list[Fraction] = []
        for coordinate, token in ((x, 1), (y, 0)):
            lexeme = coordinate['lexeme']
            if (type(lexeme) is not str or re.fullmatch(r'(?:0|-?[1-9][0-9]*)', lexeme) is None
                    or coordinate.get('token_0based') != token
                    or tuple(coordinate.get(k) for k in ('path', 'sha256')) != tuple(layers[0].get(k) for k in ('path', 'sha256'))):
                raise ValueError('net seed coordinate operand is not exact raw (y,x)')
            xy.append(Fraction(lexeme) * 1000 / cast(int, row['precision']))
        if x.get('line_1based') != y.get('line_1based') or tuple(xy) != tuple(rational(actual[i][axis]) for axis in ('x', 'y')):
            raise ValueError('net seed vertices differ from raw coordinate operands')


@dataclass(frozen=True)
class NetEvidence(_Record):
    net_id: NetId
    query_key: QueryKey
    record: FrozenMap
    identity_provenance: FrozenMap
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.net_id) is not NetId or type(self.query_key) is not QueryKey:
            raise ValueError('net evidence requires typed identities')
        if type(self.record) is not FrozenMap or type(self.identity_provenance) is not FrozenMap:
            raise ValueError('net evidence requires immutable complete provenance')
        common(self)
        row = self.record
        required = {'record_id', 'derived_layer', 'geometry_kind', 'quality', 'vertices_nm', 'bbox_nm', 'unit', 'precision', 'metadata_opaque', 'section_header_opaque', 'field_sources', 'lvs_name', 'lvs_index', 'schematic_name'}
        if set(row) != required or self.query_key.kind != 'net':
            raise ValueError('invalid net seed fields')
        if (row['lvs_name'] != self.query_key.identity or row['lvs_index'] != self.query_key.index
                or row['schematic_name'] != self.net_id.name or row['geometry_kind'] != 'rectangle'
                or row['quality'] != 'exact' or row['unit'] != 'nm'
                or type(row['precision']) is not int or row['precision'] <= 0):
            raise ValueError('unsupported or inconsistent net seed identity/geometry')
        for name in ('record_id', 'derived_layer', 'section_header_opaque'):
            text(row[name])
        identity = self.identity_provenance
        if (set(identity) != {'lvs_name', 'lvs_index', 'schematic_name', 'field_sources'}
                or any(identity[name] != row[name] for name in ('lvs_name', 'lvs_index', 'schematic_name'))
                or set(mapping(identity['field_sources'])) != {'lvs_name', 'lvs_index', 'schematic_name'}
                or set(mapping(row['field_sources'])) != required - {'field_sources'}):
            raise ValueError('net evidence requires complete matching xref')
        box = mapping(row['bbox_nm'])
        if set(box) != {'x_min', 'y_min', 'x_max', 'y_max'}:
            raise ValueError('invalid net seed bbox')
        rect = self.rectangle
        vertices = tuple(mapping(point) for point in sequence(row['vertices_nm']))
        if len(vertices) != 4 or any(set(point) != {'x', 'y'} for point in vertices):
            raise ValueError('invalid net seed polygon')
        points = tuple((rational(point['x']), rational(point['y'])) for point in vertices)
        if (set(points) != {(rect.x0, rect.y0), (rect.x0, rect.y1), (rect.x1, rect.y0), (rect.x1, rect.y1)}
                or any((a[0] == b[0]) == (a[1] == b[1]) for a, b in zip(points, (*points[1:], points[0])))):
            raise ValueError('net polygon differs from rectangle')
        _seed_operands(row, identity)

    @property
    def rectangle(self) -> RationalRect:
        box = mapping(self.record['bbox_nm'])
        return RationalRect(*(rational(box[key]) for key in ('x_min', 'y_min', 'x_max', 'y_max')))

    @property
    def source(self) -> SourceRef:
        return ref_from_location(mapping(sequence(mapping(mapping(self.record['field_sources'])['record_id'])['sources'])[0]))

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('evidence', digest(self.to_value()))


@dataclass(frozen=True)
class AnnotationBinding(_Record):
    local_ref: LocalRef
    effective_ref: RegionRef
    geometry_ref: GeometryRef
    unit_ref: GeometryRef
    partition_ref: GeometryRef
    tick_nm: int
    top: str
    source_cell: CellId
    source_digest: str
    source_ref: SourceRef
    derived: EvidenceRecord
    drawn: EvidenceRecord
    topology: tuple[ContactComponent, ...]
    drawn_record_ids: tuple[GeometryRecordId, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    capture_binding: FrozenMap
    scope: str = SCOPE
    validity: str = 'source_evidence'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'topology', records(self.topology, ContactComponent, 'topology'))
        object.__setattr__(self, 'drawn_record_ids', records(self.drawn_record_ids, GeometryRecordId, 'drawn identities'))
        object.__setattr__(self, 'evidence_refs', records(self.evidence_refs, AnnotationRef, 'evidence references'))
        validate_annotation_graph(self, NET_TYPES)
        ref(self.local_ref, LocalRef, 'draft')
        ref(self.effective_ref, RegionRef, 'draft')
        ref(self.geometry_ref, GeometryRef, 'layout')
        ref(self.unit_ref, GeometryRef, 'unit')
        ref(self.partition_ref, GeometryRef, 'base_partition')
        if type(self.tick_nm) is not int or self.tick_nm <= 0:
            raise ValueError('annotation binding requires positive exact DBU')
        text(self.top)
        if type(self.source_cell) is not CellId:
            raise ValueError('annotation binding requires a typed source cell')
        sha(self.source_digest)
        if type(self.source_ref) is not SourceRef or self.source_ref.sha256 is None:
            raise ValueError('annotation binding requires captured source CDL provenance')
        source_value(self.source_ref)
        for owner, kind in ((self.derived, 'derived'), (self.drawn, 'drawn')):
            if type(owner) is not EvidenceRecord or owner.kind != kind or len(owner.sources) != 1:
                raise ValueError('annotation binding requires one captured ' + kind + ' owner')
        object.__setattr__(self, 'topology', records(self.topology, ContactComponent, 'topology'))
        object.__setattr__(self, 'drawn_record_ids', records(self.drawn_record_ids, GeometryRecordId, 'drawn identities'))
        object.__setattr__(self, 'evidence_refs', ordered_refs(self.evidence_refs, 'evidence'))
        if self.topology != tuple(sorted(self.topology, key=lambda item: item.ref.sha256)) or len({item.ref for item in self.topology}) != len(self.topology):
            raise ValueError('annotation topology requires complete canonical components')
        if len({component.binding_ref for component in self.topology}) > 1:
            raise ValueError('annotation topology mixes contact operator owners')
        members = tuple(member for component in self.topology for member in component.members)
        if len(set(members)) != len(members):
            raise ValueError('annotation topology repeats a node')
        if self.drawn_record_ids != tuple(sorted(set(self.drawn_record_ids), key=lambda item: item.sha256)):
            raise ValueError('annotation drawn identities require canonical unique order')
        if type(self.capture_binding) is not FrozenMap or set(self.capture_binding) != {'schema', 'normalization_input_sha256', 'sources', 'readback'}:
            raise ValueError('incomplete annotation capture binding')
        capture = self.capture_binding
        if capture['schema'] != 'layauto-net-capture-binding/1':
            raise ValueError('unsupported annotation capture binding')
        sha(capture['normalization_input_sha256'])
        sources = tuple(mapping(item) for item in sequence(capture['sources']))
        if not sources or any(set(item) != {'uri', 'sha256'} for item in sources):
            raise ValueError('annotation capture requires complete source identities')
        for item in sources:
            text(item['uri'])
            sha(item['sha256'])
        if len({item['uri'] for item in sources}) != len(sources):
            raise ValueError('annotation capture repeats source URI')
        readback = capture['readback']
        if readback is not None:
            row = mapping(readback)
            if set(row) != {'run_id', 'request_digest', 'attempt_digest', 'checkpoint_ref', 'parse_ref', 'tool_ref'}:
                raise ValueError('incomplete annotation readback binding')
            text(row['run_id'])
            sha(row['request_digest'])
            sha(row['attempt_digest'])
            for name in ('checkpoint_ref', 'parse_ref', 'tool_ref'):
                pointer = mapping(row[name])
                if set(pointer) != {'kind', 'run_id', 'digest'} or pointer['run_id'] != row['run_id']:
                    raise ValueError('annotation readback pointer belongs to another run')
                expected_kind = {'checkpoint_ref': 'checkpoint', 'parse_ref': 'parse', 'tool_ref': 'tool_run'}[name]
                if pointer['kind'] != expected_kind:
                    raise ValueError('annotation readback pointer has the wrong source role')
                sha(pointer['digest'])
        if type(self.scope) is not str or self.scope != SCOPE or type(self.validity) is not str or self.validity != 'source_evidence':
            raise ValueError('annotation binding requires current source-evidence local scope')
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('binding', digest(self.to_value()))


@dataclass(frozen=True)
class AnnotationTargetId(_Record):
    binding_ref: AnnotationRef
    layer: str
    record_id: GeometryRecordId
    region_ref: RegionRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        validate_annotation_graph(self, NET_TYPES)
        ref(self.binding_ref, AnnotationRef, 'binding')
        text(self.layer)
        if type(self.record_id) is not GeometryRecordId:
            raise ValueError('annotation target requires original record identity')
        ref(self.region_ref, RegionRef, 'region')
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('target', digest(self.to_value()))


@dataclass(frozen=True)
class TargetEvidence(_Record):
    target_id: AnnotationTargetId
    node: ContactNode
    component_ref: LocalRef
    drawn_rectangle: RationalRect
    source: SourceRef
    tick_nm: int
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        validate_annotation_graph(self, NET_TYPES)
        if type(self.target_id) is not AnnotationTargetId or type(self.node) is not ContactNode or type(self.drawn_rectangle) is not RationalRect or type(self.source) is not SourceRef:
            raise ValueError('annotation target requires exact node and source evidence')
        ref(self.component_ref, LocalRef, 'component')
        if type(self.tick_nm) is not int or self.tick_nm <= 0:
            raise ValueError('annotation target requires exact DBU')
        if (self.target_id.layer != self.node.layer or self.target_id.record_id != self.node.region.owner_id
                or self.target_id.region_ref != self.node.region.ref):
            raise ValueError('annotation target differs from original region identity')
        if difference(self.rectangles, (self.drawn_rectangle,)):
            raise ValueError('annotation target extends beyond its drawn owner')
        source_value(self.source)
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return self.target_id.ref

    @property
    def node_ref(self) -> LocalRef:
        return self.node.ref

    @property
    def rectangles(self) -> tuple[RationalRect, ...]:
        return tuple(RationalRect(*(Fraction(value * self.tick_nm) for value in rect.bounds)) for rect in self.node.region.rectangles)


@dataclass(frozen=True)
class TargetIntersection(_Record):
    target_ref: AnnotationRef
    rectangles: tuple[RationalRect, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'rectangles', records(self.rectangles, RationalRect, 'exact cover'))
        validate_annotation_graph(self, NET_TYPES)
        ref(self.target_ref, AnnotationRef, 'target')
        object.__setattr__(self, 'rectangles', cover(self.rectangles))
        if not self.rectangles:
            raise ValueError('target intersection requires positive area')
        common(self)


@dataclass(frozen=True)
class MatchEvidence(_Record):
    evidence_ref: AnnotationRef
    intersections: tuple[TargetIntersection, ...]
    boundary_targets: tuple[AnnotationRef, ...]
    trimmed: tuple[RationalRect, ...]
    unmatched: tuple[RationalRect, ...]
    policy: FrozenMap
    status: str
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'intersections', records(self.intersections, TargetIntersection, 'intersections'))
        object.__setattr__(self, 'boundary_targets', records(self.boundary_targets, AnnotationRef, 'boundary targets'))
        object.__setattr__(self, 'trimmed', records(self.trimmed, RationalRect, 'trimmed cover'))
        object.__setattr__(self, 'unmatched', records(self.unmatched, RationalRect, 'unmatched cover'))
        validate_annotation_graph(self, NET_TYPES)
        ref(self.evidence_ref, AnnotationRef, 'evidence')
        object.__setattr__(self, 'intersections', records(self.intersections, TargetIntersection, 'intersections'))
        if self.intersections != tuple(sorted(self.intersections, key=lambda item: item.target_ref.sha256)) or len({item.target_ref for item in self.intersections}) != len(self.intersections):
            raise ValueError('match target intersections require canonical unique order')
        object.__setattr__(self, 'boundary_targets', ordered_refs(self.boundary_targets, 'target'))
        object.__setattr__(self, 'trimmed', cover(self.trimmed))
        object.__setattr__(self, 'unmatched', cover(self.unmatched))
        if type(self.policy) is not FrozenMap or type(self.status) is not str or self.status not in ('matched', 'partial', 'unmatched', 'unsupported', 'ambiguous'):
            raise ValueError('invalid annotation match policy/status')
        common(self)

    @property
    def multiple_candidates(self) -> bool:
        return len(self.intersections) > 1

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('match', digest(self.to_value()))


@dataclass(frozen=True)
class AnnotationFragment(_Record):
    target_ref: AnnotationRef
    rectangles: tuple[RationalRect, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    net_ids: tuple[NetId, ...]
    status: str
    validity: str = 'source_evidence'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'rectangles', records(self.rectangles, RationalRect, 'exact cover'))
        object.__setattr__(self, 'evidence_refs', records(self.evidence_refs, AnnotationRef, 'evidence refs'))
        object.__setattr__(self, 'net_ids', records(self.net_ids, NetId, 'fragment nets'))
        validate_annotation_graph(self, NET_TYPES)
        ref(self.target_ref, AnnotationRef, 'target')
        object.__setattr__(self, 'rectangles', cover(self.rectangles))
        if not self.rectangles:
            raise ValueError('annotation fragment requires positive area')
        object.__setattr__(self, 'evidence_refs', ordered_refs(self.evidence_refs, 'evidence'))
        object.__setattr__(self, 'net_ids', records(self.net_ids, NetId, 'fragment net identities'))
        if self.net_ids != tuple(sorted(set(self.net_ids), key=lambda item: item.id)):
            raise ValueError('fragment nets require canonical unique order')
        expected = 'unknown' if not self.net_ids else 'annotated' if len(self.net_ids) == 1 else 'conflict'
        if type(self.status) is not str or self.status != expected or bool(self.evidence_refs) != bool(self.net_ids):
            raise ValueError('fragment identity/status differs from complete evidence')
        if type(self.validity) is not str or self.validity != 'source_evidence':
            raise ValueError('unsupported annotation fragment validity')
        common(self)

    @property
    def area_nm2(self) -> Fraction:
        return area(self.rectangles)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('fragment', digest(self.to_value()))


@dataclass(frozen=True)
class RecordClassification(_Record):
    record_id: GeometryRecordId
    layer: str
    role: str
    classification: str
    rectangle: RationalRect
    source: SourceRef
    cell_coordinates: tuple[tuple[int, int], ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.record_id) is not GeometryRecordId or type(self.rectangle) is not RationalRect or type(self.source) is not SourceRef:
            raise ValueError('classification requires original exact drawn evidence')
        for value in (self.layer, self.role, self.classification):
            text(value)
        if self.classification not in ('target_conductor', 'connector', 'cut', 'backdrop', 'boundary', 'marker', 'auxiliary'):
            raise ValueError('unsupported non-target classification')
        if type(self.cell_coordinates) not in (tuple, list):
            raise ValueError('classification requires native cell coordinate sequence')
        copied = tuple(self.cell_coordinates)
        if any(type(item) is not tuple or len(item) != 2 or any(type(v) is not int or v < 0 for v in item) for item in copied) or copied != tuple(sorted(set(copied))):
            raise ValueError('classification cells require unique native integer pairs')
        object.__setattr__(self, 'cell_coordinates', copied)
        source_value(self.source)
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('classification', digest(self.to_value()))


@dataclass(frozen=True)
class LayerCoverage(_Record):
    layer: str
    drawn_shape_count: int
    cell_count: int
    target_count: int
    total_area: Fraction
    covered_area: Fraction
    uncovered_area: Fraction
    conflict_area: Fraction
    component_conflict_area: Fraction
    source_refs: tuple[SourceRef, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    unit: str = 'nm2'
    denominator: str = 'local_target_multiset_area'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'source_refs', records(self.source_refs, SourceRef, 'coverage sources'))
        object.__setattr__(self, 'evidence_refs', records(self.evidence_refs, AnnotationRef, 'coverage evidence'))
        validate_annotation_graph(self, NET_TYPES)
        text(self.layer)
        for value in (self.drawn_shape_count, self.cell_count, self.target_count):
            if type(value) is not int or value < 0:
                raise ValueError('coverage counts require nonnegative native integers')
        for measure in (self.total_area, self.covered_area, self.uncovered_area, self.conflict_area, self.component_conflict_area):
            fraction(measure)
        if self.covered_area + self.uncovered_area != self.total_area or self.conflict_area > self.covered_area or self.component_conflict_area > self.covered_area:
            raise ValueError('coverage measures are inconsistent')
        object.__setattr__(self, 'source_refs', records(self.source_refs, SourceRef, 'coverage sources'))
        object.__setattr__(self, 'evidence_refs', ordered_refs(self.evidence_refs, 'evidence'))
        if type(self.unit) is not str or self.unit != 'nm2' or type(self.denominator) is not str or self.denominator != 'local_target_multiset_area':
            raise ValueError('unsupported coverage unit/denominator')
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('coverage', digest(self.to_value()))


@dataclass(frozen=True)
class NetComponentSummary(_Record):
    component_ref: LocalRef
    members: tuple[LocalRef, ...]
    target_refs: tuple[AnnotationRef, ...]
    observed_net_ids: tuple[NetId, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    directly_covered_targets: tuple[AnnotationRef, ...]
    status: str
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'members', records(self.members, LocalRef, 'component members'))
        object.__setattr__(self, 'target_refs', records(self.target_refs, AnnotationRef, 'component targets'))
        object.__setattr__(self, 'observed_net_ids', records(self.observed_net_ids, NetId, 'component nets'))
        object.__setattr__(self, 'evidence_refs', records(self.evidence_refs, AnnotationRef, 'component evidence'))
        object.__setattr__(self, 'directly_covered_targets', records(self.directly_covered_targets, AnnotationRef, 'direct coverage'))
        validate_annotation_graph(self, NET_TYPES)
        ref(self.component_ref, LocalRef, 'component')
        object.__setattr__(self, 'members', records(self.members, LocalRef, 'component members'))
        if not self.members or self.members != tuple(sorted(set(self.members), key=lambda item: item.sha256)):
            raise ValueError('component summary requires canonical original members')
        for member in self.members:
            ref(member, LocalRef, 'node')
        object.__setattr__(self, 'target_refs', ordered_refs(self.target_refs, 'target'))
        object.__setattr__(self, 'directly_covered_targets', ordered_refs(self.directly_covered_targets, 'target'))
        object.__setattr__(self, 'evidence_refs', ordered_refs(self.evidence_refs, 'evidence'))
        object.__setattr__(self, 'observed_net_ids', records(self.observed_net_ids, NetId, 'component nets'))
        if self.observed_net_ids != tuple(sorted(set(self.observed_net_ids), key=lambda item: item.id)):
            raise ValueError('component nets require canonical unique order')
        expected = 'unknown' if not self.observed_net_ids else 'associated' if len(self.observed_net_ids) == 1 else 'conflict'
        if (type(self.status) is not str or self.status != expected
                or not set(self.directly_covered_targets) <= set(self.target_refs)
                or bool(self.observed_net_ids) != bool(self.evidence_refs)):
            raise ValueError('component summary differs from evidence/status')
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('component', digest(self.to_value()))


@dataclass(frozen=True)
class AnnotationIssue(_Record):
    issue: EvidenceIssue
    target_refs: tuple[AnnotationRef, ...]
    component_refs: tuple[LocalRef, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    net_ids: tuple[NetId, ...]
    severity: str = 'error'
    recommended_action: str = 'review_source_evidence'
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, 'target_refs', records(self.target_refs, AnnotationRef, 'issue targets'))
        object.__setattr__(self, 'component_refs', records(self.component_refs, LocalRef, 'issue components'))
        object.__setattr__(self, 'evidence_refs', records(self.evidence_refs, AnnotationRef, 'issue evidence'))
        object.__setattr__(self, 'net_ids', records(self.net_ids, NetId, 'issue nets'))
        validate_annotation_graph(self, NET_TYPES)
        if type(self.issue) is not EvidenceIssue:
            raise ValueError('annotation issue requires a located typed issue')
        object.__setattr__(self, 'target_refs', ordered_refs(self.target_refs, 'target'))
        object.__setattr__(self, 'evidence_refs', ordered_refs(self.evidence_refs, 'evidence'))
        object.__setattr__(self, 'component_refs', records(self.component_refs, LocalRef, 'issue component refs'))
        if self.component_refs != tuple(sorted(set(self.component_refs), key=lambda item: item.sha256)):
            raise ValueError('issue component refs require canonical unique order')
        for item in self.component_refs:
            ref(item, LocalRef, 'component')
        object.__setattr__(self, 'net_ids', records(self.net_ids, NetId, 'issue nets'))
        if self.net_ids != tuple(sorted(set(self.net_ids), key=lambda item: item.id)):
            raise ValueError('issue nets require canonical unique order')
        if type(self.severity) is not str or self.severity not in ('warning', 'error'):
            raise ValueError('invalid annotation issue severity')
        text(self.recommended_action)
        common(self)

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('issue', digest(self.to_value()))


_NEW_TYPES = (AnnotationRef, NetEvidence, AnnotationBinding, AnnotationTargetId, TargetEvidence,
              TargetIntersection, MatchEvidence, AnnotationFragment, RecordClassification,
              LayerCoverage, NetComponentSummary, AnnotationIssue)
NET_TYPES = _NEW_TYPES + (RationalRect, NetId, CellId, QueryKey, LocalRef, GeometryRecordId, GeometryRef,
                          RegionRef, ContactComponent, ContactNode, ExactRegion, Rect,
                          SourceRef, EvidenceRecord, EvidenceIssue)


def policy_for(binding: AnnotationBinding, evidence: NetEvidence) -> FrozenMap:
    """Closed owner interpretation retained by a match, without spatial stamping."""
    validate_annotation_graph((binding, evidence), NET_TYPES)
    registry = tuple(mapping(row) for row in sequence(binding.derived.payload['derived_registry']))
    matches = tuple((index, row) for index, row in enumerate(registry) if row.get('id') == evidence.record['derived_layer'])
    rows = tuple(mapping(row) for row in sequence(binding.drawn.payload['layers']))
    if len(matches) != 1:
        return FrozenMap({'declaration': None, 'registry_index': None, 'target_layer': None,
                          'trim_operator': None, 'supported': False, 'reason': 'ambiguous_registry'})
    index, declaration = matches[0]
    operand = mapping(sequence(mapping(mapping(evidence.record['field_sources'])['derived_layer'])['sources'])[1])
    location = ref_from_location(operand)
    owner = binding.derived.sources[0]
    if (canonical_bytes(operand['lexeme']) != canonical_bytes(declaration)
            or (location.uri, location.sha256, location.field) != (owner.uri, owner.sha256, f'/derived_registry/{index}')):
        raise ValueError('net seed derived operand contradicts actual owner/source role')
    layer = declaration.get('target_layer')
    drawn = tuple(row for row in rows if row.get('name') == layer)
    references = tuple(row for row in rows if evidence.record['derived_layer'] in sequence(row.get('derived_layer_refs', ())))
    reason = ''
    if len(drawn) != 1 or len(references) != 1 or references != drawn:
        reason = 'ambiguous_layer_mapping'
    elif ('net_id' not in sequence(declaration.get('carries', ()))
            or declaration.get('accepted_geometry_kinds') != ('rectangle',)
            or declaration.get('quality') != 'exact' or declaration.get('annotation_match_tolerance_nm') != 0
            or type(declaration.get('annotation_match_tolerance_nm')) is not int
            or declaration.get('conflict_policy') != 'reject_ambiguous'):
        reason = 'unsupported_quality_or_tolerance'
    elif ((layer == 'LI' and declaration.get('trim_operator') != 'cut_effective_intersection')
            or (layer in ('POLY', 'M1') and declaration.get('trim_operator') != 'identity')
            or layer not in ('LI', 'POLY', 'M1')):
        reason = 'unsupported_target_or_trim'
    return FrozenMap({'declaration': declaration, 'registry_index': index, 'target_layer': layer,
                      'trim_operator': declaration.get('trim_operator'), 'supported': not reason, 'reason': reason})
