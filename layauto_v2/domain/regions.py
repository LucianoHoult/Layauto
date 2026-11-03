"""Neutral exact-region contracts for the explicitly selected toy operators.

These values establish internal consistency, not capture authenticity. Regions
are read-only derivations of drawn records, never additional drawn geometry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from typing import Literal, TypeVar, cast

from .codec import FrozenMap, digest
from .evidence import EvidenceRecord, SourceRef
from .geometry import GeometryRecordId, GeometryRef, Rect, evidence_value, mapping, sequence, source_value
from .results import EvidenceIssue

VERSION = 'layauto-effective-regions/1'
RefKind = Literal['operators', 'draft', 'region', 'piece']
RegionRole = Literal['effective', 'channel', 'S', 'D']


def validate_closed_graph(value: object, records: tuple[type[object], ...] = ()) -> None:
    """Check retained objects before any codec can copy or fold their values.

    Exact identity checks do not invoke caller-defined metaclass equality. Only
    explicitly supplied DTO classes may appear outside the neutral Value algebra.
    Payload maps/tuples contain Values only, never arbitrary dataclass records.
    """
    def check(item: object, value_only: bool) -> None:
        cls = type(item)
        if item is None or cls is bool or cls is int or cls is str or cls is bytes:
            return
        if cls is Fraction:
            fraction = cast(Fraction, item)
            if type(fraction.numerator) is not int or type(fraction.denominator) is not int:
                raise ValueError('exact fractions require native integer components')
            return
        if cls is FrozenMap:
            for key, child in cast(FrozenMap, item).items():
                if type(key) is not str:
                    raise ValueError('closed payload keys require exact text')
                check(child, True)
            return
        if cls is tuple:
            for element in cast(tuple[object, ...], item):
                check(element, value_only)
            return
        if value_only or not any(cls is allowed for allowed in records) or not is_dataclass(item):
            raise ValueError('foreign or mutable value in effective geometry graph')
        for field in fields(item):
            check(getattr(item, field.name), False)
    check(value, False)

# A deliberately small executable subset. Presence of other required refs does
# not claim those operators have been executed by this component.
CONSUMED_PHYSICAL = FrozenMap({
    '/fin_count_profile/id': 'toy_fin_crossing/1',
    '/fin_count_profile/fin_representation': 'explicit_static_fin_plus_active_window',
    '/fin_count_profile/effective_active_operator': 'identity_OD',
    '/fin_count_profile/recognized_channel_operator':
        'positive_area_OD_intersect_POLY_with_exactly_one_gate_stripe_per_active',
    '/device_extraction_contract/id': 'toy_device_terminal_context/2',
    '/device_extraction_contract/sd_policy':
        'left connected component of OD minus channel is S, right is D; ordered terminals, swap unsupported',
    '/device_extraction_contract/gate_operator':
        'POLY conductor continuous through channels; never an OD S-to-D conductor edge',
    '/operators/rectangle_set_difference~11':
        'exact set subtraction, retain all positive-area rectangles, split disconnected results',
    '/operators/terminal_split~11':
        'effective OD minus recognized channel; device S/D relation never union',
})


def _version(value: str) -> None:
    if type(value) is not str or value != VERSION:
        raise ValueError('unsupported effective-region schema')


T = TypeVar('T')


def _tuple(value: object, cls: type[T], name: str) -> tuple[T, ...]:
    if type(value) is not tuple and type(value) is not list:
        raise ValueError('invalid effective-region ' + name)
    copied = tuple(value)
    if any(type(item) is not cls for item in copied):
        raise ValueError('invalid effective-region ' + name)
    return copied


def _ids(value: object) -> tuple[GeometryRecordId, ...]:
    result = _tuple(value, GeometryRecordId, 'contributors')
    if result != tuple(sorted(set(result), key=lambda item: item.sha256)):
        raise ValueError('contributors require unique canonical record identities')
    return result


def _unit(value: GeometryRef) -> None:
    if type(value) is not GeometryRef or type(value.kind) is not str or value.kind != 'unit':
        raise ValueError('effective regions require a typed unit reference')


def canonical_cover(rectangles: tuple[Rect, ...]) -> tuple[Rect, ...]:
    """Unique x-slab union cover, independent of redundant input boundaries."""
    xs = sorted({x for rect in rectangles for x in (rect.x0, rect.x1)})
    opened: dict[tuple[int, int], Rect] = {}
    result: list[Rect] = []
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((rect.y0, rect.y1) for rect in rectangles if rect.x0 <= left and right <= rect.x1)
        merged: list[tuple[int, int]] = []
        for low, high in intervals:
            if merged and low <= merged[-1][1]:
                merged[-1] = merged[-1][0], max(merged[-1][1], high)
            else:
                merged.append((low, high))
        updated: dict[tuple[int, int], Rect] = {}
        for low, high in merged:
            previous = opened.pop((low, high), None)
            updated[low, high] = Rect(left if previous is None else previous.x0, low, right, high)
        result.extend(opened.values())
        opened = updated
    result.extend(opened.values())
    return tuple(sorted(result, key=lambda rect: rect.bounds))


def _connected(rectangles: tuple[Rect, ...]) -> bool:
    pending = [0]
    remaining = set(range(1, len(rectangles)))
    while pending:
        current = rectangles[pending.pop()]
        neighbors = [index for index in remaining
                     if ((current.x1 == rectangles[index].x0 or rectangles[index].x1 == current.x0)
                         and max(current.y0, rectangles[index].y0) < min(current.y1, rectangles[index].y1))
                     or ((current.y1 == rectangles[index].y0 or rectangles[index].y1 == current.y0)
                         and max(current.x0, rectangles[index].x0) < min(current.x1, rectangles[index].x1))]
        for index in neighbors:
            remaining.remove(index)
            pending.append(index)
    return not remaining


@dataclass(frozen=True)
class RegionRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in ('operators', 'draft', 'region', 'piece'):
            raise ValueError('unknown region reference kind')
        if type(self.sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.sha256) is None:
            raise ValueError('region reference requires lowercase SHA-256')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


def _ref(value: RegionRef, kind: RefKind) -> None:
    if type(value) is not RegionRef or value.kind != kind:
        raise ValueError('incorrect typed region reference')


class RegionProblem(ValueError):
    """Only expected operator/profile/geometry failures cross this boundary."""

    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def _problem(source: SourceRef, field: str, message: str) -> RegionProblem:
    return RegionProblem(EvidenceIssue('unsupported', 'UnsupportedRegionOperator', message,
                                      SourceRef(source.uri, source.sha256, field=field)))


@dataclass(frozen=True)
class OperatorBinding:
    physical: EvidenceRecord
    drawn: EvidenceRecord
    unit_ref: GeometryRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _unit(self.unit_ref)
        for value, kind in ((self.physical, 'physical'), (self.drawn, 'drawn')):
            if type(value) is not EvidenceRecord or value.kind != kind or len(value.sources) != 1:
                raise ValueError('region operators require one ' + kind + ' owner')
            source_value(value.sources[0])
            validate_closed_graph(value, (EvidenceRecord, SourceRef))
            if value.payload.get('schema_version') != 'w004-tech-owner/2':
                raise _problem(value.sources[0], '/schema_version', 'unsupported region policy owner version')
        for field, expected in CONSUMED_PHYSICAL.items():
            parent, key = field[1:].split('/', 1)
            key = key.replace('~1', '/').replace('~0', '~')
            section = self.physical.payload.get(parent)
            actual = section.get(key) if type(section) is FrozenMap else None
            if actual != expected:
                raise _problem(self.physical.sources[0], field,
                               'selected region operator/profile semantics are unsupported')
        rows = tuple(mapping(row) for row in sequence(self.drawn.payload.get('layers')))
        for name, role in (('OD', 'diffusion'), ('POLY', 'gate'), ('LI', 'interconnect'), ('CUT', 'cut')):
            matches = [(i, row) for i, row in enumerate(rows) if row.get('name') == name]
            if len(matches) != 1:
                raise _problem(self.drawn.sources[0], '/layers', 'selected toy region layer must resolve uniquely: ' + name)
            index, row = matches[0]
            if row.get('role') != role:
                raise _problem(self.drawn.sources[0], f'/layers/{index}/role', 'unsupported region layer role: ' + name)
            if name == 'CUT':
                for key, expected in (('cut_target', 'LI'), ('effective_geometry_operator', 'rectangle_set_difference/1')):
                    if row.get(key) != expected:
                        raise _problem(self.drawn.sources[0], f'/layers/{index}/{key}', 'unsupported CUT target/operator')
        for index, row in enumerate(rows):
            if row.get('role') == 'cut' and row.get('name') != 'CUT':
                raise _problem(self.drawn.sources[0], f'/layers/{index}/role', 'additional cut policy is outside the selected toy subset')
        # Legacy evidence DTOs predate these strict literal guards. Ensure their
        # complete retained values are closed too, without altering those DTOs.
        self.to_value()

    @property
    def ref(self) -> RegionRef:
        return RegionRef('operators', digest(self.to_value()))

    @property
    def consumed(self) -> FrozenMap:
        return CONSUMED_PHYSICAL

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'physical': evidence_value(self.physical),
                          'drawn': evidence_value(self.drawn), 'unit_ref': self.unit_ref.to_value(),
                          'consumed_physical': self.consumed})


@dataclass(frozen=True)
class RegionPiece:
    region_ref: RegionRef
    rect: Rect
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _ref(self.region_ref, 'region')
        if type(self.rect) is not Rect:
            raise ValueError('region piece requires exact rectangle')

    @property
    def ref(self) -> RegionRef:
        return RegionRef('piece', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'region_ref': self.region_ref.to_value(),
                          'rect': self.rect.bounds})


@dataclass(frozen=True)
class ExactRegion:
    owner_id: GeometryRecordId
    role: RegionRole
    contributors: tuple[GeometryRecordId, ...]
    unit_ref: GeometryRef
    operator_ref: RegionRef
    rectangles: tuple[Rect, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if (type(self.owner_id) is not GeometryRecordId or type(self.role) is not str
                or self.role not in ('effective', 'channel', 'S', 'D')):
            raise ValueError('invalid exact region owner/role')
        _unit(self.unit_ref)
        _ref(self.operator_ref, 'operators')
        object.__setattr__(self, 'contributors', _ids(self.contributors))
        rectangles = _tuple(self.rectangles, Rect, 'rectangles')
        if not rectangles or rectangles != tuple(sorted(rectangles, key=lambda rect: rect.bounds)):
            raise ValueError('region requires nonempty canonically ordered rectangles')
        if any(rect.intersection(other) is not None for index, rect in enumerate(rectangles) for other in rectangles[index + 1:]):
            raise ValueError('region decomposition contains overlapping rectangles')
        if rectangles != canonical_cover(rectangles):
            raise ValueError('region decomposition is not the canonical exact set cover')
        if not _connected(rectangles):
            raise ValueError('one exact region must be internally connected through positive-length edges')
        object.__setattr__(self, 'rectangles', rectangles)

    @property
    def ref(self) -> RegionRef:
        return RegionRef('region', digest(self.to_value()))

    @property
    def pieces(self) -> tuple[RegionPiece, ...]:
        reference = self.ref
        return tuple(RegionPiece(reference, rect) for rect in self.rectangles)

    @property
    def area(self) -> int:
        return sum(rect.area for rect in self.rectangles)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'owner_id': self.owner_id.sha256, 'role': self.role,
                          'contributors': tuple(item.sha256 for item in self.contributors),
                          'unit_ref': self.unit_ref.to_value(), 'operator_ref': self.operator_ref.to_value(),
                          'rectangles': tuple(rect.bounds for rect in self.rectangles)})


@dataclass(frozen=True)
class RecordRegions:
    record_id: GeometryRecordId
    operation: Literal['cut', 'terminal']
    contributors: tuple[GeometryRecordId, ...]
    unit_ref: GeometryRef
    operator_ref: RegionRef
    regions: tuple[ExactRegion, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if (type(self.record_id) is not GeometryRecordId or type(self.operation) is not str
                or self.operation not in ('cut', 'terminal')):
            raise ValueError('invalid record-region owner/operation')
        _unit(self.unit_ref)
        _ref(self.operator_ref, 'operators')
        object.__setattr__(self, 'contributors', _ids(self.contributors))
        regions = _tuple(self.regions, ExactRegion, 'regions')
        if any(region.owner_id != self.record_id or region.contributors != self.contributors
               or region.unit_ref != self.unit_ref or region.operator_ref != self.operator_ref for region in regions):
            raise ValueError('record regions contain foreign provenance/unit/operator')
        if self.operation == 'terminal':
            if tuple(region.role for region in regions) != ('channel', 'S', 'D'):
                raise ValueError('terminal record requires channel and both ordered spatial roles')
        elif any(region.role != 'effective' for region in regions):
            raise ValueError('cut result requires effective regions')
        object.__setattr__(self, 'regions', regions)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'record_id': self.record_id.sha256,
                          'operation': self.operation, 'contributors': tuple(item.sha256 for item in self.contributors),
                          'unit_ref': self.unit_ref.to_value(), 'operator_ref': self.operator_ref.to_value(),
                          'regions': tuple(region.to_value() for region in self.regions)})
