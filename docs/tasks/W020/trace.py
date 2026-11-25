"""Trace one directly labelled LI fragment in the W020 synthetic full-run example."""
from dataclasses import asdict, replace
from fractions import Fraction

from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.domain.net_annotation import difference, intersections
from layauto_v2.domain.source_location import ref_from_location


def _one(rows, description):
    values = tuple(rows)
    if len(values) != 1:
        raise ValueError(f'{description}: expected one, found {len(values)}')
    return values[0]


def _source(source):
    # Only serialize a leaf location. Receipts and their captured bytes stay with the caller.
    return {key: value for key, value in asdict(source).items() if value is not None}


def _rect(rect):
    return {'bounds_dbu': list(rect.bounds), 'area_dbu2': rect.area}


def _nm_bounds(rect):
    # Integral values stay numbers; sub-nm fractions retain their exact numerator/denominator.
    return [v.numerator if v.denominator == 1 else str(v) for v in rect.bounds]


def _source_operands(evidence):
    operands = {}
    for field in ('vertices_nm', 'derived_layer', 'lvs_index', 'schematic_name'):
        locations = evidence.record['field_sources'][field]['sources']
        operands[field] = []
        for location in locations:
            source = _source(ref_from_location(location))
            if 'token_0based' in location:
                source['token_0based'] = location['token_0based']
            operands[field].append(source)
    return operands


def _drawn_fragment(occupancy, record, indices):
    fragment = _one((f for f in occupancy.for_record(record.id, view='drawn')
                     if f.indices == indices), f'{record.layer} drawn fragment at {indices}')
    cell = occupancy.model.layers[record.layer].cell_bounds(*indices)
    if (fragment.source.record != record or fragment.model_id != occupancy.model.model_id
            or fragment.rect != record.rect.intersection(cell)):
        raise ValueError('drawn fragment does not match its source intersected with the process cell')
    return fragment, cell


def _contact_edges(local, component, node, layout):
    # This LI sample has connector edges to separate conductor regions on either side.
    nodes = {n.ref: n for n in local.nodes}
    edges = []
    for edge in local.edges:
        if node.ref not in edge.endpoints:
            continue
        if edge.connector_id is None or not set(edge.endpoints) <= set(component.members):
            raise ValueError('expected a local connector edge within the LI component')
        connector = layout.record(edge.connector_id)
        endpoints = []
        for ref in edge.endpoints:
            endpoint = nodes[ref]
            overlaps = [hit for rect in endpoint.region.rectangles
                        if (hit := rect.intersection(connector.rect)) is not None]
            if not overlaps:
                raise ValueError('connector has no positive-area overlap with its endpoint')
            endpoints.append({'node_ref': ref.sha256, 'layer': endpoint.layer,
                              'region_ref': endpoint.region.ref.sha256,
                              'source': _source(layout.record(endpoint.region.owner_id).source),
                              'overlaps': [_rect(hit) for hit in overlaps]})
        edges.append({'edge_ref': edge.ref.sha256, 'kind': edge.kind, 'endpoints': endpoints,
                      'source': _source(connector.source), 'connector_id': connector.id.sha256,
                      'connector_layer': connector.layer,
                      'layer_policy': _source(layout.policy(connector.layer).source)})
    if not edges:
        raise ValueError('the selected LI sample has no incident connector edges')
    return edges


