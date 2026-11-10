"""Installed W012 A1: complete W005/W006 -> W007/W008/W009/W010/W011 composition.

Run with -I -B from outside the repository and frozen source. This script imports
only the installed runtime and stdlib; no tests/support, oracle or spec is read.
Constants below are the independently documented W011 synthetic witnesses.
"""
from __future__ import annotations

import builtins
from contextlib import ExitStack
from dataclasses import replace
from fractions import Fraction
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

import layauto_v2
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, build_effective_geometry, build_local_connectivity,
    build_channel_identity, geometry_from_parse_result, geometry_from_inputs_ready,
)
from layauto_v2.normalization.channel_identity_codec import encode_record, decode_record, record_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository


def forbidden(*args, **kwargs):
    raise AssertionError('channel identity/FIN component attempted IO or repository access')


def local_from_parse(parsed):
    assert parsed.status == 'success', parsed.issues
    geometry = build_geometry(geometry_from_parse_result(parsed))
    effective = build_effective_geometry(geometry)
    local = build_local_connectivity(effective)
    assert local.status == 'success' and local.value is not None, local.issues
    return local


def verify(result, local, counts):
    assert result.status == 'success' and not result.issues, result.issues
    draft = result.value
    assert draft is not None
    assert result.input is local
    assert draft.local == local.value
    assert result.completed == local.completed
    assert result.body_evidence is local.body_evidence
    captured = result.input.input.input.input.semantic_input.parse.sources
    assert len(captured) == 31
    acquired = {source.uri: source for source in captured}
    assert all(hashlib.sha256(source.data).hexdigest() == source.sha256 for source in captured)
    assert all(ref.uri in acquired and acquired[ref.uri].sha256 == ref.sha256
               for evidence in result.completed for ref in evidence.sources)
    assert result.semantic.value is not None
    assert draft.source == result.semantic.value.source
    identities = {identity.query_key: identity for identity in result.semantic.value.device_identities}
    seeds = {seed.record['record_id']: seed for seed in result.semantic.value.device_seeds}
    assert len(draft.seeds) == len(seeds)
    for seed in draft.seeds:
        original = seeds[seed.record['record_id']]
        assert seed.device_id == original.semantic_id
        assert seed.query_key == original.query_key and seed.record == original.record
        assert seed.identity_provenance == identities[seed.query_key].provenance
    assert len(result.semantic.value.net_seeds) > 0  # retained, not consumed as net proof
    assert len(draft.associations) == len(draft.measurements) == 2
    measures = {row.channel_ref: row for row in draft.measurements}
    actual = {row.device_id.name: measures[row.channel_ref].count for row in draft.associations}
    assert actual == counts, actual
    layout = draft.local.effective.base.layout
    # MR-008/009's independently enumerated full crossing sets, expressed here
    # as exact nm coordinates rather than runtime shape names or an oracle load.
    starts = {'MN0': (24, 34, 44, 54, 64)[:counts['MN0']],
              'MP0': (114, 124, 134, 144, 154, 164, 174)}
    for association in draft.associations:
        qualified = tuple(row for row in measures[association.channel_ref].evaluations
                          if row.status == 'qualified')
        crossings_nm = {tuple(layout.units.canonical_to_nm(value) for value in row.crossing.bounds)
                        for row in qualified}
        originals_nm = {tuple(layout.units.canonical_to_nm(value) for value in layout.record(row.fin_id).rect.bounds)
                        for row in qualified}
        ys = starts[association.device_id.name]
        assert crossings_nm == {(Fraction(58), Fraction(y), Fraction(62), Fraction(y + 2)) for y in ys}
        assert originals_nm == {(Fraction(10), Fraction(y), Fraction(110), Fraction(y + 2)) for y in ys}
    assert len(draft.local.effective.base.layout.records) == 40
    assert sum(record.layer == 'FIN' for record in draft.local.effective.base.layout.records) == 18
    assert len(local.body_evidence.payload['shapes']) == 6
    assert len(draft.local.nodes) == 14 and len(draft.local.edges) == 8
    assert len(draft.local.components) == 6 and len(draft.local.audits) == 16
    assert draft.local.local_enclosure_status == local.value.local_enclosure_status == 'pass'
    assert draft.local.audits == local.value.audits
    for measured in measures.values():
        assert measured.length_nm == Fraction(4)
        assert len(measured.evaluations) == 18
        assert {row.fin_id for row in measured.evaluations} == {
            record.id for record in layout.records if record.layer == 'FIN'}
        assert all(row.width_nm == Fraction(2) and row.source == layout.record(row.fin_id).source
                   for row in measured.evaluations)
        assert not measured.unresolved_relations
        qualified = tuple(row for row in measured.evaluations if row.status == 'qualified')
        assert len(qualified) == measured.count
        assert all(row.width_nm == Fraction(2) for row in qualified)
        assert all(row.crossing is not None and row.source.sha256 for row in qualified)
    nodes = {node.ref: node for node in draft.local.nodes}
    components = {component.ref: component for component in draft.local.components}
    assert len(draft.topology) == 2
    assert draft.topology[0].gate_nodes == draft.topology[1].gate_nodes
    assert len(draft.topology[0].gate_nodes) == 1
    terminals = set()
    for links in draft.topology:
        assert all(nodes[ref].layer == 'POLY' for ref in links.gate_nodes)
        assert nodes[links.source_node].region.role == 'S'
        assert nodes[links.drain_node].region.role == 'D'
        assert links.source_node in components[links.source_component].members
        assert links.drain_node in components[links.drain_component].members
        terminals.update((links.source_node, links.drain_node))
    assert len(terminals) == 4
    if counts['MN0'] == 5:
        assert draft.comparison_status == 'equal'
        assert not draft.differences
        assert all(comparison.status == 'equal' for comparison in draft.comparisons)
    else:
        assert draft.comparison_status == 'mismatch'
        assert len(draft.differences) == 1
        difference = draft.differences[0]
        assert difference.device_id.name == 'MN0'
        assert difference.axis == 'fins_per_finger'
        assert difference.measured == Fraction(4) and difference.declared.exact == Fraction(5)
    assert not any(hasattr(draft, key) for key in ('net_id', 'baseline', 'terminal', 'no_change'))
    started = time.perf_counter()
    wire = encode_record(result)
    encode_seconds = time.perf_counter() - started
    started = time.perf_counter()
    restored = decode_record(wire)
    decode_seconds = time.perf_counter() - started
    assert restored == result
    assert record_digest(result) == hashlib.sha256(wire).hexdigest()
    assert encode_record(restored) == wire
    try:
        replace(draft, measurements=draft.measurements[1:])
    except ValueError:
        pass
    else:
        raise AssertionError('incomplete public measurements accepted')
    return {'counts': actual, 'wire_sha256': hashlib.sha256(wire).hexdigest(),
            'wire_bytes': len(wire), 'encode_seconds': encode_seconds,
            'decode_seconds': decode_seconds, 'raw_FIN_records': 18,
            'comparison_status': draft.comparison_status, 'difference_count': len(draft.differences),
            'local_enclosure_status': draft.local.local_enclosure_status,
            'local_nodes': len(draft.local.nodes), 'local_edges': len(draft.local.edges),
            'local_components': len(draft.local.components), 'body_shapes': 6}


