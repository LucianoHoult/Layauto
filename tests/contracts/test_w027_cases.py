"""File-to-closure contracts. Assertions resolve the persisted references on the attempt."""
import pytest

from docs.tasks.W022.review_probe import read_rectangles
from docs.tasks.W027.example import publish_sample, stage_sample
from layauto_v2 import constraints
from layauto_v2.constraints import engine
from layauto_v2.pipeline import run_stage5
from w005_cases import read_json, sha, without_cache
from w007_cases import EXPECTED_PARAMETERS
from w013_cases import rewrite_net_response


T05 = 'T05.contact_enclosure'
T07 = 'T07.m1_spacing'


def close_and_read(root, run_id, monkeypatch):
    repo, request = publish_sample(root, run_id)
    before = repo.load_attempt(run_id)
    ctx = repo.read(before.context_ref)
    head_ref = repo.load_head(run_id)
    head = repo.read(head_ref)
    called = []
    check_rules = constraints.check_rules

    def checking(view):
        called.append(view.version)
        return check_rules(view)

    monkeypatch.setattr(constraints, 'check_rules', checking)
    returned = run_stage5(repo, request)
    attempt = repo.load_attempt(run_id)
    assert attempt.phase == 'stage5_closed' and attempt.revision == before.revision + 1
    closure = repo.read(attempt.closure_ref)
    assert closure == returned and attempt.terminal_ref is None
    record = repo.read(closure.run_record_ref)
    plan = repo.read(record.planning_ref)
    assert plan.binding == record.binding
    assert record.binding.context_ref == attempt.context_ref == before.context_ref
    assert record.binding.target_ref == ctx.target_ref
    assert record.binding.head_ref == repo.load_head(run_id) == head_ref
    assert record.final_snapshot_ref == head.snapshot_ref and repo.read(head.snapshot_ref).version == 0
    assert record.ordered_commit_ids == head.eco_commits == ()
    assert record.head_status_at_finalization == 'current'
    failure = repo.read(record.failure_ref) if record.failure_ref else None
    rules = repo.read(record.rule_ref) if record.rule_ref else None
    if rules is None:
        assert called == [] and plan.issues and failure.stage == 'stage4'
    else:
        version, = called
        assert version.context_ref == attempt.context_ref and version.head_ref == head_ref
        assert version.snapshot_ref == record.final_snapshot_ref
        assert rules.binding == record.binding and not plan.issues
        if failure:
            assert failure.stage == 'stage5'
    if failure:
        assert record.status == 'sealed_no_publication'
        assert record.planning_ref in failure.completed
        if rules:
            assert record.rule_ref in failure.completed
    else:
        assert record.status == 'no_change'
    return plan, rules, failure, repo.read(ctx.target_ref)


def fin_evidence(root, planning, measured):
    stream = read_rectangles(root / 'source.gds')
    observations = [o for o in planning.observations if o['kind'] == 'device_parameter'
                    and o['facts']['axis'] == 'fins_per_finger']
    assert len(observations) == 4
    assert {(o['object_ids'][0], o['facts']['circuit']) for o in observations} == {
        (device, circuit) for device in measured for circuit in ('source', 'target')}
    for row in observations:
        name = row['object_ids'][0]
        facts = row['facts']
        declared, line = (5, 3) if name == 'MN0' else (7, 4)
        assert (facts['measured'], facts['declared'], facts['unit']) == ((measured[name],), declared, 'count')
        cdl, = [s for s in row['sources'] if s['uri'] == facts['circuit'] + '.cdl']
        assert cdl['line'] == line and cdl['sha256'] == sha(root / cdl['uri'])
        gds = [s for s in row['sources'] if s['uri'] == 'source.gds']
        assert gds and all(s['sha256'] == sha(root / 'source.gds') for s in gds)
        # Check the cited stream records, including every qualified local FIN.
        fin_rects = [stream[s['byte_offset']][2] for s in gds if stream[s['byte_offset']][:2] == (1, 0)]
        assert len(set(fin_rects)) == measured[name]


def test_equal_normalized_semantics_and_measured_layout(tmp_path, monkeypatch):
    root = stage_sample(tmp_path, 'normal')
    assert (root / 'source.cdl').read_bytes() != (root / 'target.cdl').read_bytes()
    plan, rules, failure, target = close_and_read(root, 'normal', monkeypatch)
    assert failure is None and not plan.issues and not rules.issues and not target.differences
    fin_evidence(root, plan, {'MN0': 5, 'MP0': 7})
    params = {tuple(row['object_ids'][-2:]): row['facts'] for row in plan.observations if row['kind'] == 'parameter'}
    assert set(params) == {(name, axis) for name in ('MN0', 'MP0') for axis in EXPECTED_PARAMETERS}
    for (name, axis), facts in params.items():
        _, expected, unit, _ = EXPECTED_PARAMETERS[axis]
        if name == 'MP0' and axis == 'fins_per_finger':
            expected = 7
        assert facts['current'] == facts['target']
        assert (facts['target']['exact'], facts['target']['unit']) == (expected, unit)
    assert len(rules.checks) == 10 and all(row['status'] == 'pass' for row in rules.checks)
    assert {row['id'] for row in rules.checks} == {r['id'] for r in read_json(root / 'tech/rules.json')['rules']}
    assert all(r['source']['sha256'] == sha(root / 'tech/rules.json') for r in rules.checks)


