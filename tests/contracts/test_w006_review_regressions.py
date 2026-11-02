"""Independent-review reproductions retained as product regressions (CR01–03)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from layauto_v2.domain.publication import InputsReady, PublicationUnavailable, Selection
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.tooling import FixtureCapture
from w005_cases import copy_input
from w006_cases import caller_request


def test_uri_resolution_is_frozen_during_acquisition(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    source = root / 'source.cdl'
    original_bytes = source.read_bytes()
    first, second = root / 'first.cdl', root / 'second.cdl'
    first.write_bytes(original_bytes)
    second.write_bytes(b'* changed after capture\n' + original_bytes)
    source.unlink()
    source.symlink_to(first)
    request = caller_request(root)
    read_bytes = Path.read_bytes
    reads = []

    def switch_after_first_capture(path):
        data = read_bytes(path)
        reads.append(path)
        if path == first:
            source.unlink()
            source.symlink_to(second)
        return data

    repository = PublicationRepository()
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', switch_after_first_capture)
        result = prepare_inputs(repository, request)
    assert isinstance(result, InputsReady)
    assert reads.count(first) == 1 and second not in reads
    tool = repository.read(result.tool_ref)
    captured = [item for item in tool.sources if item.uri == 'source.cdl']
    assert len(captured) == 1 and captured[0].data == original_bytes


def test_uncaptured_symlink_dotdot_selection_is_not_lexically_collapsed(tmp_path):
    root = copy_input(tmp_path)
    external = tmp_path / 'external'
    (external / 'child').mkdir(parents=True)
    (external / 'source.cdl').write_text('not the acquired source')
    (root / 'link').symlink_to(external / 'child', target_is_directory=True)
    request = caller_request(root)
    request = replace(request, config_policy_selections=request.config_policy_selections +
                      (Selection('link/../source.cdl'),))
    repository = PublicationRepository()
    result = prepare_inputs(repository, request)
    assert result.deployment_disposition == 'reject'
    checkpoint = repository.load_checkpoint(request.run_id)
    failure = repository.read(checkpoint.failure_ref)
    assert failure.code == 'UnreadSelection'
    assert failure.source.uri == 'link/../source.cdl' and failure.source.sha256 is None


class BrokenMessage:
    def __str__(self):
        raise RuntimeError('diagnostic conversion failed')


@pytest.mark.parametrize('boundary', ['parse', 'read'])
@pytest.mark.parametrize('interrupt', [SystemExit(BrokenMessage()), KeyboardInterrupt('\ud800')])
def test_diagnostic_formatting_never_replaces_original_interrupt(tmp_path, monkeypatch, boundary, interrupt):
    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()

    def fail(*args, **kwargs):
        raise interrupt

    if boundary == 'parse':
        monkeypatch.setattr(reader, 'parse_query', fail)
    else:
        monkeypatch.setattr(Path, 'read_bytes', fail)
    with pytest.raises(type(interrupt)) as caught:
        prepare_inputs(repository, request)
    assert caught.value is interrupt
    checkpoint = repository.load_checkpoint(request.run_id)
    assert checkpoint is not None
    failure = repository.read(checkpoint.failure_ref)
    assert failure.category == 'interrupted'
    assert failure.causes[0].exception_type == type(interrupt).__name__
    failure.message.encode('utf-8')
    assert repository.read_terminal(request.run_id).deployment_disposition == 'reject'


def test_tool_record_construction_failure_keeps_pending_bytes_and_no_terminal(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    repository = PublicationRepository()

    def fail(self):
        raise ValueError('injected tool record construction failure')

    monkeypatch.setattr(FixtureCapture, 'freeze', fail)
    result = prepare_inputs(repository, request)
    assert isinstance(result, PublicationUnavailable)
    assert result.operation == 'freeze_tool_run'
    assert result.pending_failure.code == 'InternalStageFailure'
    assert result.pending_failure.causes[0].exception_type == 'ValueError'
    assert len(result.pending_sources) == 31 and result.pending_events
    assert result.pending_parse.status == 'success' and result.pending_evidence
    assert result.pending_tool is None and not result.completed
    assert repository.load_checkpoint(request.run_id) is None
    assert repository.read_terminal(request.run_id) is None


def test_tool_record_failure_during_interrupt_diagnostics_preserves_original(tmp_path, monkeypatch):
    root = copy_input(tmp_path)
    request = caller_request(root)
    interrupt = SystemExit(BrokenMessage())

    def fail_parse(*args, **kwargs):
        raise interrupt

    def fail_record(self):
        raise RuntimeError('second failure')

    monkeypatch.setattr(reader, 'parse_query', fail_parse)
    monkeypatch.setattr(FixtureCapture, 'freeze', fail_record)
    with pytest.raises(SystemExit) as caught:
        prepare_inputs(PublicationRepository(), request)
    assert caught.value is interrupt
