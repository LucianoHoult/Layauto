"""W006 IPMR-01: parser failure must survive a second diagnostic freeze error.

Run with the installed checkout's Python, from any cwd:
  python -B docs/tasks/W006/independent-premerge-verification/double_exception.py

Reads the accepted fixture without changing it. Only two in-process call sites
are fault-injected. Exit 1 reproduces the missing original cause on cc42ae6;
exit 0 requires the original failure and secondary diagnostic to both survive.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.publication import PublicationUnavailable, RunRequest
from layauto_v2.importers import reader
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.tooling import FixtureCapture


def parser_failure(*args: object, **kwargs: object) -> None:
    try:
        raise LookupError('original underlying cause')
    except LookupError as cause:
        raise RuntimeError('original parser failure') from cause


def freeze_failure(self: FixtureCapture) -> None:
    raise ValueError('secondary tool diagnostic freeze failure')


def main() -> None:
    root = Path(__file__).resolve().parents[4]
    site = root / 'tests/fixtures/w003_m1/site_config.yaml'
    request = RunRequest('ipmr-01-run', 'ipmr-01-lineage', 'ipmr-01-key', str(site))
    repository = PublicationRepository()
    with patch.object(reader, 'parse_query', parser_failure), patch.object(FixtureCapture, 'freeze', freeze_failure):
        result = prepare_inputs(repository, request)

    assert isinstance(result, PublicationUnavailable)
    assert result.pending_failure is not None
    causes = [(cause.exception_type, cause.message) for cause in result.pending_failure.causes]
    terminal = repository.read_terminal(request.run_id)
    checkpoint = repository.load_checkpoint(request.run_id)
    print(json.dumps({
        'status': result.status,
        'operation': result.operation,
        'publication_causes': [(cause.exception_type, cause.message) for cause in result.causes],
        'pending_failure_code': result.pending_failure.code,
        'pending_failure_causes': causes,
        'pending_parse_is_none': result.pending_parse is None,
        'captured_sources': len(result.pending_sources),
        'completed_evidence': len(result.pending_evidence),
        'checkpoint_is_none': checkpoint is None,
        'terminal_is_none': terminal is None,
    }, indent=2), flush=True)
    assert terminal is None and checkpoint is None
    assert ('ValueError', 'secondary tool diagnostic freeze failure') in [
        (cause.exception_type, cause.message) for cause in result.causes]
    assert causes == [
        ('RuntimeError', 'original parser failure'),
        ('LookupError', 'original underlying cause'),
    ], 'IPMR-01: diagnostic freeze failure discarded the original parser cause chain'


if __name__ == '__main__':
    main()
