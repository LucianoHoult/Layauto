"""Compare the rule's located Stage 3 observations with the captured bytes."""
from hashlib import sha256
from pathlib import Path
from struct import unpack_from

import pytest

from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository
from layauto_v2.transactions.initialization import InitializationRejected
from w005_cases import read_json, rebind, write_json
from w023_cases import capture
from w026_cases import inspect_published, stage_rules


def test_source_snapshot_and_ordered_chain(normal_rules):
    ctx, report, _ = normal_rules
    lifecycle = report.for_rule('T09.lifecycle')
    assert lifecycle.status == 'pass'
    checks = lifecycle.observations
    cdl, = (c for c in checks if c.kind == 'cdl_semantics')
    assert cdl.facts['input_digest'] == cdl.facts['snapshot_digest']
    assert cdl.sources[0].sha256 == sha256(ctx.inputs['source_cdl']['raw_document']).hexdigest()
    assert (cdl.sources[1].uri, cdl.sources[2].uri) == (ctx.version.snapshot_ref.id, ctx.version.checkpoint_ref.id)
    assert cdl.object_ids == ('INV_M1_SYNTH',)
    assert cdl.facts['export_readback'] == 'stage_6'
    chain, = (c for c in checks if c.kind == 'ordered_eco_commits')
    assert chain.object_ids == (ctx.version.run_id, ctx.version.head_ref.id)
    assert chain.facts['commits'] == () and chain.facts['expected_count'] == chain.facts['actual_count'] == 0
    assert chain.sources[0].uri == ctx.version.context_ref.id and chain.sources[1].field == '/eco_commits'
    raw = ctx.inputs['gds']['raw_document']
    shapes = [c for c in checks if c.kind in ('frame_signature', 'drawn_signature')]
    assert len(shapes) == len(ctx.inputs['gds']['elements']) == len({c.object_ids for c in shapes})
    frame, = (c for c in shapes if c.kind == 'frame_signature')
    assert frame.facts['input']['layer'] == 'BOUNDARY'
    for shape in shapes:
        ref, snapshot_location, _ = shape.sources
        assert ref.sha256 == sha256(raw).hexdigest()
        xy = unpack_from('>10i', raw, ref.byte_offset + 20)
        bbox = min(xy[::2]), min(xy[1::2]), max(xy[::2]), max(xy[1::2])
        assert shape.facts['input']['rect'] == shape.facts['snapshot']['rect'] == bbox
        assert snapshot_location.field == '/geometry/records/' + shape.object_ids[0]


def test_nonzero_requirement_cannot_certify_zero_change(tmp_path: Path):
    root = stage_rules(tmp_path, 'normal')
    path = root / 'tech/rules.json'
    rules = read_json(path)
    rule, = (r for r in rules['rules'] if r['id'] == 'T09.lifecycle')
    rule['parameters']['ordered_eco_commit_count'] = 1
    write_json(path, rules)
    rebind(root)
    _, report, _ = inspect_published(root, 'nonzero-requirement')
    check = report.for_rule('T09.lifecycle')
    assert check.status == 'indeterminate'
    assert check.issue.source == check.rule.location('parameters/ordered_eco_commit_count')
    assert check.issue.code == 'UnsupportedRuleDeclaration'
    assert check.policy_action == 'indeterminate_then_reject'


def test_unimplemented_lifecycle_operator_is_located_before_publication(tmp_path: Path):
    root = stage_rules(tmp_path, 'normal')
    path = root / 'tech/physical.json'
    config = read_json(path)
    config['operators']['lifecycle/1'] = 'alternate, unsupported semantics'
    write_json(path, config)
    rebind(root)
    repo = PublicationRepository()
    _, req = capture(repo, root, 'unsupported-lifecycle')
    before = repo.snapshot()
    with pytest.raises(InitializationRejected) as failure:
        publish_stage2(repo, req)
    issue, = failure.value.checks.layers['BOUNDARY'].lifecycle_issues
    assert (issue.code, issue.source.uri, issue.source.field) == (
        'UnsupportedLifecycleOperator', 'tech/physical.json', '/operators/lifecycle~11')
    assert issue.source.sha256 == sha256(path.read_bytes()).hexdigest()
    assert repo.load_head('L') is None and repo.snapshot() == before


def test_comparator_detects_semantic_and_frame_differences(normal_rules):
    # A modified snapshot cannot be published by W023. Exercise the read-only
    # comparator directly on detached operands, without forging a repository ref.
    from dataclasses import replace
    from types import SimpleNamespace

    from layauto_v2.constraints.lifecycle import evaluate_lifecycle
    from layauto_v2.domain.codec import FrozenMap

    ctx, report, _ = normal_rules
    original = report.for_rule('T09.lifecycle')
    current = ctx.snapshot.state['current']
    cell = current['cells'][0]
    changed_cell = FrozenMap({**cell, 'ports': tuple(reversed(cell['ports']))})
    changed_current = FrozenMap({**current, 'cells': (changed_cell,)})
    frame, = (o for o in original.observations if o.kind == 'frame_signature')
    key, = frame.object_ids
    geometry = ctx.snapshot.state['geometry']
    record = geometry['records'][key]
    x0, y0, x1, y1 = record['rect']
    changed_record = FrozenMap({**record, 'rect': (x0 + 1, y0, x1, y1)})
    changed_geometry = FrozenMap({**geometry, 'records': {**geometry['records'], key: changed_record}})
    state = FrozenMap({**ctx.snapshot.state, 'current': changed_current, 'geometry': changed_geometry})
    operands = SimpleNamespace(snapshot=replace(ctx.snapshot, state=state), inputs=ctx.inputs, version=ctx.version,
                               source_circuit=ctx.source_circuit, physical=ctx.physical,
                               eco_commits=(SimpleNamespace(id='test-commit'),))
    check = evaluate_lifecycle(operands, original.rule)
    bad = {o.kind: o for o in check.observations if o.status == 'violation'}
    assert check.status == 'violation' and set(bad) == {'cdl_semantics', 'frame_signature', 'ordered_eco_commits'}
    assert bad['cdl_semantics'].facts['input_digest'] != bad['cdl_semantics'].facts['snapshot_digest']
    assert bad['frame_signature'].facts['snapshot']['rect'] == changed_record['rect']
    assert bad['ordered_eco_commits'].facts['commits'] == ('test-commit',)
