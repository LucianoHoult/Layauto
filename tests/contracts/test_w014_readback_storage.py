"""Real W006 default storage is compatible with W014's closed graph guard."""
from dataclasses import fields, replace

import pytest

from layauto_v2.domain import publication_codec
from layauto_v2.domain.publication import InputsReady
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from layauto_v2.normalization.contracts import ReadbackBinding
from layauto_v2.normalization.local_connectivity_codec import _ALL_TYPES
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE
from w006_cases import caller_request


@pytest.fixture(scope='module')
def actual_readback():
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w014-default-storage'))
    assert isinstance(ready, InputsReady)
    binding = ReadbackBinding(ready, repository.load_checkpoint(ready.run_id),
                              repository.read(ready.parse_ref), repository.read(ready.tool_ref),
                              tuple(repository.read(ref) for ref in ready.evidence_refs))
    return binding


def test_real_readback_accepts_unchanged_class_default_discriminators_without_mutation(actual_readback):
    binding = actual_readback
    records = (binding.ready.attempt, binding.ready.attempt.request, binding.checkpoint,
               binding.parse_audit, binding.tool_run, binding.evidence_audits[0])
    expected = ('attempt', 'request', 'checkpoint', 'parse', 'tool_run', 'evidence')
    before = tuple(publication_codec.encode_record(record) for record in records)
    for record, kind in zip(records, expected):
        declaration = next(member for member in fields(record) if member.name == 'kind')
        assert declaration.init is False
        assert 'kind' not in vars(record)
        assert declaration.default == getattr(type(record), 'kind') == record.kind == kind
    validate_terminal_graph(binding, _ALL_TYPES)
    assert tuple(publication_codec.encode_record(record) for record in records) == before
    assert all('kind' not in vars(record) for record in records)


def test_readback_guard_still_rejects_missing_required_instance_fields(actual_readback):
    attempt = replace(actual_readback.ready.attempt)
    object.__delattr__(attempt, 'request')
    with pytest.raises(ValueError):
        validate_terminal_graph(attempt, _ALL_TYPES)


def test_readback_guard_still_rejects_extra_mutable_instance_fields(actual_readback):
    attempt = replace(actual_readback.ready.attempt)
    object.__setattr__(attempt, 'undeclared_extra', [])
    with pytest.raises(ValueError, match='undeclared retained fields'):
        validate_terminal_graph(attempt, _ALL_TYPES)


def test_readback_guard_checks_actual_default_values_for_mutable_storage(actual_readback, monkeypatch):
    attempt = replace(actual_readback.ready.attempt)
    monkeypatch.setattr(type(attempt), 'kind', ['attempt'])
    with pytest.raises(ValueError):
        validate_terminal_graph(attempt, _ALL_TYPES)


def test_readback_guard_does_not_allow_missing_class_fallbacks(actual_readback, monkeypatch):
    attempt = replace(actual_readback.ready.attempt)
    monkeypatch.delattr(type(attempt), 'kind')
    with pytest.raises(ValueError):
        validate_terminal_graph(attempt, _ALL_TYPES)
