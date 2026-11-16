"""New-boundary evidence-shell validation uses unchanged public constructors."""
from dataclasses import replace

import pytest

from layauto_v2.domain import publication_codec
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from layauto_v2.importers import read_inputs
from w005_cases import FIXTURE


@pytest.fixture(scope='module')
def actual_evidence():
    parsed = read_inputs(FIXTURE / 'site_config.yaml')
    assert parsed.status == 'success'
    body = next(record for record in parsed.completed if record.kind == 'body')
    tech = next(record for record in parsed.completed if record.kind == 'tech')
    owners = {'body': body}
    for name in ('physical', 'rules'):
        source = next(source for source in tech.sources if source.uri.endswith('tech/' + name + '.json'))
        owners[name] = EvidenceRecord(name, parsed.value['tech'][name], (source,))
    assert len(body.sources) == 2
    return owners


def test_real_body_and_owner_evidence_preserve_complete_old_wire_and_storage(actual_evidence):
    for record in actual_evidence.values():
        before = publication_codec.encode_record(record)
        payload, sources = record.payload, record.sources
        validate_terminal_graph(record, (EvidenceRecord,))
        assert record.payload is payload and record.sources is sources
        restored = publication_codec.decode_record(before)
        assert restored == record and publication_codec.encode_record(restored) == before
    # A neutral SourceRef without acquired bytes remains a valid old value;
    # EvidenceRecord itself still requires captured source hashes.
    unacquired = SourceRef('unacquired.input')
    validate_terminal_graph(unacquired)
    assert publication_codec.decode_record(publication_codec.encode_record(unacquired)) == unacquired


@pytest.mark.parametrize('owner', ['body', 'physical', 'rules'])
@pytest.mark.parametrize('metadata', ['schema_version', 'parser_version'])
def test_cr12_retained_evidence_metadata_reenters_the_unchanged_public_constructor(actual_evidence, owner, metadata):
    shell = replace(actual_evidence[owner])
    object.__setattr__(shell, metadata, 'unrecognized-evidence-version/99')
    with pytest.raises(ValueError, match='evidence discriminator/version'):
        validate_terminal_graph(shell, (EvidenceRecord,))


@pytest.mark.parametrize(('index', 'field_name', 'value'), [
    (0, 'sha256', 'invalid_hash'), (1, 'uri', ''), (0, 'field', True),
    (1, 'line', True), (0, 'byte_offset', -1), (1, 'record_index', -1),
])
def test_both_body_source_roles_reconstruct_all_original_source_fields(actual_evidence, index, field_name, value):
    body = actual_evidence['body']
    source = replace(body.sources[index])
    object.__setattr__(source, field_name, value)
    sources = list(body.sources)
    sources[index] = source
    shell = replace(body, sources=tuple(sources))
    with pytest.raises(ValueError):
        validate_terminal_graph(shell, (EvidenceRecord,))


def test_original_storage_is_checked_before_any_evidence_constructor_copies(actual_evidence, monkeypatch):
    body = replace(actual_evidence['body'])
    object.__setattr__(body.payload, '_entries', list(body.payload._entries))
    def forbidden(self):
        pytest.fail('a defensive evidence copy ran before original storage was validated')
    monkeypatch.setattr(EvidenceRecord, '__post_init__', forbidden)
    with pytest.raises(ValueError, match='immutable tuple'):
        validate_terminal_graph(body, (EvidenceRecord,))


@pytest.mark.parametrize('constructor', [SourceRef, EvidenceRecord])
def test_unexpected_public_constructor_failure_preserves_object_and_exception_history(actual_evidence, monkeypatch, constructor):
    try:
        raise LookupError('retained evidence-constructor history')
    except LookupError as history:
        try:
            raise RuntimeError('unexpected constructor failure') from history
        except RuntimeError as error:
            sentinel = error
    prior = sentinel.__cause__, sentinel.__context__, sentinel.__suppress_context__
    def fail(self):
        raise sentinel
    monkeypatch.setattr(constructor, '__post_init__', fail)
    with pytest.raises(RuntimeError) as caught:
        validate_terminal_graph(actual_evidence['body'], (EvidenceRecord,))
    assert caught.value is sentinel
    assert (sentinel.__cause__, sentinel.__context__, sentinel.__suppress_context__) == prior
