"""Independent W010 public composition and hand-authored graph audit.

No spec/oracle/expected file supplies runtime inputs or graph expectations.
The unchanged-fixture inventory hashes all fixture bytes, including answer
files, solely as a preservation check. Source acquisition happens once per
direct/readback route, and file/repository access is forbidden during W010.
"""
from __future__ import annotations

import builtins
import hashlib
import io
import json
import sys
import time
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, geometry_from_parse_result, geometry_from_inputs_ready,
    build_effective_geometry, build_local_connectivity,
)
from layauto_v2.normalization.effective_codec import record_digest
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.state.local_connectivity import build_local_connectivity_draft

REPO = Path(__file__).resolve().parents[4]
FIXTURE = REPO / 'tests/fixtures/w003_m1'
EXPECTED = {
    'ON.S': ('OD', ((20, 20, 58, 70),)), 'ON.D': ('OD', ((62, 20, 100, 70),)),
    'OP.S': ('OD', ((20, 110, 58, 180),)), 'OP.D': ('OD', ((62, 110, 100, 180),)),
    'LN': ('LI', ((28, 30, 34, 55),)), 'LP': ('LI', ((28, 130, 34, 155),)),
    'LY': ('LI', ((84, 30, 90, 165),)), 'G': ('POLY', ((58, 10, 62, 190),)),
    'MN': ('M1', ((0, 48, 45, 58),)), 'MP': ('M1', ((0, 148, 45, 158),)),
    'MA': ('M1', ((50, 90, 75, 98),)), 'MY': ('M1', ((80, 90, 110, 98),)),
    'BN': ('BODY_N', ((0, 0, 120, 90),)), 'BP': ('BODY_P', ((0, 100, 120, 200),)),
}
CONNECTORS = {
    ('CONTACT', (29, 40, 33, 44)): ('ON.S', 'LN'),
    ('CONTACT', (85, 40, 89, 44)): ('ON.D', 'LY'),
    ('CONTACT', (29, 140, 33, 144)): ('OP.S', 'LP'),
    ('CONTACT', (85, 140, 89, 144)): ('OP.D', 'LY'),
    ('VIA0', (29, 50, 33, 54)): ('LN', 'MN'),
    ('VIA0', (29, 150, 33, 154)): ('LP', 'MP'),
    ('VIA0', (85, 92, 89, 96)): ('LY', 'MY'),
    ('GCONTACT', (59, 92, 61, 96)): ('G', 'MA'),
}
COMPONENTS = {
    frozenset(('ON.S', 'LN', 'MN')), frozenset(('OP.S', 'LP', 'MP')),
    frozenset(('ON.D', 'OP.D', 'LY', 'MY')), frozenset(('G', 'MA')),
    frozenset(('BN',)), frozenset(('BP',)),
}


