"""A2 encoding trees preserve the accepted pack and the public wire contract.

The exact-class shells below isolate registry/dispatch mechanics. They are never
claimed to be valid semantic records or captured receipts. Real public values
and the existing capture/owner/run/second-authentication regressions separately
exercise admission and reconstruction.
"""
from __future__ import annotations

from dataclasses import fields
from fractions import Fraction
import hashlib
import json
import sys

import pytest

from layauto_v2.domain.channel_identity import ChannelRef, FinEvaluation, RationalRect, SeedLocation
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRecordId
from layauto_v2.domain.local_connectivity import ContactComponent, EnclosureSide, LocalRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.normalization import channel_identity_codec as channel
from layauto_v2.normalization import local_connectivity_codec as local


CODECS = (local, channel)
SCHEMAS = {local: 'layauto-local-connectivity-wire/1', channel: 'layauto-channel-identity-wire/1'}
REGISTRY = [(codec, name) for codec in CODECS for name in codec._SPEC]
DELEGATES = {
    local: ((local._EFFECTIVE, 'effective_record', local.effective_codec, 'encode_record'),
            (local._GEOMETRY, 'geometry_record', local.geometry_codec, 'encode_record'),
            (local._CAPTURED, 'captured_record', local, '_captured_bytes')),
    channel: ((channel._LOCAL, 'local_record', channel.local_connectivity_codec, 'encode_record'),
              (channel._GEOMETRY, 'geometry_record', channel.geometry_codec, 'encode_record'),
              (channel._EFFECTIVE, 'effective_record', channel.effective_codec, 'encode_record'),
              (channel._SEMANTIC, 'semantic_record', channel.semantic_codec, 'encode_record'),
              (channel._CAPTURED, 'captured_record', channel, '_captured_bytes')),
}


def shell(cls, **values):
    """Test-only exact registered type, without invoking semantic constructors."""
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def old_wire(codec, value):
    return canonical_bytes({'wire_schema': SCHEMAS[codec], 'record': codec._pack(value)})


