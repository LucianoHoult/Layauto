"""Full-deck failures retain the other independently evaluated obligations."""
from layauto_v2.constraints import check_rules, engine
from w005_cases import read_json, rebind, write_json
from w026_cases import inspect_published, stage_rules


def test_missing_rule_and_changed_declaration(tmp_path):
    root = stage_rules(tmp_path, 'normal')
    path = root / 'tech/rules.json'
    rules = read_json(path)
    del rules['rules'][6]  # no T07, other located rows shift
    rules['rules'][-1]['parameters']['unknown_nonconductor_policy'] = 'drop'
    write_json(path, rules)
    rebind(root)
    ctx, report, _ = inspect_published(root, 'gaps')
    assert not report.all_required_passed
    for name, code, pointer in (
            ('T07.m1_spacing', 'MissingRule', '/rules'),
            ('T10.coverage', 'UnsupportedRuleDeclaration', '/rules/8/parameters/unknown_nonconductor_policy')):
        check = report.for_rule(name)
        assert (check.status, check.policy_action) == ('indeterminate', 'indeterminate_then_reject')
        assert check.issue.code == code and check.issue.source.field == pointer
        assert check.issue.source.sha256 == ctx.catalog.source.sha256
    assert sum(c.status == 'pass' for c in report.checks) == 8


def test_one_evaluator_error_preserves_other_results(normal_rules, monkeypatch):
    ctx, normal, _ = normal_rules

    def fail(*args):
        raise ArithmeticError('injected evaluation error')

    monkeypatch.setattr(engine, 'evaluate_m1', fail)
    report = check_rules(ctx)
    assert normal.all_required_passed and not report.all_required_passed
    row = report.for_rule('T07.m1_spacing')
    assert (row.status, row.policy_action, row.issue.code) == ('error', 'error_then_reject', 'PredicateExecutionError')
    assert row.issue.source == row.rule.location('exact_evaluator_ref')
    for check in report.checks:
        if check != row:
            assert check == normal.for_rule(check.rule.id)
