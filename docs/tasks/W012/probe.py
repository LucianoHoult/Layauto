"""W012 finite complete-path investigation. No product/test imports or changes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import cProfile
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import json
from pathlib import Path
import platform
import pstats
import resource
import sys
import time

ROOT = Path('/workspace/Layauto')
OVERLAY = Path('/workspace/w012-inputs/extraction-mismatch')
OUT = ROOT / 'docs/tasks/W012'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def source_identity():
    manifest = json.loads((ROOT / 'docs/tasks/W011/verification/source-manifest.json').read_text())
    assert len(manifest['files']) == 262 and len(manifest['runtime_files']) == 100
    assert all(sha((ROOT / name).read_bytes()) == digest for name, digest in manifest['files'].items())
    return {'frozen_commit': manifest['git_head'], 'files': manifest['files'],
            'runtime_files': manifest['runtime_files']}


def census(root):
    """Unique object graph + logical path expansion; no codec/property/repr calls.

    Keep node references alive: ids cannot be reused. FrozenMap is walked via
    dataclass storage, counting actual tuple/key objects. Cycles are rejected.
    Shallow totals omit instance __dict__/allocator/native memory: not RSS.
    """
    nodes, byte_groups, sources = {}, defaultdict(list), []
    counts = Counter()
    def visit(value):
        key = id(value)
        if key in nodes:
            assert nodes[key][2] is not None, 'cycle in investigation graph'
            return nodes[key][2]
        nodes[key] = (value, sys.getsizeof(value), None)
        counts[type(value).__module__ + '.' + type(value).__name__] += 1
        children = []
        if is_dataclass(value) and not isinstance(value, type):
            children = [getattr(value, field.name) for field in fields(value)]
        elif type(value) in (tuple, list):
            children = value
        elif type(value) is dict:
            children = [item for pair in value.items() for item in pair]
        own = len(value) if type(value) is bytes else 0
        if type(value) is bytes:
            byte_groups[(sha(value), len(value))].append(key)
        if type(value).__name__ == 'SourceFile':
            sources.append({'uri': value.uri, 'sha256': value.sha256, 'bytes': len(value.data),
                            'data_object_id': id(value.data)})
        expanded = own + sum(visit(child) for child in children)
        nodes[key] = (value, sys.getsizeof(value), expanded)
        return expanded
    expanded = visit(root)
    return {'unique_objects': len(nodes), 'shallow_object_bytes': sum(row[1] for row in nodes.values()),
            'unique_bytes_objects': sum(len(ids) for ids in byte_groups.values()),
            'unique_bytes_payload': sum(size * len(ids) for (_, size), ids in byte_groups.items()),
            'content_unique_bytes_payload': sum(size for _, size in byte_groups),
            'content_unique_bytes_count': len(byte_groups), 'logical_path_bytes_payload': expanded,
            'equal_content_independent_bytes_extra': sum(size * (len(ids)-1) for (_, size), ids in byte_groups.items()),
            'types': dict(counts), 'sourcefile_unique_objects': sources}


class WireMeter:
    """Observe only existing calls/lengths; never encode/hash an observed value."""
    def __init__(self):
        self.stack = []
        self.events = defaultdict(Counter)
        self.bytes = defaultdict(Counter)
        self.undo = []

    @contextmanager
    def active(self):
        for modname in ('domain.publication_codec', 'normalization.codec', 'normalization.geometry_codec',
                        'normalization.effective_codec', 'normalization.local_connectivity_codec',
                        'normalization.channel_identity_codec'):
            module = importlib.import_module('layauto_v2.' + modname)
            for name in ('encode_record', 'decode_record'):
                original = getattr(module, name)
                self.undo.append((module, name, original))
                def wrapper(value, _original=original, _name=modname + '.' + name):
                    label = _name + ':' + type(value).__name__
                    parent = self.stack[-1] if self.stack else '<root>'
                    self.stack.append(label)
                    try:
                        result = _original(value)
                        row = self.events[(parent, label)]
                        row['calls'] += 1
                        if type(result) is bytes:
                            row['output_bytes_sum'] += len(result)
                            row['output_bytes_max'] = max(row['output_bytes_max'], len(result))
                        if type(value) is bytes:
                            row['input_bytes_sum'] += len(value)
                        return result
                    finally:
                        self.stack.pop()
                setattr(module, name, wrapper)
        module = importlib.import_module('layauto_v2.domain.codec')
        original = module._wire
        self.undo.append((module, '_wire', original))
        def wire(value):
            if type(value) is bytes:
                label = self.stack[-1] if self.stack else '<root>'
                row = self.bytes[label]
                row['calls'] += 1
                row['payload_bytes'] += len(value)
                row['hex_characters'] += 2 * len(value)
            return original(value)
        module._wire = wire
        try:
            yield self
        finally:
            for module, name, original in reversed(self.undo):
                setattr(module, name, original)
            self.undo.clear()

    def result(self):
        return {'edges': [{'parent': parent, 'call': label, **row}
                          for (parent, label), row in sorted(self.events.items())],
                'bytes_to_hex': {label: dict(row) for label, row in self.bytes.items()}}


def check_result(result, local, mismatch):
    draft = result.value
    assert result.status == 'success' and not result.issues and draft is not None
    assert result.input is local and draft.local is local.value
    assert result.completed == local.completed and result.body_evidence is local.body_evidence
    assert result.semantic.value.source == draft.source
    graph = draft.local
    assert len(graph.edges) == 8 and len(graph.components) == 6
    assert graph.local_enclosure_status == 'pass'
    records = graph.effective.base.layout.records
    fins = {row.id: row for row in records if row.layer == 'FIN'}
    assert len(records) == 40 and len(fins) == 18
    measurements = {row.channel_ref: row for row in draft.measurements}
    by_name = {row.device_id.name: measurements[row.channel_ref] for row in draft.associations}
    assert {name: row.count for name, row in by_name.items()} == {'MN0': 4 if mismatch else 5, 'MP0': 7}
    expected_y = {'MN0': ((24,26),(34,36),(44,46),(54,56)) + (() if mismatch else ((64,66),)),
                  'MP0': ((114,116),(124,126),(134,136),(144,146),(154,156),(164,166),(174,176))}
    crossings = {}
    for name, row in by_name.items():
        assert {e.fin_id for e in row.evaluations} == set(fins)
        assert len(row.evaluations) == 18 and row.length_nm == 4
        qualified = [e for e in row.evaluations if e.status == 'qualified']
        assert {e.crossing.bounds for e in qualified} == {(58,lo,62,hi) for lo,hi in expected_y[name]}
        assert all(e.width_nm == 2 and e.source == fins[e.fin_id].source for e in row.evaluations)
        assert not row.unresolved_relations
        crossings[name] = [list(map(str, e.crossing.bounds)) for e in qualified]
    assert all(row.full_coverage and row.coverage_fraction == 1 for row in draft.associations)
    if mismatch:
        assert len(draft.differences) == 1 and draft.comparison_status == 'mismatch'
        diff = draft.differences[0]
        assert diff.axis == 'fins_per_finger' and diff.measured == 4 and diff.declared.exact == 5
        assert any(e.status == 'touch' and fins[e.fin_id].rect.bounds == (10,64,110,66)
                   for e in by_name['MN0'].evaluations)
    else:
        assert not draft.differences and draft.comparison_status == 'equal'
    return {'counts': {name: row.count for name,row in by_name.items()}, 'crossings': crossings,
            'difference_count': len(draft.differences), 'comparison_status': draft.comparison_status,
            'local_nodes': len(graph.nodes), 'local_edges': len(graph.edges), 'local_components': len(graph.components),
            'T05_audits': len(graph.audits), 'T05_status': graph.local_enclosure_status,
            'body_kind': result.body_evidence.kind, 'complete_evaluations': 36,
            'partial_unknown': 'no unresolved/partial counts in these three fixtures; broader negatives inherited from same W011 source'}


def selfcheck():
    sys.path.insert(0, str(ROOT))
    shared = bytes(bytearray(b'abc'))
    equal = bytes(bytearray(b'abc'))
    assert shared is not equal
    graph = census((shared, shared, equal))
    assert graph['unique_bytes_payload'] == 6 and graph['content_unique_bytes_payload'] == 3
    assert graph['logical_path_bytes_payload'] == 9 and graph['equal_content_independent_bytes_extra'] == 3
    from layauto_v2.domain.codec import canonical_bytes, decode
    from layauto_v2.domain.evidence import SourceRef
    from layauto_v2.domain import publication_codec
    value = SourceRef('selfcheck', 'a' * 64)
    plain = publication_codec.encode_record(value)
    with WireMeter().active() as meter:
        observed = publication_codec.encode_record(value)
        assert publication_codec.decode_record(observed) == value
        assert decode(canonical_bytes(b'abc')) == b'abc'
    assert observed == plain and not meter.stack
    # decode also re-encodes canonically, so this small byte value is seen twice.
    assert meter.result()['bytes_to_hex']['<root>']['payload_bytes'] == 6
    assert meter.result()['bytes_to_hex']['<root>']['calls'] == 2
    dump(OUT / 'selfcheck.json', {'status': 'passed', 'tool_sha256': sha(Path(__file__).read_bytes()),
         'checks': ['shared vs equal independent bytes', 'path vs unique byte counts',
                    'hook does not change canonical output/roundtrip', 'hook restoration and byte length accounting'],
         'graph': graph, 'meter': meter.result(), 'source_identity': source_identity()})
    print('W012 lightweight selfcheck passed', flush=True)


def run(case, mode, output):
    sys.path.insert(0, str(ROOT))
    from layauto_v2.domain.publication import InputsReady, RunRequest
    from layauto_v2.importers import read_inputs
    from layauto_v2.normalization import (build_geometry, build_effective_geometry, build_local_connectivity,
        build_channel_identity, geometry_from_parse_result, geometry_from_inputs_ready)
    from layauto_v2.normalization import channel_identity_codec as codec
    from layauto_v2.pipeline import prepare_inputs
    from layauto_v2.repository import PublicationRepository
    identity = source_identity()
    started = datetime.now(timezone.utc).isoformat()
    selected = OVERLAY if case == 'extraction-mismatch' else ROOT / 'tests/fixtures/w003_m1'
    times, phases = {}, {}
    gc.collect()  # one explicit collection before acquisition; default GC thereafter

    def measure(name, call):
        profile = cProfile.Profile() if mode == 'profile' else None
        meter = WireMeter() if mode == 'profile' else None
        print('START ' + name, flush=True)
        start = time.perf_counter()
        if profile:
            with meter.active():
                profile.enable()
                try:
                    result = call()
                finally:
                    profile.disable()
        else:
            result = call()
        times[name] = time.perf_counter() - start
        if profile:
            stat = pstats.Stats(profile)
            rows = []
            for (filename, lineno, func), (primitive, calls, exclusive, cumulative, callers) in stat.stats.items():
                rows.append({'file': filename, 'line': lineno, 'function': func,
                             'primitive_calls': primitive, 'calls': calls, 'exclusive_seconds': exclusive,
                             'cumulative_seconds': cumulative})
            phases[name] = {'functions': sorted(rows, key=lambda r: -r['exclusive_seconds']), 'wire': meter.result()}
        print('DONE ' + name + ' ' + str(times[name]), flush=True)
        return result

    repository = ready = attempt = checkpoint = parse = tool = audits = None
    if case == 'normal-readback':
        repository = PublicationRepository()
        request = RunRequest(proposed_run_id='w012-investigation-run', lineage_id='w012-investigation-lineage',
                             idempotency_key='create-w012', site_path=str(selected / 'site_config.yaml'))
        ready = measure('W006_prepare_inputs', lambda: prepare_inputs(repository, request))
        assert isinstance(ready, InputsReady)
        def caller_read():
            return (repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
                    repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs),
                    repository.load_attempt(ready.run_id))
        checkpoint, parse, tool, audits, attempt = measure('W006_caller_reads', caller_read)
        parsed = parse.result
        geometry = measure('W008_adapter_and_build', lambda: build_geometry(
            geometry_from_inputs_ready(ready, checkpoint, parse, tool, audits)))
    else:
        parsed = measure('W005_read_inputs', lambda: read_inputs(selected / 'site_config.yaml'))
        assert parsed.status == 'success', parsed.issues
        geometry = measure('W008_adapter_and_build', lambda: build_geometry(geometry_from_parse_result(parsed)))
    effective = measure('W009_build', lambda: build_effective_geometry(geometry))
    local = measure('W010_build', lambda: build_local_connectivity(effective))
    result = measure('W011_build', lambda: build_channel_identity(local))
    info = check_result(result, local, case == 'extraction-mismatch')
    # All upstream roots and original complete Result remain alive during both operations.
    wire = measure('W011_result_encode', lambda: codec.encode_record(result))
    restored = measure('W011_result_decode', lambda: codec.decode_record(wire))
    assert restored == result
    # Equality of the complete DTO covers all sources/local graph/T05/body and semantics.
    assert restored.input.value == local.value and restored.body_evidence == local.body_evidence
    if ready is not None:
        assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
        assert repository.load_checkpoint(ready.run_id) == checkpoint
        assert repository.read_terminal(ready.run_id) is None
        assert result.input.input.input.input.readback is not None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Baseline peak fixed before optional diagnostic walks. Hash only final output, outside timing.
    receipt = {'case': case, 'mode': mode, 'started_at_utc': started,
               'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
               'tool_sha256': sha(Path(__file__).read_bytes()), 'source_identity': identity,
               'input_site': str(selected / 'site_config.yaml'), 'wall_seconds': times,
               'process_peak_rss_kib': peak, 'wire_bytes': len(wire), 'wire_sha256': sha(wire),
               'capture_sources': [{'uri': s.uri, 'sha256': s.sha256, 'bytes': len(s.data)} for s in parsed.sources],
               'result': info, 'public_roundtrip_equal': True, 'readback_unsealed_checkpoint_unchanged_no_terminal': ready is not None,
               'gc_enabled': gc.isenabled(), 'gc_threshold': gc.get_threshold()}
    if mode == 'profile':
        receipt['result_graph'] = census(result)
        receipt['decoded_result_graph'] = census(restored)
        receipt['retained_roots_graph'] = census((parsed, geometry, effective, local, result, restored, wire,
                                                ready, checkpoint, parse, tool, audits, attempt))
        dump(output.with_suffix('.profile.json'), phases)
    assert source_identity() == identity
    receipt['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    dump(output, receipt)
    print(json.dumps({key: receipt[key] for key in ('case','mode','wall_seconds','wire_bytes','wire_sha256','process_peak_rss_kib')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selfcheck', action='store_true')
    parser.add_argument('--case', choices=('normal-direct','normal-readback','extraction-mismatch'))
    parser.add_argument('--mode', choices=('baseline','profile'), default='baseline')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.selfcheck:
        selfcheck()
    else:
        assert args.case and args.output
        run(args.case, args.mode, args.output)