def make_mismatch_input(fixture, destination):
    # Copy original fixture bytes only; no oracle/spec/expected is parsed or
    # used as an answer. Complete owner/site inputs are retained unchanged.
    shutil.copytree(fixture, destination)
    # Existing approved replacement captures, not regenerated geometry/answers.
    for name in ('source.gds', 'query/header.json', 'query/raw/device_info_Q17.txt',
                 'query/normalized/device_regions.yaml', 'body/context.json'):
        shutil.copyfile(fixture / 'failures/extraction_mismatch' / name, destination / name)
    return destination / 'site_config.yaml'


def main():
    fixture = Path(sys.argv[1]).resolve()
    installed = Path(layauto_v2.__file__).resolve()
    purelib = Path(sysconfig.get_path('purelib')).resolve()
    assert installed.is_relative_to(purelib), (installed, purelib)
    print('W011 installed smoke: acquire direct/readback captures', file=sys.stderr, flush=True)
    parsed = read_inputs(fixture / 'site_config.yaml')
    direct_local = local_from_parse(parsed)
    repository = PublicationRepository()
    ready = prepare_inputs(repository, RunRequest(
        proposed_run_id='w011-installed-run', lineage_id='w011-installed-lineage',
        idempotency_key='create-w011-installed', site_path=str(fixture / 'site_config.yaml')))
    assert isinstance(ready, InputsReady)
    checkpoint = repository.load_checkpoint(ready.run_id)
    parse, tool = repository.read(ready.parse_ref), repository.read(ready.tool_ref)
    audits = tuple(repository.read(ref) for ref in ready.evidence_refs)
    attempt = repository.load_attempt(ready.run_id)
    readback_local = build_local_connectivity(build_effective_geometry(build_geometry(
        geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits))))
    assert readback_local.status == 'success', readback_local.issues
    with tempfile.TemporaryDirectory(prefix='w011-mismatch-', dir=Path.cwd()) as temp:
        mismatch_parse = read_inputs(make_mismatch_input(fixture, Path(temp) / 'input'))
        mismatch_local = local_from_parse(mismatch_parse)
        with ExitStack() as stack:
            for target in ('open', 'read_bytes', 'read_text', 'resolve'):
                stack.enter_context(patch.object(Path, target, forbidden))
            stack.enter_context(patch.object(builtins, 'open', forbidden))
            stack.enter_context(patch.object(io, 'open', forbidden))
            for target in ('read', 'load_checkpoint', 'load_attempt'):
                stack.enter_context(patch.object(repository, target, forbidden))
            print('W011 installed smoke: build direct', file=sys.stderr, flush=True)
            direct = build_channel_identity(direct_local)
            print('W011 installed smoke: build readback', file=sys.stderr, flush=True)
            readback = build_channel_identity(readback_local)
            print('W011 installed smoke: build extraction mismatch', file=sys.stderr, flush=True)
            mismatch = build_channel_identity(mismatch_local)
            print('W011 installed smoke: reconstruct direct', file=sys.stderr, flush=True)
            direct_checks = verify(direct, direct_local, {'MN0': 5, 'MP0': 7})
            print('W011 installed smoke: reconstruct readback', file=sys.stderr, flush=True)
            readback_checks = verify(readback, readback_local, {'MN0': 5, 'MP0': 7})
            print('W011 installed smoke: reconstruct extraction mismatch', file=sys.stderr, flush=True)
            mismatch_checks = verify(mismatch, mismatch_local, {'MN0': 4, 'MP0': 7})
    assert direct.value == readback.value
    assert direct.semantic.value == readback.semantic.value
    assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repository.load_checkpoint(ready.run_id) == checkpoint
    assert repository.read_terminal(ready.run_id) is None
    print(json.dumps({'python': sys.version, 'executable': sys.executable,
                      'package': str(installed), 'distribution_version': importlib.metadata.version('layauto'),
                      'direct': direct_checks, 'readback': readback_checks,
                      'extraction_mismatch': mismatch_checks, 'attempt_unchanged': True,
                      'checkpoint_unchanged': True, 'terminal_absent': True,
                      'limitations': ['Finite synthetic smoke, not full net/body/model equivalence or run completion.']}, indent=2))


if __name__ == '__main__':
    main()
