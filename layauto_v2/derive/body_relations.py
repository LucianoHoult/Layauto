"""Exact, read-only body context proofs, separate from the local graph.

This neutral evaluator checks internal source/owner closure. Its caller owns
captured-byte authentication; no expected net name creates a physical edge.
"""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import cast

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.codec import FrozenMap, Value, rational
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import DrawnRecord, evidence_value, mapping, sequence, source_value
from layauto_v2.domain.identifiers import identity_value
from layauto_v2.domain.net_annotation import policy_for, validate_annotation_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from layauto_v2.state.annotation import AnnotationDraft, DRAFT_TYPES as ANNOTATION_TYPES
from layauto_v2.tech.schema import SchemaError, validate_payload
from .channel_identity import ChannelIdentityDraft, DRAFT_TYPES as CHANNEL_TYPES


class BodyProblem(ValueError):
    """A located owner policy outside the implemented body context contract."""

    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def _unsupported(source: SourceRef, field: str, message: str) -> BodyProblem:
    return BodyProblem(EvidenceIssue('unsupported', 'UnsupportedBodyOperator', message,
                                     replace(source, field=field)))


_PROFILE = FrozenMap({
    'id': 'toy_readonly_tapcell_context/2', 'operator_ref': 'body_context/2',
    'coordinates': 'source local frame; integer nominal nm; identity transform only',
    'geometry_scope': 'external x<=frame left; never exported',
    'source_binding': 'actual source GDS bytes, top, FRAME and exact body/rail object identities required',
    'types': {'TOY_N': ('BODY_N', 'BTAP_N'), 'TOY_P': ('BODY_P', 'BTAP_P')},
    'missing_support': 'pre_context reject', 'geometry_failure': 'sealed_no_publication reject',
    'unique_matches_required': True,
})
_EXTRACTION = FrozenMap({
    'id': 'toy_device_terminal_context/2', 'cardinality': 'one_to_one',
    'device_reduction': 'forbidden', 'mapping_missing_or_ambiguous': 'typed_fail',
    'sd_policy': 'left connected component of OD minus channel is S, right is D; ordered terminals, swap unsupported',
    'body_operator': 'one same-type local body enclosing active; local graph separate; selected bound read-only external tapcell context supports body-to-rail association by exact geometry; no implicit edge from names',
    'gate_operator': 'POLY conductor continuous through channels; never an OD S-to-D conductor edge',
    'body_operator_ref': 'body_context/2',
})
_OPERATOR = ('same-type positive-length boundary-edge continuation local body to external body; '
             'unique typed external BTAP overlaps and is enclosed by exactly one external body and rail; '
             'external M1 rail uniquely continues local M1 at frame boundary; semantic rail checked only '
             'after geometry; no local graph union')
_RULES = {
    'T04.body': FrozenMap({
        'scope': 'local active/body and separate read-only context body chain',
        'predicate': 'matching local body encloses active >=10; no opposite body positive-area overlap in either local or external domain; bound external tapcell context proves body association to target rail',
        'relation_basis': 'same_component', 'required_relation_assurance': 'exact_local_components_plus_bound_context_association',
        'exact_evaluator_ref': 'w004-toy-predicate/T04.body/2'}),
    'T05.contact_enclosure': FrozenMap({
        'scope': 'local CONTACT,VIA0,GCONTACT; separately context BTAP_N/BTAP_P',
        'predicate': 'exactly one region on each side encloses connector >=1 nm on all sides',
        'relation_basis': 'geometry_only', 'required_relation_assurance': 'none',
        'exact_evaluator_ref': 'w004-toy-predicate/T05.contact_enclosure/2'}),
    'T08.terminal_graph': FrozenMap({
        'scope': 'all device terminals and conductor components',
        'predicate': 'ordered D/G/S agree with local exact components; B uses separately proven context association; no union by labels',
        'relation_basis': 'same_component', 'required_relation_assurance': 'exact_local_components_plus_bound_context_association',
        'exact_evaluator_ref': 'w004-toy-predicate/T08.terminal_graph/2'}),
}


