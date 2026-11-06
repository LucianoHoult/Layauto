"""Independent captured-source/role review; never imports expected answers.

Temporary fixture helper only changes input labels and rebinds actual bytes.
Graph comparison uses physical signatures and full edge/component multisets.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import fields, replace
from pathlib import Path
from unittest.mock import patch
import builtins
import hashlib
import io
import json
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tests/contracts'))
from w005_cases import copy_input
from w007_cases import query_only_rename
from layauto_v2.domain.codec import canonical_bytes
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRef
from layauto_v2.domain.local_connectivity import ContactComponent, ContactEdge, LocalRef
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (build_geometry, geometry_from_parse_result,
    geometry_from_inputs_ready, build_effective_geometry, build_local_connectivity)
from layauto_v2.normalization.local_connectivity import LocalConnectivityResult
from layauto_v2.normalization.local_connectivity_codec import encode_record, decode_record, record_digest
from layauto_v2.normalization.effective_codec import record_digest as effective_digest
from layauto_v2.normalization.geometry_input import GeometryInputError
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.local_connectivity import build_local_connectivity_draft

FIXTURE = ROOT / 'tests/fixtures/w003_m1'
RESULT = {'cases': []}


def copy_map(v):
    if isinstance(v, Mapping):
        return {k: copy_map(x) for k, x in v.items()}
    if type(v) is tuple:
        return [copy_map(x) for x in v]
    return v


def forged(record, **changes):
    out = object.__new__(type(record))
    for field in fields(record):
        object.__setattr__(out, field.name, changes.get(field.name, getattr(record, field.name)))
    return out


def block(*args, **kwargs):
    raise AssertionError('W010 attempted IO/repository access')


def no_io(repo=None):
    stack = ExitStack()
    for owner, names in ((Path, ('open', 'read_bytes', 'read_text', 'resolve')),
                         (builtins, ('open',)), (io, ('open',))):
        for name in names:
            stack.enter_context(patch.object(owner, name, block))
    if repo is not None:
        for name in ('read', 'load_attempt', 'load_checkpoint', 'read_terminal'):
            stack.enter_context(patch.object(repo, name, block))
    return stack


def accept(name, fn):
    t0 = time.monotonic()
    value = fn()
    RESULT['cases'].append({'name': name, 'status': 'pass', 'seconds': time.monotonic()-t0})
    return value


def reject(name, fn, expected=ValueError, message=None):
    t0 = time.monotonic()
    try:
        fn()
    except expected as exc:
        if message is not None:
            assert message in str(exc), (name, str(exc))
        row = {'name': name, 'status': 'rejected', 'exception': type(exc).__name__,
               'message': str(exc), 'seconds': time.monotonic()-t0}
        if hasattr(exc, 'issue'):
            row['located'] = {'code': exc.issue.code, 'uri': exc.issue.source.uri,
                              'field': exc.issue.source.field}
        RESULT['cases'].append(row)
    else:
        raise AssertionError(name + ' unexpectedly accepted')


def physical_signature(draft):
    keys = {n.ref: (n.layer, n.region.role, tuple(r.bounds for r in n.region.rectangles))
            for n in draft.nodes}
    edges = []
    for edge in draft.edges:
        c = draft.effective.base.layout.record(edge.connector_id) if edge.connector_id else None
        edges.append((edge.kind, tuple(sorted(keys[r] for r in edge.endpoints)),
                      None if c is None else (c.layer, c.rect.bounds)))
    return (tuple(sorted(keys.values())), tuple(sorted(edges)),
            tuple(sorted(tuple(sorted(keys[r] for r in c.members)) for c in draft.components)))


def actual(root):
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    effective = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
    assert effective.status == 'success'
    before = effective_digest(effective)
    with no_io():
        local = build_local_connectivity(effective)
    assert local.status == 'success' and local.input is effective
    assert local.completed == effective.completed
    assert local.body_evidence is effective.body_evidence
    assert local.value.effective is effective.value
    assert effective_digest(effective) == before
    return local


def coherent_capture_forgery(original, owner):
    eff = original.input
    geometry = eff.input
    source = geometry.input
    parse = source.parse
    value = copy_map(parse.value)
    if owner == 'rules':
        value['tech'][owner]['rules'][4]['parameters']['enclosure_nm'] = 2
    elif owner == 'physical':
        value['tech'][owner]['operators']['cross_layer_contact/1'] = 'unacquired alternative'
    elif owner == 'drawn':
        next(row for row in value['tech'][owner]['layers'] if row['name'] == 'VIA0')['electrical_connects'] = ['POLY', 'M1']
    else:
        value['tech'][owner]['unit_scale_contract']['canonical_tick_nm'] = 2
    completed = tuple(replace(r, payload={'bundle': value['tech_bundle'], 'owners': value['tech']})
                      if r.kind == 'tech' else r for r in parse.completed)
    changed_parse = replace(parse, value=value, completed=completed)
    changed_source = forged(source, semantic_input=forged(source.semantic_input, parse=changed_parse))
    changed_geometry = forged(geometry, input=changed_source, completed=completed)
    return forged(eff, input=changed_geometry, completed=completed)


def main():
    start = time.monotonic()
    direct = accept('actual_direct_no_io_retained_prior', lambda: actual(FIXTURE))
    repo = PublicationRepository()
    request = RunRequest(proposed_run_id='premerge-source-run', lineage_id='premerge-source-lineage',
                         idempotency_key='premerge-source-request', site_path=str(FIXTURE / 'site_config.yaml'))
    ready = prepare_inputs(repo, request)
    assert isinstance(ready, InputsReady)
    checkpoint = repo.load_checkpoint(ready.run_id)
    attempt = repo.load_attempt(ready.run_id)
    geometry_input = geometry_from_inputs_ready(ready, checkpoint, repo.read(ready.parse_ref),
        repo.read(ready.tool_ref), tuple(repo.read(r) for r in ready.evidence_refs))
    eff = build_effective_geometry(build_geometry(geometry_input))
    with no_io(repo):
        readback = accept('actual_readback_no_io', lambda: build_local_connectivity(eff))
    assert readback.status == 'success' and readback.input is eff
    assert readback.completed == eff.completed and readback.body_evidence is eff.body_evidence
    assert readback.input.input.input.readback is geometry_input.readback
    assert repo.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repo.load_checkpoint(ready.run_id) == checkpoint and repo.read_terminal(ready.run_id) is None
    assert physical_signature(direct.value) == physical_signature(readback.value)
    RESULT['direct_readback_equivalent'] = True
    rules = direct.value.binding.rules
    tech = next(r for r in direct.completed if r.kind == 'tech')
    assert rules.payload == direct.input.input.input.value['tech']['rules']
    assert rules.sources == (tech.sources[6],)
    RESULT['rules_actual_role_index'] = 6
    for label, source in (('unacquired_uri', SourceRef('not-captured.json', rules.sources[0].sha256)),
                          ('captured_wrong_role', tech.sources[1])):
        neutral = accept('neutral_rules_origin_'+label, lambda: build_local_connectivity_draft(
            direct.value.effective, replace(rules, sources=(source,))))
        reject('captured_rules_origin_'+label, lambda: replace(direct, value=neutral),
               message='local graph/audit differs')
    for owner in ('rules', 'physical', 'drawn', 'formats'):
        bad = coherent_capture_forgery(direct, owner)
        for entry, fn in (('builder', lambda: build_local_connectivity(bad)),
                          ('constructor', lambda: LocalConnectivityResult('success', direct.value, (), bad.completed, bad))):
            reject('grouped_'+owner+'_'+entry, fn, GeometryInputError,
                   'captured bytes differ from accepted /tech evidence')
    reject('foreign_unit', lambda: replace(direct.value, binding=replace(direct.value.binding,
        unit_ref=GeometryRef('unit', 'f'*64))), message='foreign source/scope/unit/operator binding')
    reject('lost_completed', lambda: replace(direct, completed=()), message='retain all captured completed facts')
    changed_ready = forged(ready, run_id='foreign-run')
    reject('readback_wrong_run', lambda: geometry_from_inputs_ready(changed_ready, checkpoint,
        repo.read(ready.parse_ref), repo.read(ready.tool_ref), tuple(repo.read(r) for r in ready.evidence_refs)))
    draft = direct.value
    body_ends = tuple(sorted((n.ref for n in draft.nodes if n.layer in ('BODY_N', 'BODY_P')), key=lambda r:r.sha256))
    added_edge = ContactEdge('same_layer', body_ends, draft.binding.ref)
    all_members = tuple(sorted((n.ref for n in draft.nodes), key=lambda r:r.sha256))
    extra_ref = LocalRef('node', 'e'*64)
    foreign_edge = replace(draft.edges[0], endpoints=tuple(sorted((draft.edges[0].endpoints[0], extra_ref), key=lambda r:r.sha256)))
    modifications = {
        'added_node': {'nodes': draft.nodes + draft.nodes[:1]},
        'added_body_edge': {'edges': tuple(sorted(draft.edges+(added_edge,), key=lambda e:e.ref.sha256))},
        'false_union': {'components': (ContactComponent(all_members, draft.binding.ref),)},
        'false_audit': {'audits': (replace(draft.audits[0], status='violation'),)+draft.audits[1:]},
        'foreign_endpoint': {'edges': (foreign_edge,)+draft.edges[1:]},
    }
    for label, changes in modifications.items():
        reject('constructor_'+label, lambda: replace(draft, **changes))
        malformed = encode_record(forged(direct, value=forged(draft, **changes)))
        reject('nested_result_wire_'+label, lambda: decode_record(malformed))
    reject('constructor_false_success', lambda: replace(direct, value=None), message='success requires a complete draft')
    reject('nested_wire_false_success', lambda: decode_record(encode_record(forged(direct, value=None))),
           message='success requires a complete draft')
    with tempfile.TemporaryDirectory(prefix='w010-source-', dir='/tmp') as temp:
        root = copy_input(Path(temp))
        query_only_rename(root)
        renamed = accept('actual_renamed_query_inputs', lambda: actual(root))
        assert physical_signature(renamed.value) == physical_signature(direct.value)
        assert renamed.value.semantic_digest == direct.value.semantic_digest
        # Query labels are outside the geometry draft's identity; the complete
        # captured result binds those changed inputs separately.
        assert record_digest(renamed) != record_digest(direct)
        RESULT['renamed_query_draft_ref_equal'] = renamed.value.ref == direct.value.ref
        RESULT['renamed_query_same_complete_graph'] = True
    wire = encode_record(readback)
    rebuilt = accept('readback_roundtrip', lambda: decode_record(wire))
    assert rebuilt == readback and encode_record(rebuilt) == wire
    assert record_digest(rebuilt) == record_digest(readback)
    RESULT.update(status='pass', python=sys.version, root=str(ROOT), elapsed_seconds=time.monotonic()-start,
                  wire_bytes=len(wire), wire_sha256=hashlib.sha256(wire).hexdigest(),
                  semantic_digest=direct.value.semantic_digest,
                  counts=[len(direct.value.nodes), len(direct.value.edges), len(direct.value.components), len(direct.value.audits)])
    print(json.dumps(RESULT, indent=2))


if __name__ == '__main__':
    main()
