"""The close gate retains a diagnostic for an inconsistent formal rule package."""
from layauto_v2.constraints.audit import freeze_rule_audit
from layauto_v2.constraints.drc_context import CheckedVersion
from layauto_v2.constraints.result import RuleCheck, RuleReport
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.policy import REQUIRED_M1_RULES
from layauto_v2.domain.publication import AuditBinding, ContentRef
from layauto_v2.tech.rules import RuleCatalog, RuleRecord


def test_extra_passing_row_keeps_the_complete_report_and_a_located_failure():
    def ref(kind):
        return ContentRef(kind, 'checking-run', 'a' * 64)

    binding = AuditBinding(ref('sealed_context'), ref('target_intent'), ref('state_head'), ref('snapshot'))
    version = CheckedVersion(binding.context_ref, ref('checkpoint'), ref('tool_run'),
                             binding.head_ref, binding.snapshot_ref, ref('checkpoint'), 0)
    source = SourceRef('tech/rules.json', 'b' * 64)
    rules = tuple(RuleRecord(FrozenMap({'id': name}), SourceRef(source.uri, source.sha256, field=f'/rules/{i}'))
                  for i, name in enumerate((*REQUIRED_M1_RULES, 'unexpected')))
    catalog = RuleCatalog(source, 'test', FrozenMap({}), rules)
    report = RuleReport(version, catalog, tuple(RuleCheck(rule, 'pass') for rule in rules))
    audit = freeze_rule_audit(binding, report)
    issue, = audit.issues
    assert issue.code == 'UnexpectedRuleResult' and issue.sources == (rules[-1].source,)
    assert len(audit.checks) == 11
