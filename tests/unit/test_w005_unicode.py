"""IPMR-01: document strings are Unicode scalars before schema/key checks."""
from __future__ import annotations

import json

import pytest
import yaml

from layauto_v2.domain.codec import canonical_bytes, digest, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.config import load_document, validate_document


@pytest.mark.parametrize('text', [
    '\U00010000', '\U0001f600', '\U0010ffff',
    'before 字\U0001f600\U00010000 after',
])
def test_surrogate_pairs_in_nested_keys_and_values_match_utf8(text):
    expected = {'nested': [{text: text}]}
    escaped = SourceFile('escaped.json', json.dumps(expected, ensure_ascii=True).encode())
    literal = SourceFile('literal.json', json.dumps(expected, ensure_ascii=False).encode())
    assert escaped.data != literal.data
    assert escaped.sha256 != literal.sha256
    decoded = load_document(escaped)
    assert decoded == load_document(literal) == freeze_map(expected)
    assert canonical_bytes(decoded) == canonical_bytes(expected)
    assert digest(decoded) == digest(expected)


@pytest.mark.parametrize('escaped', [
    r'\ud800', r'\udfff', r'\udc00\ud800', r'\ud800\ud800',
    r'\ud800x', r'\ud800\u0041', r'\ud800\udc00\ud800',
    r'\ud800\udc00\udfff',
])
@pytest.mark.parametrize('position', ['key', 'value'])
def test_invalid_surrogates_are_located_input_errors(escaped, position):
    line = f'  "{escaped}": 1' if position == 'key' else f'  "key": "{escaped}"'
    source = SourceFile('invalid.json', ('{\n' + line + '\n}').encode())
    with pytest.raises(InputError) as caught:
        load_document(source)
    issue = caught.value.issue
    assert issue.code == 'InvalidUnicodeScalar'
    assert issue.category == 'config'
    assert issue.source == source.ref(line=2, column=3 if position == 'key' else 10)


@pytest.mark.parametrize('reverse', [False, True])
def test_duplicate_keys_are_checked_after_surrogate_decoding(reverse):
    keys = [r'\ud83d\ude00', '\U0001f600']
    if reverse:
        keys.reverse()
    raw = ('{"nested": {\n  "' + keys[0] + '": 1,\n  "' + keys[1] + '": 2\n}}').encode()
    source = SourceFile('duplicate.json', raw)
    with pytest.raises(InputError) as caught:
        load_document(source)
    assert caught.value.issue.code == 'DuplicateKey'
    assert caught.value.issue.source == source.ref(line=3, column=3)


def test_yaml_and_literal_backslash_semantics_are_preserved():
    source = SourceFile('strings.yaml', b'"\\uD83D\\uDE00": "\\U0001F600"\nliteral: \'\\ud800\'\n')
    assert load_document(source) == freeze_map({'\U0001f600': '\U0001f600', 'literal': r'\ud800'})
    maximum = SourceFile('maximum.yaml', b'{"\\U0010FFFF": "\\U0010FFFF"}')
    assert load_document(maximum) == freeze_map({'\U0010ffff': '\U0010ffff'})


def test_decoded_key_still_reaches_closed_schema_validation():
    source = SourceFile('site.json', b'{"\\ud83d\\ude00": 1}')
    with pytest.raises(InputError) as caught:
        validate_document(load_document(source), 'site', source)
    assert caught.value.issue.code == 'UnknownKey'
    assert caught.value.issue.source == source.ref(field='/\U0001f600')


@pytest.mark.parametrize('escaped', [r'\U00110000', r'\UFFFFFFFF'])
@pytest.mark.parametrize('position', ['key', 'value'])
def test_out_of_range_yaml_escapes_are_located_syntax_errors(escaped, position):
    line = f'  "{escaped}": 1' if position == 'key' else f'  "key": "{escaped}"'
    source = SourceFile('out-of-range.yaml', ('{\n' + line + '\n}').encode())
    with pytest.raises(InputError) as caught:
        load_document(source)
    issue = caught.value.issue
    assert issue.category == 'parse' and issue.code == 'InvalidDocumentSyntax'
    assert issue.source == source.ref(line=2, column=line.index(escaped) + 3)
    assert 'U+10FFFF' in issue.message


@pytest.mark.parametrize('failure', [ValueError, OverflowError, RuntimeError, KeyboardInterrupt, SystemExit])
def test_unexpected_scanner_errors_and_interrupts_propagate(monkeypatch, failure):
    original = failure('scanner-root-cause')

    def broken(*args, **kwargs):
        raise original

    monkeypatch.setattr(yaml.SafeLoader, 'scan_flow_scalar_non_spaces', broken)
    with pytest.raises(failure) as caught:
        load_document(SourceFile('valid.json', b'{"key": "value"}'))
    assert caught.value is original
