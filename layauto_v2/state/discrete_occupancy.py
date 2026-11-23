"""Sparse, capture-traceable occupancy under explicitly bound process axes."""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Literal, TypeVar

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import DrawnRecord, GeometryRecordId, GeometryRef, Rect, integer
from layauto_v2.domain.regions import RegionRef, RegionRole
from .layout_store import LayoutDraft
from .projection_axes import CellGrid, TrackAxis, TrackLocation
from .projection_model import ProjectionModel
from .regions import EffectiveDraft

View = Literal['drawn', 'effective']


@dataclass(frozen=True, slots=True)
class ProjectionSource:
    """One drawn record or one W009 piece, before any cell intersections."""

    record: DrawnRecord
    rect: Rect
    view: View
    region_ref: RegionRef | None = None
    piece_ref: RegionRef | None = None
    role: RegionRole | None = None
    contributors: tuple[GeometryRecordId, ...] = ()

    @property
    def record_source(self) -> SourceRef:
        return self.record.source

    @property
    def record_id(self) -> GeometryRecordId:
        return self.record.id

    @property
    def layer(self) -> str:
        return self.record.layer

    def __hash__(self) -> int:
        # DrawnRecord retains its immutable, unhashable raw evidence map.
        # Its typed ID already binds the GDS bytes and stream position.
        return hash((self.record_id, self.view, self.region_ref, self.piece_ref, self.rect))


@dataclass(frozen=True, slots=True)
class DiscreteFragment:
    source: ProjectionSource
    indices: tuple[int, ...]
    rect: Rect
    model_id: str

    @property
    def unit_ref(self) -> GeometryRef:
        return self.source.record.unit_ref

    @property
    def layer(self) -> str:
        return self.source.layer

    @property
    def record_id(self) -> GeometryRecordId:
        return self.source.record_id

    @property
    def view(self) -> View:
        return self.source.view

    @property
    def region_ref(self) -> RegionRef | None:
        return self.source.region_ref

    @property
    def piece_ref(self) -> RegionRef | None:
        return self.source.piece_ref

    @property
    def contributors(self) -> tuple[GeometryRecordId, ...]:
        return self.source.contributors


@dataclass(frozen=True, slots=True)
class LayerReport:
    layer: str
    record_count: int
    projection: str
    declaration: SourceRef


@dataclass(frozen=True, slots=True)
class ProjectionDiagnostic:
    status: str
    source: ProjectionSource
    track: TrackLocation | None = None


@dataclass(frozen=True, slots=True)
class _TrackHit:
    source: ProjectionSource
    index: int

    @property
    def count(self) -> int:
        return 1

    def coverage(self) -> Iterator[tuple[tuple[int, ...], Rect]]:
        yield (self.index,), self.source.rect


@dataclass(frozen=True, slots=True)
class _GridHit:
    source: ProjectionSource
    grid: CellGrid
    span: tuple[int, int, int, int]

    @property
    def count(self) -> int:
        x0, x1, y0, y1 = self.span
        return (x1 - x0 + 1) * (y1 - y0 + 1)

    def coverage(self) -> Iterator[tuple[tuple[int, ...], Rect]]:
        x0, x1, y0, y1 = self.span
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                rect = self.source.rect.intersection(self.grid.cell_bounds(x, y))
                assert rect is not None  # Spans contain only positive-area intersections.
                yield (x, y), rect


def _sources(layout: LayoutDraft, effective: EffectiveDraft | None) -> Iterator[ProjectionSource]:
    for record in layout.records:
        yield ProjectionSource(record, record.rect, 'drawn')
    if effective is not None:
        records = {record.id: record for record in layout.records}
        for result in effective.records:
            owner = records[result.record_id]
            for region in result.regions:
                for piece in region.pieces:
                    yield ProjectionSource(owner, piece.rect, 'effective', piece.region_ref,
                                           piece.ref, region.role, region.contributors)


def _hit(source: ProjectionSource, model: ProjectionModel,
         scale: int) -> _GridHit | _TrackHit | ProjectionDiagnostic:
    if source.layer not in model.layers:
        return ProjectionDiagnostic('missing_declaration', source)
    axes = model.layers[source.layer]
    if axes is None:
        return ProjectionDiagnostic('projection_none', source)
    if isinstance(axes, TrackAxis):
        track = axes.strip(source.rect, scale)
        if track.status == 'on_track':
            return _TrackHit(source, track.neighbours[0][0])
        return ProjectionDiagnostic(track.status, source, track)
    try:
        span = axes.spans(source.rect)
    except IndexError:
        return ProjectionDiagnostic('outside_range', source)
    return _GridHit(source, axes, span)


def _describe_layers(layout: LayoutDraft, model: ProjectionModel) -> tuple[LayerReport, ...]:
    counts = Counter(record.layer for record in layout.records)
    reports = []
    for policy in layout.policies:
        name = policy.name
        axes = model.layers.get(name)
        if name not in model.layers:
            projection = 'missing_declaration'
        elif axes is None:
            projection = 'projection_none'
        elif isinstance(axes, TrackAxis):
            projection = '1d_track'
        else:
            projection = '2d_cells'
        key = name.replace('~', '~0').replace('/', '~1')
        location = replace(model.coordinate_source, field=f'/coordinate_projection/layers/{key}')
        reports.append(LayerReport(name, counts[name], projection, location))
    return tuple(reports)


class _BudgetExceeded(Exception):
    def __init__(self, total: int, source: ProjectionSource) -> None:
        self.total = total
        self.source = source
        super().__init__('projection exceeds the requested fragment budget')


Key = TypeVar('Key')
Fragments = tuple[DiscreteFragment, ...]


