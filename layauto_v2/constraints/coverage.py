"""Check drawn and effective inventories against W013's bound annotation and W010 topology."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Literal

from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import integer, mapping, record_identity, sequence, text
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import _at, _geometry
from .result import Observation, RuleCheck, observed


def _id(value: object) -> str:
    return text(mapping(value)['sha256'])


def _drawn_inventory(context: ConstraintContext, geometry: FrozenMap, annotation: FrozenMap,
                     regions: FrozenMap, nodes: FrozenMap, rule: RuleRecord) -> list[Observation]:
    records = mapping(geometry['records'])
    classifications = {_id(r['record_id']): r for r in map(mapping, sequence(annotation['classifications']))}
    node_owners = {text(mapping(regions[text(mapping(n)['region_id'])])['owner_id']) for n in nodes.values()}
    target_owners = {_id(mapping(mapping(t)['id'])['record_id']) for t in mapping(annotation['targets']).values()}
    gds = mapping(context.inputs['gds'])
    source = ref_from_location(mapping(gds['source']))
    layers = mapping(context.snapshot.state['layers'])
    rows = []
    captured = set()
    for value in sequence(gds['elements']):
        element = mapping(value)
        gds_ref = replace(source, byte_offset=integer(element['byte_offset']), record_index=integer(element['record_index']))
        identity = record_identity(gds_ref, text(gds['top'])).sha256
        captured.add(identity)
        row = mapping(records[identity])
        classified = classifications[identity]
        layer = text(row['layer'])
        policy = mapping(mapping(layers[layer])['policy'])
        role = text(mapping(policy['declaration'])['role'])
        marker = role == 'marker'
        retained = (row['preservation'] == element and classified['layer'] == layer
                    and classified['role'] == role and classified['source'] == row['source'])
        conductor = identity in node_owners
        target = identity in target_owners
        marker_ok = not marker or (classified['classification'] == 'marker' and not conductor and not target)
        facts = FrozenMap({'layer': layer, 'bbox_dbu': row['rect'], 'classification': classified['classification'],
                           'has_conductor_node': conductor, 'raw_retained': retained,
                           'direct_annotation_target': target})
        status: Literal['pass', 'violation', 'disclosed'] = 'pass' if conductor else 'disclosed'
        if not (retained and marker_ok and target == conductor):
            status = 'violation'
        rows.append(Observation('drawn_coverage', (identity,), status, facts,
                                (gds_ref, ref_from_location(mapping(policy['source'])),
                                 rule.location('parameters/unknown_nonconductor_policy'))))
    if captured != set(records) or captured != set(classifications):
        raise ValueError('drawn and classification inventories differ from captured GDS records')
    return rows


def _effective_inventory(geometry: FrozenMap, regions: FrozenMap, nodes: FrozenMap) -> list[Observation]:
    records = mapping(geometry['records'])
    pieces = mapping(geometry['pieces'])
    pieces_by_region: dict[str, list[FrozenMap]] = defaultdict(list)
    for piece in pieces.values():
        p = mapping(piece)
        pieces_by_region[_id(p['region_ref'])].append(p)
    owners: dict[str, str] = {}
    for owner, value in mapping(geometry['effective_by_record']).items():
        for rid in sequence(mapping(value)['region_ids']):
            owners[text(rid)] = owner
    node_regions = {text(mapping(n)['region_id']) for n in nodes.values()}
    if set(regions) != set(owners) | node_regions or set(regions) != set(pieces_by_region):
        raise ValueError('region inventory disagrees with effective owners, conductor nodes or pieces')
    rows = []
    for rid, region in regions.items():
        r = mapping(region)
        owner = text(r['owner_id'])
        rects = sequence(r['rectangles'])
        pieces_match = sorted(tuple(map(integer, sequence(p['rect']))) for p in pieces_by_region[rid]) == sorted(
            tuple(map(integer, sequence(rect))) for rect in rects)
        valid = owners.get(rid, owner) == owner and pieces_match
        rows.append(Observation('effective_coverage', (owner, rid), 'pass' if valid else 'violation',
                                FrozenMap({'role': r['role'], 'rectangles_dbu': rects,
                                           'has_conductor_node': rid in node_regions, 'pieces_match': pieces_match}),
                                (ref_from_location(mapping(mapping(records[owner])['source'])),)))
    return rows


def _annotation_inventory(annotation: FrozenMap, graph: FrozenMap, rule: RuleRecord) -> list[Observation]:
    targets = mapping(annotation['targets'])
    nodes = mapping(graph['nodes'])
    members = {text(node): component for component, value in mapping(graph['components']).items()
               for node in sequence(value)}
    if set(nodes) != set(members) or {mapping(t)['node'] for t in targets.values()} != set(nodes):
        raise ValueError('annotation targets must cover every local conductor node and component')
    evidence = mapping(annotation['evidence'])
    labels_by_id: dict[str, FrozenMap] = {}
    nets: dict[str, set[str]] = defaultdict(set)
    net_sources: dict[str, set[SourceRef]] = defaultdict(set)
    covered_targets = set()
    rows = []
    for fid, value in mapping(annotation['fragments']).items():
        fragment = mapping(value)
        tid = _id(fragment['target_ref'])
        target = mapping(targets[tid])
        node = text(target['node'])
        component = members[node]
        rid = _id(mapping(target['id'])['region_ref'])
        source = ref_from_location(mapping(target['source']))
        refs = [source]
        for evidence_ref in sequence(fragment['evidence_refs']):
            record = mapping(mapping(evidence[_id(evidence_ref)])['record'])
            fields = mapping(record['field_sources'])
            refs.append(ref_from_location(mapping(sequence(mapping(fields['record_id'])['sources'])[0])))
        labels = tuple(mapping(n) for n in sequence(fragment['net_ids']))
        for net in labels:
            net_id = digest(net)
            labels_by_id[net_id] = net
            nets[net_id].add(component)
            net_sources[net_id].update(refs)
        covered_targets.add(tid)
        supported = (component == target['component'] and rid == mapping(nodes[node])['region_id']
                     and fragment['status'] != 'conflict')
        disposition = text(fragment['status']) if labels else text(annotation['unknown_conductor_policy'])
        rows.append(Observation('annotation_fragment', (fid, tid, rid, node, component),
                                'violation' if not supported else 'pass' if labels else 'disclosed',
                                FrozenMap({'net_ids': labels, 'rectangles_nm': fragment['rectangles'],
                                           'annotation': fragment['status'], 'disposition': disposition}), tuple(refs)))
    if covered_targets != set(targets):
        raise ValueError('a conductor target is missing its annotation fragments')
    for net_id, components in nets.items():
        if len(components) > 1:
            sources = sorted(net_sources[net_id], key=lambda r: (r.uri, r.line or 0, r.byte_offset or 0, r.field or ''))
            rows.append(Observation('separate_label_islands', tuple(sorted(components)), 'disclosed',
                                    FrozenMap({'net': labels_by_id[net_id], 'physical_component_count': len(components)}),
                                    (*sources, rule.location('parameters/disconnected_label_policy'))))
    return rows


def evaluate_coverage(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    geometry, _ = _geometry(context)
    state = context.snapshot.state
    with _at(context, '/annotation/classifications'):
        annotation = mapping(state['annotation'])
        regions = mapping(geometry['regions'])
        graph = mapping(state['connectivity'])
        nodes = mapping(graph['nodes'])
        rows = _drawn_inventory(context, geometry, annotation, regions, nodes, rule)
    with _at(context, '/geometry/regions'):
        rows.extend(_effective_inventory(geometry, regions, nodes))
    with _at(context, '/annotation/fragments'):
        rows.extend(_annotation_inventory(annotation, graph, rule))
    return observed(rule, tuple(rows))
