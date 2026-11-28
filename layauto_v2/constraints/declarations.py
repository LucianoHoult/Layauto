"""Semantic fields of whole-cell predicates beyond the input variant grammar."""
from layauto_v2.domain.geometry import mapping
from layauto_v2.tech.rules import RuleRecord

from .result import RuleGap

# W022 already certifies T01, W014 certifies the body/terminal contracts,
# and the W010/W024/W025 evaluators bind their own specific semantics.
_CONTRACTS = {
    'T02.fin_grid': (
        'all FIN',
        'exact width, pitch and phase from selected FIN profile; full fixture sequence from input/oracle'),
    'T03.recognition': (
        'all source/target devices and all recognized channels',
        'one stripe per active, full crossings, counts and L/W match CDL, NF=M=1, one-to-one and no reduction'),
    'T09.lifecycle': (
        'local exported records and CDL only; context read-only bound input',
        'no_change preserves all declared semantics, drawn geometry and frame; empty ECO chain'),
    'T10.coverage': (
        'all drawn and effective regions',
        'retain every shape, disclose absent annotations, marker nonconducting, '
        'same-label islands not electrically shorted by label'),
}
_PARAMETERS: dict[str, dict[str, object]] = {
    'T04.body': {'active_enclosure_nm': 10},  # >=10 is part of the registered predicate.
    'T09.lifecycle': {'ordered_eco_commit_count': 0},
    'T10.coverage': {'unknown_nonconductor_policy': 'preserve_disclose',
                     'disconnected_label_policy': 'keep_separate_disclose'},
}


def validate_declaration(rule: RuleRecord) -> None:
    contract = _CONTRACTS.get(rule.id)
    if contract:
        for field, value in zip(('scope', 'predicate'), contract):
            if rule.declaration[field] != value:
                raise RuleGap('UnsupportedRuleDeclaration', f'unsupported {rule.id} {field}', rule.location(field))
    parameters = mapping(rule.declaration['parameters'])
    for field, expected in _PARAMETERS.get(rule.id, {}).items():
        if parameters.get(field) != expected:
            raise RuleGap('UnsupportedRuleDeclaration', f'{rule.evaluator} requires {field}={expected}',
                          rule.location(f'parameters/{field}'))
