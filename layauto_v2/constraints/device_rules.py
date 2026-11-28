"""Recognition and electrical checks at the selected, immutable layout version."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import combinations, product

from layauto_v2.derive.channel_identity import CONSUMED_PROFILE
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import integer, mapping, sequence, text
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import _at, _geometry, _rect
from .result import Observation, RuleCheck, RuleGap, observed


def _rows(value: object) -> tuple[FrozenMap, ...]:
    return tuple(mapping(item) for item in sequence(value))


def _source(value: object) -> SourceRef:
    return ref_from_location(mapping(value))


def _field_sources(record: FrozenMap, *fields: str) -> tuple[SourceRef, ...]:
    retained = mapping(record['field_sources'])
    return tuple(dict.fromkeys(_source(location) for field in fields
                               for location in _rows(mapping(retained[field])['sources'])))


def _devices(circuit: FrozenMap, selected_cell: FrozenMap | None = None) -> dict[str, FrozenMap]:
    if selected_cell is None:
        selected_cell = mapping(circuit['selected_cell'])
    return {text(mapping(device['id'])['name']): device for cell in _rows(circuit['cells'])
            if cell['id'] == selected_cell for device in _rows(cell['devices'])}


def _ref(value: object) -> str:
    return text(mapping(value)['sha256'])


def _refs(values: object) -> tuple[str, ...]:
    return tuple(_ref(item) for item in sequence(values))


def _names(values: object) -> tuple[str, ...]:
    return tuple(text(row['name']) for row in _rows(values))


def _observation(kind: str, ids: tuple[str, ...], satisfied: bool, facts: dict[str, object],
                 *sources: SourceRef) -> Observation:
    return Observation(kind, ids, 'pass' if satisfied else 'violation', FrozenMap(facts),
                       tuple(dict.fromkeys(sources)))


def _snapshot_source(ctx: ConstraintContext, path: str) -> SourceRef:
    ref = ctx.version.snapshot_ref
    return SourceRef(ref.id, ref.digest, field=path)


def _declared_layers(ctx: ConstraintContext, role: str) -> set[str]:
    layers = mapping(ctx.snapshot.state['layers'])
    return {name for name, row in layers.items()
            if mapping(mapping(mapping(row)['policy'])['declaration'])['role'] == role}


def _parameters(device: FrozenMap, model: FrozenMap, counts: dict[str, tuple[int | Fraction, ...]],
                domain: str, name: str, channel: str, geometric_sources: tuple[SourceRef, ...]
                ) -> tuple[Observation, ...]:
    params = {text(p['axis']): p for p in _rows(device['parameters'])}
    axes = mapping(model['parameter_axes'])
    result = []
    for axis, measured in counts.items():
        param = params[axis]
        location = _source(param['source'])
        if axes.get(text(param['token'])) != axis:
            raise RuleGap('UnsupportedParameterAxis', f'{name} token is not bound to {axis}', location)
        declared = param['exact']
        if not isinstance(declared, Fraction):
            raise RuleGap('MissingNumericParameter', f'{domain} {name} {axis}', location)
        unit = 'nm' if axis in ('channel_length', 'fin_width') else 'count'
        if unit == 'nm':
            declared *= 10**9
        result.append(_observation('device_parameter', (name, channel), bool(measured)
            and all(value == declared for value in measured), {'circuit': domain, 'axis': axis,
            'measured': measured, 'declared': declared, 'unit': unit, 'token': param['lexeme']},
            location, *geometric_sources))
    return tuple(result)


def evaluate_recognition(ctx: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    physical = ctx.physical
    profile = mapping(physical.payload['fin_count_profile'])
    extraction = mapping(physical.payload['device_extraction_contract'])
    for key, expected in CONSUMED_PROFILE.items():
        if profile.get(key) != expected:
            raise RuleGap('UnsupportedRecognitionProfile', key,
                          replace(physical.sources[0], field='/fin_count_profile/' + key))
    if extraction['cardinality'] != 'one_to_one' or extraction['device_reduction'] != 'forbidden':
        raise RuleGap('UnsupportedExtractionContract', 'expected one-to-one attribution without reduction',
                      replace(physical.sources[0], field='/device_extraction_contract'))
    geometry, scale = _geometry(ctx)
    with _at(ctx, '/channels'):
        state = ctx.snapshot.state
        drawn = {key: mapping(row) for key, row in mapping(geometry['records']).items()}
        gate_layers = _declared_layers(ctx, 'gate')
        active_layers = _declared_layers(ctx, 'diffusion')
        actives = {key for key, row in drawn.items() if row['layer'] in active_layers}
        gates = {key: _rect(row['rect']) for key, row in drawn.items() if row['layer'] in gate_layers}
        regions = {key: mapping(row) for key, row in mapping(geometry['regions']).items()
                   if mapping(row)['role'] == 'channel'}
        facts = mapping(state['channels'])
        joins = tuple(mapping(row['fields']) for row in _rows(facts['associations']))
        measurements = tuple(mapping(row['fields']) for row in _rows(facts['measurements']))
        measures = {_ref(m['channel_ref']): m for m in measurements}
        by_device = [(text(mapping(row['device_id'])['name']), _ref(row['channel_ref'])) for row in joins]
        current = mapping(state['current'])
        source = _devices(current)
        target = _devices(ctx.target.circuit, mapping(current['selected_cell']))
        joined_devices = Counter(name for name, _ in by_device)
        joined_channels = Counter(key for _, key in by_device)
        owners = Counter(text(row['owner_id']) for row in regions.values())
        bijection = (joined_devices == Counter(source.keys()) == Counter(target.keys())
                     and joined_channels == Counter(regions.keys()) == Counter(measures.keys())
                     and owners == Counter(actives))
        profile_ref = replace(physical.sources[0], field='/fin_count_profile')
        cdl_sources = tuple(_source(mapping(d['field_sources'])['name'])
                            for devices in (source, target) for d in devices.values())
        result = [_observation('recognition_cardinality', tuple(sorted(regions)), bijection,
            {'source_devices': tuple(source), 'target_devices': tuple(target), 'active_ids': tuple(sorted(actives)),
             'device_channel_pairs': tuple(by_device)}, profile_ref, _snapshot_source(ctx, '/channels/associations'), *cdl_sources)]
        query = mapping(ctx.inputs['query'])
        seeds = _rows(mapping(query['device_regions'])['records'])
        for join, (name, channel) in zip(joins, by_device):
            region = regions[channel]
            active_id = text(region['owner_id'])
            active = _rect(drawn[active_id]['rect'])
            box, = (_rect(value) for value in sequence(region['rectangles']))
            stripes = {key: rect for key, rect in gates.items() if rect.intersection(active) is not None}
            unique = set(stripes.values())
            full = (len(unique) == 1 and next(iter(unique)).intersection(active) == box
                    and box.y0 == active.y0 and box.y1 == active.y1
                    and active.x0 < box.x0 < box.x1 < active.x1)
            gate_sources = tuple(_source(drawn[key]['source']) for key in stripes)
            sources = (_source(drawn[active_id]['source']), *gate_sources)
            identity_sources = tuple(source for seed in seeds if seed['schematic_instance'] == name
                                     for source in _field_sources(seed, 'schematic_instance', 'bbox_nm'))
            result.append(_observation('channel_crossing', (name, channel, active_id, *stripes), full,
                {'active': active.bounds, 'gate_rects': tuple(r.bounds for r in stripes.values()),
                 'channel': box.bounds, 'seed_refs': tuple(_ref(row['fields']) for row in _rows(join['seed_refs']))},
                *sources, *identity_sources))
            measure = measures[channel]
            evaluations = tuple(mapping(row['fields']) for row in _rows(measure['evaluations']))
            fins = tuple(row for row in evaluations if row['status'] == 'qualified')
            if measure['count'] is None:
                raise RuleGap('UnresolvedFinCount', f'{name} has partial or non-independent FIN crossings',
                              sources[0])
            fin_ids = tuple(text(mapping(row['fin_id'])['geometry_record_id']) for row in fins)
            fin_sources = tuple(_source(row['source']) for row in fins)
            count = integer(measure['count'])
            result.append(_observation('qualified_fins', (name, channel, *fin_ids), len(fins) == count,
                {'qualified_count': count, 'fin_ids': fin_ids, 'widths_nm': tuple(f['width_nm'] for f in fins)},
                *sources, *fin_sources))
            counts: dict[str, tuple[int | Fraction, ...]] = {
                'fins_per_finger': (count,), 'channel_length': ((box.x1 - box.x0) * scale,),
                'fin_width': tuple(Fraction(f['width_nm']) for f in fins if isinstance(f['width_nm'], Fraction)),
                'finger_count': (integer(profile['finger_count_required']),),
                'multiplicity': (integer(profile['multiplicity_required']),),
            }
            if name in source and name in target:
                result.append(_observation('device_model', (name, channel), source[name]['model'] == target[name]['model'],
                    {'source_model': source[name]['model'], 'target_model': target[name]['model']},
                    *(_source(mapping(d[name]['field_sources'])['model']) for d in (source, target))))
            models = mapping(physical.payload['models'])
            for domain, devices in (('source', source), ('target', target)):
                if name in devices:
                    device = devices[name]
                    result.extend(_parameters(device, mapping(models[text(device['model'])]), counts,
                                              domain, name, channel, (*sources, *fin_sources)))
        return observed(rule, tuple(result))


def _body(ctx: ConstraintContext) -> FrozenMap:
    """Use W014's bound body operator, separate external objects, and local audit."""
    body = mapping(ctx.snapshot.state['body'])
    binding = mapping(body['binding'])
    physical = mapping(binding['physical'])
    if (physical['payload'] != ctx.physical.payload or body['local_graph_union'] is not False
            or mapping(physical['payload']).get('body_context_profile') is None):
        raise RuleGap('UnsupportedBodyEvidence', 'W014 body operator does not belong to this context',
                      _snapshot_source(ctx, '/body/binding/physical'))
    return body


