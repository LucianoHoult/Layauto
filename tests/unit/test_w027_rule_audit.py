"""The close gate retains a diagnostic for an inconsistent formal rule package."""
from dataclasses import replace

from layauto_v2.constraints.audit import freeze_rule_audit
from layauto_v2.constraints.drc_context import CheckedVersion
from layauto_v2.constraints.result import Observation, PairMeasurement, RuleCheck, RuleIssue, RuleReport, ShapeWitness
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect
from layauto_v2.domain.policy import REQUIRED_M1_RULES
from layauto_v2.domain.publication import AuditBinding, ContentRef
from layauto_v2.tech.rules import RuleCatalog, RuleRecord


def passing_report(names=REQUIRED_M1_RULES):
    def ref(kind):
        return ContentRef(kind, 'checking-run', 'a' * 64)

    binding = AuditBinding(ref('sealed_context'), ref('target_intent'), ref('state_head'), ref('snapshot'))
    version = CheckedVersion(binding.context_ref, ref('checkpoint'), ref('tool_run'),
                             binding.head_ref, binding.snapshot_ref, ref('checkpoint'), 0)
    source = SourceRef('tech/rules.json', 'b' * 64)
    rules = tuple(RuleRecord(FrozenMap({'id': name}), SourceRef(source.uri, source.sha256, field=f'/rules/{i}'))
                  for i, name in enumerate(names))
    catalog = RuleCatalog(source, 'test', FrozenMap({}), rules)
    report = RuleReport(version, catalog, tuple(RuleCheck(rule, 'pass') for rule in rules))
    return binding, report


def test_extra_passing_row_keeps_the_complete_report_and_a_located_failure():
    binding, report = passing_report((*REQUIRED_M1_RULES, 'unexpected'))
    audit = freeze_rule_audit(binding, report)
    issue, = audit.issues
    assert issue.code == 'UnexpectedRuleResult' and issue.sources == (report.catalog.rules[-1].source,)
    assert len(audit.checks) == 11


def test_passing_status_cannot_hide_errors_violations_or_another_declaration():
    binding, report = passing_report()
    rows = list(report.checks)
    source = SourceRef('source.gds', 'c' * 64, byte_offset=1648)
    observation = Observation('enclosure', ('via',), 'violation', FrozenMap({'margin': -3}), (source,))
    rows[4] = replace(rows[4], observations=(observation,))
    rows[5] = replace(rows[5], issue=RuleIssue('PredicateExecutionError', 'spacing evaluator failed', rows[5].rule.source))
    first = ShapeWitness('first', Rect(0, 0, 1, 1), source)
    second = ShapeWitness('second', Rect(5, 0, 6, 1), replace(source, byte_offset=2480))
    rows[6] = replace(rows[6], pairs=(PairMeasurement(first, second, 4, 0, 1, 5, False),))
    rows[7] = replace(rows[7], rule=replace(rows[7].rule, source=replace(rows[7].rule.source, field='/foreign')))
    audit = freeze_rule_audit(binding, replace(report, checks=tuple(rows)))
    assert [i.code for i in audit.issues] == [
        'InconsistentRuleResult', 'PredicateExecutionError', 'InconsistentRuleResult', 'RuleDeclarationMismatch']
    assert source in audit.issues[0].sources and second.source in audit.issues[2].sources
    assert all(row['status'] == 'pass' for row in audit.checks)  # retain the actual invocation
