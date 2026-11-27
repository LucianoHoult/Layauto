"""Stage 3 contracts through publication, with raw file and byte checks independent of the evaluator."""
import gc
import json
import struct
import weakref
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from layauto_v2.constraints import check_m1_spacing, engine
from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.publication import PipelineResult, RunRequest
from layauto_v2.normalization import initial_state
from layauto_v2.pipeline import open_constraint_context, prepare_inputs, publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w005_cases import read_json, rebind, write_json
from w018_cases import COORDINATE_URI
from w023_cases import capture
from w024_cases import stage

T07 = 'T07.m1_spacing'
IDS = ('T01.frame', 'T02.fin_grid', 'T03.recognition', 'T04.body', 'T05.contact_enclosure',
       'T06.li_spacing', T07, 'T08.terminal_graph', 'T09.lifecycle', 'T10.coverage')


def publish(repo, root, run, *, lineage=None, head=None):
    _, req = capture(repo, root, run, budget=400, lineage=lineage or run, head=head)
    publish_stage2(repo, req)
    return repo.load_attempt(run).context_ref


@pytest.fixture(scope='module')
def published(tmp_path_factory):
    repo, refs, candidates = PublicationRepository(), {}, []
    build = initial_state.build_proposed_initial_state

    def observe(facts):
        candidate = build(facts)
        candidates.append(weakref.ref(candidate))
        return candidate

    with patch.object(initial_state, 'build_proposed_initial_state', observe):
        for run in ('normal', 'c14', 'reuse'):
            with TemporaryDirectory(dir=tmp_path_factory.getbasetemp()) as directory:
                root = stage(Path(directory), 'c14' if run == 'c14' else 'normal')
                if run == 'reuse':
                    refs[run] = publish(repo, root, run, lineage='normal', head=repo.load_head('normal').id)
                else:
                    refs[run] = publish(repo, root, run)
            assert not root.exists()
    gc.collect()
    assert len(candidates) == 2 and all(ref() is None for ref in candidates)
    before = repo.snapshot()
    contexts = {run: open_constraint_context(repo, run, ref) for run, ref in refs.items()}
    assert repo.snapshot() == before
    return repo, contexts


@pytest.mark.parametrize('run,expected', [('normal', 5), ('c14', 4), ('reuse', 5)])
def test_rule_book_and_raw_gds_witnesses(published, run, expected):
    repo, contexts = published
    ctx = contexts[run]
    before = repo.snapshot()
    report = check_m1_spacing(ctx)
    t07 = report.for_rule(T07)
    v = report.version
    assert (v.run_id, v.version, v.snapshot_ref.run_id) == (run, 0, 'normal' if run == 'reuse' else run)
    assert ctx.snapshot.checkpoint_ref == v.original_checkpoint_ref
    assert ctx.snapshot == repo.read(v.snapshot_ref)
    assert v.checkpoint_ref == repo.load_checkpoint(run).ref
    assert v.tool_ref == repo.load_checkpoint(run).tool_ref
    assert repo.read(v.head_ref).snapshot_ref == v.snapshot_ref
    assert repo.load_attempt(run).phase == 'sealed_open' and repo.read_terminal(run) is None
    files = {s.uri: s for s in repo.read(v.tool_ref).sources}
    rules = files[report.catalog.source.uri]
    document = json.loads(rules.data)
    assert rules.sha256 == report.catalog.source.sha256
    assert report.catalog.mandatory_policy == document['mandatory_rule_policy']
    assert tuple(c.rule.id for c in report.checks) == IDS
    assert [c.status for c in report.checks if c.rule.id != T07] == ['pending'] * 9
    for i, c in enumerate(report.checks):
        assert c.rule.source == rules.ref(field=f'/rules/{i}')
        # JSON arrays are frozen to tuples in the product declaration.
        assert c.rule.declaration == freeze_map(document['rules'][i])
    assert t07.threshold_nm == 5 and t07.rule.location('parameters/min_distance_nm') == rules.ref(field='/rules/6/parameters/min_distance_nm')
    assert len(t07.pairs) == 6
    assert min(p.distance_squared_nm2 for p in t07.pairs) == expected ** 2
    assert t07.status == ('pass' if expected == 5 else 'violation')
    assert len(t07.violations) == (expected < 5)
    closest = min(t07.pairs, key=lambda p: p.distance_squared_nm2)
    assert (closest.distance_nm, closest.dx_dbu, closest.dy_dbu, closest.nm_per_dbu) == (expected, expected, 0, 1)
    assert closest.status == t07.status
    by_offset = {s.source.byte_offset: s for s in (closest.first, closest.second)}
    assert set(by_offset) == {2480, 2544}
    for offset, witness in by_offset.items():
        source = files[witness.source.uri]
        assert source.sha256 == witness.source.sha256
        assert source.data[offset:offset + 4] == bytes.fromhex('00040800')  # BOUNDARY
        points = struct.unpack_from('>10i', source.data, offset + 20)
        assert points[:2] == points[-2:]
        bounds = min(points[::2]), min(points[1::2]), max(points[::2]), max(points[1::2])
        assert bounds == witness.rect.bounds == tuple(ctx.snapshot.state['geometry']['records'][witness.record_id]['rect'])
    assert by_offset[2480].rect.bounds == (50, 90, 75, 98)
    assert by_offset[2544].rect.bounds == (75 + expected, 90, 110, 98)
    assert repo.snapshot() == before


