"""Check both sides of each declared connector in its published geometry domain."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Literal

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect, integer, mapping, sequence, text
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.state.local_connectivity import encloses_connector, unsupported_enclosure_field
from layauto_v2.tech.rules import RuleRecord
from .drc_context import ConstraintContext
from .operands import _at, _geometry, _rect, side_margins_nm
from .result import Observation, RuleCheck, RuleGap, observed


@dataclass(frozen=True)
class ConnectorPair:
    layers: tuple[str, str]
    external: bool
    source: SourceRef


def _pairs(context: ConstraintContext, rule: RuleRecord) -> dict[str, ConnectorPair]:
    result = {}
    with _at(context, '/layers'):
        for layer, row in mapping(context.snapshot.state['layers']).items():
            policy = mapping(mapping(row)['policy'])
            declaration = mapping(policy['declaration'])
            if declaration.get('enclosure_rule') != rule.id:
                continue
            first, second = sequence(declaration['electrical_connects'])
            source = ref_from_location(mapping(policy['source']))
            result[layer] = ConnectorPair((text(first), text(second)), declaration['role'] == 'body_contact',
                                          replace(source, field=f'{source.field}/electrical_connects'))
    return result


@dataclass(frozen=True)
class Endpoint:
    region_id: str
    owner_id: str
    layer: str
    pieces: tuple[Rect, ...]
    contributor_ids: tuple[str, ...]


def _nodes(graph: FrozenMap, regions: FrozenMap) -> dict[str, Endpoint]:
    nodes = {}
    for key, item in mapping(graph['nodes']).items():
        row = mapping(item)
        region_id = text(row['region_id'])
        region = mapping(regions[region_id])
        pieces = tuple(_rect(r) for r in sequence(region['rectangles']))
        nodes[key] = Endpoint(region_id, text(region['owner_id']), text(row['layer']), pieces,
                              tuple(text(i) for i in sequence(region['contributors'])))
    return nodes


def _record_source(records: FrozenMap, key: str) -> SourceRef:
    return ref_from_location(mapping(mapping(records[key])['source']))


def _local(context: ConstraintContext, rule: RuleRecord, pairs: dict[str, ConnectorPair],
           threshold: int) -> Iterator[Observation]:
    geometry, scale = _geometry(context)
    graph = mapping(context.snapshot.state['connectivity'])
    records = mapping(geometry['records'])
    nodes = _nodes(graph, mapping(geometry['regions']))
    edges = {text(edge['connector_id']): (key, edge) for key, item in mapping(graph['edges']).items()
             if (edge := mapping(item))['kind'] == 'connector'}
    audits = {(text(a['connector_id']), text(a['layer'])): a for a in map(mapping, sequence(graph['enclosure']))}
    margin = Fraction(threshold, scale)
    for key, item in records.items():
        record = mapping(item)
        layer = text(record['layer'])
        pair = pairs.get(layer)
        if pair is None or pair.external:
            continue
        rect = _rect(record['rect'])
        connector_source = _record_source(records, key)
        edge_id, edge = edges[key]
        ends = tuple(text(mapping(ref)['sha256']) for ref in sequence(edge['endpoints']))
        for side, side_layer in enumerate(pair.layers):
            # Count independent positive-area regions, before component grouping.
            candidates = tuple(node_id for node_id, n in nodes.items() if n.layer == side_layer and
                               any(r.intersection(rect) is not None for r in n.pieces))
            if len(candidates) != 1 or candidates[0] not in ends:
                raise RuleGap('UnconfirmedConnectorMatch', f'{layer} side {side_layer} has candidates {candidates}',
                              connector_source)
            node_id, = candidates
            endpoint = nodes[node_id]
            audit = audits[key, side_layer]
            ok = encloses_connector(endpoint.pieces, rect, margin)
            status: Literal['pass', 'violation'] = 'pass' if ok else 'violation'
            if (mapping(audit['node_ref'])['sha256'] != node_id or audit['margin_ticks'] != margin
                    or audit['status'] != status):
                raise RuleGap('EnclosureAuditMismatch', f'W010 side disagrees with {side_layer} geometry or threshold',
                              connector_source)
            measured = None
            if len(endpoint.pieces) == 1:
                r, = endpoint.pieces
                measured = side_margins_nm(r, rect, scale)
            facts = FrozenMap({'connector_layer': layer, 'side_layer': side_layer, 'side': side,
                               'connector_rect_dbu': rect.bounds,
                               'region_rectangles_dbu': tuple(r.bounds for r in endpoint.pieces),
                               'nm_per_dbu': scale, 'margins_nm': measured, 'threshold_nm': threshold,
                               'edge_id': edge_id, 'candidate_node_ids': candidates, 'contributors': endpoint.contributor_ids})
            sources = (connector_source, _record_source(records, endpoint.owner_id), pair.source,
                       rule.location('parameters/enclosure_nm'),
                       replace(context.physical.sources[0], field='/operators/cross_layer_contact~11'))
            yield Observation('local_enclosure', (key, endpoint.region_id, endpoint.owner_id), status, facts,
                              sources + tuple(_record_source(records, contributor) for contributor in endpoint.contributor_ids))


def _external(context: ConstraintContext, rule: RuleRecord, pairs: dict[str, ConnectorPair],
              threshold: int) -> Iterator[Observation]:
    body = mapping(context.snapshot.state['body'])
    evidence = mapping(mapping(body['binding'])['body_evidence'])
    source = ref_from_location(mapping(sequence(evidence['sources'])[0]))
    shape_rows = map(mapping, sequence(mapping(evidence['payload'])['shapes']))
    shapes = {text(shape['id']): (shape, replace(source, field=f'/shapes/{i}'))
              for i, shape in enumerate(shape_rows)}
    audits = {text(tap['tap_id']): tap for tap in map(mapping, sequence(body['tap_audits']))}
    for key, (shape, tap_ref) in shapes.items():
        layer = text(shape['layer'])
        pair = pairs.get(layer)
        if pair is None or not pair.external:
            continue
        tap = audits[key]
        if tap['threshold_nm'] != threshold or tap['layer'] != layer or ref_from_location(mapping(tap['source'])) != tap_ref:
            raise RuleGap('EnclosureAuditMismatch', 'W014 tap has another layer, threshold or input source', tap_ref)
        for side, side_layer in zip(('body', 'rail'), pair.layers):
            candidates = sequence(tap[side + '_candidates'])
            if len(candidates) != 1:
                raise RuleGap('UnconfirmedConnectorMatch', f'{key} {side} has candidates {candidates}', tap_ref)
            candidate_id = text(candidates[0])
            conductor, conductor_ref = shapes[candidate_id]
            if conductor['layer'] != side_layer:
                raise RuleGap('EnclosureAuditMismatch', f'{key} {side} selected an unexpected layer', conductor_ref)
            reported = sequence(tap[side + '_margins_nm'])
            margins = tuple(v for v in reported if isinstance(v, Fraction))
            if len(reported) != 4 or len(margins) != 4:
                raise RuleGap('MissingMeasurement', f'{key} lacks four exact {side} margins', tap_ref)
            ok = min(margins) >= threshold
            facts = FrozenMap({'connector_layer': layer, 'side_layer': side_layer, 'side': side,
                               'candidate_ids': candidates, 'margins_nm': margins, 'threshold_nm': threshold,
                               'connector_bbox_nm': shape['bbox'], 'conductor_bbox_nm': conductor['bbox']})
            yield Observation('external_enclosure', (key, candidate_id), 'pass' if ok else 'violation', facts,
                              (tap_ref, conductor_ref, pair.source, rule.location('parameters/enclosure_nm'),
                               replace(context.physical.sources[0], field='/operators/body_context~12')))


def evaluate_enclosure(context: ConstraintContext, rule: RuleRecord) -> RuleCheck:
    field = unsupported_enclosure_field(rule.declaration)
    if field is not None:
        raise RuleGap('UnsupportedRuleDeclaration', f'unsupported T05 {field}', rule.location(field))
    threshold = integer(mapping(rule.declaration['parameters'])['enclosure_nm'])
    pairs = _pairs(context, rule)
    observations: list[Observation] = []
    for path, collect in (('/connectivity/enclosure', _local), ('/body/tap_audits', _external)):
        try:
            observations.extend(collect(context, rule, pairs, threshold))
        except RuleGap:
            raise
        except (KeyError, ValueError, IndexError) as exc:
            ref = context.version.snapshot_ref
            raise RuleGap('InvalidSnapshotOperand', str(exc), SourceRef(ref.id, ref.digest, field=path)) from exc
    return observed(rule, tuple(observations))
