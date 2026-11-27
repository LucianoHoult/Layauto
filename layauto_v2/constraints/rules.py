"""Exact whole-cell M1 spacing for the declared synthetic predicate."""
from __future__ import annotations

from dataclasses import replace
from itertools import combinations

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect, integer, mapping, sequence, text
from layauto_v2.domain.local_connectivity import CONSUMED_PHYSICAL
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.state.local_connectivity import same_layer_contact
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .result import PairMeasurement, RuleCheck, RuleIssue, RuleStatus, ShapeWitness

M1_RULE = 'T07.m1_spacing'
M1_EVALUATOR = 'w003-toy-predicate/T07.m1_spacing/1'
_SPACING = ('Euclidean minimum separation of closed exact rectangles; compare squared integer distance '
            'with squared threshold; geometry_only has no label exemption')


class RuleGap(ValueError):
    def __init__(self, code: str, message: str, source: SourceRef) -> None:
        self.issue = RuleIssue(code, message, source)
        super().__init__(message)


def _threshold(context: ConstraintContext, rule: RuleRecord) -> int:
    row = rule.declaration
    params = mapping(row['parameters'])
    threshold = params.get('min_distance_nm')
    if type(threshold) is not int or threshold < 0:
        raise RuleGap('MissingThreshold', 'expected a nonnegative integer in nm', rule.location('parameters/min_distance_nm'))
    supported = {
        'exact_evaluator_ref': M1_EVALUATOR,
        'schema_version': 'w003-toy-rule/1',
        'scope': 'all unordered pairs of M1 rectangles',
        'predicate': f'distance>={threshold} nm unless actual same-layer contact makes one region',
        'unit': 'nm',
        'relation_basis': 'geometry_only',
        'required_relation_assurance': 'none',
    }
    for field, expected in supported.items():
        if row.get(field) != expected:
            raise RuleGap('UnsupportedRuleDeclaration', f'{field} disagrees with {M1_EVALUATOR}', rule.location(field))
    operators = mapping(context.physical.payload['operators'])
    for operator, semantics in (('spacing/1', _SPACING), ('same_layer_contact/1', CONSUMED_PHYSICAL['same_layer_contact/1'])):
        if operators.get(operator) != semantics:
            source = replace(context.physical.sources[0], field='/operators/' + operator.replace('/', '~1'))
            raise RuleGap('UnsupportedOperator', f'unsupported {operator} semantics', source)
    return threshold


def _metal(context: ConstraintContext) -> tuple[int, tuple[ShapeWitness, ...]]:
    """Decode only operands used by this predicate from the authenticated state."""
    state = context.snapshot.state
    path = '/layers/M1'
    try:
        layer = mapping(mapping(state['layers'])['M1'])
        declaration = mapping(mapping(layer['policy'])['declaration'])
        stream = mapping(declaration['stream_key'])
        if declaration['name'] != 'M1' or declaration['role'] != 'interconnect' or stream['element'] != 'BOUNDARY':
            raise ValueError('expected the selected M1 interconnect BOUNDARY layer')
        path = '/geometry/units/contract/canonical_tick_nm'
        geometry = mapping(state['geometry'])
        nm_per_dbu = integer(mapping(mapping(geometry['units'])['contract'])['canonical_tick_nm'])
        if nm_per_dbu <= 0:
            raise ValueError('canonical DBU scale must be positive')
        path = '/geometry/records'
        sources = mapping(context.snapshot.binding['sources'])
        records = mapping(geometry['records'])
        shapes = []
        for record_id, value in records.items():
            path = '/geometry/records/' + record_id
            row = mapping(value)
            if row['layer'] != 'M1':
                continue
            if row['stream_key'] != stream or row['id'] != record_id:
                raise ValueError('drawn record disagrees with the selected stream key or record ID')
            path += '/source'
            source = ref_from_location(mapping(row['source']))
            if (source.byte_offset is None or source.record_index is None
                    or sources.get(source.uri) != source.sha256):
                raise ValueError('expected a bound GDS stream location')
            path = '/geometry/records/' + record_id + '/rect'
            x0, y0, x1, y1 = sequence(row['rect'])
            rect = Rect(integer(x0), integer(y0), integer(x1), integer(y1))
            shapes.append(ShapeWitness(record_id, rect, source))
    except (KeyError, ValueError) as exc:
        ref = context.version.snapshot_ref
        raise RuleGap('InvalidSnapshotOperand', str(exc), SourceRef(ref.id, ref.digest, field=path)) from exc
    return nm_per_dbu, tuple(shapes)


def measure_pair(first: ShapeWitness, second: ShapeWitness, nm_per_dbu: int, threshold_nm: int) -> PairMeasurement:
    a, b = first.rect, second.rect
    dx = max(0, a.x0 - b.x1, b.x0 - a.x1)
    dy = max(0, a.y0 - b.y1, b.y0 - a.y1)
    contact = dx == dy == 0 and same_layer_contact((a,), (b,))
    return PairMeasurement(first, second, dx, dy, nm_per_dbu, threshold_nm, contact)


def evaluate_m1(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    threshold = _threshold(context, rule)
    nm_per_dbu, shapes = _metal(context)
    pairs = tuple(measure_pair(a, b, nm_per_dbu, threshold) for a, b in combinations(shapes, 2))
    status: RuleStatus = 'violation' if any(p.status == 'violation' for p in pairs) else 'pass'
    return RuleCheck(rule, status, pairs=pairs, threshold_nm=threshold)
