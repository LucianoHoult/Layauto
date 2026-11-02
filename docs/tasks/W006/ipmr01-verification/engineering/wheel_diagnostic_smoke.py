"""Exercise IPMR-01 from a clean installed wheel, outside the source tree."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import layauto_v2
from layauto_v2.domain.publication import PublicationUnavailable, RunRequest
from layauto_v2.domain.publication_codec import decode_record, encode_record
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.tooling import FixtureCapture


def original_failure(*args, **kwargs):
    try:
        raise LookupError('original underlying cause')
    except LookupError as cause:
        raise RuntimeError('original stage failure') from cause


def freeze_failure(self):
    raise ValueError('secondary diagnostic freeze failure')


def main():
    installed = Path(layauto_v2.__file__).resolve()
    assert installed.is_relative_to(Path(sys.prefix).resolve()), installed
    fixture = Path(sys.argv[1]).resolve()
    results = []
    for boundary in ('parser', 'acquisition'):
        repository = PublicationRepository()
        request = RunRequest('wheel-ipmr01-' + boundary, 'wheel-lineage', boundary,
                             str(fixture / 'site_config.yaml'))
        original_read = Path.read_bytes

        def read(path):
            if path == fixture / 'source.gds':
                original_failure()
            return original_read(path)

        first = patch.object(reader, 'parse_query', original_failure) if boundary == 'parser' else patch.object(Path, 'read_bytes', read)
        with first, patch.object(FixtureCapture, 'freeze', freeze_failure):
            result = prepare_inputs(repository, request)
        assert isinstance(result, PublicationUnavailable)
        assert result.operation == 'freeze_tool_run'
        assert [(c.exception_type, c.message) for c in result.causes] == [
            ('ValueError', 'secondary diagnostic freeze failure')]
        failure = result.pending_failure
        assert failure is not None and failure.category == 'internal'
        assert [(c.exception_type, c.message) for c in failure.causes] == [
            ('RuntimeError', 'original stage failure'), ('LookupError', 'original underlying cause')]
        assert result.pending_tool is None and result.pending_parse is None and not result.completed
        assert result.pending_sources and result.pending_events and result.pending_evidence
        by_uri = {source.uri: source for source in result.pending_sources}
        for source in result.pending_sources:
            assert source.sha256 == hashlib.sha256(source.data).hexdigest()
        for event in result.pending_events:
            if event.operation == 'read' and event.status == 'success':
                assert event.sha256 == by_uri[event.uri].sha256
        for evidence in result.pending_evidence:
            for source_ref in evidence.sources:
                assert source_ref.sha256 == by_uri[source_ref.uri].sha256
        if boundary == 'acquisition':
            errors = [event for event in result.pending_events if event.status == 'error']
            assert len(errors) == 1 and errors[0].exception_type == 'RuntimeError'
        assert repository.load_checkpoint(request.run_id) is None
        assert repository.read_terminal(request.run_id) is None
        attempt = repository.load_attempt(request.run_id)
        assert attempt.phase == 'unsealed' and attempt.revision == 0
        assert decode_record(encode_record(result)) == result
        results.append({'boundary': boundary, 'original_causes': len(failure.causes),
                        'secondary_causes': len(result.causes), 'sources': len(result.pending_sources),
                        'evidence': len(result.pending_evidence), 'terminal': None})
    print(json.dumps({'python': sys.version, 'installed_module': str(installed),
                      'ipmr01': results}, indent=2))


if __name__ == '__main__':
    main()
