"""Evaluate bound whole-cell predicates and retain every declared obligation."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from layauto_v2.domain import policy
from layauto_v2.domain.geometry import text
from layauto_v2.domain.publication import safe_exception_message, safe_exception_type
from layauto_v2.tech.rules import RuleRecord
from .coverage import evaluate_coverage
from .declarations import validate_declaration
from .device_rules import evaluate_body, evaluate_recognition, evaluate_terminals
from .drawn import evaluate_fin, evaluate_frame
from .drc_context import ConstraintContext
from .enclosure import evaluate_enclosure
from .lifecycle import evaluate_lifecycle
from .result import MissingRule, RuleCheck, RuleGap, RuleIssue, RuleReport
from .rules import evaluate_li, evaluate_m1

Evaluator = Callable[[ConstraintContext, RuleRecord], RuleCheck]


def _check(context: ConstraintContext, rule: RuleRecord, evaluators: Mapping[str, Evaluator],
           complete: bool) -> RuleCheck:
    policy = context.catalog.mandatory_policy
    # The closed input grammar recognizes versioned evaluator names. In
    # particular T06 has the same parameter schema as T07; verify the ID too.
    if rule.evaluator.split('/')[1:2] != [rule.id]:
        issue = RuleIssue('EvaluatorMismatch', f'{rule.evaluator} does not implement {rule.id}',
                          rule.location('exact_evaluator_ref'))
        return RuleCheck(rule, 'indeterminate', issue=issue, policy_action=text(policy['missing_operator_or_context']))
    evaluate = evaluators.get(rule.id)
    if evaluate is None:
        if complete:
            issue = RuleIssue('MissingOperator', f'no evaluator for {rule.id}', rule.location('exact_evaluator_ref'))
            return RuleCheck(rule, 'indeterminate', issue=issue, policy_action=text(policy['missing_operator_or_context']))
        return RuleCheck(rule, 'pending')
    try:
        if complete:
            validate_declaration(rule)
        return evaluate(context, rule)
    except RuleGap as gap:
        return RuleCheck(rule, 'indeterminate', issue=gap.issue, policy_action=text(policy['missing_operator_or_context']))
    except Exception as exc:
        issue = RuleIssue('PredicateExecutionError', f'{safe_exception_type(exc)}: {safe_exception_message(exc)}',
                          rule.location('exact_evaluator_ref'))
        return RuleCheck(rule, 'error', issue=issue, policy_action=text(policy['predicate_execution_error']))


def _report(context: ConstraintContext, evaluators: Mapping[str, Evaluator], *,
            complete: bool = False) -> RuleReport:
    if type(context) is not ConstraintContext:
        operation = 'check_rules' if complete else 'spacing'
        raise TypeError(f'{operation} requires a published ConstraintContext from open_constraint_context')
    checks = [_check(context, rule, evaluators, complete) for rule in context.catalog.rules]
    declared = {c.rule.id for c in checks}
    for rule_id in evaluators:
        if rule_id in declared:
            continue
        source = replace(context.catalog.source, field='/rules')
        issue = RuleIssue('MissingRule', f'{rule_id} is absent from the bound catalog', source)
        action = text(context.catalog.mandatory_policy['missing_operator_or_context'])
        checks.append(RuleCheck(MissingRule(rule_id, source), 'indeterminate', issue=issue, policy_action=action))
    return RuleReport(context.version, context.catalog, tuple(checks))


def check_m1_spacing(context: ConstraintContext) -> RuleReport:
    """Evaluate only T07, preserving the W024 report."""
    return _report(context, {policy.M1_SPACING: evaluate_m1})


def check_spacing(context: ConstraintContext) -> RuleReport:
    """Evaluate T06 and T07 against the same published version and bound deck."""
    return _report(context, {policy.LI_SPACING: evaluate_li, policy.M1_SPACING: evaluate_m1})


def check_rules(context: ConstraintContext) -> RuleReport:
    """Evaluate the M1 obligations once on the explicitly selected publication."""
    return _report(context, {
        policy.FRAME: evaluate_frame,
        policy.FIN_GRID: evaluate_fin,
        policy.RECOGNITION: evaluate_recognition,
        policy.BODY: evaluate_body,
        policy.CONTACT_ENCLOSURE: evaluate_enclosure,
        policy.LI_SPACING: evaluate_li,
        policy.M1_SPACING: evaluate_m1,
        policy.TERMINAL_GRAPH: evaluate_terminals,
        policy.LIFECYCLE: evaluate_lifecycle,
        policy.COVERAGE: evaluate_coverage,
    }, complete=True)
