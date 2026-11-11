"""Bounded A2 owned-pack reference. Never installs or replaces a runtime entry.

This attachment uses the unchanged registries and lower encoders on small values.
Its bounds are demonstration limits, not proposed product input limits.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from fractions import Fraction
from types import ModuleType

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, freeze
from layauto_v2.normalization import channel_identity_codec as channel
from layauto_v2.normalization import local_connectivity_codec as local


class ReferenceBoundExceeded(ValueError):
    pass


def bound_small(value: object) -> None:
    remaining = 2048

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 24:
            raise ReferenceBoundExceeded('reference only: 2048 nodes / depth 24')
        if type(item) in (bytes, str) and len(item) > 4096:
            raise ReferenceBoundExceeded('reference only: leaf length 4096')
        if type(item) is int and item.bit_length() > 256:
            raise ReferenceBoundExceeded('reference only: 256-bit integer')
        if type(item) is Fraction:
            visit(item.numerator, depth + 1)
            visit(item.denominator, depth + 1)
        elif type(item) is FrozenMap:
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is tuple:
            for child in item:
                visit(child, depth + 1)
        elif is_dataclass(item) and not isinstance(item, type):
            for field in fields(item):
                visit(getattr(item, field.name), depth + 1)

    visit(value, 0)


def _pack(codec: ModuleType, value: object) -> object:
    spec = codec._SPEC.get(type(value).__name__)
    if spec is not None and type(value) is spec[0]:
        return {'record': type(value).__name__,
                'fields': {field: _pack(codec, getattr(value, field)) for field in spec[1]}}
    if codec is channel:
        delegates = (
            (channel._LOCAL, 'local_record', channel.local_connectivity_codec.encode_record),
            (channel._GEOMETRY, 'geometry_record', channel.geometry_codec.encode_record),
            (channel._EFFECTIVE, 'effective_record', channel.effective_codec.encode_record),
            (channel._SEMANTIC, 'semantic_record', channel.semantic_codec.encode_record),
            (channel._CAPTURED, 'captured_record', channel._captured_bytes),
        )
    elif codec is local:
        delegates = (
            (local._EFFECTIVE, 'effective_record', local.effective_codec.encode_record),
            (local._GEOMETRY, 'geometry_record', local.geometry_codec.encode_record),
            (local._CAPTURED, 'captured_record', local._captured_bytes),
        )
    else:
        raise ValueError('reference has exactly two owners')
    for classes, tag, encoder in delegates:
        if any(type(value) is cls for cls in classes):
            return {tag: encoder(value)}
    if type(value) is FrozenMap:
        # Snapshot at the original map-branch position, not at operation end.
        return {'map': freeze(value)}
    if type(value) is tuple:
        return {'tuple': tuple(_pack(codec, item) for item in value)}
    return {'scalar': freeze(value)}


def pack_small(codec: ModuleType, value: object) -> object:
    bound_small(value)
    return _pack(codec, value)


def encode_small(codec: ModuleType, record: object) -> bytes:
    bound_small(record)
    spec = codec._SPEC.get(type(record).__name__)
    if spec is None or type(record) is not spec[0]:
        raise ValueError('unsupported reference root')
    codec.validate_closed_graph(record, codec._ALL_TYPES)
    schema = ('layauto-channel-identity-wire/1' if codec is channel
              else 'layauto-local-connectivity-wire/1')
    return canonical_bytes({'wire_schema': schema, 'record': _pack(codec, record)})