def _owners(channels: ChannelIdentityDraft) -> tuple[Fraction, Fraction]:
    binding = channels.local.binding
    for owner, kind in ((binding.physical, 'physical'), (binding.drawn, 'drawn'), (binding.rules, 'rules')):
        failure: SchemaError | None = None
        try:
            validate_payload(owner.payload, kind)
        except SchemaError as exc:
            failure = exc
        if failure is not None:
            raise _unsupported(owner.sources[0], failure.path or '/', 'invalid body owner: ' + str(failure)) from failure
    physical = binding.physical
    for group, expected in (('body_context_profile', _PROFILE), ('device_extraction_contract', _EXTRACTION)):
        actual = mapping(physical.payload[group])
        for key, value in expected.items():
            if actual.get(key) != value:
                raise _unsupported(physical.sources[0], '/' + group + '/' + key, 'unsupported consumed body policy')
    operators = mapping(physical.payload['operators'])
    if (operators.get('body_context/2') != _OPERATOR
            or 'body_context/2' not in sequence(physical.payload['required_operator_refs'])):
        raise _unsupported(physical.sources[0], '/operators/body_context~12', 'required body operator is unavailable or changed')
    drawn = binding.drawn
    rows = tuple(mapping(row) for row in sequence(drawn.payload['layers']))
    for name, body_layer in (('BTAP_N', 'BODY_N'), ('BTAP_P', 'BODY_P')):
        matches = tuple((i, row) for i, row in enumerate(rows) if row['name'] == name)
        if len(matches) != 1:
            raise _unsupported(drawn.sources[0], '/layers', 'body tap layer must resolve uniquely')
        index, row = matches[0]
        for key, expected_value in (
                ('role', 'body_contact'), ('purpose', 'drawing'),
                ('electrical_connects', (body_layer, 'M1')),
                ('contact_predicate', 'positive_area_overlap_with_exactly_one_effective_region_on_each_side'),
                ('enclosure_rule', 'T05.contact_enclosure')):
            if row.get(key) != expected_value:
                raise _unsupported(drawn.sources[0], f'/layers/{index}/{key}', 'unsupported external body tap declaration')
    rules = binding.rules
    found: dict[str, FrozenMap] = {}
    for name, expected in _RULES.items():
        matches = tuple((i, mapping(row)) for i, row in enumerate(sequence(rules.payload['rules']))
                        if mapping(row)['id'] == name)
        if len(matches) != 1:
            raise _unsupported(rules.sources[0], '/rules', 'body rule must resolve uniquely')
        index, row = matches[0]
        for key, rule_value in (*expected.items(), ('schema_version', 'w004-toy-rule/2'),
                                    ('unit', 'nm'), ('missing_context_policy', 'reject_indeterminate'), ('required', True)):
            if row.get(key) != rule_value:
                raise _unsupported(rules.sources[0], f'/rules/{index}/{key}', 'unsupported consumed body rule')
        found[name] = row
    if mapping(found['T08.terminal_graph']['parameters']) != FrozenMap({'terminal_order': ('D', 'G', 'S', 'B')}):
        raise _unsupported(rules.sources[0], '/rules', 'unsupported body terminal ordering')
    active = mapping(found['T04.body']['parameters'])
    tap = mapping(found['T05.contact_enclosure']['parameters'])
    if set(active) != {'active_enclosure_nm'} or set(tap) != {'enclosure_nm'}:
        raise _unsupported(rules.sources[0], '/rules', 'unsupported body enclosure parameters')
    # Rule scalar schema uses native integer nm; rational() decodes only the
    # numerator/denominator wire representation used by unit declarations.
    active_value, tap_value = active['active_enclosure_nm'], tap['enclosure_nm']
    if type(active_value) is not int or type(tap_value) is not int:
        raise _unsupported(rules.sources[0], '/rules', 'body enclosure thresholds require native integer nm')
    active_nm, tap_nm = Fraction(active_value), Fraction(tap_value)
    if active_nm < 0 or tap_nm < 0:
        raise _unsupported(rules.sources[0], '/rules', 'body enclosure threshold cannot be negative')
    return active_nm, tap_nm


