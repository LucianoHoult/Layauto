"""Finite, immutable device-terminal comparisons; no topology or capture owner."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import MISSING, dataclass, fields, is_dataclass, replace
from fractions import Fraction
from inspect import getattr_static
from typing import Literal, TypeVar, cast

from .circuit import Terminal
from .codec import FrozenMap, Value, canonical_bytes, digest
from .evidence import EvidenceRecord, SourceRef
from .geometry import evidence_value, mapping, source_value
from .identifiers import CellId, DeviceId, NetId, identity_value
from .local_connectivity import LocalRef
from .net_annotation import AnnotationRef, sha, validate_annotation_graph
from .regions import RegionRef
from .results import EvidenceIssue

VERSION = 'layauto-terminal-relations/1'
SCOPE = 'source_device_terminal_external_body_relations/1'
ROLES = ('D', 'G', 'S', 'B')
BODY_PATH_FIELDS = frozenset((
    'device_id', 'channel_ref', 'active_id', 'association_source', 'context_claim',
    'local_body_id', 'local_body_record_id', 'local_body_node_ref', 'local_body_component_ref',
    'external_body_id', 'tap_id', 'external_rail_id', 'local_rail_id', 'rail_record_id',
    'rail_node_ref', 'rail_component_ref', 'body_candidates', 'rail_candidates',
    'evidence_refs', 'observed_net_ids', 'body_edge_length_nm', 'rail_edge_length_nm',
    'active_enclosure_nm', 'tap_body_enclosure_nm', 'tap_rail_enclosure_nm',
    'chain_status', 'rule_status', 'claim_status',
))
RefKind = Literal['binding', 'target', 'relation', 'draft']
SupportStatus = Literal['established', 'indeterminate']
ComparisonStatus = Literal['equal', 'mismatch', 'conflict', 'unknown', 'indeterminate']
T = TypeVar('T')


def records(value: object, cls: type[T], name: str) -> tuple[T, ...]:
    """Snapshot caller sequences; retained graphs accept only native tuples."""
    if type(value) is not tuple and type(value) is not list:
        raise ValueError('invalid terminal collection: ' + name)
    copied = tuple(value)
    if any(type(item) is not cls for item in copied):
        raise ValueError('invalid terminal collection: ' + name)
    return copied


def validate_terminal_graph(value: object, record_types: tuple[type[object], ...] = ()) -> None:
    """Check original storage, including forged map backing and extra fields."""
    validate_annotation_graph(value, TERMINAL_TYPES + record_types)
    seen: set[int] = set()
    evidence_leaves: list[SourceRef | EvidenceRecord] = []

    def check(item: object) -> None:
        if item is None or type(item) in (bool, int, str, bytes, Fraction):
            return
        if id(item) in seen:
            return
        seen.add(id(item))
        if type(item) is tuple:
            for child in cast(tuple[object, ...], item):
                check(child)
        elif type(item) is FrozenMap:
            stored = vars(item)
            if type(stored) is not dict or set(stored) != {'_entries'}:
                raise ValueError('terminal map has missing or undeclared retained fields')
            for child in item.values():
                check(child)
        elif is_dataclass(item):
            stored = vars(item)
            members = fields(item)
            if type(stored) is not dict or set(stored) - {field.name for field in members}:
                raise ValueError('terminal record has missing or undeclared retained fields')
            for member in members:
                # Dataclasses can retain an init=False immutable default on the
                # class (W006's kind discriminators). That is a real effective
                # field, while required/default-factory fields need instance
                # storage. Do not invoke arbitrary fallback descriptors.
                if member.name not in stored and (member.init or member.default is MISSING
                        or getattr_static(type(item), member.name, MISSING) is not member.default):
                    raise ValueError('terminal record has missing or undeclared retained fields')
                check(getattr(item, member.name))
            if type(item) is SourceRef or type(item) is EvidenceRecord:
                evidence_leaves.append(item)

    check(value)
    # Complete the original native/storage walk before a public constructor
    # makes defensive copies. Rebuild each shared leaf once, never mutate the
    # caller's shell or invoke its __post_init__ on the original object.
    for leaf in evidence_leaves:
        if type(leaf) is SourceRef:
            rebuilt_source = SourceRef(leaf.uri, leaf.sha256, leaf.field, leaf.line,
                                       leaf.column, leaf.byte_offset, leaf.record_index)
            actual = FrozenMap({member.name: getattr(leaf, member.name) for member in fields(leaf)})
            expected = FrozenMap({member.name: getattr(rebuilt_source, member.name)
                                  for member in fields(rebuilt_source)})
        else:
            evidence = cast(EvidenceRecord, leaf)
            rebuilt_evidence = EvidenceRecord(evidence.kind, evidence.payload, evidence.sources,
                                              evidence.parser_version, evidence.schema_version)
            actual, expected = evidence_value(evidence), evidence_value(rebuilt_evidence)
        if canonical_bytes(actual) != canonical_bytes(expected):
            raise ValueError('terminal evidence leaf differs from its complete public reconstruction')


def _value(value: object) -> Value:
    if type(value) is TerminalRef:
        return value.to_value()
    if type(value) in (CellId, DeviceId, NetId):
        return identity_value(cast(CellId | DeviceId | NetId, value))
    if type(value) in (LocalRef, RegionRef, AnnotationRef):
        return cast(LocalRef | RegionRef | AnnotationRef, value).to_value()
    if type(value) is SourceRef:
        return source_value(value)
    if type(value) is Terminal:
        terminal = value
        return FrozenMap({'role': terminal.role, 'net_id': identity_value(terminal.net_id),
                          'source': source_value(terminal.source)})
    if type(value) is EvidenceIssue:
        issue = value
        return FrozenMap({'category': issue.category, 'code': issue.code,
                          'message': issue.message, 'source': source_value(issue.source)})
    if type(value) in (TerminalTarget, TerminalRelation) and is_dataclass(value):
        return FrozenMap({'type': type(value).__name__,
                          'fields': {field.name: _value(getattr(value, field.name)) for field in fields(value)}})
    if type(value) is tuple:
        return tuple(_value(item) for item in value)
    if value is None or type(value) in (str, int, bool, bytes, Fraction, FrozenMap):
        return cast(Value, value)
    raise ValueError('foreign terminal value')


def validate_members(value: object) -> None:
    """Reconstruct every leaf before numeric or dataclass equality is trusted."""
    if type(value) is tuple:
        for child in value:
            validate_members(child)
    elif any(type(value) is cls for cls in TERMINAL_TYPES) and is_dataclass(value):
        for field in fields(value):
            validate_members(getattr(value, field.name))
        if type(value) is SourceRef:
            source = value
            if type(source.uri) is not str or source.sha256 is not None and type(source.sha256) is not str:
                raise ValueError('terminal source requires native text')
            if source.field is not None and type(source.field) is not str:
                raise ValueError('terminal source field requires native text')
        if type(value) is EvidenceIssue:
            issue = value
            if any(type(text) is not str for text in (issue.category, issue.code, issue.message)):
                raise ValueError('terminal issue requires native text')
        constructor = cast(Callable[..., object], type(value))
        rebuilt = constructor(**{field.name: getattr(value, field.name) for field in fields(value)})
        if canonical_bytes(_value(rebuilt)) != canonical_bytes(_value(value)):
            raise ValueError('terminal member differs from its validated reconstruction')


def _common(value: object) -> None:
    if type(getattr(value, 'schema_version')) is not str or getattr(value, 'schema_version') != VERSION:
        raise ValueError('unsupported terminal relation schema')
    validate_terminal_graph(value)
    if not is_dataclass(value):
        raise ValueError('terminal record requires a dataclass')
    for field in fields(value):
        validate_members(getattr(value, field.name))


def _ref(value: object, cls: type[object], kind: str) -> None:
    if type(value) is not cls or getattr(value, 'kind', None) != kind:
        raise ValueError('incorrect typed terminal reference')


def _ordered_refs(value: tuple[T, ...], cls: type[object], kind: str) -> None:
    for reference in value:
        _ref(reference, cls, kind)
    if value != tuple(sorted(set(value), key=lambda item: cast(str, getattr(item, 'sha256')))):
        raise ValueError('terminal references require canonical unique order')


def _nets(value: tuple[NetId, ...], cell: CellId) -> None:
    if value != tuple(sorted(set(value), key=lambda item: item.id)) or any(net.cell != cell for net in value):
        raise ValueError('terminal nets require canonical unique source-cell identities')


def _body_path_structure(path: FrozenMap) -> None:
    """Validate exact neutral field types without redoing body geometry."""
    for name in ('body_edge_length_nm', 'rail_edge_length_nm', 'active_enclosure_nm',
                 'tap_body_enclosure_nm', 'tap_rail_enclosure_nm'):
        measure = path[name]
        if measure is not None:
            if type(measure) is not Fraction:
                raise ValueError('body path measures require native exact Fraction values')
            if name in ('body_edge_length_nm', 'rail_edge_length_nm') and measure < 0:
                raise ValueError('body path edge lengths cannot be negative')
    for name in ('active_id', 'local_body_record_id', 'rail_record_id'):
        if path[name] is not None:
            sha(path[name])
    for name in ('context_claim', 'local_body_id', 'external_body_id', 'tap_id',
                 'external_rail_id', 'local_rail_id'):
        label = path[name]
        if label is not None:
            if type(label) is not str or not label:
                raise ValueError('body path context identities require native nonempty text')
            label.encode('utf-8')
    for name in ('body_candidates', 'rail_candidates'):
        candidates = path[name]
        if type(candidates) is not tuple or any(type(item) is not str or not item for item in candidates):
            raise ValueError('body path candidates require immutable native text identities')
        if len(set(candidates)) != len(candidates):
            raise ValueError('body path candidates must retain unique object identities')
        for candidate in candidates:
            if name == 'rail_candidates':
                sha(candidate)
            else:
                cast(str, candidate).encode('utf-8')
    if path['association_source'] is not None:
        source = mapping(path['association_source'])
        if set(source) != {member.name for member in fields(SourceRef)}:
            raise ValueError('body association source has missing or unknown fields')
        reference = SourceRef(cast(str, source['uri']), cast(str | None, source['sha256']),
                              cast(str | None, source['field']), cast(int | None, source['line']),
                              cast(int | None, source['column']), cast(int | None, source['byte_offset']),
                              cast(int | None, source['record_index']))
        validate_members(reference)
        if source_value(reference) != source:
            raise ValueError('body association source differs from its native reconstruction')
    for name, kind in (('rail_node_ref', 'node'), ('rail_component_ref', 'component')):
        if path[name] is not None:
            value = mapping(path[name])
            if set(value) != {'schema', 'kind', 'sha256'} or value['kind'] != kind:
                raise ValueError('body rail reference has missing/unknown fields or wrong kind')
            reference_value = LocalRef('node' if kind == 'node' else 'component', cast(str, value['sha256'])).to_value()
            if value != reference_value:
                raise ValueError('body rail reference has an unsupported schema')


class TerminalProblem(ValueError):
    """An expected unsupported terminal owner or admitted source requirement."""

    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def problem(source: SourceRef, field: str, message: str,
            code: str = 'UnsupportedTerminalOperator') -> TerminalProblem:
    return TerminalProblem(EvidenceIssue('unsupported', code, message, replace(source, field=field)))


@dataclass(frozen=True)
class TerminalRef:
    kind: RefKind
    sha256: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in ('binding', 'target', 'relation', 'draft'):
            raise ValueError('unknown terminal reference kind')
        sha(self.sha256)
        validate_terminal_graph(self)

    def to_value(self) -> FrozenMap:
        validate_terminal_graph(self)
        TerminalRef(self.kind, self.sha256)
        return FrozenMap({'schema': VERSION, 'kind': self.kind, 'sha256': self.sha256})


@dataclass(frozen=True)
class TerminalTarget:
    binding_ref: TerminalRef
    device_id: DeviceId
    role: str
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        _ref(self.binding_ref, TerminalRef, 'binding')
        if type(self.device_id) is not DeviceId or type(self.role) is not str or self.role not in ROLES:
            raise ValueError('terminal target requires a source device and ordered D/G/S/B role')
        _common(self)

    @property
    def ref(self) -> TerminalRef:
        return TerminalRef('target', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        validate_terminal_graph(self)
        validate_members(self)
        return cast(FrozenMap, _value(self))


@dataclass(frozen=True)
class TerminalRelation:
    target: TerminalTarget
    expected: Terminal
    channel_ref: RegionRef | None
    node_refs: tuple[LocalRef, ...]
    component_refs: tuple[LocalRef, ...]
    annotation_target_refs: tuple[AnnotationRef, ...]
    local_observed_net_ids: tuple[NetId, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    context_path: FrozenMap | None
    observed_net_ids: tuple[NetId, ...]
    support_status: SupportStatus
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        for name, cls in (('node_refs', LocalRef), ('component_refs', LocalRef),
                          ('annotation_target_refs', AnnotationRef), ('local_observed_net_ids', NetId),
                          ('evidence_refs', AnnotationRef), ('observed_net_ids', NetId)):
            object.__setattr__(self, name, records(getattr(self, name), cls, name))
        _common(self)
        if type(self.target) is not TerminalTarget or type(self.expected) is not Terminal:
            raise ValueError('terminal relation requires a typed target and source terminal')
        if (self.expected.role != self.target.role or self.expected.net_id.cell != self.target.device_id.cell):
            raise ValueError('terminal expectation differs from target role/source cell')
        if self.channel_ref is not None:
            _ref(self.channel_ref, RegionRef, 'region')
        for name, cls, kind in (('node_refs', LocalRef, 'node'), ('component_refs', LocalRef, 'component'),
                                ('annotation_target_refs', AnnotationRef, 'target'), ('evidence_refs', AnnotationRef, 'evidence')):
            _ordered_refs(getattr(self, name), cls, kind)
        for name in ('local_observed_net_ids', 'observed_net_ids'):
            _nets(getattr(self, name), self.target.device_id.cell)
        if type(self.support_status) is not str or self.support_status not in ('established', 'indeterminate'):
            raise ValueError('invalid terminal relation support status')
        if (self.context_path is not None and type(self.context_path) is not FrozenMap
                or self.target.role != 'B' and self.context_path is not None):
            raise ValueError('only body targets can carry independent external context')
        if self.target.role != 'B' and self.observed_net_ids != self.local_observed_net_ids:
            raise ValueError('local terminal observation differs from its local evidence')
        if self.target.role == 'B' and self.context_path is None and self.observed_net_ids:
            raise ValueError('body observation requires its independent context path')
        if self.context_path is not None:
            path = self.context_path
            if set(path) != BODY_PATH_FIELDS:
                raise ValueError('body terminal path has missing or unknown fields')
            _body_path_structure(path)
            if (path['device_id'] != identity_value(self.target.device_id)
                    or path['channel_ref'] != (None if self.channel_ref is None else self.channel_ref.to_value())
                    or path['observed_net_ids'] != tuple(identity_value(net) for net in self.observed_net_ids)):
                raise ValueError('body terminal path differs from its target, channel or observed nets')
            for name, references in (('local_body_node_ref', self.node_refs),
                                      ('local_body_component_ref', self.component_refs)):
                values = () if path[name] is None else (path[name],)
                if values != tuple(reference.to_value() for reference in references):
                    raise ValueError('body path differs from its original local physical target')
            raw_evidence = path['evidence_refs']
            if type(raw_evidence) is not tuple:
                raise ValueError('body path requires immutable exact query references')
            evidence_values = tuple(reference.to_value() for reference in self.evidence_refs)
            if (any(value not in evidence_values for value in raw_evidence)
                    or len({canonical_bytes(value) for value in raw_evidence}) != len(raw_evidence)):
                raise ValueError('body path query references do not close to terminal evidence')
            if type(path['chain_status']) is not str or path['chain_status'] not in ('established', 'indeterminate'):
                raise ValueError('body path has an unsupported chain status')
            if type(path['rule_status']) is not str or path['rule_status'] not in ('satisfied', 'violation', 'indeterminate'):
                raise ValueError('body path has an unsupported rule status')
            if type(path['claim_status']) is not str or path['claim_status'] not in ('equal', 'mismatch', 'conflict', 'indeterminate'):
                raise ValueError('body path has an unsupported claim status')
            expected_support = 'established' if path['chain_status'] == 'established' and self.channel_ref is not None else 'indeterminate'
            if self.support_status != expected_support:
                raise ValueError('body terminal support differs from its independent path')
        if self.support_status == 'established' and (self.channel_ref is None or not self.node_refs or not self.component_refs):
            raise ValueError('established terminal requires localized channel and physical targets')

    @property
    def status(self) -> ComparisonStatus:
        if self.support_status == 'indeterminate':
            return 'indeterminate'
        if not self.observed_net_ids:
            return 'unknown'
        if len(self.observed_net_ids) > 1:
            return 'conflict'
        return 'equal' if self.observed_net_ids[0] == self.expected.net_id else 'mismatch'

    @property
    def ref(self) -> TerminalRef:
        return TerminalRef('relation', digest(self.to_value()))

    def to_value(self) -> FrozenMap:
        validate_terminal_graph(self)
        validate_members(self)
        return cast(FrozenMap, _value(self))


TERMINAL_TYPES = (TerminalRef, TerminalTarget, TerminalRelation, Terminal, CellId, DeviceId, NetId,
                  LocalRef, RegionRef, AnnotationRef, SourceRef, EvidenceIssue)
