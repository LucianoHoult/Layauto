"""Bind registered synthetic spacing declarations and measure their exact operands."""
from __future__ import annotations

from dataclasses import replace
from itertools import combinations, product

from layauto_v2.domain.geometry import mapping
from layauto_v2.domain.local_connectivity import CONSUMED_PHYSICAL
from layauto_v2.domain.policy import LI_SPACING as LI_RULE, M1_SPACING as M1_RULE
from layauto_v2.domain.regions import CONSUMED_PHYSICAL as REGION_PHYSICAL
from layauto_v2.state.local_connectivity import same_layer_contact
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import Operands, effective_li, metal
from .result import PairMeasurement, RuleCheck, RuleGap, RuleStatus, ShapeWitness

_SCOPES = {
    LI_RULE: 'local effective LI; dedicated cut-island specimen evaluated separately',
    M1_RULE: 'all unordered pairs of M1 rectangles',
}
_SPACING = ('Euclidean minimum separation of closed exact rectangles; compare squared integer distance '
            'with squared threshold; geometry_only has no label exemption')


def _threshold(context: ConstraintContext, rule: RuleRecord, rule_id: str) -> int:
    row = rule.declaration
    params = mapping(row['parameters'])
    threshold = params.get('min_distance_nm')
    if type(threshold) is not int or threshold < 0:
        raise RuleGap('MissingThreshold', 'expected a nonnegative integer in nm', rule.location('parameters/min_distance_nm'))
    evaluator = f'w003-toy-predicate/{rule_id}/1'
    supported = {
        'id': rule_id,
        'exact_evaluator_ref': evaluator,
        'schema_version': 'w003-toy-rule/1',
        'scope': _SCOPES[rule_id],
        'predicate': f'distance>={threshold} nm unless actual same-layer contact makes one region',
        'unit': 'nm',
        'relation_basis': 'geometry_only',
        'required_relation_assurance': 'none',
    }
    for field, expected in supported.items():
        if row.get(field) != expected:
            raise RuleGap('UnsupportedRuleDeclaration', f'{field} disagrees with {evaluator}', rule.location(field))
    operators = mapping(context.physical.payload['operators'])
    required = {'spacing/1': _SPACING, 'same_layer_contact/1': CONSUMED_PHYSICAL['same_layer_contact/1']}
    if rule_id == LI_RULE:
        required['rectangle_set_difference/1'] = REGION_PHYSICAL['/operators/rectangle_set_difference~11']
    for operator, semantics in required.items():
        if operators.get(operator) != semantics:
            source = replace(context.physical.sources[0], field='/operators/' + operator.replace('/', '~1'))
            raise RuleGap('UnsupportedOperator', f'unsupported {operator} semantics', source)
    return threshold


def measure_pair(first: ShapeWitness, second: ShapeWitness, nm_per_dbu: int, threshold_nm: int) -> PairMeasurement:
    a, b = first.rect, second.rect
    dx = max(0, a.x0 - b.x1, b.x0 - a.x1)
    dy = max(0, a.y0 - b.y1, b.y0 - a.y1)
    contact = dx == dy == 0 and same_layer_contact((a,), (b,))
    return PairMeasurement(first, second, dx, dy, nm_per_dbu, threshold_nm, contact)


def measure_spacing(operands: tuple[tuple[ShapeWitness, ...], ...], nm_per_dbu: int,
                    threshold_nm: int) -> tuple[PairMeasurement, ...]:
    """Measure each independent pair. A direct contact wins ties with point touches."""
    pairs = []
    for first, second in combinations(operands, 2):
        measurements = (measure_pair(a, b, nm_per_dbu, threshold_nm) for a, b in product(first, second))
        pairs.append(min(measurements, key=lambda p: (p.distance_squared_dbu2, not p.same_layer_contact)))
    return tuple(pairs)


def _evaluate(rule: RuleRecord, threshold: int, decoded: Operands) -> RuleCheck:
    nm_per_dbu, operands = decoded
    pairs = measure_spacing(operands, nm_per_dbu, threshold)
    status: RuleStatus = 'violation' if any(p.status == 'violation' for p in pairs) else 'pass'
    return RuleCheck(rule, status, pairs=pairs, threshold_nm=threshold, operands=operands)


def evaluate_m1(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    threshold = _threshold(context, rule, M1_RULE)
    return _evaluate(rule, threshold, metal(context, 'M1'))


def evaluate_li(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    threshold = _threshold(context, rule, LI_RULE)
    return _evaluate(rule, threshold, effective_li(context))
