"""Unpublished Stage 2 facts built exclusively from one W006 readback."""
from __future__ import annotations

from dataclasses import InitVar, dataclass, field

from layauto_v2.state.discrete_occupancy import DiscreteOccupancy, OccupancyResult
from .effective import EffectiveGeometryResult, build_effective_geometry
from .geometry import GeometryResult, build_geometry
from .geometry_input import GeometryInput
from .local_connectivity import LocalConnectivityResult, build_local_connectivity
from .projection import build_discrete_occupancy
from .terminal_relations import TerminalRelationsResult, build_terminal_relations


class Stage2AssemblyError(ValueError):
    """The original component outcome retains its evidence, issues or budget shortfall."""

    def __init__(self, stage: str, result: GeometryResult | EffectiveGeometryResult |
                 LocalConnectivityResult | TerminalRelationsResult | OccupancyResult) -> None:
        self.stage = stage
        self.result = result
        if isinstance(result, OccupancyResult):
            detail = f'{result.required_fragments} fragments required, budget {result.budget}'
        else:
            detail = ', '.join(f'{issue.code} at {issue.source.uri}' for issue in result.issues)
        super().__init__(f'{stage}: {detail}')


@dataclass(frozen=True, slots=True, eq=False)
class Stage2Facts:
    """A read-only assembly. Both branches retain the same layout and effective draft."""

    capture: InitVar[GeometryInput]
    fragment_budget: InitVar[int]
    repository_scope: object | None = field(default=None, repr=False, compare=False)
    occupancy: DiscreteOccupancy = field(init=False, repr=False)
    terminals: TerminalRelationsResult = field(init=False, repr=False)

    def __post_init__(self, capture: GeometryInput, fragment_budget: int) -> None:
        if type(capture) is not GeometryInput or capture.readback is None:
            raise ValueError('assembly requires a geometry input bound to a full-run readback')
        if type(fragment_budget) is not int or fragment_budget < 0:
            raise ValueError('fragment_budget requires a nonnegative integer')
        geometry = build_geometry(capture)
        if geometry.status != 'success':
            raise Stage2AssemblyError('geometry', geometry)
        effective = build_effective_geometry(geometry)
        if effective.status != 'success':
            raise Stage2AssemblyError('effective', effective)
        projection = build_discrete_occupancy(geometry, effective=effective, fragment_budget=fragment_budget)
        if projection.value is None:
            raise Stage2AssemblyError('occupancy', projection)
        graph = build_local_connectivity(effective)
        if graph.status != 'success':
            raise Stage2AssemblyError('local_connectivity', graph)
        terminals = build_terminal_relations(graph)
        if terminals.status != 'success':
            raise Stage2AssemblyError('terminal_relations', terminals)
        object.__setattr__(self, 'occupancy', projection.value)
        object.__setattr__(self, 'terminals', terminals)
