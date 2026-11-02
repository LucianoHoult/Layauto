"""IPMR-01 public API regressions use only temporary input copies."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from layauto_v2.domain.codec import canonical_bytes, digest
from layauto_v2.importers import read_inputs
from w005_cases import copy_input, read_json, rebind


@pytest.mark.parametrize('position', ['key', 'value'])
@pytest.mark.parametrize('invalid', ['\ud800', '\udfff', '\udc00\ud800', '\ud800x'])
def test_invalid_cache_unicode_retains_bytes_hash_location_and_completed(tmp_path, position, invalid):
    root = copy_input(tmp_path)
    path = root / 'query/normalized/device_regions.yaml'
    cache = read_json(path)
    if position == 'key':
        cache[invalid] = cache.pop('schema_version')
    else:
        cache['schema_version'] = invalid
    # Exactly the original report's cache mutation for value/high-surrogate.
    path.write_text(json.dumps(cache) + '\n', encoding='utf-8')
    raw = path.read_bytes()
    result = read_inputs(root / 'site_config.yaml', tool_run_id='unicode-regression')
    assert result.status == 'error' and result.value is None
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.code == 'InvalidUnicodeScalar' and issue.category == 'config'
    assert Path(issue.source.uri) == path
    token = json.dumps(invalid)
    assert (issue.source.line, issue.source.column) == (1, raw.decode().index(token) + 1)
    captured = next(source for source in result.sources if source.uri == issue.source.uri)
    assert captured.data == raw
    assert captured.sha256 == issue.source.sha256 == hashlib.sha256(raw).hexdigest()
    assert result.tool_run_id == 'unicode-regression'
    assert [record.kind for record in result.completed] == [
        'config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query',
    ]
    sources = {source.uri: source.sha256 for source in result.sources}
    for record in result.completed:
        assert all(sources[ref.uri] == ref.sha256 for ref in record.sources)
        assert len(digest(record.payload)) == 64


def test_escaped_and_literal_config_notes_have_equal_semantics_and_digestible_evidence(tmp_path):
    root = copy_input(tmp_path)
    path = root / 'site_config.yaml'
    site = read_json(path)
    site['note'] = 'example \U0001f600'
    configs = []
    source_hashes = []
    for escaped in (True, False):
        path.write_text(json.dumps(site, ensure_ascii=escaped) + '\n', encoding='utf-8')
        rebind(root)
        result = read_inputs(path)
        assert result.status == 'success', result.issues
        assert result.value is not None
        assert result.value['config']['note'] == site['note']
        assert len(digest(result.value)) == 64
        for record in result.completed:
            assert len(digest(record.payload)) == 64
        config_record = next(record for record in result.completed if record.kind == 'config')
        assert config_record.payload == result.value['config']
        configs.append(canonical_bytes(config_record.payload))
        captured = next(source for source in result.sources if Path(source.uri).name == 'site_config.yaml')
        assert captured.data == path.read_bytes()
        assert captured.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
        source_hashes.append(captured.sha256)
    assert configs[0] == configs[1]
    assert source_hashes[0] != source_hashes[1]


def test_cache_duplicate_decoded_key_is_not_silently_overwritten(tmp_path):
    root = copy_input(tmp_path)
    path = root / 'query/normalized/device_regions.yaml'
    raw = '{\n  "\\ud83d\\ude00": 1,\n  "\U0001f600": 2\n}\n'.encode()
    path.write_bytes(raw)
    result = read_inputs(root / 'site_config.yaml')
    assert result.status == 'error'
    issue = result.issues[0]
    assert issue.code == 'DuplicateKey'
    assert Path(issue.source.uri) == path
    assert (issue.source.line, issue.source.column) == (3, 3)
    assert issue.source.sha256 == hashlib.sha256(raw).hexdigest()
    assert next(source for source in result.sources if source.uri == issue.source.uri).data == raw
    assert len(result.completed) == 9 and result.completed[-1].kind == 'query'


@pytest.mark.parametrize('escaped', [r'\U00110000', r'\UFFFFFFFF'])
@pytest.mark.parametrize('position', ['key', 'value'])
def test_out_of_range_cache_escape_retains_typed_failure_evidence(tmp_path, escaped, position):
    root = copy_input(tmp_path)
    path = root / 'query/normalized/device_regions.yaml'
    cache = read_json(path)
    if position == 'key':
        cache['UNICODE_MARKER'] = cache.pop('schema_version')
    else:
        cache['schema_version'] = 'UNICODE_MARKER'
    raw = (json.dumps(cache).replace('UNICODE_MARKER', escaped) + '\n').encode()
    path.write_bytes(raw)
    result = read_inputs(root / 'site_config.yaml')
    assert result.status == 'error' and result.value is None
    issue = result.issues[0]
    assert issue.code == 'InvalidDocumentSyntax' and issue.category == 'parse'
    assert Path(issue.source.uri) == path
    assert (issue.source.line, issue.source.column) == (1, raw.decode().index(escaped) + 3)
    assert issue.source.sha256 == hashlib.sha256(raw).hexdigest()
    assert next(source for source in result.sources if source.uri == issue.source.uri).data == raw
    assert [record.kind for record in result.completed] == [
        'config', 'tech', 'policies', 'header', 'gds', 'source_cdl', 'target_cdl', 'body', 'query',
    ]
    for record in result.completed:
        assert len(digest(record.payload)) == 64
