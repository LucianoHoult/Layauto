"""Freeze a formal rule invocation for repository readback."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import source_value
from layauto_v2.domain.policy import REQUIRED_M1_RULES
from layauto_v2.domain.publication import AuditBinding, AuditIssue, RuleAudit
from layauto_v2.tech.rules import RuleRecord

from .result import MissingRule, PairMeasurement, RuleCheck, RuleReport, ShapeWitness


def _shape(shape: ShapeWitness) -> FrozenMap:
    return FrozenMap({'record_id': shape.record_id, 'rect': shape.rect.bounds,
                      'source': source_value(shape.source), 'region_id': shape.region_id,
                      'piece_id': shape.piece_id, 'cuts': tuple(_shape(cut) for cut in shape.cuts)})


def _pair(pair: PairMeasurement) -> FrozenMap:
    return FrozenMap({'first': _shape(pair.first), 'second': _shape(pair.second),
                      'dx_dbu': pair.dx_dbu, 'dy_dbu': pair.dy_dbu, 'nm_per_dbu': pair.nm_per_dbu,
                      'threshold_nm': pair.threshold_nm, 'same_layer_contact': pair.same_layer_contact,
                      'status': pair.status, 'distance_nm': pair.distance_nm,
                      'distance_squared_nm2': pair.distance_squared_nm2})


def _row(check: RuleCheck) -> FrozenMap:
    rule, issue = check.rule, check.issue
    return FrozenMap({
        'id': rule.id, 'status': check.status, 'source': source_value(rule.source),
        'declaration': rule.declaration if isinstance(rule, RuleRecord) else None,
        'policy_action': check.policy_action, 'threshold_nm': check.threshold_nm,
        'issue': None if issue is None else {'code': issue.code, 'message': issue.message,
                                             'source': source_value(issue.source)},
        'pairs': tuple(_pair(pair) for pair in check.pairs),
        'operands': tuple(tuple(_shape(s) for s in pieces) for pieces in check.operands),
        'observations': tuple(item.to_value() for item in check.observations),
    })


def _issue(check: RuleCheck) -> AuditIssue | None:
    rule = check.rule
    if check.issue is not None:
        return AuditIssue(check.issue.code, f'{rule.id}: {check.issue.message}', (check.issue.source,))
    if isinstance(rule, MissingRule):
        return AuditIssue('MissingRule', f'{rule.id} is absent from the bound catalog', (rule.source,))
    violations = [source for item in check.observations if item.status == 'violation' for source in item.sources]
    for pair in check.violations:
        violations.extend((pair.first.source, pair.second.source))
    if check.status == 'pass':
        if not check.policy_action and not violations and not any(o.status == 'violation' for o in check.observations):
            return None
        return AuditIssue('InconsistentRuleResult', f'{rule.id}: reported pass conflicts with its evidence or policy',
                          tuple(dict.fromkeys((rule.source, *violations))))
    return AuditIssue('RuleViolation' if check.status == 'violation' else 'RequiredRuleNotPassed',
                      f'{rule.id}: {check.status}', tuple(dict.fromkeys((rule.source, *violations))))


def freeze_rule_audit(binding: AuditBinding, report: RuleReport) -> RuleAudit:
    counts = Counter(check.rule.id for check in report.checks)
    issues = []
    catalog = replace(report.catalog.source, field='/rules')
    declarations = {rule.id: rule for rule in report.catalog.rules}
    for check in report.checks:
        issue = _issue(check)
        if issue is not None:
            issues.append(issue)
        rule = check.rule
        expected = declarations.get(rule.id, MissingRule(rule.id, catalog))
        if rule != expected:
            issues.append(AuditIssue('RuleDeclarationMismatch', f'{rule.id}: row differs from its catalog declaration',
                                     (rule.source, expected.source)))
        if rule.id not in REQUIRED_M1_RULES:
            issues.append(AuditIssue('UnexpectedRuleResult', f'{rule.id} is outside the bound M1 rule package',
                                     (rule.source,)))
    for rule_id in REQUIRED_M1_RULES:
        if counts[rule_id] != 1:
            issues.append(AuditIssue('IncompleteRuleReport', f'{rule_id}: expected one result, found {counts[rule_id]}',
                                     (catalog,)))
    return RuleAudit(binding, tuple(_row(check) for check in report.checks), tuple(issues))