def _rectangle(value: Value) -> RationalRect:
    values = sequence(value)
    if len(values) != 4 or any(type(item) is not int for item in values):
        raise ValueError('context rectangle requires four native integer nm coordinates')
    return RationalRect(*(Fraction(cast(int, item)) for item in values))


def positive_area(left: RationalRect, right: RationalRect) -> bool:
    return min(left.x1, right.x1) > max(left.x0, right.x0) and min(left.y1, right.y1) > max(left.y0, right.y0)


def edge_length(left: RationalRect, right: RationalRect) -> Fraction:
    if left.x1 == right.x0 or right.x1 == left.x0:
        return max(Fraction(0), min(left.y1, right.y1) - max(left.y0, right.y0))
    if left.y1 == right.y0 or right.y1 == left.y0:
        return max(Fraction(0), min(left.x1, right.x1) - max(left.x0, right.x0))
    return Fraction(0)


def enclosure(outer: RationalRect, inner: RationalRect) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    return inner.x0 - outer.x0, inner.y0 - outer.y0, outer.x1 - inner.x1, outer.y1 - inner.y1


def frame_edge_length(local: RationalRect, external: RationalRect, frame: RationalRect) -> Fraction:
    """Only vertical continuation at the declared local frame's left edge."""
    if local.x0 != frame.x0 or external.x1 != frame.x0:
        return Fraction(0)
    return max(Fraction(0), min(local.y1, external.y1) - max(local.y0, external.y0))