def inventory():
    return {str(p.relative_to(FIXTURE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(FIXTURE.rglob('*')) if p.is_file()}


def forbidden(*args, **kwargs):
    raise AssertionError('pure W010 attempted new IO or repository access')


def check_graph(result):
    assert result.status == 'success' and not result.issues
    draft = result.value
    reverse = {value: name for name, value in EXPECTED.items()}
    actual = {(node.layer, tuple(rect.bounds for rect in node.region.rectangles)) for node in draft.nodes}
    assert actual == set(reverse) and len(draft.nodes) == 14
    names = {node.ref: reverse[node.layer, tuple(rect.bounds for rect in node.region.rectangles)]
             for node in draft.nodes}
    edges = {}
    for edge in draft.edges:
        assert edge.kind == 'connector'
        record = draft.effective.base.layout.record(edge.connector_id)
        edges[record.layer, record.rect.bounds] = frozenset(names[ref] for ref in edge.endpoints)
    assert edges == {key: frozenset(value) for key, value in CONNECTORS.items()} and len(draft.edges) == 8
    assert {frozenset(names[ref] for ref in group.members) for group in draft.components} == COMPONENTS
    assert len(draft.components) == 6 and len(draft.audits) == 16
    assert draft.local_enclosure_status == 'pass'
    assert all(audit.status == 'pass' and audit.margin_ticks == Fraction(1) for audit in draft.audits)
    assert draft.coverage['scope'] == 'local_flat_cell/1'
    assert len(result.body_evidence.payload['shapes']) == 6
    assert len(draft.effective.base.layout.records) == 40 and len(draft.effective.base.fragments) == 41
    return {'nodes': len(draft.nodes), 'edges': len(draft.edges), 'components': len(draft.components),
            'audits': len(draft.audits), 'semantic_digest': draft.semantic_digest}


def reject(call):
    try:
        call()
    except ValueError:
        return True
    raise AssertionError('public captured success accepted forged input')


def main():
    start = time.monotonic()
    before = inventory()
    parsed = read_inputs(FIXTURE / 'site_config.yaml')
    effective = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
    previous_digest = record_digest(effective)
    with patch.object(Path, 'open', forbidden), patch.object(Path, 'read_bytes', forbidden), \
         patch.object(Path, 'read_text', forbidden), patch.object(Path, 'resolve', forbidden), \
         patch.object(builtins, 'open', forbidden), patch.object(io, 'open', forbidden):
        direct = build_local_connectivity(effective)
    direct_summary = check_graph(direct)
    assert direct.input is effective and direct.completed == effective.completed
    assert direct.value.effective is effective.value and direct.body_evidence is effective.body_evidence
    assert record_digest(effective) == previous_digest
    repo = PublicationRepository()
    request = RunRequest(proposed_run_id='w010-independent-review', lineage_id='w010-review-lineage',
                         idempotency_key='w010-review-request', site_path=str(FIXTURE / 'site_config.yaml'))
    ready = prepare_inputs(repo, request)
    assert isinstance(ready, InputsReady)
    checkpoint = repo.load_checkpoint(ready.run_id)
    attempt = repo.load_attempt(ready.run_id)
    readback_input = geometry_from_inputs_ready(
        ready, checkpoint, repo.read(ready.parse_ref), repo.read(ready.tool_ref),
        tuple(repo.read(ref) for ref in ready.evidence_refs))
    readback_effective = build_effective_geometry(build_geometry(readback_input))
    with patch.object(Path, 'open', forbidden), patch.object(Path, 'read_bytes', forbidden), \
         patch.object(Path, 'read_text', forbidden), patch.object(Path, 'resolve', forbidden), \
         patch.object(builtins, 'open', forbidden), patch.object(io, 'open', forbidden), \
         patch.object(repo, 'read', forbidden):
        readback = build_local_connectivity(readback_effective)
    readback_summary = check_graph(readback)
    assert direct.value == readback.value
    assert repo.load_checkpoint(ready.run_id) == checkpoint
    assert repo.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
    assert repo.read_terminal(ready.run_id) is None
    rules = direct.value.binding.rules
    wrong_ref = SourceRef('unacquired-rules.json', rules.sources[0].sha256)
    neutral = build_local_connectivity_draft(direct.value.effective, replace(rules, sources=(wrong_ref,)))
    assertions = {
        'foreign_rules_source_rejected_by_captured_result': reject(lambda: replace(direct, value=neutral)),
        'missing_edge_rejected': reject(lambda: replace(direct.value, edges=direct.value.edges[1:])),
        'false_audit_rejected': reject(lambda: replace(direct.value, audits=(
            replace(direct.value.audits[0], status='violation'),) + direct.value.audits[1:])),
        'missing_completed_rejected': reject(lambda: replace(direct, completed=())),
        'fixture_unchanged': inventory() == before,
    }
    assert all(assertions.values())
    print(json.dumps({'status': 'passed', 'python': sys.version, 'product_head':
                     '0f5029df935bc0acd106aad1bc2be81304d4f442', 'direct': direct_summary,
                     'readback': readback_summary, 'assertions': assertions,
                     'elapsed_seconds': time.monotonic() - start}, indent=2))


if __name__ == '__main__':
    main()
