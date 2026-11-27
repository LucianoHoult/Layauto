"""Run T07 and keep all other mandatory obligations visible."""
from __future__ import annotations

from dataclasses import replace

from layauto_v2.domain.geometry import text
from layauto_v2.domain.publication import safe_exception_message, safe_exception_type
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .result import MissingRule, RuleCheck, RuleIssue, RuleReport
from .rules import M1_RULE, RuleGap, evaluate_m1


def _check(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    policy = context.catalog.mandatory_policy
    # The closed input grammar recognizes versioned evaluator names. In
    # particular T06 has the same parameter schema as T07; verify the ID too.
    if rule.evaluator.split('/')[1:2] != [rule.id]:
        issue = RuleIssue('EvaluatorMismatch', f'{rule.evaluator} does not implement {rule.id}',
                          rule.location('exact_evaluator_ref'))
        return RuleCheck(rule, 'indeterminate', issue=issue, policy_action=text(policy['missing_operator_or_context']))
    if rule.id != M1_RULE:
        return RuleCheck(rule, 'pending')
    try:
        return evaluate_m1(context, rule)
    except RuleGap as gap:
        return RuleCheck(rule, 'indeterminate', issue=gap.issue, policy_action=text(policy['missing_operator_or_context']))
    except Exception as exc:
        issue = RuleIssue('PredicateExecutionError', f'{safe_exception_type(exc)}: {safe_exception_message(exc)}',
                          rule.location('exact_evaluator_ref'))
        return RuleCheck(rule, 'error', issue=issue, policy_action=text(policy['predicate_execution_error']))


def check_m1_spacing(context: ConstraintContext) -> RuleReport:
    """Evaluate the selected T07 declaration across the entire published cell."""
    if type(context) is not ConstraintContext:
        raise TypeError('T07 requires a published ConstraintContext from open_constraint_context')
    checks = tuple(_check(context, rule) for rule in context.catalog.rules)
    if not any(c.rule.id == M1_RULE for c in checks):
        source = replace(context.catalog.source, field='/rules')
        issue = RuleIssue('MissingRule', f'{M1_RULE} is absent from the bound catalog', source)
        action = text(context.catalog.mandatory_policy['missing_operator_or_context'])
        checks += (RuleCheck(MissingRule(M1_RULE, source), 'indeterminate', issue=issue, policy_action=action),)
    return RuleReport(context.version, context.catalog, checks)
