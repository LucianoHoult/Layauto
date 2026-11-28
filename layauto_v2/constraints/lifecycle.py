"""T09 compares the selected snapshot to captured inputs and its run-bound head."""
from __future__ import annotations

from dataclasses import replace

from layauto_v2.domain.codec import FrozenMap, Value, digest
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import UnitBinding, mapping, record_identity, sequence, source_value, text
from layauto_v2.domain.publication import ContentRef
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.state.layer_checks import LIFECYCLE_OPERATOR, source_signatures
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import _at
from .result import Observation, RuleCheck, RuleGap, observed


def _location(ref: ContentRef, field: str) -> SourceRef:
    return SourceRef(ref.id, ref.digest, field=field)


def _semantics(value: Value) -> Value:
    """Keep the identifiers, ordered terminals/ports, memberships, model and exact normalized axes.

    W023 serializes the W007 DTO fields, including preservation records and field
    locations. These additional audit fields do not participate in CDL semantics.
    """
    if isinstance(value, FrozenMap):
        audit_fields = ('source', 'sources', 'preservation', 'field_sources', 'field_evidence',
                        'token', 'lexeme', 'schema_version')
        return FrozenMap({k: _semantics(v) for k, v in value.items() if k not in audit_fields})
    if isinstance(value, tuple):
        return tuple(_semantics(v) for v in value)
    return value


def _drawn(context: ConstraintContext) -> tuple[Observation, ...]:
    snapshot = context.version.snapshot_ref
    with _at(context, '/checks/comparator'):
        comparator = ref_from_location(mapping(mapping(context.snapshot.state['checks'])['comparator']))
    unit_ref = replace(comparator, field='/unit_scale_contract')
    try:
        gds = mapping(context.inputs['gds'])
        source = ref_from_location(mapping(gds['source']))
        tech = mapping(context.inputs['tech'])
        drawn = mapping(tech['drawn'])
        units = UnitBinding(mapping(mapping(tech['formats'])['unit_scale_contract']), mapping(gds['units']), unit_ref)
        roles = {text(mapping(r)['name']): mapping(r)['role'] for r in sequence(drawn['layers'])}
        signatures = source_signatures(gds, source, drawn, units)
    except (KeyError, ValueError) as exc:
        raise RuleGap('InvalidInputOperand', str(exc), _location(context.version.checkpoint_ref, '/ready_value')) from exc
    with _at(context, '/geometry'):
        geometry = mapping(context.snapshot.state['geometry'])
        top, published_units = text(geometry['top']), mapping(geometry['units'])
    with _at(context, '/geometry/records'):
        records = mapping(geometry['records'])
    expected_ids = set()
    rows = [Observation('gds_top_and_units', (text(gds['top']),),
                        'pass' if top == gds['top'] and published_units == units.to_value() else 'violation',
                        FrozenMap({'input_top': gds['top'], 'snapshot_top': top,
                                   'input_unit_digest': units.ref.sha256, 'snapshot_unit_digest': digest(published_units)}),
                        (source, unit_ref, comparator, _location(snapshot, '/geometry/units')))]
    for layer, shapes in signatures.items():
        for signature in shapes:
            identity = record_identity(signature.source, signature.top).sha256
            expected_ids.add(identity)
            expected = FrozenMap({'id': identity, 'top': signature.top, 'stream_key': signature.key.to_value(),
                                  'layer': layer, 'purpose': signature.purpose, 'rect': signature.rect.bounds,
                                  'source': source_value(signature.source)})
            published = records.get(identity)
            with _at(context, '/geometry/records/' + identity):
                actual = None if published is None else FrozenMap({k: mapping(published)[k] for k in expected})
            kind = 'frame_signature' if roles[layer] == 'boundary' else 'drawn_signature'
            rows.append(Observation(kind, (identity,), 'pass' if expected == actual else 'violation',
                                    FrozenMap({'input': expected, 'snapshot': actual}),
                                    (signature.source, _location(snapshot, '/geometry/records/' + identity), comparator)))
    for unexpected in sorted(set(records) - expected_ids):
        with _at(context, '/geometry/records/' + unexpected):
            row = mapping(records[unexpected])
            facts = FrozenMap({'layer': row['layer'], 'rect': row['rect']})
        rows.append(Observation('unexpected_drawn_signature', (unexpected,), 'violation',
                                facts,
                                (source, _location(snapshot, '/geometry/records/' + unexpected))))
    return tuple(rows)


def evaluate_lifecycle(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    operator = replace(context.physical.sources[0], field='/operators/lifecycle~11')
    operators = context.physical.payload.get('operators')
    if not isinstance(operators, FrozenMap) or operators.get('lifecycle/1') != LIFECYCLE_OPERATOR:
        raise RuleGap('UnsupportedOperator', 'unsupported lifecycle/1 semantics', operator)
    version = context.version
    original = context.source_circuit
    with _at(context, '/current'):
        current = mapping(context.snapshot.state['current'])
        for field in ('cells', 'selected_cell', 'profile_id', 'dialect'):
            if field not in current:
                raise ValueError(f'missing published circuit field {field}')
    source_operand = _location(version.checkpoint_ref, '/ready_value/source_cdl')
    try:
        cdl = ref_from_location(mapping(mapping(context.inputs['source_cdl'])['source']))
        cells = tuple(text(mapping(mapping(cell)['id'])['name']) for cell in sequence(original['cells']))
    except (KeyError, ValueError) as exc:
        raise RuleGap('InvalidInputOperand', str(exc), source_operand) from exc
    expected, actual = _semantics(original), _semantics(current)
    circuit = Observation('cdl_semantics', cells, 'pass' if expected == actual else 'violation',
                          FrozenMap({'input_digest': digest(expected), 'snapshot_digest': digest(actual),
                                     'checked_version': version.version, 'basis': 'source_cdl_vs_snapshot_current',
                                     'export_readback': 'stage_6'}),
                          (cdl, _location(version.snapshot_ref, '/current'), source_operand))
    commits = tuple(ref.id for ref in context.eco_commits)
    limit = mapping(rule.declaration['parameters'])['ordered_eco_commit_count']
    chain = Observation('ordered_eco_commits', (version.run_id, version.head_ref.id),
                        'pass' if len(commits) == limit else 'violation',
                        FrozenMap({'commits': commits, 'expected_count': limit, 'actual_count': len(commits)}),
                        (_location(version.context_ref, '/head_ref'), _location(version.head_ref, '/eco_commits'),
                         rule.location('parameters/ordered_eco_commit_count'), operator))
    return observed(rule, (circuit, *_drawn(context), chain))