@pytest.mark.parametrize('codec,name', REGISTRY, ids=[name for _, name in REGISTRY])
def test_every_registry_field_keeps_accepted_order_tag_and_bytes(codec, name, monkeypatch):
    cls, names = codec._SPEC[name]
    # Dataclass definitions are a separate completeness source from _SPEC.
    assert names == tuple(field.name for field in fields(cls))
    markers = {field: name + ':' + field + ':界' for field in names}
    specimen = shell(cls, **markers)
    observed = []
    original = cls.__getattribute__

    def read(self, attr):
        if self is specimen and attr in markers:
            observed.append(attr)
        return original(self, attr)

    monkeypatch.setattr(cls, '__getattribute__', read)
    packed = codec._pack_for_encode(specimen)
    assert observed == list(names)
    assert type(packed) is dict and type(packed['fields']) is dict
    assert packed == {'record': name, 'fields': {field: {'scalar': markers[field]} for field in names}}
    assert tuple(packed['fields']) == names
    expected_dom = {'$map': {'record': name, 'fields': {'$map': {
        field: {'$map': {'scalar': markers[field]}} for field in names}}}}
    expected = json.dumps(expected_dom, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    assert canonical_bytes(packed) == canonical_bytes(codec._pack(specimen)) == expected


@pytest.mark.parametrize('codec', CODECS, ids=('local', 'channel'))
def test_every_exact_delegate_keeps_order_identity_and_complete_bytes(codec, monkeypatch):
    calls = []
    values = []
    tags = []
    wires = {}
    for classes, tag, owner, attr in DELEGATES[codec]:
        for cls in classes:
            values.append(object.__new__(cls))
            tags.append(tag)
        # This is the complete return value, including embedded NUL/non-ASCII
        # bytes, so slicing, decoding, digest substitution or omission is visible.
        raw = ('complete-' + tag).encode() + b'\x00\xff'
        wires[tag] = raw

        def encode(value, tag=tag, raw=raw):
            calls.append((tag, value))
            return raw

        monkeypatch.setattr(owner, attr, encode)
    packed = codec._pack_for_encode(tuple(values))
    assert type(packed) is dict and type(packed['tuple']) is tuple
    assert len(calls) == len(values)
    assert all(tag == expected and value is original
               for (tag, value), expected, original in zip(calls, tags, values))
    assert all(item == {tag: wires[tag]} and item[tag] is wires[tag]
               for item, tag in zip(packed['tuple'], tags))
    calls.clear()
    assert canonical_bytes(packed) == canonical_bytes(codec._pack(tuple(values)))
    assert all(value is original for (_, value), original in zip(calls, values))


@pytest.mark.parametrize('codec', CODECS, ids=('local', 'channel'))
def test_scalar_types_opaque_map_and_tuple_have_explicit_wire(codec):
    values = (None, False, 0, Fraction(0), True, 1, Fraction(1), '', 'é\n界😀',
              b'', b'\x00\xff', Fraction(-3, 7), 10**100)
    for value in values:
        packed = codec._pack_for_encode(value)
        assert type(packed) is dict and set(packed) == {'scalar'}
        assert type(packed['scalar']) is type(value)
        assert canonical_bytes(packed) == canonical_bytes(codec._pack(value))
    assert len({canonical_bytes(codec._pack_for_encode(value)) for value in (False, 0, Fraction(0))}) == 3
    assert canonical_bytes(codec._pack_for_encode(b'\x00\xff')) == b'{"$map":{"scalar":{"$bytes":"00ff"}}}'
    assert canonical_bytes(codec._pack_for_encode(Fraction(-3, 7))) == (
        b'{"$map":{"scalar":{"$rational":{"denominator":"7","numerator":"-3"}}}}')
    assert canonical_bytes(codec._pack_for_encode('é\n界😀')) == (
        '{"$map":{"scalar":"é\\n界😀"}}'.encode('utf-8'))
    payload = FrozenMap({'record': 'opaque', 'fields': (b'\x00', Fraction(1, 3)), '$map': True})
    tree = codec._pack_for_encode((payload, values))
    assert set(tree) == {'tuple'} and type(tree['tuple']) is tuple
    assert set(tree['tuple'][0]) == {'map'} and type(tree['tuple'][0]['map']) is FrozenMap
    assert canonical_bytes(tree) == canonical_bytes(codec._pack((payload, values)))


@pytest.mark.parametrize('codec', CODECS, ids=('local', 'channel'))
def test_map_leaf_is_snapshotted_before_later_tuple_items(codec, monkeypatch):
    payload = FrozenMap({'nested': (Fraction(1, 3), b'original')})
    original = canonical_bytes(payload)
    sentinel = object()
    actual_freeze = codec.freeze
    seen = []

    def freeze(value):
        seen.append(value)
        if value is sentinel:
            object.__setattr__(payload, '_entries', (('changed', b'later'),))
            return 'later'
        return actual_freeze(value)

    monkeypatch.setattr(codec, 'freeze', freeze)
    packed = codec._pack_for_encode((payload, sentinel))
    assert seen[0] is payload and seen[1] is sentinel
    assert packed['tuple'][0]['map'] is not payload
    assert canonical_bytes(packed['tuple'][0]['map']) == original
    assert packed['tuple'][1] == {'scalar': 'later'}


PUBLIC = (
    (local, LocalRef('node', '1' * 64)),
    (local, ContactComponent((LocalRef('node', '1' * 64),), LocalRef('operators', '2' * 64))),
    (local, EnclosureSide(GeometryRecordId('1' * 64), LocalRef('node', '2' * 64), 'OD',
                          Fraction(2, 3), 'pass', LocalRef('operators', '3' * 64))),
    (channel, ChannelRef('seed', '1' * 64)),
    (channel, RationalRect(Fraction(-1, 3), Fraction(0), Fraction(2), Fraction(10**100))),
    (channel, SeedLocation(ChannelRef('seed', '1' * 64), (), ChannelRef('binding', '2' * 64))),
    (channel, FinEvaluation(GeometryRecordId('1' * 64), RegionRef('region', '2' * 64),
                            'outside', None, Fraction(2), SourceRef('file:///界', '3' * 64),
                            ChannelRef('binding', '4' * 64))),
)


@pytest.mark.parametrize('codec,record', PUBLIC, ids=[type(record).__name__ for _, record in PUBLIC])
def test_real_public_values_keep_old_wire_hash_and_exact_reconstruction(codec, record):
    wire = codec.encode_record(record)
    assert wire == old_wire(codec, record)
    assert codec.record_digest(record) == hashlib.sha256(wire).hexdigest()
    rebuilt = codec.decode_record(wire)
    assert type(rebuilt) is type(record) and rebuilt == record
    assert codec.encode_record(rebuilt) == wire
    for field in fields(record):
        assert type(getattr(rebuilt, field.name)) is type(getattr(record, field.name))


@pytest.mark.parametrize('codec,record', (PUBLIC[0], PUBLIC[3]), ids=('local', 'channel'))
def test_public_root_and_original_alias_graph_are_checked_before_packing(codec, record, monkeypatch):
    cls = type(record)

    class Subclass(cls):
        pass

    class MutableText(str):
        pass

    class EqualObject:
        def __eq__(self, other):
            return other == record.kind

    def pack_must_not_run(value):
        pytest.fail('packing occurred before the public root/original graph checks')

    monkeypatch.setattr(codec, '_pack_for_encode', pack_must_not_run)
    for foreign in (None, {}, record.kind, Subclass(record.kind, record.sha256)):
        with pytest.raises(ValueError):
            codec.encode_record(foreign)
    for foreign in (MutableText(record.kind), EqualObject(), [record.kind]):
        with pytest.raises(ValueError):
            codec.encode_record(shell(cls, kind=foreign, sha256=record.sha256))


@pytest.mark.parametrize('wrong', (False, 0, 0.0, Fraction(0)))
def test_public_constructor_and_decoder_keep_wrong_type_equal_scalar_rejection(wrong):
    if type(wrong) is Fraction:
        # Fraction zero is the accepted coordinate type; bool/int/float are not.
        assert RationalRect(wrong, Fraction(0), Fraction(1), Fraction(1)).x0 is wrong
        return
    with pytest.raises(ValueError):
        RationalRect(wrong, Fraction(0), Fraction(1), Fraction(1))
    record = RationalRect(Fraction(0), Fraction(0), Fraction(1), Fraction(1))
    tree = dict(decode(channel.encode_record(record)))
    tagged = dict(tree['record'])
    payload = dict(tagged['fields'])
    payload['x0'] = {'scalar': wrong}
    tagged['fields'] = payload
    tree['record'] = tagged
    with pytest.raises(ValueError):
        channel.decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('codec,record', (PUBLIC[0], PUBLIC[3]), ids=('local', 'channel'))
@pytest.mark.parametrize('change', ('missing', 'extra', 'wrong_tag', 'unknown', 'scalar_collection', 'wrong_tuple'))
def test_public_decoder_keeps_closed_fields_and_tags(codec, record, change):
    tree = dict(decode(codec.encode_record(record)))
    tagged = dict(tree['record'])
    payload = dict(tagged['fields'])
    if change == 'missing':
        del payload['sha256']
    elif change == 'extra':
        payload['foreign'] = {'scalar': None}
    elif change == 'wrong_tag':
        payload['kind'] = {'foreign': record.kind}
    elif change == 'unknown':
        tagged['record'] = 'Foreign'
    elif change == 'scalar_collection':
        payload['kind'] = {'scalar': (record.kind,)}
    else:
        payload['kind'] = {'tuple': record.kind}
    tagged['fields'] = payload
    tree['record'] = tagged
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(tree))