@pytest.mark.parametrize('case', ('c13', 'multi'))
def test_all_unsupported_differences_retain_both_cdl_locations(tmp_path, monkeypatch, case):
    root = stage_sample(tmp_path, case)
    plan, rules, failure, target = close_and_read(root, case, monkeypatch)
    assert rules is None and failure.code == 'UnsupportedTargetAxis'
    expected = {'channel_length': (3, 'L=4n', 'L=5n')}
    if case == 'multi':
        expected['fin_width'] = (4, 'W=2n', 'W=3n')
    assert {delta['axis'] for delta in target.differences} == set(expected)
    differences = [o for o in plan.observations if o['kind'] == 'target_difference']
    assert len(differences) == len(expected)
    assert len([i for i in plan.issues if i.code == 'UnsupportedTargetAxis']) == len(expected)
    for row in differences:
        axis = row['facts']['axis']
        line, before, after = expected[axis]
        for uri, token in (('source.cdl', before), ('target.cdl', after)):
            source, = [s for s in row['sources'] if s['uri'] == uri]
            assert source['line'] == line and source['sha256'] == sha(root / uri)
            assert token in (root / uri).read_text().splitlines()[line - 1]
    fin_evidence(root, plan, {'MN0': 5, 'MP0': 7})


def test_equal_cdls_do_not_hide_layout_count_mismatch(tmp_path, monkeypatch):
    root = stage_sample(tmp_path, 'c16')
    plan, rules, failure, target = close_and_read(root, 'c16', monkeypatch)
    assert not target.differences and rules is None and failure.code == 'ExtractionCountMismatch'
    fin_evidence(root, plan, {'MN0': 4, 'MP0': 7})
    locations = {s.uri for issue in plan.issues if issue.code == 'ExtractionCountMismatch' for s in issue.sources}
    assert locations >= {'source.cdl', 'target.cdl', 'source.gds'}


@pytest.mark.parametrize(('case', 'violations'), [('c14', {T07}), ('c15', {T05}), ('combined', {T05, T07})])
def test_rule_violations_retain_independently_measurable_shapes(tmp_path, monkeypatch, case, violations):
    root = stage_sample(tmp_path, case)
    _, rules, failure, _ = close_and_read(root, case, monkeypatch)
    assert failure and len(rules.checks) == 10
    assert {r['id'] for r in rules.checks if r['status'] != 'pass'} == violations
    assert all(r['status'] == 'violation' for r in rules.checks if r['id'] in violations)
    rows = {r['id']: r for r in rules.checks}
    stream = read_rectangles(root / 'source.gds')
    gds_hash = sha(root / 'source.gds')
    if T07 in violations:
        pairs = [p for p in rows[T07]['pairs'] if p['status'] == 'violation']
        pair, = pairs
        first, second = sorted((p['source']['byte_offset'] for p in (pair['first'], pair['second'])))
        gap = stream[second][2][0] - stream[first][2][2]
        assert (first, second, gap, rows[T07]['threshold_nm']) == (2480, 2544, 4, 5)
        assert pair['first']['source']['sha256'] == pair['second']['source']['sha256'] == gds_hash
        assert pair['distance_nm'] == gap
    if T05 in violations:
        obs, = [o for o in rows[T05]['observations'] if o['status'] == 'violation']
        via, li = (s['byte_offset'] for s in obs['sources'][:2])
        outer, inner = stream[li][2], stream[via][2]
        margins = inner[0] - outer[0], inner[1] - outer[1], outer[2] - inner[2], outer[3] - inner[3]
        assert obs['facts']['margins_nm'] == margins
        assert (via, li, min(margins), obs['facts']['threshold_nm']) == (2096, 1648, -3, 1)
        assert all(s['sha256'] == gds_hash for s in obs['sources'][:2])


@pytest.mark.parametrize(('case', 'status', 'code', 'action', 'pointer'), [
    ('missing_t07', 'indeterminate', 'MissingRule', 'indeterminate_then_reject', '/rules'),
    ('error', 'error', 'PredicateExecutionError', 'error_then_reject', '/rules/6/exact_evaluator_ref'),
])
def test_rule_gaps_preserve_other_nine_results(tmp_path, monkeypatch, case, status, code, action, pointer):
    root = stage_sample(tmp_path, 'normal' if case == 'error' else case)
    if case == 'error':
        def failing(*_):
            raise ArithmeticError('injected W027 arithmetic error')
        monkeypatch.setattr(engine, 'evaluate_m1', failing)
    _, rules, failure, _ = close_and_read(root, case, monkeypatch)
    assert failure and len(rules.checks) == 10
    row, = [r for r in rules.checks if r['status'] != 'pass']
    assert (row['id'], row['status'], row['issue']['code'], row['policy_action']) == (T07, status, code, action)
    source = row['issue']['source']
    assert source['field'] == pointer and source['sha256'] == sha(root / source['uri'])

def test_missing_gate_net_evidence_is_located_during_planning(tmp_path, monkeypatch):
    root = stage_sample(tmp_path, 'normal')
    without_cache(root)
    rewrite_net_response(root, 'n_a', ())
    plan, rules, failure, target = close_and_read(root, 'missing_gate', monkeypatch)
    assert not target.differences and rules is None and failure.code == 'MissingExtractionFact'
    gaps = [o for o in plan.observations if o['kind'] == 'terminal_extraction'
            and not o['facts']['observed_net_ids']]
    assert len(gaps) == 2
    for gap in gaps:
        locs = gap['sources']
        assert {s['uri'] for s in locs} >= {'source.cdl', 'target.cdl', plan.binding.snapshot_ref.id}
        assert any(s['field'].startswith('/terminals/') for s in locs if s['uri'] == plan.binding.snapshot_ref.id)
