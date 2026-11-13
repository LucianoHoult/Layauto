"""W014 source-external installation smoke for device terminal and external body relations.

Run the finalized script with -I -B outside the checkout and frozen source.
It imports installed runtime plus stdlib only, never tests/support or answers.
Independent constants come from accepted oracle/manual/raw facts.
Readiness means the actual API assertions are integrated; it does not claim execution.
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


W014_SMOKE_READY = True


def forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError('W014 annotation component attempted IO or repository access')


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


def terminal_checks(local: object, case: str) -> dict[str, object]:
    """Independent eight-terminal witnesses, full public wire and retained gaps."""
    from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
    from layauto_v2.normalization import build_terminal_relations
    from layauto_v2.normalization.terminal_relations_codec import encode_record, decode_record, record_digest
    from layauto_v2.domain.publication_codec import content_ref

    tick = time.perf_counter()
    result = build_terminal_relations(local)
    build_seconds = time.perf_counter() - tick
    assert result.status == 'success' and result.value is not None and not result.issues, result.issues
    assert result.input is local and result.completed is local.completed
    assert result.body_evidence is local.body_evidence
    draft, graph = result.value, local.value
    assert draft.local is graph and draft.source == result.semantic_facts.source
    assert draft.comparison_status == 'equal' and not draft.issues
    assert len(draft.relations) == 8
    assert len({row.target.ref for row in draft.relations}) == 8
    expected = {('MN0', 'D'): 'Y', ('MN0', 'G'): 'A', ('MN0', 'S'): 'VSS', ('MN0', 'B'): 'VSS',
                ('MP0', 'D'): 'Y', ('MP0', 'G'): 'A', ('MP0', 'S'): 'VDD', ('MP0', 'B'): 'VDD'}
    rows = {(row.target.device_id.name, row.target.role): row for row in draft.relations}
    assert set(rows) == set(expected)
    source_devices = {device.id: device for cell in draft.source.cells
                      if cell.id == draft.source.selected_cell for device in cell.devices}
    local_node_refs = {node.ref for node in graph.nodes}
    local_component_refs = {component.ref for component in graph.components}
    annotation = draft.annotation
    annotation_targets = {target.ref: target for target in annotation.targets}
    assert annotation.binding.local_ref == graph.ref
    assert len(annotation.targets) == 14 and len(annotation.components) == 6
    assert len(annotation.evidence) == 8
    assert Counter(row.status for row in annotation.components) == {'associated': 4, 'unknown': 2}
    for key, row in rows.items():
        assert row.expected == next(terminal for terminal in source_devices[row.target.device_id].terminals
                                    if terminal.role == row.target.role)
        assert row.expected.net_id.name == expected[key]
        assert tuple(net.name for net in row.observed_net_ids) == (expected[key],)
        assert row.status == 'equal' and row.support_status == 'established'
        assert row.channel_ref is not None and row.node_refs and row.component_refs
        assert set(row.node_refs) <= local_node_refs and set(row.component_refs) <= local_component_refs
        assert set(row.annotation_target_refs) <= set(annotation_targets)
        if row.target.role == 'B':
            assert not row.local_observed_net_ids and row.context_path is not None
            component = next(item for item in annotation.components if item.component_ref in row.component_refs)
            assert component.status == 'unknown' and not component.observed_net_ids
        else:
            assert tuple(net.name for net in row.local_observed_net_ids) == (expected[key],)
            assert row.context_path is None
    # Shared conductor membership does not assign the full POLY shape to one device.
    assert set(rows[('MN0', 'G')].node_refs) & set(rows[('MP0', 'G')].node_refs)
    assert rows[('MN0', 'G')].target.ref != rows[('MP0', 'G')].target.ref
    assert rows[('MN0', 'D')].node_refs != rows[('MN0', 'S')].node_refs
    assert rows[('MP0', 'D')].node_refs != rows[('MP0', 'S')].node_refs
    check_body(draft.body, rows)
    assert draft.coverage['local_graph_union'] is False
    assert draft.coverage['physical_pin_access_established'] is False
    assert draft.coverage['production_matched_body_evidence'] is False
    assert draft.coverage['lvs_status'] == 'not_run'
    comparisons = tuple(item['fields'] for item in draft.channel_observations['comparisons'])
    fin_counts = {item['device_id']['name']: item for item in comparisons if item['axis'] == 'fins_per_finger'}
    assert set(fin_counts) == {'MN0', 'MP0'}
    assert fin_counts['MP0']['measured'] == fin_counts['MP0']['declared']['exact'] == 7
    if case == 'extraction-mismatch':
        assert fin_counts['MN0']['measured'] == 4 and fin_counts['MN0']['declared']['exact'] == 5
        assert draft.differences
        assert draft.channel_comparison_status == draft.source_comparison_status == 'mismatch'
    else:
        assert fin_counts['MN0']['measured'] == fin_counts['MN0']['declared']['exact'] == 5
        assert not draft.differences
        assert draft.channel_comparison_status == draft.source_comparison_status == 'equal'
    by_layer = {item.layer: item for item in annotation.coverage}
    expected_total = Fraction(34634 if case == 'extraction-mismatch' else 35090)
    assert sum((item.total_area for item in by_layer.values()), Fraction()) == expected_total
    assert sum((item.covered_area for item in by_layer.values()), Fraction()) == 3170
    assert sum((item.uncovered_area for item in by_layer.values()), Fraction()) == expected_total - 3170
    assert by_layer['BODY_N'].covered_area == by_layer['BODY_P'].covered_area == 0
    assert graph.local_enclosure_status == 'pass' and len(graph.audits) == 16
    assert len(graph.nodes) == 14 and len(graph.edges) == 8 and len(graph.components) == 6
    captures = local.input.input.input.semantic_input.parse.sources
    capture_binding = annotation.binding.capture_binding
    assert tuple((item['uri'], item['sha256']) for item in capture_binding['sources']) == tuple(
        (item.uri, item.sha256) for item in captures)
    readback = capture_binding['readback']
    semantic_input = local.input.input.input.semantic_input
    if semantic_input.readback is None:
        assert readback is None and case != 'normal-readback'
    else:
        ready = semantic_input.readback.ready
        assert case == 'normal-readback' and readback['run_id'] == ready.run_id
        assert readback['request_digest'] == content_ref(ready.attempt.request).digest
        assert readback['attempt_digest'] == content_ref(ready.attempt).digest
    try:
        rows[('MN0', 'D')].target.role = 'S'
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError('terminal target is mutable')
    tick = time.perf_counter()
    wire = encode_record(result)
    encode_seconds = time.perf_counter() - tick
    tick = time.perf_counter()
    restored = decode_record(wire)
    decode_seconds = time.perf_counter() - tick
    assert restored == result and restored.input == local
    assert restored.completed == local.completed and restored.body_evidence == local.body_evidence
    packet = decode(wire)
    assert 'captured_input_wire' in packet
    compact = {key: value for key, value in packet.items() if key != 'captured_input_wire'}
    wire_sha = hashlib.sha256(wire).hexdigest()
    if case == 'normal-direct':
        assert record_digest(result) == wire_sha
        forged = copy.copy(rows[('MN0', 'D')])
        object.__setattr__(forged, 'support_status', 'authoritative')
        try:
            encode_record(forged)
        except ValueError:
            pass
        else:
            raise AssertionError('public codec accepted a forged support status')
    return {'wire_bytes': len(wire), 'wire_sha256': wire_sha,
            'compact_envelope_bytes': len(canonical_bytes(compact)), 'public_roundtrip_equal': True,
            'public_result_digest_checked': case == 'normal-direct',
            'build_seconds': build_seconds, 'encode_seconds': encode_seconds, 'decode_seconds': decode_seconds,
            'terminal_count': 8, 'local_terminal_count': 6, 'independent_body_count': 2,
            'terminal_comparison': draft.comparison_status,
            'retained_MN0_fin_count': int(fin_counts['MN0']['measured']),
            'retained_MN0_source_fin_count': int(fin_counts['MN0']['declared']['exact']),
            'local_nodes_edges_components': [14, 8, 6], 'unknown_local_body_components': 2,
            'direct_annotation_nm2': 3170, 'uncovered_annotation_nm2': int(expected_total - 3170)}


def check_body(body: object, rows: dict[tuple[str, str], object]) -> None:
    """Exact independent body geometry witnesses, without a local graph union."""
    from layauto_v2.domain.codec import FrozenMap
    assert type(body) is FrozenMap
    assert body['production_matched_body_evidence'] is False and body['lvs_status'] == 'not_run'
    assert body['local_graph_union'] is False
    assert body['binding']['active_threshold_nm'] == Fraction(10)
    assert body['binding']['tap_threshold_nm'] == Fraction(1)
    assert all(audit['status'] == 'satisfied' for key in ('active_audits', 'body_pair_audits', 'tap_audits')
               for audit in body[key])
    assert len(body['active_audits']) == 2 and len(body['tap_audits']) == 2
    assert len(body['body_pair_audits']) == 2
    assert {audit['domain'] for audit in body['body_pair_audits']} == {'local', 'external'}
    assert all(audit['positive_area_overlap'] is False for audit in body['body_pair_audits'])
    active_audits = {audit['device_id']['name']: audit for audit in body['active_audits']}
    assert active_audits['MN0']['margins_nm'] == (Fraction(20),) * 4
    assert active_audits['MP0']['margins_nm'] == (Fraction(20), Fraction(10), Fraction(20), Fraction(20))
    assert all(type(margin) is Fraction for audit in body['tap_audits']
               for name in ('body_margins_nm', 'rail_margins_nm') for margin in audit[name])
    assert all(min(audit['body_margins_nm']) == 8 and min(audit['rail_margins_nm']) == 2
               for audit in body['tap_audits'])
    paths = {path['device_id']['name']: path for path in body['paths']}
    assert set(paths) == {'MN0', 'MP0'}
    for device, active_margin, body_edge, rail in (('MN0', 20, 90, 'VSS'), ('MP0', 10, 100, 'VDD')):
        path = paths[device]
        assert path == rows[(device, 'B')].context_path
        assert path['chain_status'] == 'established'
        assert path['rule_status'] == 'satisfied' and path['claim_status'] == 'equal'
        assert path['body_edge_length_nm'] == Fraction(body_edge)
        assert path['rail_edge_length_nm'] == Fraction(10)
        assert path['active_enclosure_nm'] == Fraction(active_margin)
        assert path['tap_body_enclosure_nm'] == Fraction(8)
        assert path['tap_rail_enclosure_nm'] == Fraction(2)
        assert tuple(net['name'] for net in path['observed_net_ids']) == (rail,)
        assert path['evidence_refs']
        assert path['local_body_node_ref'] in tuple(reference.to_value() for reference in rows[(device, 'B')].node_refs)
        assert path['local_body_component_ref'] in tuple(reference.to_value() for reference in rows[(device, 'B')].component_refs)


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
    if not W014_SMOKE_READY:
        parser.error('W014 API assertions are not integrated; this scaffold cannot report success')
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
    from layauto_v2.normalization import terminal_relations, terminal_relations_codec

    fixture = args.fixture.resolve()
    installed = Path(layauto_v2.__file__).resolve()
    purelib = Path(sysconfig.get_path('purelib')).resolve()
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert installed.is_relative_to(purelib), (installed, purelib)
    parsed = read_inputs(fixture / 'site_config.yaml')
    direct_local = local_from_parse(parsed)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w014-installed-run', lineage_id='w014-installed-lineage',
        idempotency_key='create-w014-installed', site_path=str(fixture / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    readback_local = build_local_connectivity(build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))))
    assert readback_local.status == 'success', readback_local.issues
    with tempfile.TemporaryDirectory(prefix='w014-installed-mismatch-', dir=Path.cwd()) as temp:
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
            checks = {case: terminal_checks(local, case) for case, local in (
                ('normal-direct', direct_local), ('normal-readback', readback_local),
                ('extraction-mismatch', mismatch_local))}
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    print(json.dumps({'python': sys.version, 'executable': sys.executable,
                      'package': str(installed), 'distribution_version': importlib.metadata.version('layauto'),
                      'cases': checks, 'attempt_unchanged': True, 'checkpoint_unchanged': True,
                      'terminal_absent': True,
                      'limitations': ['Finite synthetic D/G/S/B and external body draft; not complete extraction, mandatory-rule, production LVS assurance or a run terminal.',
                                      'Installation-smoke mismatch URI is correctness-only; not fixed-URI performance evidence.']}, indent=2))


if __name__ == '__main__':
    main()
