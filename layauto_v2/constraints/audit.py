"""Freeze a formal rule invocation for repository readback."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import source_value
from layauto_v2.domain.policy import REQUIRED_M1_RULES
from layauto_v2.domain.publication import AuditBinding, AuditIssue, RuleAudit
from layauto_v2.tech.rules import RuleRecord

from .result import PairMeasurement, RuleCheck, RuleReport, ShapeWitness


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


def _issue(check: RuleCheck) -> AuditIssue:
    rule = check.rule
    if check.issue is not None:
        return AuditIssue(check.issue.code, f'{rule.id}: {check.issue.message}', (check.issue.source,))
    sources = [rule.source]
    for observation in check.observations:
        if observation.status == 'violation':
            sources.extend(observation.sources)
    for pair in check.violations:
        sources.extend((pair.first.source, pair.second.source))
    return AuditIssue('RuleViolation' if check.status == 'violation' else 'RequiredRuleNotPassed',
                      f'{rule.id}: {check.status}', tuple(dict.fromkeys(sources)))


def freeze_rule_audit(binding: AuditBinding, report: RuleReport) -> RuleAudit:
    counts = Counter(check.rule.id for check in report.checks)
    issues = [_issue(check) for check in report.checks if check.status != 'pass']
    catalog = replace(report.catalog.source, field='/rules')
    for rule_id in REQUIRED_M1_RULES:
        if counts[rule_id] != 1:
            issues.append(AuditIssue('IncompleteRuleReport', f'{rule_id}: expected one result, found {counts[rule_id]}',
                                     (catalog,)))
    return RuleAudit(binding, tuple(_row(check) for check in report.checks), tuple(issues))
