"""Neutral, exact values for a read-only local contact graph.

These contracts establish representation consistency. Capture authentication
belongs to normalization; no net or device label is a topology input.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal, TypeVar

from .codec import FrozenMap, digest
from .evidence import EvidenceRecord, SourceRef
from .geometry import GeometryRecordId, GeometryRef, Rect, evidence_value, source_value
from .regions import ExactRegion, RegionRef, validate_closed_graph
from .results import EvidenceIssue

VERSION = 'layauto-local-connectivity/1'
SCOPE = 'local_flat_cell/1'
RefKind = Literal['operators', 'node', 'edge', 'component', 'audit', 'draft']
CONDUCTOR_LAYERS = ('OD', 'LI', 'POLY', 'M1', 'BODY_N', 'BODY_P')
CONNECTOR_PAIRS = FrozenMap({'CONTACT': ('OD', 'LI'), 'VIA0': ('LI', 'M1'),
                             'GCONTACT': ('POLY', 'M1')})
CONSUMED_PHYSICAL = FrozenMap({
    'same_layer_contact/1': 'positive-area overlap OR positive-length shared edge; corner/point touch never edge',
    'cross_layer_contact/1': 'connector positive-area overlap with exactly one region in each declared conductor layer; no via-as-wire duplication; enclosure independently mandatory',
})


def _version(value: object) -> None:
    if type(value) is not str or value != VERSION:
        raise ValueError('unsupported local connectivity schema')


def _text(value: object) -> None:
    if type(value) is not str or not value:
        raise ValueError('local connectivity requires exact nonempty text')
    value.encode('utf-8')


T = TypeVar('T')


def record_tuple(value: object, cls: type[T], name: str) -> tuple[T, ...]:
    """Copy a caller collection exactly once, then check the stored snapshot."""
    if type(value) is not tuple and type(value) is not list:
        raise ValueError('invalid local connectivity ' + name)
    copied = tuple(value)
    if any(type(item) is not cls for item in copied):
        raise ValueError('invalid local connectivity ' + name)
    return copied


@dataclass(frozen=True)
class LocalRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in ('operators', 'node', 'edge', 'component', 'audit', 'draft'):
            raise ValueError('unknown local connectivity reference kind')
        if type(self.sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.sha256) is None:
            raise ValueError('local connectivity reference requires lowercase SHA-256')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


def local_ref(value: object, kind: RefKind) -> None:
    if type(value) is not LocalRef:
        raise ValueError('incorrect typed local connectivity reference')
    validate_closed_graph(value, (LocalRef,))
    if value.kind != kind:
        raise ValueError('incorrect typed local connectivity reference')


class ContactProblem(ValueError):
    """Expected located contact/profile failures, distinct from algorithm bugs."""

    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def contact_problem(source: SourceRef, field: str, message: str,
                    code: str = 'UnsupportedLocalContactOperator') -> ContactProblem:
    return ContactProblem(EvidenceIssue('unsupported', code, message, replace(source, field=field)))


@dataclass(frozen=True)
class LocalContactBinding:
    physical: EvidenceRecord
    drawn: EvidenceRecord
    rules: EvidenceRecord
    effective_ref: RegionRef
    unit_ref: GeometryRef
    top: str
    scope: str = SCOPE
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for owner, kind in ((self.physical, 'physical'), (self.drawn, 'drawn'), (self.rules, 'rules')):
            if type(owner) is not EvidenceRecord:
                raise ValueError('local contact binding requires one ' + kind + ' source')
            validate_closed_graph(owner, (EvidenceRecord, SourceRef))
            if owner.kind != kind or len(owner.sources) != 1:
                raise ValueError('local contact binding requires one ' + kind + ' source')
            source_value(owner.sources[0])
        if type(self.effective_ref) is not RegionRef or self.effective_ref.kind != 'draft':
            raise ValueError('local contact binding requires an effective draft reference')
        if type(self.unit_ref) is not GeometryRef or self.unit_ref.kind != 'unit':
            raise ValueError('local contact binding requires a canonical unit reference')
        _text(self.top)
        if type(self.scope) is not str or self.scope != SCOPE:
            raise ValueError('unsupported local graph scope')
        validate_closed_graph(self, LOCAL_TYPES)

    @property
    def ref(self) -> LocalRef:
        return LocalRef('operators', digest(self.to_value()))

    @property
    def consumed(self) -> FrozenMap:
        return FrozenMap({'physical_operators': CONSUMED_PHYSICAL,
                          'local_connector_pairs': CONNECTOR_PAIRS,
                          'local_rule': 'w004-toy-predicate/T05.contact_enclosure/2'})

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'physical': evidence_value(self.physical),
                          'drawn': evidence_value(self.drawn), 'rules': evidence_value(self.rules),
                          'effective_ref': self.effective_ref.to_value(), 'unit_ref': self.unit_ref.to_value(),
                          'top': self.top, 'scope': self.scope, 'consumed': self.consumed})


@dataclass(frozen=True)
class ContactNode:
    layer: str
    region: ExactRegion
    binding_ref: LocalRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if type(self.layer) is not str or self.layer not in CONDUCTOR_LAYERS:
            raise ValueError('unsupported local conductor layer')
        if type(self.region) is not ExactRegion:
            raise ValueError('contact node requires one exact independent region')
        validate_closed_graph(self.region, LOCAL_TYPES)
        if self.region.role == 'channel':
            raise ValueError('channel is not a conductor node')
        local_ref(self.binding_ref, 'operators')
        validate_closed_graph(self, LOCAL_TYPES)

    @property
    def ref(self) -> LocalRef:
        return LocalRef('node', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'layer': self.layer,
                          'region': self.region.to_value(), 'binding_ref': self.binding_ref.to_value()})


@dataclass(frozen=True)
class ContactEdge:
    kind: Literal['same_layer', 'connector']
    endpoints: tuple[LocalRef, ...]
    binding_ref: LocalRef
    connector_id: GeometryRecordId | None = None
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if type(self.kind) is not str or self.kind not in ('same_layer', 'connector'):
            raise ValueError('invalid local contact edge kind')
        endpoints = record_tuple(self.endpoints, LocalRef, 'endpoints')
        if len(endpoints) != 2:
            raise ValueError('contact edge requires two distinct nodes')
        for reference in endpoints:
            local_ref(reference, 'node')
        if endpoints != tuple(sorted(set(endpoints), key=lambda ref: ref.sha256)):
            raise ValueError('contact edge endpoints require canonical unique order')
        object.__setattr__(self, 'endpoints', endpoints)
        local_ref(self.binding_ref, 'operators')
        if (self.kind == 'connector' and type(self.connector_id) is not GeometryRecordId
                or self.kind == 'same_layer' and self.connector_id is not None):
            raise ValueError('connector provenance differs from contact edge kind')
        validate_closed_graph(self, LOCAL_TYPES)

    @property
    def ref(self) -> LocalRef:
        return LocalRef('edge', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'kind': self.kind,
                          'endpoints': tuple(ref.to_value() for ref in self.endpoints),
                          'binding_ref': self.binding_ref.to_value(),
                          'connector_id': None if self.connector_id is None else self.connector_id.sha256})


@dataclass(frozen=True)
class EnclosureSide:
    connector_id: GeometryRecordId
    node_ref: LocalRef
    layer: str
    margin_ticks: Fraction
    status: Literal['pass', 'violation']
    binding_ref: LocalRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        if type(self.connector_id) is not GeometryRecordId:
            raise ValueError('enclosure side requires connector record identity')
        local_ref(self.node_ref, 'node')
        local_ref(self.binding_ref, 'operators')
        if type(self.layer) is not str or self.layer not in CONDUCTOR_LAYERS:
            raise ValueError('unsupported enclosure side layer')
        if type(self.margin_ticks) is not Fraction:
            raise ValueError('enclosure margin requires a positive exact Fraction')
        validate_closed_graph(self.margin_ticks)
        if self.margin_ticks <= 0:
            raise ValueError('enclosure margin requires a positive exact Fraction')
        if type(self.status) is not str or self.status not in ('pass', 'violation'):
            raise ValueError('invalid local enclosure status')
        validate_closed_graph(self, LOCAL_TYPES)

    @property
    def ref(self) -> LocalRef:
        return LocalRef('audit', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'connector_id': self.connector_id.sha256,
                          'node_ref': self.node_ref.to_value(), 'layer': self.layer,
                          'margin_ticks': self.margin_ticks, 'status': self.status,
                          'binding_ref': self.binding_ref.to_value()})


@dataclass(frozen=True)
class ContactComponent:
    members: tuple[LocalRef, ...]
    binding_ref: LocalRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        members = record_tuple(self.members, LocalRef, 'component members')
        if not members:
            raise ValueError('local component requires at least one node')
        for reference in members:
            local_ref(reference, 'node')
        if members != tuple(sorted(set(members), key=lambda ref: ref.sha256)):
            raise ValueError('component members require canonical unique order')
        object.__setattr__(self, 'members', members)
        local_ref(self.binding_ref, 'operators')
        validate_closed_graph(self, LOCAL_TYPES)

    @property
    def ref(self) -> LocalRef:
        return LocalRef('component', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'members': tuple(ref.to_value() for ref in self.members),
                          'binding_ref': self.binding_ref.to_value()})


LOCAL_TYPES = (LocalRef, LocalContactBinding, ContactNode, ContactEdge, EnclosureSide, ContactComponent,
               ExactRegion, RegionRef, GeometryRef, GeometryRecordId, Rect, EvidenceRecord, SourceRef)
