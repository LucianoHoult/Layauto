"""A2/A6: exact immutable neutral DTO and dependency boundary contracts."""
from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from fractions import Fraction
from pathlib import Path

import pytest

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode, digest, freeze, freeze_map, rational
from layauto_v2.domain.evidence import EvidenceRecord, SourceFile, SourceRef
from layauto_v2.domain.results import EvidenceIssue, ParseResult


REPO = Path(__file__).resolve().parents[2]


def test_codec_has_stable_canonical_roundtrip_and_sha256():
    original = {'fraction': Fraction(-17, 20), 'bytes': b'\x00\xff', 'nested': [None, True, 7, {'字': '值'}]}
    encoded = canonical_bytes(original)
    assert decode(encoded) == freeze(original)
    assert canonical_bytes(decode(encoded)) == encoded
    assert digest(original) == hashlib.sha256(encoded).hexdigest()
    assert digest(original) == digest(dict(reversed(list(original.items()))))
    assert digest([1, 2]) != digest([2, 1])
    assert digest({'value': Fraction(1, 1)}) != digest({'value': 1})


def test_codec_digest_is_stable_in_fresh_processes():
    program = "from fractions import Fraction; from layauto_v2.domain.codec import digest; print(digest({'x':Fraction(1,20),'name':'坐标','a':[2,1]}))"
    outputs = []
    for seed in ('1', '987654'):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outputs.append(subprocess.check_output([sys.executable, '-B', '-c', program], cwd=REPO, env=env, text=True).strip())
    assert outputs[0] == outputs[1] == digest({'x': Fraction(1, 20), 'name': '坐标', 'a': [2, 1]})


@pytest.mark.parametrize('value', [
    {'numerator': '2', 'denominator': '4'},
    {'numerator': '1', 'denominator': '-2'},
    {'numerator': '1', 'denominator': '0'},
    {'numerator': '-0', 'denominator': '1'},
    {'numerator': '01', 'denominator': '1'},
    {'numerator': '+1', 'denominator': '1'},
    {'numerator': '1', 'denominator': '01'},
    {'numerator': 1, 'denominator': '2'},
    {'numerator': '1', 'denominator': 2},
    {'numerator': '1', 'denominator': '2', 'extra': 1},
])
def test_rational_rejects_noncanonical_exact_representation(value):
    with pytest.raises(ValueError):
        rational(value)


@pytest.mark.parametrize('data', [
    b'1.0', b'NaN', b'Infinity', b'-Infinity', b'{"a":1}',
    b'{"$map":{"a":1,"a":2}}', b'{"$bytes":"FF"}',
    b'{"$rational":{"numerator":"2","denominator":"4"}}',
    b'{"$rational":{"denominator":"1","numerator":"-0"}}',
    b'{"$map":{}}\n', b'{ "$map": {} }',
])
def test_codec_rejects_float_ambiguous_or_noncanonical_wire(data):
    with pytest.raises(ValueError):
        decode(data)


@pytest.mark.parametrize('value', [0.1, float('nan'), float('inf'), {1: 'one'}, object(), {'x': [0.1]}])
def test_canonical_truth_rejects_floats_and_implicit_coercion(value):
    with pytest.raises(ValueError):
        canonical_bytes(value)


def test_nested_freeze_and_records_retain_no_mutable_alias():
    original = {'list': [{'a': 1}], 'fraction': Fraction(1, 20)}
    frozen = freeze_map(original)
    original['list'][0]['a'] = 99
    original['list'].append({'b': 2})
    assert frozen['list'][0]['a'] == 1 and len(frozen['list']) == 1
    with pytest.raises((TypeError, FrozenInstanceError, AttributeError)):
        frozen['list'][0]['a'] = 8
    with pytest.raises((FrozenInstanceError, AttributeError)):
        frozen._entries = ()
    source = SourceFile('source.cdl', b'actual source bytes')
    refs = [source.ref(line=1, column=1)]
    evidence = EvidenceRecord('cdl', frozen, refs)
    refs.clear()
    assert len(evidence.sources) == 1
    values = {'payload': [{'x': 1}]}
    result = ParseResult('success', values, (), [evidence], [source])
    values['payload'][0]['x'] = 9
    assert result.value['payload'][0]['x'] == 1
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.status = 'error'


def test_source_bytes_hash_and_location_validation():
    source = SourceFile('input.bin', b'\x00\xff')
    assert source.sha256 == hashlib.sha256(source.data).hexdigest()
    assert source.ref(byte_offset=0, record_index=0).sha256 == source.sha256
    assert SourceRef('missing.bin').sha256 is None
    with pytest.raises(ValueError):
        SourceFile('input.bin', bytearray(b'mutable'))
    with pytest.raises(ValueError):
        SourceRef('missing.bin', line=1)
    for kwargs in ({'line': 0}, {'column': True}, {'byte_offset': -1}, {'record_index': False}):
        with pytest.raises(ValueError):
            source.ref(**kwargs)
    with pytest.raises(ValueError):
        SourceRef('input', 'not-sha256')


@pytest.mark.parametrize('status,value,with_issues', [
    ('success', None, False), ('success', {}, True), ('error', {}, True),
    ('error', None, False), ('unknown', {}, False),
])
def test_parse_result_rejects_illegal_discriminator_combinations(status, value, with_issues):
    issue = EvidenceIssue('read', 'MissingInput', 'not found', SourceRef('missing'))
    with pytest.raises(ValueError):
        ParseResult(status, value, (issue,) if with_issues else (), (), ())


def test_runtime_record_versions_fields_and_tool_link_validate():
    source = SourceFile('actual', b'')
    with pytest.raises(ValueError):
        EvidenceRecord('cdl', FrozenMap({}), (SourceRef('unread'),))
    with pytest.raises(ValueError):
        EvidenceRecord('cdl', FrozenMap({}), (source.ref(),), schema_version='future/2')
    with pytest.raises(ValueError):
        EvidenceIssue('validation', 'Bad', 'wrong owner', source.ref())
    with pytest.raises(ValueError):
        ParseResult('success', FrozenMap({}), (), (), (), tool_run_id='')
    result = ParseResult('success', FrozenMap({}), (), (), (), tool_run_id='external-execution-id')
    assert result.tool_run_id == 'external-execution-id'
    assert not hasattr(result, 'tool_result') and not hasattr(result, 'execution_status')


def test_importer_and_domain_dependency_direction():
    violations = []
    for root in ('layauto_v2/importers', 'layauto_v2/domain', 'layauto_v2/tech'):
        directory = REPO / root
        if not directory.exists():
            continue
        for path in directory.rglob('*.py'):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                imported = []
                if isinstance(node, ast.Import):
                    imported = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported = [node.module or '']
                for module in imported:
                    if module.startswith(('legacy_mvp', 'tests.support')):
                        violations.append((str(path), module))
                    if '/importers' in root and module.startswith(('layauto_v2.tooling', 'layauto_v2.state', 'layauto_v2.normalization', 'layauto_v2.pipeline')):
                        violations.append((str(path), module))
                    if '/domain' in root and module.startswith(('pathlib', 'io', 'os', 'subprocess', 'layauto_v2.importers', 'layauto_v2.tech')):
                        violations.append((str(path), module))
    assert not violations
