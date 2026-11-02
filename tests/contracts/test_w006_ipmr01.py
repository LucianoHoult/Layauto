"""IPMR-01: retain stage and diagnostic failures as separate immutable facts."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from layauto_v2.domain.publication import PublicationUnavailable
from layauto_v2.domain.publication_codec import decode_record, encode_record
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.tooling import FixtureCapture
from w005_cases import copy_input
from w006_cases import caller_request


class BrokenMessage:
    def __str__(self):
        raise RuntimeError('message formatting failed')


def inject_stage_failure(monkeypatch, root, boundary, fail):
    if boundary == 'parse':
        monkeypatch.setattr(reader, 'parse_query', fail)
    elif boundary == 'read':
        read_bytes = Path.read_bytes

        def read(path):
            if path == root / 'source.gds':
                fail()
            return read_bytes(path)

        monkeypatch.setattr(Path, 'read_bytes', read)


@pytest.mark.parametrize('boundary', ['parse', 'read', None], ids=['parse', 'read', 'freeze-only'])
@pytest.mark.parametrize('message,stage_message,freeze_message', [
    ('failure', 'failure', 'failure'),
    ('', 'RuntimeError', 'ValueError'),
    ('\ud800', '\\ud800', '\\ud800'),
    (BrokenMessage(), '<unprintable exception>', '<unprintable exception>'),
], ids=['plain', 'empty', 'surrogate', 'broken-str'])
def test_stage_cause_survives_tool_freeze_failure(
        tmp_path, monkeypatch, boundary, message, stage_message, freeze_message):
    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()

    def fail_stage(*args, **kwargs):
        try:
            raise LookupError('original underlying cause')
        except LookupError as cause:
            raise RuntimeError(message) from cause

    def fail_freeze(self):
        try:
            raise ArithmeticError('secondary underlying cause')
        except ArithmeticError as cause:
            raise ValueError(message) from cause

    with monkeypatch.context() as patch:
        inject_stage_failure(patch, root, boundary, fail_stage)
        patch.setattr(FixtureCapture, 'freeze', fail_freeze)
        result = prepare_inputs(repository, request)

    assert isinstance(result, PublicationUnavailable)
    assert result.operation == 'freeze_tool_run' and result.message == freeze_message
    secondary = [('ValueError', freeze_message), ('ArithmeticError', 'secondary underlying cause')]
    assert [(cause.exception_type, cause.message) for cause in result.causes] == secondary
    failure = result.pending_failure
    assert failure.category == 'internal' and failure.code == 'InternalStageFailure'
    assert failure.stage == 'stage1' and failure.run_id == request.run_id
    expected = secondary if boundary is None else [
        ('RuntimeError', stage_message), ('LookupError', 'original underlying cause')]
    assert [(cause.exception_type, cause.message) for cause in failure.causes] == expected
    assert failure.message == (freeze_message if boundary is None else stage_message)

    # A failed ToolRun freeze retains in-memory facts, without publishing a
    # RunRecord freeze closure, checkpoint, terminal or invented audit refs.
    assert result.pending_tool is None and result.completed == failure.completed == ()
    if boundary is None:
        assert result.pending_parse.status == 'success'
        assert result.pending_evidence == result.pending_parse.completed
        assert result.pending_sources == result.pending_parse.sources
    else:
        assert result.pending_parse is None
    assert result.pending_sources and result.pending_events and result.pending_evidence
    sources = {source.uri: source for source in result.pending_sources}
    for source in sources.values():
        assert source.data == (root / source.uri).read_bytes()
        assert source.sha256 == hashlib.sha256(source.data).hexdigest()
    for evidence in result.pending_evidence:
        for ref in evidence.sources:
            assert ref.sha256 == sources[ref.uri].sha256
    reads = {(event.uri, event.sha256) for event in result.pending_events
             if event.operation == 'read' and event.status == 'success'}
    assert reads == {(source.uri, source.sha256) for source in sources.values()}
    if boundary == 'read':
        failed = [event for event in result.pending_events if event.status == 'error']
        assert len(failed) == 1 and failed[0].uri == 'source.gds'
        assert failed[0].message == stage_message and failed[0].sha256 is None
        assert 'source.gds' not in sources
    attempt = repository.load_attempt(request.run_id)
    assert attempt == result.attempt and attempt.phase == 'unsealed' and attempt.revision == 0
    assert repository.load_checkpoint(request.run_id) is None
    assert repository.read_terminal(request.run_id) is None
    assert {ref.kind for ref in repository.snapshot().content_refs} == {'request', 'attempt'}
    assert decode_record(encode_record(result)) == result


@pytest.mark.parametrize('boundary', ['parse', 'read'])
@pytest.mark.parametrize('exception', [KeyboardInterrupt, SystemExit])
def test_interrupt_survives_secondary_tool_freeze_with_broken_message(
        tmp_path, monkeypatch, boundary, exception):
    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()
    interrupt = exception('\ud800')

    def fail_stage(*args, **kwargs):
        raise interrupt

    def fail_freeze(self):
        raise ValueError(BrokenMessage())

    inject_stage_failure(monkeypatch, root, boundary, fail_stage)
    monkeypatch.setattr(FixtureCapture, 'freeze', fail_freeze)
    with pytest.raises(exception) as caught:
        prepare_inputs(repository, request)
    assert caught.value is interrupt
    assert repository.load_attempt(request.run_id).revision == 0
    assert repository.load_checkpoint(request.run_id) is None
    assert repository.read_terminal(request.run_id) is None
