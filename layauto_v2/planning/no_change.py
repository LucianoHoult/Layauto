"""Read-only whole-intent admission on a published synthetic cell."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from layauto_v2.constraints.device_rules import recognition_observations
from layauto_v2.constraints.drc_context import ConstraintContext
from layauto_v2.constraints.result import Observation, RuleGap
from layauto_v2.domain.codec import FrozenMap, Value
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import mapping, sequence, text
from layauto_v2.domain.publication import AuditBinding, AuditIssue, PlanningAudit
from layauto_v2.domain.publication_codec import content_ref
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.repository import RepositoryConflict


@dataclass(frozen=True, slots=True)
class NoChangePlanningResult:
    audit: PlanningAudit
    candidates: tuple[()] = field(default=(), init=False)
    mutations: tuple[()] = field(default=(), init=False)

    def __post_init__(self) -> None:
        if self.audit.issues or not self.audit.observations:
            raise ValueError('no-change planning requires positive evidence for all goals')


@dataclass(frozen=True, slots=True)
class RejectedPlanningResult:
    audit: PlanningAudit

    def __post_init__(self) -> None:
        if not self.audit.issues:
            raise ValueError('a rejected plan requires located reasons')


GoalKey = tuple[str, ...]
Goal = tuple[Value, tuple[SourceRef, ...]]


def _rows(value: object) -> tuple[FrozenMap, ...]:
    return tuple(mapping(item) for item in sequence(value))


def _sources(value: object) -> tuple[SourceRef, ...]:
    return tuple(ref_from_location(row) for row in _rows(value))


def _goals(circuit: FrozenMap, selected: FrozenMap) -> dict[GoalKey, Goal]:
    """Index the W007 semantic fields. Units and terminal/pin order are significant."""
    name = text(selected['name'])
    sources = _sources(mapping(circuit['preservation'])['sources'])
    goals: dict[GoalKey, Goal] = {
        ('profile', name): (circuit['profile_id'], sources),
        ('dialect', name): (circuit['dialect'], sources),
    }
    for cell in _rows(circuit['cells']):
        if cell['id'] != selected:
            continue
        fields = mapping(cell['field_sources'])
        declaration = (ref_from_location(mapping(fields['name'])),)
        pins = _sources(fields['pins'])
        goals['cell', name] = cell['id'], declaration
        goals['ports', name] = cell['ports'], pins or declaration
        goals['globals', name] = cell['globals'], declaration
        for net in _rows(cell['nets']):
            net_name = text(mapping(net['id'])['name'])
            goals['net', name, net_name] = (FrozenMap({k: net[k] for k in (
                'id', 'port_indices', 'global_net', 'memberships')}), _sources(net['sources']))
        for device in _rows(cell['devices']):
            device_name = text(mapping(device['id'])['name'])
            fields = mapping(device['field_sources'])
            goals['device', name, device_name] = device['id'], (ref_from_location(mapping(fields['name'])),)
            goals['model', name, device_name] = device['model'], (ref_from_location(mapping(fields['model'])),)
            terminals = _rows(device['terminals'])
            goals['terminal_order', name, device_name] = (
                tuple(t['role'] for t in terminals), tuple(ref_from_location(mapping(t['source'])) for t in terminals))
            for terminal in terminals:
                role = text(terminal['role'])
                goals['terminal', name, device_name, role] = (
                    terminal['net_id'], (ref_from_location(mapping(terminal['source'])),))
            for param in _rows(device['parameters']):
                axis = text(param['axis'])
                goals['parameter', name, device_name, axis] = (
                    FrozenMap({k: param[k] for k in ('axis', 'unit', 'exact')}),
                    (ref_from_location(mapping(param['source'])),))
    return goals


def _difference_issues(view: ConstraintContext) -> Iterator[tuple[Observation, AuditIssue]]:
    for delta in view.target.differences:
        name = text(mapping(delta['operand_ref'])['name'])
        axis = delta['axis']
        op = text(delta['op_type'])
        label = text(axis) if axis is not None else op
        code = 'UnsupportedTargetAxis' if axis is not None else 'UnsupportedTargetChange'
        sources = _sources(delta['provenance'])
        yield (Observation('target_difference', (name, label), 'violation', delta, sources),
               AuditIssue(code, f'{name}.{label} requires {text(delta["required_capability"])}', sources))


def _terminal_observations(view: ConstraintContext, current: dict[GoalKey, Goal],
                           target: dict[GoalKey, Goal]) -> Iterator[tuple[Observation, AuditIssue | None]]:
    """W014 retains the independently observed net and the local or external support path."""
    relations: dict[GoalKey, tuple[int, FrozenMap]] = {}
    ref = view.version.snapshot_ref
    for i, row in enumerate(_rows(view.snapshot.state['terminals'])):
        term = mapping(row['target'])
        device = mapping(term['device_id'])
        key: GoalKey = ('terminal', text(mapping(device['cell'])['name']), text(device['name']), text(term['role']))
        if key in relations:
            raise RuleGap('AmbiguousTerminalRelation', str(key), SourceRef(ref.id, ref.digest, field=f'/terminals/{i}'))
        relations[key] = (i, row)
    for key in sorted(k for k in current if k[0] == 'terminal'):
        declaration, cdl = current[key]
        desired, target_cdl = target.get(key, (None, ()))
        index, relation = relations.get(key, (-1, FrozenMap({})))
        path = '/terminals' if index < 0 else f'/terminals/{index}'
        sources = (*cdl, *target_cdl, SourceRef(ref.id, ref.digest, field=path))
        observed = sequence(relation.get('observed_net_ids', ()))
        supported = relation.get('support_status') == 'established' and bool(observed)
        agrees = supported and observed == (declaration,) == (desired,)
        facts = FrozenMap({'current': declaration, 'target': desired, 'observed_net_ids': observed,
                           'support_status': relation.get('support_status'), 'component_refs': relation.get('component_refs')})
        yield (Observation('terminal_extraction', key[1:], 'pass' if agrees else 'violation', facts, sources),
               None if agrees else AuditIssue('ExtractionRelationMismatch' if supported else 'MissingExtractionFact',
                                              '.'.join(key[1:]) + f' observed {observed}', sources))


def _recognition_issue(obs: Observation) -> AuditIssue:
    if obs.kind != 'device_parameter':
        return AuditIssue('ExtractionIdentityMismatch', f'{obs.kind} for {obs.object_ids}', obs.sources)
    axis = text(obs.facts['axis'])
    code = 'ExtractionCountMismatch' if axis == 'fins_per_finger' else 'ExtractionValueMismatch'
    measured = sequence(obs.facts['measured'])
    declared = str(obs.facts['declared'])
    message = (f'{obs.object_ids[0]}.{axis} measured {measured}, {text(obs.facts["circuit"])} '
               f'declared {declared} {text(obs.facts["unit"])}')
    return AuditIssue(code, message, obs.sources)


def plan_no_change(view: ConstraintContext, binding: AuditBinding) -> NoChangePlanningResult | RejectedPlanningResult:
    """Compare every selected target field and each required physical fact on one version."""
    if type(view) is not ConstraintContext:
        raise TypeError('planning requires a published ConstraintContext')
    version = view.version
    if binding != AuditBinding(version.context_ref, content_ref(view.target), version.head_ref, version.snapshot_ref):
        raise RepositoryConflict('BindingConflict', 'planning input differs from the bound context, target or version')

    observations: list[FrozenMap] = []
    issues: list[AuditIssue] = []
    for obs, issue in _difference_issues(view):
        observations.append(obs.to_value())
        issues.append(issue)

    circuit = mapping(view.snapshot.state['current'])
    selected = mapping(circuit['selected_cell'])
    current, target = _goals(circuit, selected), _goals(view.target.circuit, selected)
    for key in sorted(current.keys() | target.keys()):
        before, left = current.get(key, (None, ()))
        after, right = target.get(key, (None, ()))
        equal = before == after
        obs = Observation(key[0], key[1:], 'pass' if equal else 'violation',
                          FrozenMap({'current': before, 'target': after}), left + right)
        observations.append(obs.to_value())
        if not equal and not view.target.differences:
            issues.append(AuditIssue('UnreportedTargetDifference', '.'.join(key) + ' differs', left + right))

    try:
        for obs in recognition_observations(view):
            observations.append(obs.to_value())
            if obs.status != 'pass':
                issues.append(_recognition_issue(obs))
    except RuleGap as exc:
        issues.append(AuditIssue('MissingExtractionFact', f'{exc.issue.code}: {exc.issue.message}', (exc.issue.source,)))

    try:
        for obs, terminal_issue in _terminal_observations(view, current, target):
            observations.append(obs.to_value())
            if terminal_issue:
                issues.append(terminal_issue)
    except RuleGap as exc:
        issues.append(AuditIssue('MissingExtractionFact', f'{exc.issue.code}: {exc.issue.message}', (exc.issue.source,)))

    audit = PlanningAudit(binding, tuple(observations), tuple(issues))
    return RejectedPlanningResult(audit) if issues else NoChangePlanningResult(audit)
