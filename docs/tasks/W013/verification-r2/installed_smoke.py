"""W013 source-external installation smoke for the public local annotation API.

Run the finalized script with -I -B outside the checkout and frozen source.
It imports installed runtime plus stdlib only, never tests/support or answers.
Independent constants come from accepted local oracle/manual/raw facts.
Preparing this script does not establish an actual successful smoke or matrix.
"""
from __future__ import annotations

import argparse
import builtins
from collections import Counter
import copy
from dataclasses import FrozenInstanceError
from fractions import Fraction
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
import time
from unittest.mock import patch


W013_SMOKE_READY = True


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
    """Check complete public Result and independent exact local witnesses."""
    from layauto_v2.domain.codec import FrozenMap
    from layauto_v2.normalization.net_annotation import build_net_annotation
    from layauto_v2.normalization.net_annotation_codec import encode_record, decode_record, record_digest
    from layauto_v2.domain.publication_codec import content_ref

    started = time.perf_counter()
    result = build_net_annotation(local)
    build_seconds = time.perf_counter() - started
    assert result.status == 'success' and result.value is not None and not result.issues, result.issues
    assert result.input is local and result.completed is local.completed
    assert result.body_evidence is local.body_evidence
    draft, graph = result.value, local.value
    binding = draft.binding
    layout = graph.effective.base.layout
    assert binding.scope == 'source_evidence_local_net_annotation/1'
    assert binding.validity == 'source_evidence'
    assert binding.local_ref == graph.ref and binding.effective_ref == graph.effective.ref
    assert binding.geometry_ref == layout.ref and binding.unit_ref == layout.units.ref
    assert binding.partition_ref == graph.effective.base.partition.ref
    assert binding.tick_nm == layout.units.canonical_tick_nm and binding.top == layout.top
    assert binding.topology == graph.components and binding.drawn == graph.binding.drawn
    assert len(draft.targets) == 14 and len(draft.evidence) == len(draft.matches) == 8
    assert len(draft.components) == 6 and len(draft.classifications) == 40 and not draft.issues
    assert {target.node_ref for target in draft.targets} == {node.ref for node in graph.nodes}
    assert all(target.node == next(node for node in graph.nodes if node.ref == target.node_ref)
               for target in draft.targets)
    assert set(binding.drawn_record_ids) == {record.id for record in layout.records}
    assert tuple(seed.ref for seed in draft.evidence) == binding.evidence_refs
    assert {match.evidence_ref for match in draft.matches} == set(binding.evidence_refs)
    assert all(match.status in ('matched', 'partial') and match.intersections for match in draft.matches)

    semantic_input = local.input.input.input.semantic_input
    captures = semantic_input.parse.sources
    expected_sources = tuple((source.uri, source.sha256) for source in captures)
    actual_sources = tuple((row['uri'], row['sha256']) for row in binding.capture_binding['sources'])
    assert actual_sources == expected_sources
    assert binding.capture_binding['schema'] == 'layauto-net-capture-binding/1'
    assert all(seed.source.sha256 in {source.sha256 for source in captures} for seed in draft.evidence)
    # A was explicitly selected: preserve the current captured ordinal identities.
    identities = {(seed.net_id.name, seed.query_key.identity, seed.query_key.index) for seed in draft.evidence}
    assert identities == {('A', 'n_a', '1'), ('Y', 'n_y', '2'),
                          ('VSS', 'n_lo', '3'), ('VDD', 'n_hi', '4')}
    assert all(seed.record['lvs_index'] == seed.query_key.index and
               seed.record['lvs_name'] == seed.query_key.identity and
               seed.record['schematic_name'] == seed.net_id.name and
               seed.record['quality'] == 'exact' and seed.record['unit'] == 'nm' and
               type(seed.record['field_sources']) is FrozenMap and
               type(seed.identity_provenance['field_sources']) is FrozenMap
               for seed in draft.evidence)
    readback = binding.capture_binding['readback']
    if semantic_input.readback is None:
        assert readback is None and case != 'normal-readback'
    else:
        ready = semantic_input.readback.ready
        assert case == 'normal-readback' and readback['run_id'] == ready.run_id
        assert readback['request_digest'] == content_ref(ready.attempt.request).digest
        assert readback['attempt_digest'] == content_ref(ready.attempt).digest
        for name in ('checkpoint_ref', 'parse_ref', 'tool_ref'):
            reference = getattr(ready, name)
            assert (readback[name]['kind'], readback[name]['run_id'], readback[name]['digest']) == (
                reference.kind, reference.run_id, reference.digest)

    by_layer = {row.layer: row for row in draft.coverage}
    assert len(by_layer) == len(draft.coverage)
    assert all(row.unit == 'nm2' and row.denominator == 'local_target_multiset_area' for row in draft.coverage)
    expected_total = Fraction(34634 if case == 'extraction-mismatch' else 35090)
    assert sum((row.total_area for row in draft.coverage), Fraction()) == expected_total
    assert sum((row.covered_area for row in draft.coverage), Fraction()) == Fraction(3170)
    assert sum((row.uncovered_area for row in draft.coverage), Fraction()) == expected_total - 3170
    assert all(type(getattr(row, name)) is Fraction for row in draft.coverage
               for name in ('total_area', 'covered_area', 'uncovered_area', 'conflict_area', 'component_conflict_area'))
    assert all(row.conflict_area == row.component_conflict_area == 0 for row in draft.coverage)
    assert {layer: by_layer[layer].covered_area for layer in ('POLY', 'LI', 'M1')} == {
        'POLY': Fraction(720), 'LI': Fraction(1110), 'M1': Fraction(1340)}
    assert all(by_layer[layer].covered_area == 0 for layer in ('OD', 'BODY_N', 'BODY_P'))
    assert sum(row.target_count for row in draft.coverage) == 14
    assert sum(row.drawn_shape_count for row in draft.coverage) == 40
    targets = {target.ref: target for target in draft.targets}
    assert sum((fragment.area_nm2 for fragment in draft.fragments), Fraction()) == expected_total
    assert sum((fragment.area_nm2 for fragment in draft.fragments if fragment.net_ids), Fraction()) == 3170
    assert any(fragment.status == 'unknown' for fragment in draft.fragments)
    assert all(fragment.validity == 'source_evidence' and fragment.target_ref in targets
               and fragment.status in ('annotated', 'unknown') for fragment in draft.fragments)
    # Current local oracle: four associated physical components and two separate
    # unknown local body components. Component inference never marks OD direct.
    assert Counter(row.status for row in draft.components) == {'associated': 4, 'unknown': 2}
    expected_layers = {'A': Counter({'POLY': 1, 'M1': 1}),
                       'Y': Counter({'OD': 2, 'LI': 1, 'M1': 1}),
                       'VSS': Counter({'OD': 1, 'LI': 1, 'M1': 1}),
                       'VDD': Counter({'OD': 1, 'LI': 1, 'M1': 1})}
    associated = {row.observed_net_ids[0].name: row for row in draft.components if row.status == 'associated'}
    assert set(associated) == set(expected_layers)
    for name, row in associated.items():
        assert len(row.observed_net_ids) == 1
        assert Counter(targets[ref].target_id.layer for ref in row.target_refs) == expected_layers[name]
        assert all(targets[ref].target_id.layer in ('POLY', 'LI', 'M1') for ref in row.directly_covered_targets)
    unknown = [row for row in draft.components if row.status == 'unknown']
    assert {targets[row.target_refs[0]].target_id.layer for row in unknown} == {'BODY_N', 'BODY_P'}
    assert all(len(row.members) == len(row.target_refs) == 1 and not row.evidence_refs and
               not row.observed_net_ids and not row.directly_covered_targets for row in unknown)
    assert {row.component_ref for row in draft.components} == {row.ref for row in graph.components}
    assert {member for row in draft.components for member in row.members} == {node.ref for node in graph.nodes}
    markers = [row for row in draft.classifications if row.classification == 'marker']
    assert len(markers) == 1 and sum((row.rectangle.area for row in markers), Fraction()) == 25
    assert not {row.record_id for row in markers} & {target.target_id.record_id for target in draft.targets}
    assert all(type(getattr(draft, name)) is tuple for name in (
        'targets', 'evidence', 'matches', 'fragments', 'coverage', 'components', 'classifications', 'issues'))
    try:
        binding.validity = 'authoritative'
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError('public annotation binding was mutable')

    started = time.perf_counter()
    wire = encode_record(result)
    encode_seconds = time.perf_counter() - started
    started = time.perf_counter()
    restored = decode_record(wire)
    decode_seconds = time.perf_counter() - started
    assert restored == result and restored.input == local
    assert restored.completed == local.completed and restored.body_evidence == local.body_evidence
    wire_sha = hashlib.sha256(wire).hexdigest()
    public_digest_checked = case == 'normal-direct'
    if public_digest_checked:
        # One complete public digest check is sufficient; avoid repeatedly
        # authenticating every neutral field or adding a second W011 workload.
        assert record_digest(result) == wire_sha
        forged = copy.copy(by_layer['POLY'])
        object.__setattr__(forged, 'covered_area', Fraction(-1))
        try:
            encode_record(forged)
        except ValueError:
            pass
        else:
            raise AssertionError('public codec accepted a forged negative coverage value')
        assert by_layer['POLY'].covered_area == 720
    return {'wire_bytes': len(wire), 'wire_sha256': wire_sha, 'public_roundtrip_equal': True,
            'public_result_digest_checked': public_digest_checked, 'build_seconds': build_seconds,
            'encode_seconds': encode_seconds, 'decode_seconds': decode_seconds,
            'targets': 14, 'evidence': 8, 'classifications': 40, 'components': 6,
            'associated_components': 4, 'unknown_components': 2,
            'target_area_nm2': int(expected_total), 'direct_area_nm2': 3170,
            'uncovered_area_nm2': int(expected_total - 3170), 'marker_area_nm2': 25,
            'scope': binding.scope, 'validity': binding.validity}


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
    # Import component/codec before the no-IO instrumentation below.
    from layauto_v2.normalization import net_annotation, net_annotation_codec

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
