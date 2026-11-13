"""Independent bounded W013 public-path review; no test helper or saved wire."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.net_annotation import validate_annotation_graph
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, build_local_connectivity,
    build_net_annotation, geometry_from_parse_result,
)
from layauto_v2.normalization import local_connectivity_codec as old
from layauto_v2.normalization import net_annotation_codec as new
from layauto_v2.normalization.net_annotation import NetAnnotationResult


def sha(data):
    return hashlib.sha256(data).hexdigest()


def current_source():
    original = json.loads((ROOT / 'docs/tasks/W013/verification-r2/source-manifest.json').read_text())
    files = {name: sha((ROOT / name).read_bytes()) for name in original['files']}
    assert files == original['files']
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def log(name, **values):
    print(json.dumps({'check': name, **values}, sort_keys=True), flush=True)


source_id = current_source()
log('environment', python=sys.version, source_id=source_id, root=str(ROOT))
started = time.monotonic()
parsed = read_inputs(ROOT / 'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'
geometry = build_geometry(geometry_from_parse_result(parsed))
effective = build_effective_geometry(geometry)
local = build_local_connectivity(effective)
assert local.status == 'success'
graph = local.value
assert graph is not None
edges_before, components_before = graph.edges, graph.components
log('upstream_real_files', nodes=len(graph.nodes), edges=len(graph.edges), components=len(graph.components))

real_decode = old.decode_record
calls = []


def observed_decode(packet):
    calls.append(sha(packet))
    return real_decode(packet)


with patch.object(old, 'decode_record', observed_decode):
    result = build_net_annotation(local)
    build_calls = len(calls)
    wire = new.encode_record(result)
    encode_calls = len(calls) - build_calls
    restored = new.decode_record(wire)
    decode_calls = len(calls) - build_calls - encode_calls
assert (build_calls, encode_calls, decode_calls) == (1, 1, 2)
assert result == restored and result.status == 'success' and not result.issues
assert result.input is local
assert graph.edges is edges_before and graph.components is components_before
assert result.completed is local.completed and result.body_evidence is local.body_evidence
draft = result.value
assert draft is not None
assert draft.binding.scope == 'source_evidence_local_net_annotation/1'
assert draft.binding.validity == 'source_evidence'
assert draft.binding.capture_binding['readback'] is None

# Compute areas directly from retained coordinates, without product area/union
# functions or test expected-value helpers.
total = sum(((rect.x1 - rect.x0) * (rect.y1 - rect.y0)
             for target in draft.targets for rect in target.rectangles), Fraction())
covered = sum(((rect.x1 - rect.x0) * (rect.y1 - rect.y0)
               for fragment in draft.fragments if fragment.evidence_refs
               for rect in fragment.rectangles), Fraction())
assert (total, covered, total-covered) == (35090, 3170, 31920)
assert len(draft.targets) == 14
assert Counter(row.status for row in draft.components) == {'associated': 4, 'unknown': 2}
assert Counter(net.name for row in draft.components for net in row.observed_net_ids) == {
    'A': 1, 'Y': 1, 'VDD': 1, 'VSS': 1}
unknown = {row.component_ref for row in draft.components if row.status == 'unknown'}
assert {target.node.layer for target in draft.targets if target.component_ref in unknown} == {'BODY_N', 'BODY_P'}
by_target = {target.ref: target for target in draft.targets}
assert not any(by_target[fragment.target_ref].node.layer in ('OD', 'BODY_N', 'BODY_P')
               for fragment in draft.fragments if fragment.evidence_refs)
marker = [row for row in draft.classifications if row.classification == 'marker']
assert len(marker) == 1 and marker[0].rectangle.bounds == (145, 180, 150, 185)
assert len(draft.classifications) == 40

packet = decode(wire)
assert set(packet) == {'wire_schema', 'captured_input_wire', 'record'}
old_wire = old.encode_record(local)
assert canonical_bytes(packet['captured_input_wire']) == old_wire
assert set(calls) == {sha(old_wire)}
log('public_roundtrip', status=result.status, old_decode_calls=[build_calls, encode_calls, decode_calls],
    wire_bytes=len(wire), old_wire_bytes=len(old_wire), increment_bytes=len(wire)-len(old_wire),
    wire_sha256=sha(wire), old_wire_sha256=sha(old_wire), total=str(total), covered=str(covered),
    uncovered=str(total-covered), elapsed_seconds=time.monotonic()-started)

# A fully canonical packet with authenticated input but a forged derived field
# must fail after complete input reconstruction; no validator is patched here.
forged = dict(packet.items())
row = dict(packet['record'].items())
fields = dict(row['fields'].items())
fields['status'] = FrozenMap({'scalar': 'error'})
row['fields'] = FrozenMap(fields)
forged['record'] = FrozenMap(row)
try:
    new.decode_record(canonical_bytes(forged))
except ValueError as exc:
    log('canonical_derived_status_tamper', rejected=True, error=str(exc))
else:
    raise AssertionError('canonical forged status accepted')

# Exercise all public authentication boundaries with original exception objects.
# Fail at the old public decoder, preserving cause/context/suppression exactly.
for name, operation in (
    ('builder', lambda: build_net_annotation(local)),
    ('constructor', lambda: NetAnnotationResult(local)),
    ('encoder', lambda: new.encode_record(result)),
    ('decoder', lambda: new.decode_record(wire)),
):
    for cls in (RuntimeError, ValueError, KeyboardInterrupt, SystemExit):
        original = cls('independent-premerge-origin')
        cause, context = RuntimeError('cause'), LookupError('context')
        original.__cause__, original.__context__, original.__suppress_context__ = cause, context, True
        def fail(packet):
            raise original
        try:
            with patch.object(old, 'decode_record', fail):
                operation()
        except BaseException as caught:
            assert caught is original
            assert caught.__cause__ is cause and caught.__context__ is context
            assert caught.__suppress_context__ is True
        else:
            raise AssertionError((name, cls.__name__, 'exception swallowed'))
    log('original_exception_chain', boundary=name, types=4, passed=True)

# Attack the original retained input before copying: same logical values with
# an externally writable FrozenMap backing are inadmissible at the public API.
original_map = local.input.input.input.semantic_input.parse.value
forged_map = object.__new__(FrozenMap)
backing = list(object.__getattribute__(original_map, '_entries'))
object.__setattr__(forged_map, '_entries', backing)
try:
    validate_annotation_graph(forged_map)
except ValueError as exc:
    log('original_map_storage_attack', rejected=True, error=str(exc))
else:
    raise AssertionError('mutable original map storage accepted')

assert current_source() == source_id
log('complete', passed=True, source_stable=True, elapsed_seconds=time.monotonic()-started,
    saved_large_wire=False, fixture_modified=False)
