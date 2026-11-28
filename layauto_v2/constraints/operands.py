"""Read exact spacing operands and their provenance from a published Stage 2 snapshot."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect, integer, mapping, sequence, text
from layauto_v2.domain.regions import RegionPiece, RegionRef
from layauto_v2.domain.source_location import ref_from_location
from .drc_context import ConstraintContext
from .result import RuleGap, ShapeWitness

# Each operand is one independent shape, even when it has several pieces.
Operands = tuple[int, tuple[tuple[ShapeWitness, ...], ...]]


@contextmanager
def _at(context: ConstraintContext, path: str) -> Iterator[None]:
    try:
        yield
    except (KeyError, ValueError) as exc:
        ref = context.version.snapshot_ref
        raise RuleGap('InvalidSnapshotOperand', str(exc), SourceRef(ref.id, ref.digest, field=path)) from exc


def _geometry(context: ConstraintContext) -> tuple[FrozenMap, int]:
    with _at(context, '/geometry/units/contract/canonical_tick_nm'):
        geometry = mapping(context.snapshot.state['geometry'])
        contract = mapping(mapping(geometry['units'])['contract'])
        scale = integer(contract['canonical_tick_nm'])
        if scale <= 0:
            raise ValueError('canonical DBU scale must be positive')
    return geometry, scale


def _rect(value: object) -> Rect:
    x0, y0, x1, y1 = sequence(value)
    return Rect(integer(x0), integer(y0), integer(x1), integer(y1))


def _drawn_layer(context: ConstraintContext, geometry: FrozenMap, layer_name: str,
                 role: str) -> dict[str, ShapeWitness]:
    with _at(context, '/layers/' + layer_name):
        layer = mapping(mapping(context.snapshot.state['layers'])[layer_name])
        declaration = mapping(mapping(layer['policy'])['declaration'])
        stream = mapping(declaration['stream_key'])
        if (declaration['name'], declaration['role'], stream['element']) != (layer_name, role, 'BOUNDARY'):
            raise ValueError(f'expected the selected {layer_name} {role} BOUNDARY layer')
        if role == 'cut' and (declaration['cut_target'] != 'LI'
                              or declaration['effective_geometry_operator'] != 'rectangle_set_difference/1'):
            raise ValueError('expected CUT to select rectangle_set_difference/1 on LI')
    with _at(context, '/geometry/records'):
        records = mapping(geometry['records'])
        sources = mapping(context.snapshot.binding['sources'])
    shapes = {}
    for record_id, value in records.items():
        path = '/geometry/records/' + record_id
        with _at(context, path):
            row = mapping(value)
            if row['layer'] != layer_name:
                continue
            if row['stream_key'] != stream or row['id'] != record_id:
                raise ValueError('drawn record disagrees with the selected stream key or record ID')
        with _at(context, path + '/source'):
            source = ref_from_location(mapping(row['source']))
            if (source.byte_offset is None or source.record_index is None
                    or sources.get(source.uri) != source.sha256):
                raise ValueError('expected a bound GDS stream location')
        with _at(context, path + '/rect'):
            shapes[record_id] = ShapeWitness(record_id, _rect(row['rect']), source)
    return shapes


def metal(context: ConstraintContext, layer_name: str) -> Operands:
    geometry, scale = _geometry(context)
    records = _drawn_layer(context, geometry, layer_name, 'interconnect')
    return scale, tuple((shape,) for shape in records.values())


def effective_li(context: ConstraintContext) -> Operands:
    geometry, scale = _geometry(context)
    wires = _drawn_layer(context, geometry, 'LI', 'interconnect')
    cuts = _drawn_layer(context, geometry, 'CUT', 'cut')
    with _at(context, '/geometry'):
        effective = mapping(geometry['effective_by_record'])
        regions = mapping(geometry['regions'])
        pieces = mapping(geometry['pieces'])

    operands = []
    for wire in wires.values():
        with _at(context, '/geometry/effective_by_record/' + wire.record_id):
            row = mapping(effective[wire.record_id])
            if row['operation'] != 'cut':
                raise ValueError('expected a CUT result for each drawn LI')
            contributors = sequence(row['contributors'])
            cut_shapes = tuple(cuts[text(record_id)] for record_id in contributors)
            region_ids = tuple(text(value) for value in sequence(row['region_ids']))
        for region_id in region_ids:
            with _at(context, '/geometry/regions/' + region_id):
                region = mapping(regions[region_id])
                if (region['role'], region['owner_id'], region['contributors']) != ('effective', wire.record_id, contributors):
                    raise ValueError('effective region disagrees with its LI owner or CUT contributors')
                region_ref = RegionRef('region', region_id)
                rectangles = tuple(_rect(value) for value in sequence(region['rectangles']))
                if not rectangles:
                    raise ValueError('an effective region must contain a rectangle')
            witnesses = []
            for rect in rectangles:
                # W009 keys a piece by its parent region and its exact rectangle.
                piece = RegionPiece(region_ref, rect)
                piece_id = piece.ref.sha256
                with _at(context, '/geometry/pieces/' + piece_id):
                    if pieces[piece_id] != piece.to_value():
                        raise ValueError('piece disagrees with its effective region geometry')
                witnesses.append(replace(wire, rect=rect, region_id=region_id, piece_id=piece_id, cuts=cut_shapes))
            operands.append(tuple(witnesses))
    return scale, tuple(operands)
