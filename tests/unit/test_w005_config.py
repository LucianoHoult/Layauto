"""Tests for actual byte parsing, closed schemas, and tech reference contracts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from layauto_v2.domain.codec import FrozenMap, freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.config import load_document, validate_document, validate_tech

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'w003_m1'
OWNERS = ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')
DOCUMENTS = {
    'site': 'site_config.yaml', 'tech': 'tech.json', 'export_policy': 'export_policy.json',
    'validation_policy': 'validation_policy.json', 'limitations': 'limitations.json',
    'header': 'query/header.json', 'body': 'body/context.json',
    'requests': 'query/requests.json', 'dialect': 'query/dialect.json',
    **{name: f'tech/{name}.json' for name in OWNERS},
}


def source_for(kind: str) -> SourceFile:
    path = DOCUMENTS[kind]
    return SourceFile(path, (FIXTURE / path).read_bytes())


def document(kind: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads(source_for(kind).data))


def mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def items(value: object) -> list[object]:
    assert isinstance(value, list)
    return value


def validate_mutation(kind: str, value: dict[str, object]) -> None:
    raw = SourceFile(DOCUMENTS[kind], json.dumps(value).encode())
    validate_document(load_document(raw), kind, raw)


def tech_documents() -> tuple[dict[str, object], dict[str, SourceFile]]:
    docs: dict[str, object] = {kind: document(kind) for kind in OWNERS}
    sources = {kind: source_for(kind) for kind in OWNERS}
    return docs, sources


@pytest.mark.parametrize('kind', DOCUMENTS)
def test_every_declared_document_is_safe_and_schema_valid(kind: str) -> None:
    raw = source_for(kind)
    value = load_document(raw)
    assert isinstance(value, FrozenMap)
    validate_document(value, kind, raw)


def test_six_owners_cross_validate() -> None:
    docs, sources = tech_documents()
    validate_tech(freeze_map(docs), sources)


@pytest.mark.parametrize(('raw', 'code'), [
    (b'a: 1\na: 2\n', 'DuplicateKey'),
    (b'{"a":{"b":1,"b":2}}', 'DuplicateKey'),
    (b'1: value\n', 'InvalidKeyType'),
    (b'a: .nan\n', 'NonExactNumber'),
    (b'a: .inf\n', 'NonExactNumber'),
    (b'{"a":1e50}', 'NonExactNumber'),
    (b'{"a":NaN}', 'NonExactNumber'),
    (b'{"a":1.25}', 'NonExactNumber'),
    (b'a: !!python/object/apply:os.system ["touch /tmp/w005-unwanted"]\n', 'UnsupportedTag'),
    (b'a: !unregistered foo\n', 'UnsupportedTag'),
    (b'a: &x [1]\nb: *x\n', 'UnsupportedAlias'),
    (b'a: 2026-01-01\n', 'UnsupportedTag'),
    (b'a: yes\n', 'InvalidBoolean'),
    (b'a: 0x10\n', 'InvalidInteger'),
    (b'a: +2\n', 'InvalidInteger'),
    (b'[]\n', 'InvalidRootType'),
    (b'', 'EmptyDocument'),
    (b'\xff', 'InvalidEncoding'),
    (b'a: [\n', 'InvalidDocumentSyntax'),
])
def test_safe_parse_rejects_unsupported_bytes(raw: bytes, code: str) -> None:
    source = SourceFile('bad.yaml', raw)
    with pytest.raises(InputError) as caught:
        load_document(source)
    assert caught.value.issue.code == code
    assert caught.value.issue.source.sha256 == source.sha256
    assert caught.value.issue.source.uri == 'bad.yaml'


def test_size_is_measured_in_bytes_including_whitespace() -> None:
    exact = b'a: 1\n' + b' ' * (1_000_000 - len(b'a: 1\n'))
    assert load_document(SourceFile('large.yaml', exact))['a'] == 1
    with pytest.raises(InputError, match='bytes') as caught:
        load_document(SourceFile('large.yaml', exact + b' '))
    assert caught.value.issue.code == 'SizeLimitExceeded'
    multibyte = 'a: "é"\n'.encode()
    assert load_document(SourceFile('utf8.yaml', multibyte), max_bytes=len(multibyte))['a'] == 'é'
    with pytest.raises(InputError):
        load_document(SourceFile('utf8.yaml', multibyte), max_bytes=len(multibyte) - 1)


def test_depth_counts_containers_root_one_and_scalar_no_extra_level() -> None:
    depth32 = b'{"a":' + b'[' * 31 + b'0' + b']' * 31 + b'}'
    load_document(SourceFile('depth.json', depth32))
    depth33 = b'{"a":' + b'[' * 32 + b'0' + b']' * 32 + b'}'
    with pytest.raises(InputError) as caught:
        load_document(SourceFile('depth.json', depth33))
    assert caught.value.issue.code == 'DepthLimitExceeded'
    assert load_document(SourceFile('depth.yaml', b'a: 1\n'), max_depth=1)['a'] == 1
    with pytest.raises(InputError):
        load_document(SourceFile('depth.yaml', b'a: []\n'), max_depth=1)


@pytest.mark.parametrize('limits', [{'max_bytes': 1_000_001}, {'max_bytes': True}, {'max_depth': 33}, {'max_depth': 0}])
def test_loader_limits_cannot_widen_bootstrap_schema(limits: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        load_document(SourceFile('a.yaml', b'a: 1\n'), **limits)


@pytest.mark.parametrize(('kind', 'path'), [
    ('site', ('tool',)), ('tech', ('owners', 'drawn')), ('drawn', ('layers', 0, 'stream_key')),
    ('physical', ('models', 'TOY_N', 'parameter_axes')), ('formats', ('unit_scale_contract', 'nominal_source')),
    ('rules', ('rules', 0, 'parameters')), ('header', ('closure', 'entries', 0)),
    ('body', ('associations', 0)), ('requests', ('requests', 0)), ('dialect', ('geometry',)),
    ('export_policy', ('required_artifacts', 0)), ('validation_policy', ('check_obligations', 0)),
    ('limitations', ('production_checks',)),
])
def test_nested_unknown_keys_are_rejected(kind: str, path: tuple[str | int, ...]) -> None:
    value = document(kind)
    node: object = value
    for key in path:
        node = items(node)[key] if isinstance(key, int) else mapping(node)[key]
    mapping(node)['unrecognized'] = 'must fail'
    with pytest.raises(InputError) as caught:
        validate_mutation(kind, value)
    assert caught.value.issue.code == 'UnknownKey'
    assert caught.value.issue.source.field is not None
    assert caught.value.issue.source.field.endswith('/unrecognized')


def test_version_type_missing_and_exact_failures() -> None:
    value = document('site')
    value['schema_version'] = 'w003-site/999'
    with pytest.raises(InputError):
        validate_mutation('site', value)
    value = document('formats')
    mapping(value['limits'])['max_records'] = True
    with pytest.raises(InputError, match='integer'):
        validate_mutation('formats', value)
    value = document('formats')
    del mapping(value['unit_scale_contract'])['nominal_tick_m']
    with pytest.raises(InputError) as caught:
        validate_mutation('formats', value)
    assert caught.value.issue.code == 'MissingField'
    value = document('formats')
    mapping(value['unit_scale_contract'])['nominal_tick_m'] = {'numerator': '2', 'denominator': '2000000000'}
    with pytest.raises(InputError) as caught:
        validate_mutation('formats', value)
    assert caught.value.issue.code == 'InvalidExactValue'


@pytest.mark.parametrize(('field', 'ceiling'), [('max_records', 1000), ('max_bytes_per_text_file', 1_000_000), ('max_json_depth', 32)])
def test_declared_profile_limits_exact_boundary(field: str, ceiling: int) -> None:
    value = document('formats')
    mapping(value['limits'])[field] = ceiling
    validate_mutation('formats', value)
    mapping(value['limits'])[field] = ceiling + 1
    with pytest.raises(InputError) as caught:
        validate_mutation('formats', value)
    assert caught.value.issue.code == 'InvalidLimit'


@pytest.mark.parametrize('mutation', ['unit', 'model', 'owner', 'duplicate_owner', 'registry', 'stream_key', 'operator', 'rule'])
def test_cross_field_contract_conflicts(mutation: str) -> None:
    docs, sources = tech_documents()
    if mutation == 'unit':
        formats = mapping(docs['formats'])
        mapping(formats['unit_scale_contract'])['canonical_tick_nm'] = 2
    elif mutation == 'model':
        physical = mapping(docs['physical'])
        mapping(mapping(physical['models'])['TOY_N'])['required_parameters'] = ['NFIN']
    elif mutation in ('owner', 'duplicate_owner'):
        value = document('tech')
        owners = mapping(value['owners'])
        if mutation == 'owner':
            mapping(owners['drawn'])['keys'] = ['derived_registry']
        else:
            mapping(owners['derived'])['path'] = mapping(owners['drawn'])['path']
        with pytest.raises(InputError) as caught:
            validate_mutation('tech', value)
        assert caught.value.issue.code == 'OwnerConflict'
        return
    elif mutation == 'registry':
        derived = mapping(docs['derived'])
        mapping(items(derived['derived_registry'])[0])['target_layer'] = 'LI'
    elif mutation == 'stream_key':
        layers = items(mapping(docs['drawn'])['layers'])
        mapping(layers[1])['stream_key'] = mapping(layers[0])['stream_key']
    elif mutation == 'operator':
        del mapping(mapping(docs['physical'])['operators'])['body_context/2']
    elif mutation == 'rule':
        rules = items(mapping(docs['rules'])['rules'])
        mapping(rules[0])['parameters'] = {'min_distance_nm': 2}
    with pytest.raises(InputError) as caught:
        validate_tech(freeze_map(docs), sources)
    assert caught.value.issue.source.field
    if mutation == 'operator':
        assert caught.value.issue.code == 'RequiredBodyOperatorUnavailable'


def test_unknown_status_is_preserved_for_binding_policy() -> None:
    value = document('header')
    value['lvs_completion_status'] = value['lvs_match_status'] = 'unknown'
    validate_mutation('header', value)
    value = document('body')
    value['lvs_status'] = 'unknown'
    validate_mutation('body', value)


def test_loader_does_not_keep_mutable_aliases() -> None:
    original = {'nested': {'values': [1, 2]}}
    raw = SourceFile('immutable.json', json.dumps(original).encode())
    loaded = load_document(raw)
    original['nested']['values'][0] = 99
    assert loaded['nested'] == freeze_map({'values': [1, 2]})
