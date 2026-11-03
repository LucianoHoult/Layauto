"""The W009 nested capture/readback codec preserves internal failures."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.publication import InputsReady, Selection
from layauto_v2.domain import publication_codec
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.normalization import build_effective_geometry, build_geometry
from layauto_v2.normalization.effective_codec import decode_record, encode_record
from layauto_v2.normalization.geometry_input import geometry_from_inputs_ready, geometry_from_parse_result
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE
from w006_cases import caller_request
from w007_cases import mutable


@pytest.fixture(scope='module')
def captured():
    repository = PublicationRepository()
    ready = prepare_inputs(repository, caller_request(FIXTURE, run_id='w009-captured-wire'))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse = repository.read(ready.parse_ref)
    tool = repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    direct = build_effective_geometry(build_geometry(geometry_from_parse_result(parse.result)))
    readback = build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
    assert direct.status == readback.status == 'success'
    assert direct.value == readback.value
    records = (Selection('source.gds'), ready.checkpoint_ref, tool.events[0],
               parse.result.sources[0].ref(), parse.result.sources[0],
               EvidenceIssue('binding', 'Example', 'located rejection', parse.result.sources[0].ref()),
               parse.result.completed[0], parse.result, ready.attempt.request, ready.attempt,
               tool, parse, audits[0], checkpoint, ready)
    return ({'direct': encode_record(direct), 'readback': encode_record(readback)}, records)


@pytest.mark.parametrize('enclosing', ('direct', 'readback'))
@pytest.mark.parametrize('failure_type', (RuntimeError, ValueError, TypeError, KeyError,
                                        AttributeError, IndexError, UnicodeError,
                                        KeyboardInterrupt, SystemExit))
def test_captured_source_hash_failure_keeps_object_and_prior_chain(captured, monkeypatch, enclosing, failure_type):
    wires, _ = captured
    cause = OSError('existing explicit cause')
    context = LookupError('existing implicit context')
    failure = failure_type('unexpected SourceFile reconstruction failure')
    failure.__cause__, failure.__context__ = cause, context
    prior_suppression = failure.__suppress_context__

    def broken(*args, **kwargs):
        raise failure

    # Replace only evidence.py's module binding: changing hashlib.sha256 itself
    # would also inject into earlier geometry hashes and miss this boundary.
    monkeypatch.setattr('layauto_v2.domain.evidence.hashlib', SimpleNamespace(sha256=broken))
    with pytest.raises(failure_type) as caught:
        decode_record(wires[enclosing])
    assert caught.value is failure
    assert failure.__cause__ is cause
    assert failure.__context__ is context
    assert failure.__suppress_context__ is prior_suppression


@pytest.mark.parametrize('field', ('issues', 'completed', 'sources'))
@pytest.mark.parametrize('bad', (None, 7, b'wrong collection', 'wrong collection', (None,)))
def test_parse_public_constructor_rejects_invalid_collections(captured, field, bad):
    _, records = captured
    parsed = next(record for record in records if type(record).__name__ == 'ParseResult')
    with pytest.raises(ValueError):
        replace(parsed, **{field: bad})


@pytest.mark.parametrize('bad', (None, 7, b'wrong collection', 'wrong collection', (None,)))
def test_evidence_public_constructor_rejects_invalid_sources(captured, bad):
    _, records = captured
    evidence = next(record for record in records if type(record) is EvidenceRecord)
    with pytest.raises(ValueError):
        replace(evidence, sources=bad)


def test_all_nested_captured_dtos_still_roundtrip_and_reject_malformed_fields(captured):
    _, records = captured
    for record in records:
        wire = publication_codec.encode_record(record)
        assert publication_codec.decode_record(wire) == record
        assert publication_codec.record_digest(record) == publication_codec.record_digest(
            publication_codec.decode_record(wire))
        tree = mutable(decode(wire))
        fields = tree['value']['fields']
        key = next(key for key in fields if key not in ('kind', 'sha256'))
        missing = mutable(decode(wire))
        del missing['value']['fields'][key]
        extra = mutable(decode(wire))
        extra['value']['fields']['extra'] = {'scalar': None}
        for malformed in (missing, extra):
            with pytest.raises(ValueError):
                publication_codec.decode_record(canonical_bytes(malformed))
        # Substituting arbitrary wire scalars/collections at each field exercises
        # the explicit DTO checks now that constructor failures are not wrapped.
        for key, original in fields.items():
            if key in ('kind', 'sha256'):
                continue
            for wrong in ({'scalar': 7}, {'scalar': None}, {'tuple': ()}, {'value': {}}):
                if original == wrong:
                    continue
                malformed = mutable(decode(wire))
                malformed['value']['fields'][key] = wrong
                try:
                    rebuilt = publication_codec.decode_record(canonical_bytes(malformed))
                except ValueError:
                    pass
                else:
                    # Some values are valid alternatives (e.g. optional None or
                    # empty collections). Their canonical form must still bind.
                    assert publication_codec.encode_record(rebuilt) == canonical_bytes(malformed)