def test_reuse_crossed_missing_and_immutable_refs(published):
    repo, ctx = published
    old, second, changed = (ctx[run].version for run in ('normal', 'reuse', 'c14'))
    assert old.context_ref != second.context_ref and old.checkpoint_ref != second.checkpoint_ref
    assert old.tool_ref != second.tool_ref and old.head_ref == second.head_ref and old.snapshot_ref == second.snapshot_ref
    assert old.original_checkpoint_ref == second.original_checkpoint_ref and changed.snapshot_ref != old.snapshot_ref
    assert ctx['c14'].catalog.source == ctx['normal'].catalog.source
    start = repo.snapshot()
    for ref in (None, old.context_ref, changed.context_ref, second.head_ref, replace(second.context_ref, digest='0' * 64)):
        with pytest.raises(RepositoryConflict, match='reuse.*attempt.context_ref') as caught:
            open_constraint_context(repo, 'reuse', ref)
        assert caught.value.code == 'ReadbackConflict'
    mixed = SimpleNamespace(version=old, snapshot=ctx['c14'].snapshot,
                            catalog=ctx['normal'].catalog, physical=ctx['normal'].physical)
    with pytest.raises(TypeError, match='published ConstraintContext'):
        check_m1_spacing(mixed)
    with pytest.raises(ValueError, match='_issuer'):
        replace(ctx['normal'], snapshot=ctx['c14'].snapshot)
    with pytest.raises(TypeError):
        ctx['normal'].catalog.mandatory_policy['scope'] = 'empty'
    with pytest.raises(FrozenInstanceError):
        ctx['normal'].version.version = 1
    assert repo.snapshot() == start


