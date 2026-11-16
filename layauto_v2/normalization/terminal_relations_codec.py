"""Closed W014 wire, sharing one unchanged captured W010 Value subtree."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import fields, is_dataclass, replace
from typing import cast

from layauto_v2.domain import publication_codec
from layauto_v2.domain.codec import FrozenMap, Value, canonical_bytes, decode, freeze
from layauto_v2.domain.terminal_relations import (
    TerminalRef, TerminalTarget, TerminalRelation, validate_terminal_graph,
)
from layauto_v2.derive.terminal_relations import TerminalRelationsDraft
from . import channel_identity_codec, local_connectivity_codec, net_annotation_codec
from . import codec as semantic_codec
from .local_connectivity import LocalConnectivityResult
from .terminal_relations import TerminalRelationsResult, _types

WIRE_VERSION = 'layauto-terminal-relations-wire/1'

# Registries name every persisted field. Old codecs and old wire are unchanged.
_SPEC: dict[str, tuple[Callable[..., object], tuple[str, ...]]] = {
    **{name: semantic_codec._SPEC[name] for name in ('CellId', 'DeviceId', 'NetId', 'Terminal')},
    **{name: net_annotation_codec._SPEC[name] for name in (
        'SourceRef', 'EvidenceIssue', 'LocalRef', 'RegionRef', 'AnnotationRef')},
    'TerminalRef': (TerminalRef, ('kind', 'sha256')),
    'TerminalTarget': (TerminalTarget, ('binding_ref', 'device_id', 'role', 'schema_version')),
    'TerminalRelation': (TerminalRelation, ('target', 'expected', 'channel_ref', 'node_refs',
        'component_refs', 'annotation_target_refs', 'local_observed_net_ids', 'evidence_refs',
        'context_path', 'observed_net_ids', 'support_status', 'schema_version')),
}
_LEAVES = (TerminalRef, TerminalTarget, TerminalRelation)
_INPUTS = ('local', 'source', 'channel_seeds', 'net_evidence', 'derived',
           'body_evidence', 'capture_binding', 'schema_version')


def _pack(value: object) -> Value:
    spec = next((entry for entry in _SPEC.values() if type(value) is entry[0]), None)
    if spec is not None:
        return FrozenMap({'record': type(value).__name__, 'fields': {
            name: _pack(getattr(value, name)) for name in spec[1]}})
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_pack(item) for item in value)})
    return FrozenMap({'scalar': freeze(value)})


def _unpack(value: Value) -> object:
    if type(value) is not FrozenMap:
        raise ValueError('expected tagged terminal wire value')
    if set(value) == {'map'}:
        if type(value['map']) is not FrozenMap:
            raise ValueError('terminal wire map requires immutable payload')
        return value['map']
    if set(value) == {'tuple'}:
        if type(value['tuple']) is not tuple:
            raise ValueError('terminal wire tuple requires native tuple')
        return tuple(_unpack(item) for item in value['tuple'])
    if set(value) == {'scalar'}:
        if type(value['scalar']) in (FrozenMap, tuple):
            raise ValueError('terminal scalar cannot contain collections')
        return value['scalar']
    if (set(value) != {'record', 'fields'} or type(value['record']) is not str
            or type(value['fields']) is not FrozenMap):
        raise ValueError('invalid terminal wire discriminator')
    spec = _SPEC.get(value['record'])
    if spec is None:
        raise ValueError('unknown terminal wire record')
    constructor, names = spec
    payload = value['fields']
    if set(payload) != set(names):
        raise ValueError('unknown/missing terminal wire fields')
    result = constructor(**{name: _unpack(payload[name]) for name in names})
    if canonical_bytes(_pack(result)) != canonical_bytes(value):
        raise ValueError('noncanonical terminal wire record')
    return result


def _compact(result: TerminalRelationsResult) -> FrozenMap:
    return FrozenMap({'schema_version': result.schema_version, 'status': result.status,
        'semantic_facts': decode(semantic_codec.encode_record(result.semantic_facts)),
        'value': None if result.value is None else result.value.to_value(),
        'issues': _pack(result.issues)})


def _stored_value(value: object) -> Value:
    """Tag actual retained types without invoking derived properties.

    The original graph has already passed native/closed storage validation.
    Maps remain distinct from typed records, even if their keys imitate this
    comparison representation. This value is never another captured packet.
    """
    if type(value) is FrozenMap:
        return FrozenMap({'map': value})
    if type(value) is tuple:
        return FrozenMap({'tuple': tuple(_stored_value(item) for item in value)})
    if is_dataclass(value):
        return FrozenMap({'record_type': type(value).__module__ + '.' + type(value).__qualname__,
            'fields': {member.name: _stored_value(object.__getattribute__(value, member.name))
                       for member in fields(value)}})
    return FrozenMap({'scalar': cast(Value, value)})


def _retained(record: TerminalRelationsResult | TerminalRelationsDraft, *, skip_input: bool = False) -> bytes:
    return canonical_bytes(FrozenMap({member.name: _stored_value(object.__getattribute__(record, member.name))
        for member in fields(record) if not (skip_input and member.name == 'input')}))


def _validate_result(result: TerminalRelationsResult) -> TerminalRelationsResult:
    validate_terminal_graph(result, _types())
    _storage(result)
    rebuilt = TerminalRelationsResult(result.input, result.schema_version)
    # Include all retained neutral inputs inside value, even though the wire
    # intentionally stores them through the single captured input subtree.
    if _retained(result, skip_input=True) != _retained(rebuilt, skip_input=True):
        raise ValueError('terminal result differs from complete captured reconstruction')
    return rebuilt


def _validate_draft(draft: TerminalRelationsDraft) -> TerminalRelationsDraft:
    validate_terminal_graph(draft, _types())
    _storage(draft)
    rebuilt = replace(draft)
    if _retained(draft) != _retained(rebuilt):
        raise ValueError('terminal draft differs from complete neutral reconstruction')
    return rebuilt


def _storage(record: TerminalRelationsResult | TerminalRelationsDraft) -> None:
    stored = vars(record)
    if type(stored) is not dict or set(stored) != {field.name for field in fields(record)}:
        raise ValueError('terminal aggregate has missing or undeclared retained fields')


def _draft_inputs(draft: TerminalRelationsDraft) -> FrozenMap:
    return FrozenMap({
        'local': decode(local_connectivity_codec.encode_record(draft.local)),
        'source': decode(semantic_codec.encode_record(draft.source)),
        'channel_seeds': tuple(decode(channel_identity_codec.encode_record(seed))
                               for seed in draft.channel_seeds),
        'net_evidence': tuple(decode(net_annotation_codec.encode_record(seed))
                              for seed in draft.net_evidence),
        'derived': decode(publication_codec.encode_record(draft.derived)),
        'body_evidence': decode(publication_codec.encode_record(draft.body_evidence)),
        'capture_binding': draft.capture_binding,
        'schema_version': draft.schema_version,
    })


def encode_record(record: object) -> bytes:
    if type(record) is TerminalRelationsResult:
        rebuilt = _validate_result(record)
        return canonical_bytes({'wire_schema': WIRE_VERSION, 'kind': 'result',
            'captured_input_wire': decode(local_connectivity_codec.encode_record(rebuilt.input)),
            'result': _compact(rebuilt)})
    if type(record) is TerminalRelationsDraft:
        rebuilt_draft = _validate_draft(record)
        return canonical_bytes({'wire_schema': WIRE_VERSION, 'kind': 'draft',
            'inputs': _draft_inputs(rebuilt_draft), 'output': rebuilt_draft.to_value()})
    if not any(type(record) is cls for cls in _LEAVES):
        raise ValueError('unsupported terminal relations wire type')
    validate_terminal_graph(record, _types())
    packed = _pack(record)
    _unpack(packed)
    return canonical_bytes({'wire_schema': WIRE_VERSION, 'kind': 'record', 'record': packed})


def decode_record(data: bytes) -> object:
    if type(data) is not bytes:
        raise ValueError('terminal wire requires native immutable bytes')
    value = decode(data)
    if type(value) is not FrozenMap or value.get('wire_schema') != WIRE_VERSION:
        raise ValueError('unsupported terminal relations wire schema')
    kind = value.get('kind')
    if kind == 'result' and set(value) == {'wire_schema', 'kind', 'captured_input_wire', 'result'}:
        input = local_connectivity_codec.decode_record(canonical_bytes(value['captured_input_wire']))
        if type(input) is not LocalConnectivityResult:
            raise ValueError('terminal result requires its complete W010 receipt')
        result = TerminalRelationsResult(input)
        if canonical_bytes(_compact(result)) != canonical_bytes(value['result']):
            raise ValueError('terminal wire differs from complete captured reconstruction')
        return result
    if kind == 'draft' and set(value) == {'wire_schema', 'kind', 'inputs', 'output'}:
        payload = value['inputs']
        if type(payload) is not FrozenMap or set(payload) != set(_INPUTS):
            raise ValueError('unknown/missing terminal neutral inputs')
        if type(payload['channel_seeds']) is not tuple or type(payload['net_evidence']) is not tuple:
            raise ValueError('terminal neutral seeds require native tuples')
        # Each old public decoder re-enters its unchanged neutral constructors.
        args: dict[str, object] = {
            'local': local_connectivity_codec.decode_record(canonical_bytes(payload['local'])),
            'source': semantic_codec.decode_record(canonical_bytes(payload['source'])),
            'channel_seeds': tuple(channel_identity_codec.decode_record(canonical_bytes(seed))
                                   for seed in payload['channel_seeds']),
            'net_evidence': tuple(net_annotation_codec.decode_record(canonical_bytes(seed))
                                  for seed in payload['net_evidence']),
            'derived': publication_codec.decode_record(canonical_bytes(payload['derived'])),
            'body_evidence': publication_codec.decode_record(canonical_bytes(payload['body_evidence'])),
            'capture_binding': payload['capture_binding'], 'schema_version': payload['schema_version'],
        }
        constructor = cast(Callable[..., TerminalRelationsDraft], TerminalRelationsDraft)
        draft = constructor(**args)
        if canonical_bytes(draft.to_value()) != canonical_bytes(value['output']):
            raise ValueError('terminal neutral wire differs from reconstructed outputs')
        return draft
    if kind == 'record' and set(value) == {'wire_schema', 'kind', 'record'}:
        root = value['record']
        if (type(root) is not FrozenMap
                or root.get('record') not in ('TerminalRef', 'TerminalTarget', 'TerminalRelation')):
            raise ValueError('foreign terminal root wire record')
        leaf = _unpack(value['record'])
        if not any(type(leaf) is cls for cls in _LEAVES):
            raise ValueError('foreign terminal root wire record')
        return leaf
    raise ValueError('unknown/missing terminal relations envelope fields')


def record_digest(record: object) -> str:
    return hashlib.sha256(encode_record(record)).hexdigest()
