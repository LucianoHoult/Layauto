"""A1 preserves the closed exact bytes language and public failure boundaries."""
from __future__ import annotations

from itertools import product
import json

import pytest

from layauto_v2.domain import codec


def wire(text: object) -> bytes:
    return json.dumps({'$bytes': text}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def accepted(text: str) -> bool:
    return len(text) % 2 == 0 and all('0' <= char <= '9' or 'a' <= char <= 'f' for char in text)


def assert_language(text: str) -> None:
    if accepted(text):
        value = codec.decode(wire(text))
        assert type(value) is bytes and value == bytes.fromhex(text)
        assert codec.canonical_bytes(value) == wire(text)
    else:
        with pytest.raises(ValueError):
            codec.decode(wire(text))


def test_complete_ascii_pairs_and_every_byte_keep_the_exact_language():
    assert codec.decode(wire('')) == b''
    for left, right in product(map(chr, range(128)), repeat=2):
        assert_language(left + right)
    for value in range(256):
        data = bytes((value,))
        assert codec.decode(codec.canonical_bytes(data)) == data
    data = bytes(range(256))
    assert codec.decode(codec.canonical_bytes(data)) == data


def test_finite_mixed_language_witnesses_include_odd_and_unicode():
    for length in range(5):
        for chars in product('0fAz \né１', repeat=length):
            assert_language(''.join(chars))
    for text in ('ＦＦ', 'ｆｆ', '００', '١١', '𝟎𝟎', '\u00a0\u00a0', '\u2028\u2028', 'K0', 'ff\x00'):
        assert_language(text)


@pytest.mark.parametrize('suffix', ('', '0', 'F0', 'g0', '  ', '\n\n', '０0'))
def test_long_valid_prefix_does_not_hide_invalid_tail(suffix):
    assert_language('0123456789abcdef' * 4096 + suffix)


@pytest.mark.parametrize('data', (
    b'{"$bytes":null}', b'{"$bytes":[]}', b'{"$bytes":0}', b'{"$bytes":true}',
    b'{"$bytes":"00","foreign":0}', b'{"$bytes":"00","$bytes":"00"}',
    b'{"$bytes": "00"}', b' {"$bytes":"00"}', b'{"$bytes":"00"}\n',
    b'{"$bytes":"\\u0030\\u0030"}', b'{"$bytes":"00"}{}',
    b'{"$map":{"a":{"$bytes":"00"},"a":{"$bytes":"00"}}}',
    b'[NaN,{"$bytes":"00"}]', b'[1.0,{"$bytes":"00"}]',
))
def test_public_json_tags_and_canonical_rejection_stay_closed(data):
    with pytest.raises(ValueError):
        codec.decode(data)


def test_nested_bytes_roundtrip_and_invalid_leaf_rejection():
    value = {'nested': (b'', bytes(range(256)), {'leaf': b'\x00\xff'})}
    encoded = codec.canonical_bytes(value)
    assert codec.canonical_bytes(codec.decode(encoded)) == encoded
    with pytest.raises(ValueError):
        codec.decode(b'{"$map":{"nested":[{"$bytes":"00"},{"$bytes":"F0"}]}}')


@pytest.mark.parametrize('failure_type', (ValueError, TypeError, KeyError, KeyboardInterrupt, SystemExit))
@pytest.mark.parametrize('suppression', (False, True))
@pytest.mark.parametrize('boundary', ('matcher', 'fromhex'))
def test_unexpected_bytes_decoder_exception_keeps_original_history(monkeypatch, failure_type, suppression, boundary):
    failure = failure_type('injected A1 failure')
    cause, context = RuntimeError('prior cause'), LookupError('prior context')
    failure.__cause__, failure.__context__, failure.__suppress_context__ = cause, context, suppression
    def fail(*args, **kwargs):
        raise failure
    if boundary == 'matcher':
        monkeypatch.setattr(codec.re, 'fullmatch', fail)
    else:
        class FaultingBytes:
            fromhex = staticmethod(fail)
        monkeypatch.setattr(codec, 'bytes', FaultingBytes, raising=False)
    with pytest.raises(failure_type) as raised:
        codec.decode(wire('00'))
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is suppression


@pytest.mark.parametrize('text', ('', '0', '00', 'a', 'F0', ' \n', '００'))
def test_matcher_is_called_before_parity_and_fromhex_only_for_valid_language(monkeypatch, text):
    original = codec.re.fullmatch
    matcher_calls, fromhex_calls = [], []
    def match(pattern, string, flags=0):
        matcher_calls.append(string)
        return original(pattern, string, flags)
    class RecordingBytes:
        @staticmethod
        def fromhex(string):
            fromhex_calls.append(string)
            return bytes.fromhex(string)
    # _decode itself isolates the ingress calls from canonical re-encoding's
    # isinstance(bytes) use. Public failures/roundtrips are checked above.
    monkeypatch.setattr(codec.re, 'fullmatch', match)
    monkeypatch.setattr(codec, 'bytes', RecordingBytes, raising=False)
    if accepted(text):
        assert codec._decode({'$bytes': text}) == bytes.fromhex(text)
    else:
        with pytest.raises(ValueError):
            codec._decode({'$bytes': text})
    assert matcher_calls == [text]
    assert fromhex_calls == ([text] if accepted(text) else [])