@pytest.mark.parametrize('codec,record', (PUBLIC[0], PUBLIC[3]), ids=('local', 'channel'))
@pytest.mark.parametrize('change', ('whitespace', 'duplicate', 'float', 'schema'))
def test_public_decoder_keeps_canonical_json_rejections(codec, record, change):
    wire = codec.encode_record(record)
    if change == 'whitespace':
        wire += b'\n'
    elif change == 'duplicate':
        wire = wire.replace(b'"wire_schema":', b'"wire_schema":"duplicate","wire_schema":')
    elif change == 'float':
        wire = wire.replace(b'"scalar":"' + record.kind.encode() + b'"', b'"scalar":1.0')
    else:
        wire = wire.replace(b'-wire/1', b'-wire/2')
    with pytest.raises(ValueError):
        codec.decode_record(wire)


@pytest.mark.parametrize('codec', CODECS, ids=('local', 'channel'))
def test_public_decoder_keeps_each_delegated_bytes_and_exact_result_boundary(codec, monkeypatch):
    for classes, tag, owner, _ in DELEGATES[codec]:
        for wrong in (None, 'wire', 0, FrozenMap({}), (b'wire',)):
            with pytest.raises(ValueError):
                codec.decode_record(canonical_bytes({
                    'wire_schema': SCHEMAS[codec], 'record': {tag: wrong}}))
        decoder_owner = codec.publication_codec if tag == 'captured_record' else owner
        with monkeypatch.context() as patch:
            patch.setattr(decoder_owner, 'decode_record', lambda value: object())
            with pytest.raises(ValueError, match='foreign nested'):
                codec.decode_record(canonical_bytes({
                    'wire_schema': SCHEMAS[codec], 'record': {tag: b'complete'}}))