def evaluate_body(channels: ChannelIdentityDraft, annotation: AnnotationDraft,
                  body: EvidenceRecord) -> tuple[FrozenMap, tuple[EvidenceIssue, ...]]:
    """Recompute all applicable body facts without modifying local topology."""
    validate_terminal_graph((channels, annotation, body), CHANNEL_TYPES + ANNOTATION_TYPES)
    if type(channels) is not ChannelIdentityDraft or type(annotation) is not AnnotationDraft:
        raise ValueError('body proof requires neutral channel and annotation drafts')
    if type(body) is not EvidenceRecord or body.kind != 'body' or len(body.sources) != 2:
        raise ValueError('body proof requires ordered context and GDS sources')
    local = channels.local
    layout = local.effective.base.layout
    allowed = {(mapping(row)['uri'], mapping(row)['sha256'])
               for row in sequence(annotation.binding.capture_binding['sources'])}
    if any((ref.uri, ref.sha256) not in allowed for ref in body.sources):
        raise ValueError('body sources belong to another capture')
    if (body.sources[1] != layout.gds.sources[0] or body.sources[0].uri == body.sources[1].uri
            or annotation.binding.local_ref != local.ref):
        raise ValueError('body source roles or local graph disagree with the common input')
    failure: SchemaError | None = None
    try:
        validate_payload(body.payload, 'body')
    except SchemaError as exc:
        failure = exc
    if failure is not None:
        raise ValueError('body evidence has an invalid neutral schema') from failure
    active_threshold, tap_threshold = _owners(channels)
    doc = body.payload
    issues: list[EvidenceIssue] = []

    def issue(code: str, field: str, message: str) -> None:
        issues.append(EvidenceIssue('binding', code, message, replace(body.sources[0], field=field)))

    body_gds = mapping(doc['source_gds'])
    declared_uri = body_gds['uri']
    selected_refs = {(uri, sha) for uri, sha in allowed if uri == declared_uri}
    # Preserve GeometryInput.selected's historical alias contract: a later
    # binding can use an absent spelling, but an existing captured URI cannot
    # be reinterpreted as another role solely by copying the GDS hash.
    wrong_role = bool(selected_refs) and selected_refs != {(body.sources[1].uri, body.sources[1].sha256)}
    if body_gds['sha256'] != body.sources[1].sha256 or doc['top'] != layout.top or wrong_role:
        issue('BodySourceBindingMismatch', '/source_gds', 'body source GDS or top differs from actual local geometry')
    if (doc['profile_ref'] != _PROFILE['id'] or doc['operator_ref'] != _PROFILE['operator_ref']
            or doc['coordinate_frame'] != 'source local frame; identity transform'):
        issue('BodyProfileBindingMismatch', '/profile_ref', 'body context has a different selected profile or transform')
    if rational(mapping(doc['unit'])['metres_per_tick']) != layout.units.nominal_tick_m:
        issue('BodyUnitMismatch', '/unit', 'body context nominal unit differs from actual source')
    records_nm = {record.id: RationalRect(*(layout.units.canonical_to_nm(value) for value in record.rect.bounds))
                  for record in layout.records}
    local_rows = tuple(mapping(row) for row in sequence(doc['local_bindings']))
    external_rows = tuple(mapping(row) for row in sequence(doc['shapes']))
    context_local: dict[str, DrawnRecord] = {}
    local_bindings: list[FrozenMap] = []
    ids: set[str] = set()
    for index, row in enumerate(local_rows):
        name = cast(str, row['id'])
        if name in ids:
            issue('BodyDuplicateIdentity', f'/local_bindings/{index}/id', 'duplicate body context identity')
        ids.add(name)
        rect = _rectangle(row['bbox'])
        matches = tuple(record for record in layout.records if record.layer == row['layer'] and records_nm[record.id] == rect)
        local_bindings.append(FrozenMap({'id': name, 'source': source_value(replace(body.sources[0], field=f'/local_bindings/{index}')),
            'record_ids': tuple(record.id.sha256 for record in matches), 'bbox_nm': rect.bounds, 'layer': row['layer']}))
        if len(matches) != 1:
            issue('BodyObjectBindingMismatch', f'/local_bindings/{index}', 'local context object has no unique exact drawn match')
        else:
            context_local[name] = matches[0]
    ext: dict[str, FrozenMap] = {}
    ext_rects: dict[str, RationalRect] = {}
    ext_index: dict[str, int] = {}
    for index, row in enumerate(external_rows):
        name = cast(str, row['id'])
        if name in ids:
            issue('BodyDuplicateIdentity', f'/shapes/{index}/id', 'duplicate local/external context identity')
        ids.add(name)
        ext[name], ext_rects[name], ext_index[name] = row, _rectangle(row['bbox']), index
    frame = context_local.get(cast(str, doc['frame_id']))
    frames = tuple(record for record in layout.records if record.layer == 'BOUNDARY')
    frame_ok = (frame is not None and frame.layer == 'BOUNDARY' and len(frames) == 1
                and frames[0].id == frame.id and records_nm[frame.id] == _rectangle(doc['frame_bbox_nm']))
    if not frame_ok:
        issue('BodyObjectBindingMismatch', '/frame_id', 'body FRAME does not bind the unique actual local boundary')
    for name, rect in ext_rects.items():
        if frame is None or rect.x1 > records_nm[frame.id].x0:
            issue('BodyContextScope', f'/shapes/{ext_index[name]}/bbox', 'external context extends inside the local frame')
    # Every opposite-type pair is audited, including unreferenced objects.
    pair_audits: list[FrozenMap] = []
    for domain in ('local', 'external'):
        candidates = tuple((record.id.sha256, record.layer, records_nm[record.id]) for record in layout.records) if domain == 'local' else tuple((name, cast(str, row['layer']), ext_rects[name]) for name, row in ext.items())
        for n_id, n_layer, n_rect in candidates:
            if n_layer != 'BODY_N':
                continue
            for p_id, p_layer, p_rect in candidates:
                if p_layer != 'BODY_P':
                    continue
                overlap = positive_area(n_rect, p_rect)
                pair_audits.append(FrozenMap({'domain': domain, 'n_id': n_id, 'p_id': p_id, 'positive_area_overlap': overlap,
                                               'status': 'violation' if overlap else 'satisfied'}))
                if overlap:
                    issue('BodyOppositeTypeOverlap', '/shapes' if domain == 'external' else '/local_bindings', 'opposite body types overlap with positive area')
    # Audit all external taps, not only the ones selected by successful paths.
    taps: dict[str, FrozenMap] = {}
    for name, row in ext.items():
        if row['layer'] not in ('BTAP_N', 'BTAP_P'):
            continue
        body_layer = 'BODY_N' if row['layer'] == 'BTAP_N' else 'BODY_P'
        body_matches = tuple(key for key, candidate in ext.items() if candidate['layer'] == body_layer and positive_area(ext_rects[key], ext_rects[name]))
        rail_matches = tuple(key for key, candidate in ext.items() if candidate['layer'] == 'M1' and positive_area(ext_rects[key], ext_rects[name]))
        bm = None if len(body_matches) != 1 else enclosure(ext_rects[body_matches[0]], ext_rects[name])
        rm = None if len(rail_matches) != 1 else enclosure(ext_rects[rail_matches[0]], ext_rects[name])
        unique = len(body_matches) == len(rail_matches) == 1
        satisfied = unique and bm is not None and rm is not None and min(*bm, *rm) >= tap_threshold
        taps[name] = FrozenMap({'tap_id': name, 'layer': row['layer'], 'body_candidates': body_matches,
            'rail_candidates': rail_matches, 'body_margins_nm': bm, 'rail_margins_nm': rm,
            'threshold_nm': tap_threshold, 'status': 'satisfied' if satisfied else 'violation',
            'source': source_value(replace(body.sources[0], field=f'/shapes/{ext_index[name]}'))})
        if not unique:
            issue('BodyUniqueMatchFailure', f'/shapes/{ext_index[name]}', 'external tap does not positively contact exactly one typed body and one rail')
        elif not satisfied:
            issue('BodyTapEnclosureFailure', f'/shapes/{ext_index[name]}', 'external tap enclosure violates the selected T05 threshold')
    selected = next(cell for cell in channels.source.cells if cell.id == channels.source.selected_cell)
    associations = tuple(mapping(row) for row in sequence(doc['associations']))
    expected_names = {device.id.name for device in selected.devices}
    actual_names = tuple(cast(str, row['device']) for row in associations)
    if len(actual_names) != len(set(actual_names)) or set(actual_names) != expected_names:
        issue('BodyAssociationCardinality', '/associations', 'body associations must cover all source devices exactly once')
    channel_by_device = {row.device_id: row.channel_ref for row in channels.associations}
    measurement_by_channel = {row.channel_ref: row for row in channels.measurements}
    active_audits: list[FrozenMap] = []
    paths: list[FrozenMap] = []
    opposite_overlap = any(row['status'] == 'violation' for row in pair_audits)
    # Freeze shared binding failures before device-local diagnostics are added.
    # A wrong MN0 selection must not invalidate an independent MP0 proof.
    global_binding_invalid = any(row.code in (
        'BodySourceBindingMismatch', 'BodyProfileBindingMismatch', 'BodyUnitMismatch',
        'BodyContextScope', 'BodyObjectBindingMismatch', 'BodyDuplicateIdentity') for row in issues)
    covered_actives: set[str] = set()

    def physical_refs(record: DrawnRecord | None) -> tuple[Value, Value]:
        if record is None:
            return None, None
        nodes = tuple(node for node in local.nodes if node.region.owner_id == record.id)
        if len(nodes) != 1:
            return None, None
        components = tuple(component for component in local.components if nodes[0].ref in component.members)
        return nodes[0].ref.to_value(), components[0].ref.to_value() if len(components) == 1 else None

    for device in selected.devices:
        channel = channel_by_device.get(device.id)
        measurement = None if channel is None else measurement_by_channel.get(channel)
        active_record = None if measurement is None else layout.record(measurement.active_id)
        device_matches = tuple((i, row) for i, row in enumerate(associations) if row['device'] == device.id.name)
        index, association = device_matches[0] if len(device_matches) == 1 else (-1, None)
        row_out: dict[str, Value] = {key: None for key in (
            'channel_ref', 'active_id', 'association_source', 'context_claim', 'local_body_id',
            'local_body_record_id', 'local_body_node_ref', 'local_body_component_ref', 'external_body_id',
            'tap_id', 'external_rail_id', 'local_rail_id', 'rail_record_id', 'rail_node_ref', 'rail_component_ref',
            'body_edge_length_nm', 'rail_edge_length_nm', 'active_enclosure_nm', 'tap_body_enclosure_nm', 'tap_rail_enclosure_nm')}
        row_out.update({'device_id': identity_value(device.id), 'body_candidates': (), 'rail_candidates': (),
                        'evidence_refs': (), 'observed_net_ids': (), 'chain_status': 'indeterminate',
                        'rule_status': 'indeterminate', 'claim_status': 'indeterminate'})
        if channel is not None:
            row_out['channel_ref'] = channel.to_value()
        if active_record is not None:
            row_out['active_id'] = active_record.id.sha256
            covered_actives.add(active_record.id.sha256)
        pair = mapping(_PROFILE['types']).get(device.model)
        if pair is None:
            raise _unsupported(local.binding.physical.sources[0], '/body_context_profile/types', 'device model has no supported body type')
        body_layer, tap_layer = (cast(str, value) for value in sequence(pair))
        enclosing = () if active_record is None else tuple(record for record in layout.records
            if record.layer == body_layer and min(enclosure(records_nm[record.id], records_nm[active_record.id])) >= 0)
        local_body = enclosing[0] if len(enclosing) == 1 else None
        margins = None if local_body is None or active_record is None else enclosure(records_nm[local_body.id], records_nm[active_record.id])
        active_ok = margins is not None and min(margins) >= active_threshold
        active_audits.append(FrozenMap({'device_id': identity_value(device.id), 'active_id': row_out['active_id'],
            'body_candidates': tuple(record.id.sha256 for record in enclosing), 'margins_nm': margins,
            'threshold_nm': active_threshold, 'status': 'satisfied' if active_ok else 'violation'}))
        if len(enclosing) != 1:
            issue('BodyUniqueMatchFailure', f'/associations/{index}/local_body', 'device active has no unique enclosing typed local body')
        elif not active_ok:
            issue('BodyActiveEnclosureFailure', f'/associations/{index}/local_body', 'local body does not satisfy the selected active enclosure threshold')
        if margins is not None:
            row_out['active_enclosure_nm'] = min(margins)
        if not active_ok or opposite_overlap:
            row_out['rule_status'] = 'violation'
        row_out['local_body_node_ref'], row_out['local_body_component_ref'] = physical_refs(local_body)
        if local_body is not None:
            row_out['local_body_record_id'] = local_body.id.sha256
        if association is None:
            paths.append(FrozenMap(row_out))
            continue
        row_out.update({'association_source': source_value(replace(body.sources[0], field=f'/associations/{index}')),
            'context_claim': association['expected_semantic_rail'], 'local_body_id': association['local_body'],
            'external_body_id': association['external_body'], 'tap_id': association['tap'],
            'external_rail_id': association['external_rail'], 'local_rail_id': association['local_rail']})
        local_declared = context_local.get(cast(str, association['local_body']))
        rail = context_local.get(cast(str, association['local_rail']))
        eb, tap_id, er = (cast(str, association[key]) for key in ('external_body', 'tap', 'external_rail'))
        fields_exist = local_declared is not None and rail is not None and eb in ext and tap_id in ext and er in ext
        typed = (fields_exist and local_declared is not None and rail is not None
                 and local_declared.layer == ext[eb]['layer'] == body_layer
                 and ext[tap_id]['layer'] == tap_layer and ext[er]['layer'] == rail.layer == 'M1')
        if not typed:
            issue('BodyTypeMismatch', f'/associations/{index}', 'body path objects have missing or incompatible model types')
        if local_body is None or local_declared is None or local_body.id != local_declared.id:
            issue('BodyObjectBindingMismatch', f'/associations/{index}/local_body', 'declared body is not the active uniquely enclosing body')
        row_out['rail_node_ref'], row_out['rail_component_ref'] = physical_refs(rail)
        if rail is not None:
            row_out['rail_record_id'] = rail.id.sha256
        if not typed or local_body is None or rail is None:
            paths.append(FrozenMap(row_out))
            continue
        body_candidates = tuple(name for name, value in ext.items() if value['layer'] == body_layer
                                and frame is not None
                                and frame_edge_length(records_nm[local_body.id], ext_rects[name], records_nm[frame.id]) > 0)
        rail_candidates = tuple(record.id.sha256 for record in layout.records if record.layer == 'M1'
                                and frame is not None
                                and frame_edge_length(records_nm[record.id], ext_rects[er], records_nm[frame.id]) > 0)
        row_out['body_candidates'], row_out['rail_candidates'] = body_candidates, rail_candidates
        row_out['body_edge_length_nm'] = edge_length(records_nm[local_body.id], ext_rects[eb])
        row_out['rail_edge_length_nm'] = edge_length(records_nm[rail.id], ext_rects[er])
        continuation = body_candidates == (eb,) and rail_candidates == (rail.id.sha256,)
        if not body_candidates or not rail_candidates:
            issue('BodyContinuationMismatch', f'/associations/{index}', 'body or rail has no positive-length boundary continuation')
        elif not continuation:
            issue('BodyUniqueMatchFailure', f'/associations/{index}', 'body or rail continuation is ambiguous or selects another object')
        tap_audit = taps.get(tap_id)
        tap_unique = tap_audit is not None and tap_audit['body_candidates'] == (eb,) and tap_audit['rail_candidates'] == (er,)
        if not tap_unique:
            issue('BodyUniqueMatchFailure', f'/associations/{index}/tap', 'selected tap does not uniquely contact the declared body and rail')
        if tap_audit is not None:
            path_bm, path_rm = tap_audit['body_margins_nm'], tap_audit['rail_margins_nm']
            row_out['tap_body_enclosure_nm'] = None if path_bm is None else min(cast(tuple[Fraction, ...], path_bm))
            row_out['tap_rail_enclosure_nm'] = None if path_rm is None else min(cast(tuple[Fraction, ...], path_rm))
        geometric = (not global_binding_invalid and frame_ok and continuation and tap_unique
                     and local_declared is not None and local_declared.id == local_body.id)
        # Exact rail evidence is stricter than component association. A query
        # extending to 45.05nm must never be truncated to the local 45nm edge.
        rail_rect = records_nm[rail.id]
        layer_evidence = []
        for seed in annotation.evidence:
            policy = policy_for(annotation.binding, seed)
            if policy['target_layer'] == 'M1' and policy['supported'] is True:
                layer_evidence.append(seed)
        exact = tuple(seed for seed in layer_evidence if seed.rectangle == rail_rect)
        overlapping = tuple(seed for seed in layer_evidence if positive_area(seed.rectangle, rail_rect))
        if overlapping and not exact:
            issue('BodyTargetRailMismatch', f'/associations/{index}/local_rail', 'provided rail query geometry has no exact match to the local rail')
            geometric = False
        rail_summaries = tuple(summary for summary in annotation.components
                               if summary.component_ref.to_value() == row_out['rail_component_ref'])
        anchored_nets = {seed.net_id for seed in exact}
        anchored_refs = {seed.ref for seed in exact}
        # An exact anchor proves which actual rail is being named; after that,
        # retain every conflicting net/evidence on its physical component.
        # Without that anchor a component summary cannot create a body proof.
        if exact:
            anchored_nets.update(net for summary in rail_summaries for net in summary.observed_net_ids)
            anchored_refs.update(ref for summary in rail_summaries for ref in summary.evidence_refs)
        observed = tuple(sorted(anchored_nets, key=lambda net: net.id)) if geometric and exact else ()
        row_out['observed_net_ids'] = tuple(identity_value(net) for net in observed)
        row_out['evidence_refs'] = tuple(reference.to_value() for reference in sorted(anchored_refs, key=lambda ref: ref.sha256))
        row_out['chain_status'] = 'established' if geometric else 'indeterminate'
        row_out['rule_status'] = ('satisfied' if not opposite_overlap and active_ok and tap_audit is not None and tap_audit['status'] == 'satisfied'
                                  and geometric and len(observed) == 1 else 'violation' if not active_ok or tap_audit is not None and tap_audit['status'] == 'violation' else 'indeterminate')
        claim_status = 'indeterminate' if not observed else 'conflict' if len(observed) > 1 else 'equal' if observed[0].name == association['expected_semantic_rail'] else 'mismatch'
        row_out['claim_status'] = claim_status
        if claim_status == 'mismatch':
            issue('BodyTargetRailMismatch', f'/associations/{index}/expected_semantic_rail', 'context rail claim differs from the independently observed rail net')
        if opposite_overlap or claim_status == 'mismatch':
            row_out['rule_status'] = 'violation'
        # A failed enclosure does not erase established geometric contact.
        if global_binding_invalid:
            row_out['chain_status'], row_out['observed_net_ids'] = 'indeterminate', ()
            row_out['claim_status'] = 'indeterminate'
            if row_out['rule_status'] == 'satisfied':
                row_out['rule_status'] = 'indeterminate'
        paths.append(FrozenMap(row_out))
    for record in layout.records:
        if record.layer == 'OD' and record.id.sha256 not in covered_actives:
            active_audits.append(FrozenMap({'device_id': None, 'active_id': record.id.sha256, 'body_candidates': (),
                'margins_nm': None, 'threshold_nm': active_threshold, 'status': 'indeterminate'}))
            issue('BodyUnassociatedActive', '/associations', 'a local active has no unique source device for body audit')
    result = FrozenMap({'schema': 'layauto-body-relations/1',
        'binding': {'body_evidence': evidence_value(body), 'local_ref': local.ref.to_value(),
            'channel_binding_ref': channels.binding_ref.to_value(), 'annotation_binding_ref': annotation.binding.ref.to_value(),
            'physical': evidence_value(local.binding.physical), 'rules': evidence_value(local.binding.rules),
            'unit_ref': layout.units.ref.to_value(), 'active_threshold_nm': active_threshold, 'tap_threshold_nm': tap_threshold,
            'rule_status_scope': ('T04.body', 'T05.contact_enclosure'),
            'terminal_comparison_rule': 'T08.terminal_graph'},
        'local_bindings': tuple(local_bindings), 'active_audits': tuple(active_audits),
        'body_pair_audits': tuple(pair_audits), 'tap_audits': tuple(taps.values()), 'paths': tuple(paths),
        'production_matched_body_evidence': False, 'lvs_status': doc['lvs_status'], 'local_graph_union': False})
    validate_annotation_graph(result)
    return result, tuple(issues)