def _net_evidence(ctx: ConstraintContext, refs: object) -> tuple[SourceRef, ...]:
    registry = mapping(mapping(ctx.snapshot.state['annotation'])['evidence'])
    sources: list[SourceRef] = []
    for key in _refs(refs):
        record = mapping(mapping(registry[key])['record'])
        sources.extend(_field_sources(record, 'bbox_nm', 'schematic_name'))
    return tuple(dict.fromkeys(sources))


def evaluate_body(ctx: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    threshold = integer(mapping(rule.declaration['parameters'])['active_enclosure_nm'])
    with _at(ctx, '/body'):
        body = _body(ctx)
        records = mapping(mapping(ctx.snapshot.state['geometry'])['records'])
        binding = mapping(body['binding'])
        if threshold != binding['active_threshold_nm']:
            raise RuleGap('UnboundActiveThreshold', 'active margin differs from the W014 binding',
                          rule.location('parameters/active_enclosure_nm'))
        evidence = mapping(binding['body_evidence'])
        document = mapping(evidence['payload'])
        external_source = _source(sequence(evidence['sources'])[0])
        shapes = _rows(document['shapes'])
        external = {text(row['id']): replace(external_source, field=f'/shapes/{index}')
                    for index, row in enumerate(shapes)}
        devices = _devices(mapping(ctx.snapshot.state['current']))
        paths = _rows(body['paths'])
        audits = _rows(body['active_audits'])
        actives = _declared_layers(ctx, 'diffusion')
        required_actives = [key for key, row in records.items() if mapping(row)['layer'] in actives]
        if (Counter(text(row['active_id']) for row in audits) != Counter(required_actives)
                or Counter(text(mapping(p['device_id'])['name']) for p in paths) != Counter(devices.keys())):
            raise RuleGap('MissingBodyAudit', 'expected a body audit for each active and each device',
                          _snapshot_source(ctx, '/body'))
        result = []
        for row in audits:
            active = text(row['active_id'])
            candidates = tuple(text(v) for v in sequence(row['body_candidates']))
            if row['margins_nm'] is None:
                raise RuleGap('UnresolvedBodyMatch', f'could not measure active {active}',
                              _source(mapping(records[active])['source']))
            margins = sequence(row['margins_nm'])
            if len(margins) != 4 or not all(isinstance(n, Fraction) for n in margins):
                raise RuleGap('MissingActiveMargins', f'expected four margins for {active}',
                              _snapshot_source(ctx, '/body/active_audits'))
            sources = tuple(_source(mapping(records[key])['source']) for key in (active, *candidates))
            result.append(_observation('active_enclosure', (active, *candidates), len(candidates) == 1
                and all(n >= threshold for n in margins if isinstance(n, Fraction)),
                {'margins_nm': margins, 'threshold_nm': threshold}, *sources,
                rule.location('parameters/active_enclosure_nm')))
        profile = mapping(ctx.physical.payload['body_context_profile'])
        body_layers = {text(sequence(pair)[0]) for pair in mapping(profile['types']).values()}
        pairs = _rows(body['body_pair_audits'])
        expected_pairs: set[tuple[str, frozenset[str]]] = set()
        objects = {
            'local': {key: mapping(row)['layer'] for key, row in records.items()},
            'external': {text(row['id']): row['layer'] for row in shapes},
        }
        for domain, layers in objects.items():
            for a, b in combinations(sorted(body_layers), 2):
                left = (key for key, layer in layers.items() if layer == a)
                right = (key for key, layer in layers.items() if layer == b)
                expected_pairs.update((domain, frozenset(pair)) for pair in product(left, right))
        audited_pairs = {(text(row['domain']), frozenset((text(row['n_id']), text(row['p_id']))))
                         for row in pairs}
        if audited_pairs != expected_pairs or len(audited_pairs) != len(pairs):
            raise RuleGap('MissingOppositeBodyPair', 'incomplete opposite-type body comparisons',
                          _snapshot_source(ctx, '/body/body_pair_audits'))
        for pair in pairs:
            ids: tuple[str, ...] = (text(pair['n_id']), text(pair['p_id']))
            pair_sources = (tuple(_source(mapping(records[key])['source']) for key in ids)
                            if pair['domain'] == 'local' else tuple(external[key] for key in ids))
            result.append(_observation('opposite_bodies', ids, pair['positive_area_overlap'] is False,
                {'domain': pair['domain'], 'positive_area_overlap': pair['positive_area_overlap']}, *pair_sources))
        for path in paths:
            name = text(mapping(path['device_id'])['name'])
            source = _source(path['association_source'])
            nets = _names(path['observed_net_ids'])
            if path['chain_status'] != 'established' or not nets:
                raise RuleGap('UnresolvedBodyRail', f'no proven rail observation for {name}', source)
            if len(nets) > 1:
                raise RuleGap('ConflictingRailNets', f'{name} rail has competing annotations {nets}', source)
            ids = tuple(text(path[key]) for key in ('local_body_record_id', 'external_body_id', 'tap_id',
                                                    'external_rail_id', 'rail_record_id'))
            result.append(_observation('body_to_rail', (name, *ids), nets == (path['context_claim'],),
                {'claim': path['context_claim'], 'observed_nets': nets, 'rail_component': _ref(path['rail_component_ref']),
                 'body_edge_length_nm': path['body_edge_length_nm'], 'rail_edge_length_nm': path['rail_edge_length_nm'],
                 'body_candidates': path['body_candidates'], 'rail_candidates': path['rail_candidates']},
                source, _source(mapping(records[ids[0]])['source']), _source(mapping(records[ids[-1]])['source']),
                *(external[key] for key in ids[1:-1]), *_net_evidence(ctx, path['evidence_refs'])))
        return observed(rule, tuple(result))


def evaluate_terminals(ctx: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    order = tuple(text(v) for v in sequence(mapping(rule.declaration['parameters'])['terminal_order']))
    with _at(ctx, '/terminals'):
        state = ctx.snapshot.state
        graph = mapping(state['connectivity'])
        members = mapping(graph['components'])
        models = mapping(ctx.physical.payload['models'])
        body = _body(ctx)
        paths = {text(mapping(row['device_id'])['name']): row for row in _rows(body['paths'])}
        devices = _devices(mapping(state['current']))
        rows = _rows(state['terminals'])
        summaries = {_ref(row['component_ref']): row for row in _rows(mapping(state['annotation'])['components'])}
        by_terminal = {}
        for row in rows:
            target = mapping(row['target'])
            key = text(mapping(target['device_id'])['name']), text(target['role'])
            by_terminal[key] = row
        expected = {(name, role) for name in devices for role in order}
        if set(by_terminal) != expected or len(rows) != len(expected):
            raise RuleGap('MissingTerminalRelation', 'expected exactly one W014 relation per declared terminal',
                          _snapshot_source(ctx, '/terminals'))
        result = []
        for name, device in devices.items():
            terminals = _rows(device['terminals'])
            roles = tuple(text(t['role']) for t in terminals)
            model = text(device['model'])
            model_order = sequence(mapping(models[model])['terminal_order'])
            model_source = replace(ctx.physical.sources[0], field=f'/models/{model}/terminal_order')
            result.append(_observation('terminal_order', (name,), roles == order == model_order,
                {'observed_order': roles, 'declared_order': order, 'model_order': model_order},
                model_source, *(_source(t['source']) for t in terminals)))
            for terminal in terminals:
                role = text(terminal['role'])
                source = _source(terminal['source'])
                row = by_terminal[name, role]
                nodes, components = _refs(row['node_refs']), _refs(row['component_refs'])
                if row['support_status'] != 'established' or not nodes or not components:
                    raise RuleGap('UnresolvedTerminal', f'{name}.{role} lacks physical support', source)
                if not all(any(n in sequence(members[c]) for c in components) for n in nodes):
                    raise RuleGap('UnboundTerminalComponent', f'{name}.{role} node lacks its bound component', source)
                witness = [_snapshot_source(ctx, '/connectivity/components/' + c) for c in components]
                witness.extend(_net_evidence(ctx, row['evidence_refs']))
                if role == 'B':
                    path = paths[name]
                    if row['context_path'] != path or path['chain_status'] != 'established':
                        raise RuleGap('UnresolvedBodyTerminal', f'independent {name}.B path is missing', source)
                    actual = _names(path['observed_net_ids'])
                    witness.append(_source(path['association_source']))
                else:
                    actual = tuple(sorted({net for c in components for net in _names(summaries[c]['observed_net_ids'])}))
                if not actual:
                    raise RuleGap('UnobservedTerminalNet', f'{name}.{role} has no observed net', witness[0])
                if len(actual) > 1:
                    raise RuleGap('ConflictingTerminalNets', f'{name}.{role} has competing annotations {actual}',
                                  witness[0])
                declared = text(mapping(terminal['net_id'])['name'])
                result.append(_observation('terminal_relation', (name, role, *nodes, *components),
                    actual == (declared,), {'role': role, 'declared_net': declared, 'observed_nets': actual,
                    'domain': 'external_body_path' if role == 'B' else 'local_components',
                    'channel_id': _ref(row['channel_ref']), 'component_ids': components,
                    'evidence_ids': _refs(row['evidence_refs'])}, source, *witness))
        return observed(rule, tuple(result))