def _freeze(index: dict[Key, list[DiscreteFragment]]) -> Mapping[Key, Fragments]:
    return MappingProxyType({key: tuple(fragments) for key, fragments in index.items()})


def _view(fragments: Fragments, view: View | None) -> Fragments:
    if view is None:
        return fragments
    if view not in ('drawn', 'effective'):
        raise ValueError('unknown occupancy view')
    return tuple(fragment for fragment in fragments if fragment.view == view)


@dataclass(frozen=True, slots=True)
class DiscreteOccupancy:
    layout: LayoutDraft
    model: ProjectionModel
    effective: EffectiveDraft | None
    budget: int
    fragments: Fragments = field(init=False)
    layers: tuple[LayerReport, ...] = field(init=False)
    diagnostics: tuple[ProjectionDiagnostic, ...] = field(init=False)
    _by_cell: Mapping[tuple[str, tuple[int, ...]], Fragments] = field(init=False, repr=False, compare=False)
    _by_record: Mapping[GeometryRecordId, Fragments] = field(init=False, repr=False, compare=False)
    _by_layer: Mapping[str, Fragments] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if integer(self.budget) < 0:
            raise ValueError('fragment budget must be nonnegative')
        layout, model, effective = self.layout, self.model, self.effective
        if type(layout) is not LayoutDraft or type(model) is not ProjectionModel:
            raise ValueError('discrete occupancy requires a verified layout and bound projection model')
        if model.unit_ref != layout.units.ref:
            raise ValueError('projection unit differs from layout unit')
        if (model.tech_sources[1] != layout.drawn.sources[0]
                or model.tech_sources[4] != layout.formats.sources[0]):
            raise ValueError('projection model and layout have different layer or format owners')
        if model.layers.keys() - {policy.name for policy in layout.policies}:
            raise ValueError('model declares a layer outside this layout policy table')
        if effective is not None and (type(effective) is not EffectiveDraft
                                      or effective.base.layout != layout
                                      or effective.physical.sources[0] != model.tech_sources[3]):
            raise ValueError('effective geometry belongs to another layout or physical owner')

        total = 0
        exceeded_at = None
        hits: list[_GridHit | _TrackHit] = []
        diagnostics: list[ProjectionDiagnostic] = []
        for source in _sources(layout, effective):
            hit = _hit(source, model, layout.units.canonical_tick_nm)
            if isinstance(hit, ProjectionDiagnostic):
                diagnostics.append(hit)
                continue
            total += hit.count
            if total > self.budget:
                if exceeded_at is None:
                    exceeded_at = source
            else:
                hits.append(hit)
        if exceeded_at is not None:
            raise _BudgetExceeded(total, exceeded_at)

        # Store each fragment once. Index buckets hold references to that same object.
        fragments: list[DiscreteFragment] = []
        reports = _describe_layers(layout, model)
        by_layer: dict[str, list[DiscreteFragment]] = {report.layer: [] for report in reports}
        by_record: dict[GeometryRecordId, list[DiscreteFragment]] = {r.id: [] for r in layout.records}
        by_cell: dict[tuple[str, tuple[int, ...]], list[DiscreteFragment]] = defaultdict(list)
        model_id = model.model_id
        for planned in hits:
            for indices, rect in planned.coverage():
                fragment = DiscreteFragment(planned.source, indices, rect, model_id)
                fragments.append(fragment)
                by_layer[fragment.layer].append(fragment)
                by_record[fragment.record_id].append(fragment)
                by_cell[(fragment.layer, indices)].append(fragment)
        object.__setattr__(self, 'layers', reports)
        object.__setattr__(self, 'diagnostics', tuple(diagnostics))
        object.__setattr__(self, 'fragments', tuple(fragments))
        object.__setattr__(self, '_by_cell', _freeze(by_cell))
        object.__setattr__(self, '_by_layer', _freeze(by_layer))
        object.__setattr__(self, '_by_record', _freeze(by_record))

    def for_record(self, identity: GeometryRecordId, *, view: View | None = None) -> Fragments:
        return _view(self._by_record[identity], view)

    def for_layer(self, layer: str, *, view: View | None = None) -> Fragments:
        return _view(self._by_layer[layer], view)

    def in_cell(self, layer: str, *indices: int, view: View | None = None) -> Fragments:
        axes = self.model.layers[layer]
        if isinstance(axes, TrackAxis) and len(indices) == 1:
            axes.centre(indices[0])
        elif isinstance(axes, CellGrid) and len(indices) == 2:
            axes.cell_bounds(indices[0], indices[1])
        else:
            raise ValueError('cell indices must match the declared projection')
        return _view(self._by_cell.get((layer, indices), ()), view)


@dataclass(frozen=True, slots=True)
class OccupancyResult:
    status: Literal['success', 'resource_limit']
    layout: LayoutDraft
    model: ProjectionModel
    effective: EffectiveDraft | None
    budget: int
    required_fragments: int
    exceeded_at: ProjectionSource | None
    value: DiscreteOccupancy | None


def build_discrete_occupancy(layout: LayoutDraft, model: ProjectionModel, *, fragment_budget: int,
                             effective: EffectiveDraft | None = None) -> OccupancyResult:
    """Preflight the aggregate before materializing any fragment or occupied cell."""
    try:
        occupancy = DiscreteOccupancy(layout, model, effective, fragment_budget)
    except _BudgetExceeded as exc:
        return OccupancyResult('resource_limit', layout, model, effective, fragment_budget,
                               exc.total, exc.source, None)
    return OccupancyResult('success', layout, model, effective, fragment_budget,
                           len(occupancy.fragments), None, occupancy)
