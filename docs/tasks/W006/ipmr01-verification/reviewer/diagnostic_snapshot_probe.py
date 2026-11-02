"""Independent IPMR-01 probe: original snapshots survive diagnostic failures."""
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.publication import PublicationUnavailable, RunRequest
from layauto_v2.domain.publication_codec import decode_record, encode_record
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.tooling import FixtureCapture


class MutableMessage:
    value = 'original stage message'

    def __str__(self):
        return self.value


class InterruptedMessage:
    def __str__(self):
        raise KeyboardInterrupt('secondary formatting interrupt')


def check(boundary):
    root = Path(__file__).resolve().parents[5] / 'tests/fixtures/w003_m1'
    request = RunRequest('snapshot-' + boundary, 'snapshot-lineage', 'snapshot-key', str(root / 'site_config.yaml'))
    repository = PublicationRepository()
    message = MutableMessage()
    diagnostic_phase = False
    load_attempt = repository.load_attempt
    read_bytes = Path.read_bytes

    def fail_stage(*args, **kwargs):
        try:
            raise LookupError('original underlying cause')
        except LookupError as cause:
            raise RuntimeError(message) from cause

    def read(path):
        if path == root / 'source.gds':
            fail_stage()
        return read_bytes(path)

    def fail_freeze(self):
        nonlocal diagnostic_phase
        diagnostic_phase = True
        message.value = 'changed only after stage snapshot'
        raise ValueError(InterruptedMessage())

    def diagnostic_readback(run_id):
        if diagnostic_phase:
            raise OSError('diagnostic readback unavailable')
        return load_attempt(run_id)

    with patch.object(FixtureCapture, 'freeze', fail_freeze), patch.object(repository, 'load_attempt', diagnostic_readback):
        if boundary == 'parse':
            with patch.object(reader, 'parse_query', fail_stage):
                result = prepare_inputs(repository, request)
        else:
            with patch.object(Path, 'read_bytes', read):
                result = prepare_inputs(repository, request)

    assert isinstance(result, PublicationUnavailable)
    assert result.operation == 'freeze_tool_run'
    assert result.message == '<unprintable exception>'
    assert [(cause.exception_type, cause.message) for cause in result.causes] == [('ValueError', '<unprintable exception>')]
    assert [(cause.exception_type, cause.message) for cause in result.pending_failure.causes] == [
        ('RuntimeError', 'original stage message'), ('LookupError', 'original underlying cause')]
    assert str(message) == 'changed only after stage snapshot'
    assert result.attempt is None and result.completed == ()
    assert result.pending_parse is None and result.pending_tool is None
    assert result.pending_sources and result.pending_events and result.pending_evidence
    assert repository.load_attempt(request.run_id).revision == 0
    assert repository.load_checkpoint(request.run_id) is None
    assert repository.read_terminal(request.run_id) is None
    assert {ref.kind for ref in repository.snapshot().content_refs} == {'request', 'attempt'}
    assert decode_record(encode_record(result)) == result
    print('PASS', boundary, 'original cause snapshot, secondary hostile message and failed diagnostic readback; no invented publication')


if __name__ == '__main__':
    check('parse')
    check('read')
