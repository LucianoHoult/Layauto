"""Run outside the checkout with a clean wheel installation and a fixture copy."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import layauto_v2
from layauto_v2.domain.publication import (
    InputsReady, PipelineResult, RunRequest, Selection, StageFailure, WithRunRecordClosure,
)
from layauto_v2.domain.publication_codec import decode_record, encode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository


def request(root: Path, run: str) -> RunRequest:
    site = json.loads((root / 'site_config.yaml').read_text())
    header = json.loads((root / site['inputs']['query_header']).read_text())
    inputs = set(site['inputs'].values())
    raw = {item['uri'] for item in header['raw']}
    config = {item['uri'] for item in header['closure']['entries']} - inputs

    def selections(paths):
        return tuple(Selection(path, hashlib.sha256((root / path).read_bytes()).hexdigest())
                     for path in sorted(paths))

    return RunRequest(run, 'wheel-lineage', 'create-' + run, str(root / 'site_config.yaml'),
                      selections(inputs), selections(raw), selections(config))


def main() -> None:
    installed = Path(layauto_v2.__file__).resolve()
    assert installed.is_relative_to(Path(sys.prefix).resolve()), (installed, sys.prefix)
    fixture, output = (Path(arg).resolve() for arg in sys.argv[1:])
    root = output / 'normal'
    shutil.copytree(fixture, root)
    repository = PublicationRepository()
    normal_request = request(root, 'wheel-normal')
    assert len(normal_request.selections) == 27
    ready = prepare_inputs(repository, normal_request)
    assert isinstance(ready, InputsReady), ready
    assert ready.attempt.phase == 'unsealed' and ready.attempt.terminal_ref is None
    assert decode_record(encode_record(ready)) == ready
    assert prepare_inputs(repository, normal_request) == ready
    for ref in (ready.tool_ref, ready.parse_ref, *ready.evidence_refs):
        repository.read(ref)

    bad = output / 'missing-terminator'
    shutil.copytree(fixture, bad)
    for name in ('query/header.json', 'query/raw/device_info_Q17.txt'):
        shutil.copyfile(fixture / 'failures/missing_terminator' / name, bad / name)
    (bad / 'query/normalized/device_regions.yaml').unlink()
    bad_request = request(bad, 'wheel-f2')
    terminal = prepare_inputs(repository, bad_request)
    assert isinstance(terminal, PipelineResult), terminal
    assert terminal.deployment_disposition == 'reject'
    closure = repository.read(terminal.closure_ref)
    assert isinstance(closure, WithRunRecordClosure)
    failure = repository.read(closure.failure_ref)
    assert isinstance(failure, StageFailure) and failure.code == 'MissingTerminator'
    assert failure.source.sha256 == hashlib.sha256((bad / 'query/raw/device_info_Q17.txt').read_bytes()).hexdigest()
    repository.read(closure.run_record_ref)
    assert repository.read_terminal('wheel-f2') == terminal
    print(json.dumps({'python': sys.version, 'installed_module': str(installed),
                      'normal': ready.status, 'attempt_phase': ready.attempt.phase,
                      'declarations': len(normal_request.selections),
                      'f2': failure.code, 'disposition': terminal.deployment_disposition,
                      'scope': 'pre-context only; no Stage 2, success terminal or EDA'}, indent=2))


if __name__ == '__main__':
    main()
