"""Small diagnostic views of one successful W020 assembly."""
from collections import Counter, defaultdict

from layauto_v2.domain.regions import canonical_cover


def _source(ref):
    return {key: value for key, value in vars(ref).items() if value is not None}


def _layers(index):
    # Check each original/piece separately. Overlapping records have distinct IDs.
    pieces_by_record = defaultdict(list)
    for result in index.effective.records:
        for region in result.regions:
            pieces_by_record[result.record_id].extend(region.pieces)

    reconstructed = Counter()
    expected_pieces = Counter()
    for record in index.layout.records:
        drawn = index.for_record(record.id, view="drawn")
        if canonical_cover(tuple(fragment.rect for fragment in drawn)) == (record.rect,):
            reconstructed[record.layer, "drawn"] += 1

        covers = defaultdict(list)
        for fragment in index.for_record(record.id, view="effective"):
            covers[fragment.piece_ref].append(fragment.rect)
        for piece in pieces_by_record[record.id]:
            expected_pieces[record.layer] += 1
            if canonical_cover(tuple(covers[piece.ref])) == (piece.rect,):
                reconstructed[record.layer, "effective"] += 1

    diagnostics = defaultdict(Counter)
    for issue in index.diagnostics:
        diagnostics[issue.source.layer, issue.source.view][issue.status] += 1
    return {
        row.layer: {
            "declaration": row.projection,
            "coordinate_field": row.declaration.field,
            "drawn_records": row.record_count,
            "drawn_reconstructed": reconstructed[row.layer, "drawn"],
            "drawn_fragments": len(index.for_layer(row.layer, view="drawn")),
            "drawn_diagnostics": dict(diagnostics[row.layer, "drawn"]),
            "effective_source_pieces": expected_pieces[row.layer],
            "effective_reconstructed": reconstructed[row.layer, "effective"],
            "effective_fragments": len(index.for_layer(row.layer, view="effective")),
            "effective_diagnostics": dict(diagnostics[row.layer, "effective"]),
        }
        for row in index.layers
    }


def scope_summary(facts):
    """Read the existing capture and indices without serializing the receipt chain."""
    index = facts.occupancy
    semantic = facts.terminals.semantic_facts
    terminals = facts.terminals.value
    graph = terminals.local
    annotation = terminals.annotation
    source_cell = next(cell for cell in semantic.source.cells if cell.id == semantic.source.selected_cell)
    target_ids = {target.target_id.record_id for target in annotation.targets}
    markers = [record for record in index.layout.records if record.layer == "MARKER"]
    return {
        "current_semantic": {
            "source": _source(semantic.source.preservation.sources[0]),
            "cell": source_cell.id.name,
            "devices": [device.id.name for device in source_cell.devices],
            "nets": [net.id.name for net in source_cell.nets],
            "semantic_digest": semantic.source.semantic_digest,
        },
        "immutable_target": {
            "source": _source(semantic.target.preservation.sources[0]),
            "cells": [cell.id.name for cell in semantic.target.cells],
            "semantic_digest": semantic.target.semantic_digest,
            "delta_ids": [diff.delta_id.value for diff in semantic.differences],
        },
        "geometry": {
            "source": _source(index.layout.gds.sources[0]),
            "records": len(index.layout.records),
            "canonical_tick_nm": index.layout.units.canonical_tick_nm,
            "markers": [
                {"record_id": record.id.sha256, "bounds_dbu": record.rect.bounds,
                 "source": _source(record.source), "has_net_target": record.id in target_ids}
                for record in markers
            ],
        },
        "occupancy": {
            "coordinate_source": _source(index.model.coordinate_source),
            "unit_ref": index.model.unit_ref.sha256,
            "model_id": index.model.model_id,
            "layers": _layers(index),
        },
        "annotation": {
            "derived_registry_source": _source(annotation.binding.derived.sources[0]),
            "validity": annotation.binding.validity,
            "net_evidence": len(annotation.evidence),
            "region_targets": len(annotation.targets),
            "directly_covered_nm2": str(sum(row.covered_area for row in annotation.coverage)),
            "uncovered_nm2": str(sum(row.uncovered_area for row in annotation.coverage)),
            "conflict_nm2": str(sum(row.conflict_area for row in annotation.coverage)),
        },
        "connectivity": {
            "physical_source": _source(graph.binding.physical.sources[0]),
            "rules_source": _source(graph.binding.rules.sources[0]),
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "components": len(graph.components),
            "body_context_source": _source(terminals.body_evidence.sources[0]),
            "local_graph_union": terminals.body["local_graph_union"],
            "production_matched_body_evidence": terminals.body["production_matched_body_evidence"],
            "lvs_status": terminals.body["lvs_status"],
            "body_terminals": [
                {"device": row.target.device_id.name,
                 "local_components": [component.sha256 for component in row.component_refs],
                 "local_observed_nets": [net.name for net in row.local_observed_net_ids],
                 "context_field": row.context_path["association_source"]["field"],
                 "context_chain": row.context_path["chain_status"],
                 "context_observed_nets": [net.name for net in row.observed_net_ids]}
                for row in terminals.relations if row.context_path is not None
            ],
        },
    }