def conductor_trace(facts, *, byte_offset=1648, indices=(1, 3)):
    """Return the source-backed chain for one fully covered LI piece and the M1 line end.

    The locators select input geometry. Every identity, net, edge, and intersection is
    looked up in the assembled objects. A missing or ambiguous hop fails this example.
    """
    occupancy = facts.occupancy
    layout = occupancy.layout
    local = facts.terminals.input.value
    terminal = facts.terminals.value
    annotation = terminal.annotation
    record = _one((r for r in layout.records if r.layer == 'LI' and r.source.byte_offset == byte_offset),
                  f'LI record at stream offset {byte_offset}')
    drawn, cell = _drawn_fragment(occupancy, record, indices)
    effective = _one((f for f in occupancy.for_record(record.id, view='effective')
                      if f.indices == indices), f'LI effective piece at {indices}')
    region = _one((r for r in local.effective.for_record(record.id).regions
                   if r.ref == effective.region_ref), 'effective region')
    piece = _one((p for p in region.pieces if p.ref == effective.piece_ref), 'effective region piece')
    if (effective.source.record != record or effective.source.rect != piece.rect
            or effective.rect != piece.rect.intersection(drawn.rect)):
        raise ValueError('effective fragment does not agree with the original record, piece and cell')

    node = _one((n for n in local.nodes if n.layer == record.layer and n.region == region), 'physical node')
    component = _one((c for c in local.components if node.ref in c.members), 'physical component')
    target = _one((t for t in annotation.targets if t.target_id.record_id == record.id
                   and t.target_id.region_ref == region.ref and t.source == record.source
                   and t.node_ref == node.ref and t.component_ref == component.ref), 'annotation target')
    tick = layout.units.canonical_tick_nm
    window = RationalRect(*(Fraction(v * tick) for v in effective.rect.bounds))
    fragment = _one((f for f in annotation.fragments if f.target_ref == target.ref
                     and f.status == 'annotated' and not difference((window,), f.rectangles)),
                    'direct annotation covering the selected effective fragment')
    evidence_ref = _one(fragment.evidence_refs, 'query polygon for the example')
    evidence = _one((e for e in annotation.evidence if e.ref == evidence_ref
                     and fragment.net_ids == (e.net_id,)), 'net evidence')
    match = _one((m for m in annotation.matches if m.evidence_ref == evidence.ref), 'query polygon match')
    hit = _one((h for h in match.intersections if h.target_ref == target.ref), 'matched physical region')
    if (target.tick_nm != tick or difference((window,), hit.rectangles)
            or evidence.rectangle.intersection(window) != window):
        raise ValueError('query coverage does not span the selected effective fragment')
    net = _one((net for c in terminal.source.cells for net in c.nets if net.id == evidence.net_id),
               'source CDL net')

    line_end = _one((r for r in layout.records if r.layer == 'M1' and r.source.byte_offset == 2352),
                    'M1 line-end record')
    end, end_cell = _drawn_fragment(occupancy, line_end, (2, 2))
    coordinate = occupancy.model.coordinate_source
    physical = local.binding.physical.sources[0]
    return {
        'record': {'layer': record.layer, 'top': record.top, 'id': record.id.sha256,
                   'source': _source(record.source), 'stream_key': asdict(record.stream_key),
                   'raw_xy': [list(p) for p in record.raw_xy], **_rect(record.rect),
                   'layer_policy': _source(layout.policy(record.layer).source)},
        'drawn': {'indices': list(indices), 'cell_bounds_dbu': list(cell.bounds), **_rect(drawn.rect),
                  'model_id': drawn.model_id, 'tick_nm': tick, 'unit_ref': drawn.unit_ref.sha256,
                  'unit_source': _source(layout.units.source),
                  'coordinate': _source(replace(coordinate, field='/coordinate_projection/layers/LI'))},
        'effective': {'piece_ref': piece.ref.sha256, 'region_ref': region.ref.sha256,
                      'piece_bounds_dbu': list(piece.rect.bounds), **_rect(effective.rect),
                      'operator_ref': region.operator_ref.sha256,
                      'operator': _source(replace(physical, field='/operators/rectangle_set_difference~11')),
                      'contributors': [r.sha256 for r in region.contributors]},
        'physical': {'node_ref': node.ref.sha256, 'component_ref': component.ref.sha256,
                     'members': [r.sha256 for r in component.members],
                     'operator': _source(replace(physical, field='/operators/cross_layer_contact~11')),
                     'edges': _contact_edges(local, component, node, layout)},
        'annotation': {'target_ref': target.ref.sha256, 'fragment_ref': fragment.ref.sha256,
                       'component_ref': target.component_ref.sha256, 'match_ref': match.ref.sha256,
                       'coverage_nm': [_nm_bounds(r) for r in fragment.rectangles],
                       'covered_fragment_nm': [_nm_bounds(r) for r in intersections((window,), fragment.rectangles)],
                       'covered_area_nm2': window.area.numerator,  # All DBU bounds and tick_nm are integers.
                       'evidence_ref': evidence.ref.sha256, 'query_record': evidence.record['record_id'],
                       'query_key': asdict(evidence.query_key), 'query_rect_nm': _nm_bounds(evidence.rectangle),
                       'request_source': _source(evidence.source), 'source_operands': _source_operands(evidence),
                       'net_name': net.id.name, 'net_id': net.id.id, 'source_cdl': [_source(s) for s in net.sources]},
        'm1_line_end': {'source': _source(line_end.source), 'record_id': line_end.id.sha256,
                        'indices': [2, 2], 'cell_bounds_dbu': list(end_cell.bounds), **_rect(end.rect),
                        'coordinate': _source(replace(coordinate, field='/coordinate_projection/layers/M1'))},
    }