def test_execution_error_is_distinct_and_interrupts_propagate(published, monkeypatch):
    repo, contexts = published
    before = repo.snapshot()

    def fail(*args):
        raise RuntimeError('predicate stopped')

    monkeypatch.setattr(engine, 'evaluate_m1', fail)
    report = check_m1_spacing(contexts['normal'])
    outcome = report.for_rule(T07)
    assert (outcome.status, outcome.policy_action, outcome.issue.code) == ('error', 'error_then_reject', 'PredicateExecutionError')
    assert 'RuntimeError' in outcome.issue.message and outcome.issue.source.field == '/rules/6/exact_evaluator_ref'
    assert sum(c.status == 'pending' for c in report.checks) == 9

    def interrupt(*args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(engine, 'evaluate_m1', interrupt)
    with pytest.raises(KeyboardInterrupt):
        check_m1_spacing(contexts['normal'])
    assert repo.snapshot() == before


@pytest.mark.parametrize('change,code,pointer', [
    ('missing', 'MissingField', '/rules/6/relation_basis'),
    ('threshold', 'RuleDeclarationConflict', '/rules/6'),
    ('unknown', 'UnsupportedRuleVariant', '/rules/6/exact_evaluator_ref'),
    ('relation', 'RuleDeclarationConflict', '/rules/6'),
])
def test_unpublishable_rules_retain_upstream_failure(tmp_path, change, code, pointer):
    repo = PublicationRepository()
    root = stage(tmp_path, 'normal')
    path = root / 'tech/rules.json'
    owner = read_json(path)
    row = owner['rules'][6]
    if change == 'missing':
        del row['relation_basis']
    elif change == 'threshold':
        del row['parameters']['min_distance_nm']
    elif change == 'unknown':
        row['exact_evaluator_ref'] += '-unknown'
    else:
        row['relation_basis'] = 'same_component'
    write_json(path, owner)
    rebind(root)
    result = prepare_inputs(repo, RunRequest(change, change, 'create', str(root / 'site_config.yaml')))
    assert isinstance(result, PipelineResult) and result.deployment_disposition == 'reject'
    failure = repo.read(repo.load_checkpoint(change).failure_ref)
    assert (failure.code, failure.source.uri, failure.source.field) == (code, 'tech/rules.json', pointer)
    assert repo.load_head(change) is None
    before = repo.snapshot()
    with pytest.raises(RepositoryConflict, match='terminal'):
        open_constraint_context(repo, change, None)
    assert repo.snapshot() == before


def test_different_grid_threshold_and_owner_are_selected_from_files(tmp_path):
    repo = PublicationRepository()
    root = stage(tmp_path, 'normal')
    grid = yaml.safe_load((root / COORDINATE_URI).read_bytes())
    grid['coordinate_projection']['layers']['M1']['x_edges'].update(pitch_dbu=20, cells=8)
    write_json(root / COORDINATE_URI, grid)

    original = 'tech/rules.json'
    selected = 'tech/chosen-rules.json'
    doc = read_json(root / original)
    row = doc['rules'].pop(6)
    row['parameters']['min_distance_nm'] = 6
    row['predicate'] = row['predicate'].replace('>=5', '>=6')
    doc['rules'].insert(0, row)
    write_json(root / selected, doc)  # Keep the old file in place as a decoy.
    bundle = read_json(root / 'tech.json')
    bundle['owners']['rules']['path'] = selected
    write_json(root / 'tech.json', bundle)
    header = read_json(root / 'query/header.json')
    next(e for e in header['closure']['entries'] if e['uri'] == original)['uri'] = selected
    write_json(root / 'query/header.json', header)
    rebind(root)

    ref = publish(repo, root, 'different')
    ctx = open_constraint_context(repo, 'different', ref)
    outcome = check_m1_spacing(ctx).for_rule(T07)
    assert (outcome.threshold_nm, outcome.status, len(outcome.violations)) == (6, 'violation', 1)
    assert outcome.violations[0].distance_nm == 5 and len(outcome.pairs) == 6
    assert outcome.rule.location('parameters/min_distance_nm').field == '/rules/0/parameters/min_distance_nm'
    assert outcome.rule.source.uri == selected and original not in ctx.snapshot.binding['sources']


@pytest.mark.parametrize('change,expected', [
    ('swap', ('EvaluatorMismatch', 'tech/rules.json', '/rules/6/exact_evaluator_ref')),
    ('operator', ('UnsupportedOperator', 'tech/physical.json', '/operators/spacing~11')),
    ('scope', ('UnsupportedRuleDeclaration', 'tech/rules.json', '/rules/6/scope')),
    ('absent', ('MissingRule', 'tech/rules.json', '/rules')),
])
def test_sealed_rule_gaps_remain_located_and_read_only(tmp_path, change, expected):
    repo = PublicationRepository()
    root = stage(tmp_path, 'normal')
    path = root / ('tech/physical.json' if change == 'operator' else 'tech/rules.json')
    doc = read_json(path)
    if change == 'operator':
        doc['operators']['spacing/1'] = 'Manhattan distance'
    elif change == 'scope':
        doc['rules'][6]['scope'] = 'only annotated rectangles'
    elif change == 'absent':
        del doc['rules'][6]
    else:
        li, m1 = doc['rules'][5:7]
        li['exact_evaluator_ref'], m1['exact_evaluator_ref'] = m1['exact_evaluator_ref'], li['exact_evaluator_ref']
    write_json(path, doc)
    rebind(root)
    ref = publish(repo, root, change)
    before = repo.snapshot()
    ctx = open_constraint_context(repo, change, ref)
    report = check_m1_spacing(ctx)
    outcome = report.for_rule(T07)
    assert (outcome.status, outcome.policy_action, outcome.pairs) == ('indeterminate', 'indeterminate_then_reject', ())
    assert (outcome.issue.code, outcome.issue.source.uri, outcome.issue.source.field) == expected
    assert outcome.issue.source.sha256 == ctx.snapshot.binding['sources'][expected[1]]
    if change == 'swap':
        assert report.for_rule('T06.li_spacing').status == 'indeterminate'
    if change == 'absent':
        assert len(ctx.catalog.rules) == 9
    assert repo.load_attempt(change).phase == 'sealed_open' and repo.snapshot() == before


def test_changed_gds_cannot_reuse_normal_head(published, tmp_path):
    repo, contexts = published
    old = contexts['normal'].version
    root = stage(tmp_path, 'c14')
    ready, request = capture(repo, root, 'mismatch', head=old.head_ref.id, lineage='normal', budget=400)
    before = repo.snapshot()
    with pytest.raises(RepositoryConflict, match='source.gds') as caught:
        publish_stage2(repo, request)
    assert caught.value.code == 'BindingConflict'
    assert repo.load_attempt('mismatch') == ready.attempt and repo.load_head('normal') == old.head_ref
    assert repo.snapshot() == before
