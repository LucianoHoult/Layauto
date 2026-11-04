"""Pure exact CUT difference and toy spatial channel/terminal drafts.

Slab boundaries are only an internal Boolean decomposition. They are neither a
manufacturing lattice nor connectivity edges or occupancy replacements.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from layauto_v2.domain.codec import FrozenMap, canonical_bytes, digest
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import (
    DrawnRecord, GeometryRecordId, GeometryRef, LayerPolicy, OccupantFragmentId,
    Rect, StreamLayerKey, UnitBinding,
)
from layauto_v2.domain.regions import (
    VERSION, ExactRegion, OperatorBinding, RecordRegions, RegionProblem, RegionRef, validate_closed_graph,
)
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.tech.schema import SchemaError, validate_payload
from .coordinate import BasePartition, LayerPartition
from .layout_store import LayoutDraft
from .occupancy import BaseCellId, BaseOccupancy, OccupantFragment

_BASE_TYPES = (BaseOccupancy, BasePartition, LayerPartition, LayoutDraft, UnitBinding,
               DrawnRecord, LayerPolicy, GeometryRecordId, GeometryRef, OccupantFragmentId,
               Rect, StreamLayerKey, BaseCellId, OccupantFragment, EvidenceRecord, SourceRef)


def slab_difference(target: Rect, cuts: Iterable[Rect]) -> tuple[Rect, ...]:
    """Canonical disjoint rectangle cover of target minus the union of cuts.

    All calculations retain exact integers. Equal y intervals extend over
    adjacent x slabs, removing artificial decomposition boundaries.
    """
    if type(target) is not Rect:
        raise ValueError('difference target must be an exact rectangle')
    clipped: set[Rect] = set()
    for cut in cuts:
        if type(cut) is not Rect:
            raise ValueError('difference cuts must be exact rectangles')
        overlap = target.intersection(cut)
        if overlap is not None:
            clipped.add(overlap)
    xs = sorted({target.x0, target.x1} | {x for rect in clipped for x in (rect.x0, rect.x1)})
    open_spans: dict[tuple[int, int], Rect] = {}
    result: list[Rect] = []
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((cut.y0, cut.y1) for cut in clipped if cut.x0 <= left and right <= cut.x1)
        spans: list[tuple[int, int]] = []
        cursor = target.y0
        for low, high in intervals:
            if cursor < low:
                spans.append((cursor, low))
            cursor = max(cursor, high)
        if cursor < target.y1:
            spans.append((cursor, target.y1))
        new_spans: dict[tuple[int, int], Rect] = {}
        for low, high in spans:
            previous = open_spans.pop((low, high), None)
            new_spans[low, high] = Rect(left if previous is None else previous.x0, low, right, high)
        result.extend(open_spans.values())
        open_spans = new_spans
    result.extend(open_spans.values())
    return tuple(sorted(result, key=lambda rect: rect.bounds))


def _edge(a: Rect, b: Rect) -> bool:
    # Only single-region internal grouping; no same-layer contact inference.
    return ((a.x1 == b.x0 or b.x1 == a.x0) and max(a.y0, b.y0) < min(a.y1, b.y1)
            or (a.y1 == b.y0 or b.y1 == a.y0) and max(a.x0, b.x0) < min(a.x1, b.x1))


def _groups(rectangles: tuple[Rect, ...]) -> tuple[tuple[Rect, ...], ...]:
    remaining = set(range(len(rectangles)))
    groups: list[tuple[Rect, ...]] = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        seen, pending = [seed], [seed]
        while pending:
            index = pending.pop()
            neighbors = [other for other in remaining if _edge(rectangles[index], rectangles[other])]
            for other in neighbors:
                remaining.remove(other)
                pending.append(other)
                seen.append(other)
        groups.append(tuple(sorted((rectangles[index] for index in seen), key=lambda rect: rect.bounds)))
    return tuple(sorted(groups, key=lambda group: tuple(rect.bounds for rect in group)))


def _records(base: BaseOccupancy, operators: OperatorBinding) -> tuple[RecordRegions, ...]:
    if type(base) is not BaseOccupancy or type(operators) is not OperatorBinding:
        raise ValueError('effective draft requires immutable base geometry and operators')
    validate_closed_graph(base, _BASE_TYPES)
    for values, cls in ((base.layout.records, DrawnRecord), (base.layout.policies, LayerPolicy),
                        (base.partition.layers, LayerPartition), (base.fragments, OccupantFragment)):
        if type(values) is not tuple or any(type(item) is not cls for item in values):
            raise ValueError('effective base requires exact immutable geometry records')
    # Validate the complete retained W008 value chain, including legacy literal
    # fields that may compare equal while carrying mutable caller attributes.
    canonical_bytes(base.to_value())
    layout = base.layout
    if operators.drawn != layout.drawn or operators.unit_ref != layout.units.ref:
        raise ValueError('region operator owner/unit differ from base geometry')
    for owner, kind in ((operators.physical, 'physical'), (operators.drawn, 'drawn')):
        try:
            validate_payload(owner.payload, kind)
        except SchemaError as exc:
            raise RegionProblem(EvidenceIssue('unsupported', 'UnsupportedRegionOperator',
                                              'invalid closed region policy owner: ' + str(exc),
                                              replace(owner.sources[0], field=exc.path or '/'))) from exc
    unit_ref, operator_ref = operators.unit_ref, operators.ref
    cuts = tuple(record for record in layout.records if record.layer == 'CUT')
    gates = tuple(record for record in layout.records if record.layer == 'POLY')
    results: list[RecordRegions] = []
    for record in sorted(layout.records, key=lambda item: item.id.sha256):
        if record.layer == 'LI':
            applicable = tuple(cut for cut in cuts if record.rect.intersection(cut.rect) is not None)
            contributors = tuple(sorted((cut.id for cut in applicable), key=lambda item: item.sha256))
            groups = _groups(slab_difference(record.rect, (cut.rect for cut in applicable)))
            regions = tuple(ExactRegion(record.id, 'effective', contributors, unit_ref, operator_ref, group)
                            for group in groups)
            results.append(RecordRegions(record.id, 'cut', contributors, unit_ref, operator_ref, regions))
        elif record.layer == 'OD':
            applicable = tuple(gate for gate in gates if record.rect.intersection(gate.rect) is not None)
            stripes = {gate.rect for gate in applicable}
            if len(stripes) != 1:
                raise RegionProblem(EvidenceIssue('unsupported', 'AmbiguousGateStripe',
                                                  'active requires exactly one positive-area gate stripe',
                                                  replace(record.source, field='/recognized_channel')))
            channel = record.rect.intersection(next(iter(stripes)))
            assert channel is not None
            active = record.rect
            if not (active.y0 == channel.y0 and active.y1 == channel.y1
                    and active.x0 < channel.x0 < channel.x1 < active.x1):
                raise RegionProblem(EvidenceIssue('unsupported', 'UnsupportedTerminalSplit',
                                                  'channel must divide all active coverage into left S and right D',
                                                  replace(record.source, field='/terminal_split')))
            contributors = tuple(sorted((gate.id for gate in applicable), key=lambda item: item.sha256))
            source = Rect(active.x0, active.y0, channel.x0, active.y1)
            drain = Rect(channel.x1, active.y0, active.x1, active.y1)
            regions = (ExactRegion(record.id, 'channel', contributors, unit_ref, operator_ref, (channel,)),
                       ExactRegion(record.id, 'S', contributors, unit_ref, operator_ref, (source,)),
                       ExactRegion(record.id, 'D', contributors, unit_ref, operator_ref, (drain,)))
            results.append(RecordRegions(record.id, 'terminal', contributors, unit_ref, operator_ref, regions))
    return tuple(results)


@dataclass(frozen=True)
class EffectiveDraft:
    base: BaseOccupancy
    operators: OperatorBinding
    records: tuple[RecordRegions, ...]
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported effective draft version')
        values: object = self.records
        if type(values) is not tuple and type(values) is not list:
            raise ValueError('effective draft requires typed record regions')
        object.__setattr__(self, 'records', tuple(values))
        if any(type(item) is not RecordRegions for item in self.records):
            raise ValueError('effective draft requires typed record regions')
        if self.records != _records(self.base, self.operators):
            raise ValueError('effective draft omitted/duplicated geometry or contains foreign regions/provenance/unit/operators')

    @property
    def physical(self) -> EvidenceRecord:
        return self.operators.physical

    @property
    def ref(self) -> RegionRef:
        return RegionRef('draft', digest(self.to_value()))

    @property
    def semantic_digest(self) -> str:
        # Keep original record multiplicity while ignoring source order/positions.
        rows = []
        for result in self.records:
            record = self.base.layout.record(result.record_id)
            rows.append(FrozenMap({'layer': record.layer, 'drawn_rect': record.rect.bounds,
                                   'operation': result.operation,
                                   'regions': tuple(FrozenMap({'role': region.role,
                                                              'rectangles': tuple(rect.bounds for rect in region.rectangles)})
                                                    for region in result.regions)}))
        return digest({'schema': 'layauto-effective-geometry-semantic/1',
                       'drawn_semantic': self.base.layout.semantic_digest,
                       'canonical_tick_nm': self.base.layout.units.canonical_tick_nm,
                       'records': tuple(sorted(rows, key=canonical_bytes))})

    def for_record(self, record_id: GeometryRecordId) -> RecordRegions:
        self.base.layout.record(record_id)
        for result in self.records:
            if result.record_id == record_id:
                return result
        raise KeyError(record_id)

    def to_value(self) -> FrozenMap:
        return FrozenMap({'schema': self.schema_version, 'base_ref': self.base.ref.to_value(),
                          'operators': self.operators.to_value(),
                          'records': tuple(result.to_value() for result in self.records)})


def build_effective_draft(base: BaseOccupancy, physical: EvidenceRecord) -> EffectiveDraft:
    if type(base) is not BaseOccupancy:
        raise ValueError('effective geometry requires a complete immutable base occupancy')
    operators = OperatorBinding(physical, base.layout.drawn, base.layout.units.ref)
    return EffectiveDraft(base, operators, _records(base, operators))
