"""W013 source-external installation smoke scaffold; API assertions pending.

Run the finalized script with -I -B outside the checkout and frozen source.
It imports installed runtime plus stdlib only, never tests/support or answers.
The readiness guard must remain false until actual W013 assertions are added.
This preparation artifact is not a successful W013 smoke or final matrix.
"""
from __future__ import annotations

import argparse
import builtins
from contextlib import ExitStack
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import shutil
import sys
import sysconfig
import tempfile
from unittest.mock import patch


W013_SMOKE_READY = False


def forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError('W013 annotation component attempted IO or repository access')


def local_from_parse(parsed: object) -> object:
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, build_local_connectivity,
        geometry_from_parse_result,
    )
    assert parsed.status == 'success', parsed.issues
    geometry = build_geometry(geometry_from_parse_result(parsed))
    effective = build_effective_geometry(geometry)
    local = build_local_connectivity(effective)
    assert local.status == 'success' and local.value is not None, local.issues
    return local


def check_upstream(local: object) -> None:
    """Independent accepted local-scope witnesses; no external body graph added."""
    graph = local.value
    assert graph is not None
    assert len(graph.nodes) == 14 and len(graph.edges) == 8
    assert len(graph.components) == 6 and len(graph.audits) == 16
    assert graph.local_enclosure_status == 'pass'
    assert len(graph.effective.base.layout.records) == 40
    assert len(local.body_evidence.payload['shapes']) == 6
    captured = local.input.input.input.semantic_input.parse.sources
    acquired = {source.uri: source for source in captured}
    assert len(captured) == len(acquired) == 31
    assert all(hashlib.sha256(source.data).hexdigest() == source.sha256 for source in captured)
    assert all(ref.uri in acquired and acquired[ref.uri].sha256 == ref.sha256
               for evidence in local.completed for ref in evidence.sources)


def annotation_checks(local: object, case: str) -> dict[str, object]:
    """Integration point for finalized W013 public API and independent witnesses.

    Required: build_net_annotation(local), full public encode/decode/digest,
    source/local scope and input/owner/source binding, complete target/fragment
    coverage with gaps visible, exact independent per-layer/component witnesses,
    preserved graph/T05/body/readback, and invalid public reconstruction rejection.
    Do not instantiate W011 or weaken source authentication to finish this hook.
    """
    raise NotImplementedError('Finalize W013 AnnotationDraft/Result assertions before freezing the matrix')


def make_mismatch_input(fixture: Path, destination: Path) -> Path:
    # Only accepted capture bytes are copied. No answer/oracle/spec is parsed.
    # Random installation-smoke URI is correctness-only, never a performance pair.
    shutil.copytree(fixture, destination)
    for name in ('source.gds', 'query/header.json', 'query/raw/device_info_Q17.txt',
                 'query/normalized/device_regions.yaml', 'body/context.json'):
        shutil.copyfile(fixture / 'failures/extraction_mismatch' / name, destination / name)
    return destination / 'site_config.yaml'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args()
    if not W013_SMOKE_READY:
        parser.error('W013 API assertions are not integrated; this scaffold cannot report success')
    import layauto_v2
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (
        build_geometry, build_effective_geometry, build_local_connectivity,
        geometry_from_inputs_ready,
    )
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository

    fixture = args.fixture.resolve()
    installed = Path(layauto_v2.__file__).resolve()
    purelib = Path(sysconfig.get_path('purelib')).resolve()
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert installed.is_relative_to(purelib), (installed, purelib)
    parsed = read_inputs(fixture / 'site_config.yaml')
    direct_local = local_from_parse(parsed)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w013-installed-run', lineage_id='w013-installed-lineage',
        idempotency_key='create-w013-installed', site_path=str(fixture / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    readback_local = build_local_connectivity(build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))))
    assert readback_local.status == 'success', readback_local.issues
    with tempfile.TemporaryDirectory(prefix='w013-installed-mismatch-', dir=Path.cwd()) as temp:
        mismatch_parse = read_inputs(make_mismatch_input(fixture, Path(temp) / 'input'))
        mismatch_local = local_from_parse(mismatch_parse)
        for local in (direct_local, readback_local, mismatch_local):
            check_upstream(local)
        with ExitStack() as stack:
            for target in ('open', 'read_bytes', 'read_text', 'resolve'):
                stack.enter_context(patch.object(Path, target, forbidden))
            stack.enter_context(patch.object(builtins, 'open', forbidden))
            stack.enter_context(patch.object(io, 'open', forbidden))
            for target in ('read', 'load_checkpoint', 'load_attempt'):
                stack.enter_context(patch.object(repository, target, forbidden))
            checks = {case: annotation_checks(local, case) for case, local in (
                ('normal-direct', direct_local), ('normal-readback', readback_local),
                ('extraction-mismatch', mismatch_local))}
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    print(json.dumps({'python': sys.version, 'executable': sys.executable,
                      'package': str(installed), 'distribution_version': importlib.metadata.version('layauto'),
                      'cases': checks, 'attempt_unchanged': True, 'checkpoint_unchanged': True,
                      'terminal_absent': True,
                      'limitations': ['Finite synthetic source-evidence/local draft; not full M1, body/LVS assurance, or a run terminal.',
                                      'Installation-smoke mismatch URI is correctness-only; not fixed-URI performance evidence.']}, indent=2))


if __name__ == '__main__':
    main()