@pytest.mark.parametrize('codec,record', (PUBLIC[0], PUBLIC[3]), ids=('local', 'channel'))
@pytest.mark.parametrize('failure_type', (ValueError, TypeError, KeyboardInterrupt, SystemExit))
@pytest.mark.parametrize('suppression', (False, True))
def test_public_scalar_freeze_fault_keeps_original_exception_history(codec, record, monkeypatch, failure_type, suppression):
    failure = failure_type('scalar freeze failure')
    cause, context = RuntimeError('prior cause'), LookupError('prior context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression

    def fail(value):
        raise failure

    monkeypatch.setattr(codec, 'freeze', fail)
    with pytest.raises(failure_type) as caught:
        codec.encode_record(record)
    assert caught.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is suppression


@pytest.mark.parametrize('codec,record', (PUBLIC[2], PUBLIC[6]), ids=('local', 'channel'))
def test_public_nested_encoder_fault_keeps_original_exception_history(codec, record, monkeypatch):
    failure = UnicodeError('nested geometry encoder failure')
    cause, context = RuntimeError('prior cause'), LookupError('prior context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, True

    def fail(value):
        raise failure

    monkeypatch.setattr(codec.geometry_codec, 'encode_record', fail)
    with pytest.raises(UnicodeError) as caught:
        codec.encode_record(record)
    assert caught.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is True


@pytest.mark.parametrize('codec', CODECS, ids=('local', 'channel'))
def test_json_integer_then_whole_utf8_error_order_and_attributes_stay_original(codec):
    def error(pack, value):
        with pytest.raises((ValueError, UnicodeEncodeError)) as caught:
            canonical_bytes(pack(value))
        exc = caught.value
        return type(exc), exc.args, exc.__cause__, exc.__context__, exc.__suppress_context__

    value = ('\ud800', 10**5000)
    previous_limit = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(4300)
        old = error(codec._pack, value)
        assert old[0] is ValueError
        assert error(codec._pack_for_encode, value) == old
        sys.set_int_max_str_digits(0)
        old = error(codec._pack, value)
        assert old[0] is UnicodeEncodeError
        assert error(codec._pack_for_encode, value) == old
    finally:
        sys.set_int_max_str_digits(previous_limit)
