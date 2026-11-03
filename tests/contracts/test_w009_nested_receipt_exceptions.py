"""W009 reaches the complete semantic receipt reconstruction boundary.

These controls use real W005 and W006 captures. Faults occur only after a valid
wire is built; malformed receipts are separate explicit input controls.
"""
from dataclasses import replace
from unittest.mock import patch

import pytest

from layauto_v2.domain import publication_codec
from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, from_inputs_ready, from_parse_result,
    geometry_from_normalization_input,
)
from layauto_v2.normalization import codec as semantic_codec
from layauto_v2.normalization import contracts
from layauto_v2.normalization.effective_codec import decode_record, encode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE
from w007_cases import mutable, read


@pytest.fixture(scope='module')
def receipts():
    parsed = read(FIXTURE)
    direct = from_parse_result(parsed)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w009-receipt-exceptions', lineage_id='w009-receipt-lineage',
        idempotency_key='w009-receipt-create', site_path=str((FIXTURE / 'site_config.yaml').resolve())))
    assert isinstance(ready, InputsReady)
    readback = from_inputs_ready(
        ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
        repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
    values = {'direct': direct, 'readback': readback}
    wires = {}
    for name, value in values.items():
        result = build_effective_geometry(build_geometry(geometry_from_normalization_input(value)))
        assert result.status == 'success'
        wires[name] = encode_record(result)
    return values, wires


TARGETS = (
    'layauto_v2.normalization.contracts.request_decoder_input',
    'layauto_v2.normalization._validation._validate_cdl',
    'layauto_v2.normalization._validation._validate_query',
    'layauto_v2.normalization.contracts.content_ref',
)
FAILURES = (RuntimeError, ValueError, TypeError, KeyError, AttributeError,
            IndexError, UnicodeError, KeyboardInterrupt, SystemExit)


def failure_with_history(cls):
    failure = cls('unexpected receipt reconstruction failure')
    cause, context = RuntimeError('existing cause'), LookupError('existing context')
    failure.__cause__, failure.__context__ = cause, context
    failure.__suppress_context__ = False
    return failure, cause, context


@pytest.mark.parametrize('target', TARGETS)
@pytest.mark.parametrize('cls', FAILURES)
def test_receipt_reconstruction_preserves_exception_and_existing_history(receipts, target, cls):
    values, _ = receipts
    receipt = values['readback'] if target.endswith('content_ref') else values['direct']
    failure, cause, context = failure_with_history(cls)
    def broken(*args, **kwargs):
        raise failure
    with patch(target, broken), pytest.raises(cls) as raised:
        replace(receipt.readback) if target.endswith('content_ref') else replace(receipt)
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is False


@pytest.mark.parametrize('name,target', [
    (name, target) for name in ('direct', 'readback') for target in TARGETS
    if name == 'readback' or not target.endswith('content_ref')
])
def test_w009_result_wire_reaches_receipt_boundary_without_exception_translation(receipts, name, target):
    _, wires = receipts
    failure, cause, context = failure_with_history(TypeError)
    def broken(*args, **kwargs):
        raise failure
    with patch(target, broken), pytest.raises(TypeError) as raised:
        decode_record(wires[name])
    assert raised.value is failure
    assert failure.__cause__ is cause and failure.__context__ is context
    assert failure.__suppress_context__ is False


def forged_parse(parsed, change):
    value = mutable(parsed.value)
    if change == 'missing_formats': value['tech'].pop('formats')
    elif change == 'missing_limits': value['tech']['formats'].pop('limits')
    elif change == 'scalar_limits': value['tech']['formats']['limits'] = 1
    elif change == 'collection_limit': value['tech']['formats']['limits']['max_json_depth'] = []
    elif change == 'missing_model': value['tech']['physical']['models']['TOY_N'].pop('terminal_order')
    elif change == 'nested_required_parameter': value['tech']['physical']['models']['TOY_N']['required_parameters'][0] = {}
    elif change == 'missing_top_field': value['source_cdl']['tops'][0].pop('pins')
    elif change == 'extra_top_field': value['source_cdl']['tops'][0]['extra'] = 1
    elif change == 'nested_pin': value['source_cdl']['tops'][0]['pins'][0] = {}
    elif change == 'unknown_model': value['source_cdl']['tops'][0]['devices'][0]['model'] = 'absent-model'
    elif change == 'missing_lexeme': value['source_cdl']['tops'][0]['field_sources']['name'].pop('lexeme')
    elif change == 'missing_layout': value['header'].pop('layout')
    elif change == 'collection_raw_ref': value['query']['device_regions']['raw_refs'][0]['path'] = {}
    elif change == 'missing_records': value['query']['device_regions'].pop('records')
    elif change == 'missing_responses': value['query']['_format_metadata'].pop('responses')
    elif change == 'blank_count_header':
        header = value['query']['_format_metadata']['responses'][0]['count_header']
        header['lexeme'] = ' '
        header.pop('token_0based', None)
        header.pop('column', None)
    else: raise AssertionError(change)
    completed = tuple(replace(record, payload=(
        {'bundle': value['tech_bundle'], 'owners': value['tech']} if record.kind == 'tech'
        else value[record.kind])) for record in parsed.completed)
    return replace(parsed, value=value, completed=completed)


@pytest.mark.parametrize('change', [
    'missing_formats', 'missing_limits', 'scalar_limits', 'collection_limit',
    'missing_model', 'nested_required_parameter', 'missing_top_field', 'extra_top_field',
    'nested_pin', 'unknown_model', 'missing_lexeme', 'missing_layout',
    'collection_raw_ref', 'missing_records', 'missing_responses', 'blank_count_header',
])
def test_malformed_receipt_fields_still_raise_explicit_value_error(receipts, change):
    values, _ = receipts
    original = values['direct']
    parsed = forged_parse(original.parse, change)
    with pytest.raises(ValueError):
        contracts.NormalizationInput(parsed)
    tree = mutable(decode(semantic_codec.encode_record(original)))
    tree['record']['fields']['parse'] = {'captured_record': publication_codec.encode_record(parsed)}
    with pytest.raises(ValueError):
        semantic_codec.decode_record(canonical_bytes(tree))
