"""Exact multi-occupant drawn-base index; never annotation or connectivity."""
from __future__ import annotations

from dataclasses import dataclass

from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.geometry import (
    VERSION, GeometryRecordId, GeometryRef, OccupantFragmentId, Rect,
    integer, text, version,
)
from .coordinate import BasePartition
from .layout_store import LayoutDraft


@dataclass(frozen=True)
class BaseCellId:
    partition_ref: GeometryRef
    layer: str
    x: int
    y: int

    def __post_init__(self) -> None:
        if type(self.partition_ref) is not GeometryRef or self.partition_ref.kind != 'base_partition':
            raise ValueError('base cell requires a typed base-partition reference')
        text(self.layer)
        if integer(self.x) < 0 or integer(self.y) < 0:
            raise ValueError('negative base cell index')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': 'layauto-base-cell-id/1', 'partition_ref': self.partition_ref.to_value(),
                          'layer': self.layer, 'x': self.x, 'y': self.y})


def fragment_identity(record_id: GeometryRecordId, cell: BaseCellId, rect: Rect,
                      unit_ref: GeometryRef) -> OccupantFragmentId:
    if type(record_id) is not GeometryRecordId or type(cell) is not BaseCellId or type(rect) is not Rect:
        raise ValueError('fragment identity requires typed geometry/cell/rectangle')
    if type(unit_ref) is not GeometryRef or unit_ref.kind != 'unit':
        raise ValueError('fragment identity requires a typed unit reference')
    return OccupantFragmentId(digest({'schema': 'layauto-base-fragment-id/1', 'record_id': record_id.sha256,
                                      'cell': cell.to_value(), 'rect': rect.bounds, 'unit_ref': unit_ref.to_value()}))


@dataclass(frozen=True)
class OccupantFragment:
    id: OccupantFragmentId
    record_id: GeometryRecordId
    cell: BaseCellId
    rect: Rect
    unit_ref: GeometryRef
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        if type(self.id) is not OccupantFragmentId or self.id != fragment_identity(self.record_id, self.cell, self.rect, self.unit_ref):
            raise ValueError('fragment identity differs from its exact coverage/references')

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'id': self.id.sha256, 'record_id': self.record_id.sha256,
                          'cell': self.cell.to_value(), 'rect': self.rect.bounds, 'unit_ref': self.unit_ref.to_value()})


def _fragments(partition: BasePartition) -> tuple[OccupantFragment, ...]:
    if type(partition) is not BasePartition:
        raise ValueError('base occupancy requires a verified immutable partition')
    layout = partition.layout
    partition_ref, unit_ref = partition.ref, layout.units.ref
    layers = {layer.layer: layer for layer in partition.layers}
    fragments: list[OccupantFragment] = []
    for record in layout.records:
        if not layout.policy(record.layer).projected:
            continue
        layer = layers[record.layer]
        for x, y, rect in layer.project(record.rect):
            cell = BaseCellId(partition_ref, record.layer, x, y)
            identity = fragment_identity(record.id, cell, rect, unit_ref)
            fragments.append(OccupantFragment(identity, record.id, cell, rect, unit_ref))
    return tuple(sorted(fragments, key=lambda f: (f.cell.layer, f.cell.x, f.cell.y, f.record_id.sha256)))


@dataclass(frozen=True)
class BaseOccupancy:
    partition: BasePartition
    fragments: tuple[OccupantFragment, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        version(self.schema_version)
        if not isinstance(self.fragments, (tuple, list)) or any(type(f) is not OccupantFragment for f in self.fragments):
            raise ValueError('base occupancy requires exact typed fragments')
        object.__setattr__(self, 'fragments', tuple(self.fragments))
        if self.fragments != _fragments(self.partition):
            raise ValueError('base occupancy omitted/duplicated coverage or contains foreign geometry/cell/unit refs')

    @property
    def layout(self) -> LayoutDraft:
        return self.partition.layout

    @property
    def layout_ref(self) -> GeometryRef:
        return self.layout.ref

    @property
    def partition_ref(self) -> GeometryRef:
        return self.partition.ref

    @property
    def ref(self) -> GeometryRef:
        return GeometryRef('base_occupancy', digest(self.to_value()))

    def for_record(self, record_id: GeometryRecordId) -> tuple[OccupantFragment, ...]:
        self.layout.record(record_id)
        return tuple(fragment for fragment in self.fragments if fragment.record_id == record_id)

    def in_cell(self, cell: BaseCellId) -> tuple[OccupantFragment, ...]:
        if type(cell) is not BaseCellId or cell.partition_ref != self.partition_ref:
            raise ValueError('cell belongs to a different base partition')
        self.partition.layer(cell.layer).cell_bounds(cell.x, cell.y)
        return tuple(fragment for fragment in self.fragments if fragment.cell == cell)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'partition_ref': self.partition_ref.to_value(),
                          'layout_ref': self.layout_ref.to_value(),
                          'fragments': tuple(fragment.to_value() for fragment in self.fragments)})


def build_occupancy(partition: BasePartition) -> BaseOccupancy:
    return BaseOccupancy(partition, _fragments(partition))
