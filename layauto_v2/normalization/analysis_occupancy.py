"""Optional projection of geometry already constructed by single-cell analysis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from layauto_v2.domain.analysis import LocalAnalysis
from layauto_v2.domain.results import EvidenceIssue, InputError
from layauto_v2.state.discrete_occupancy import OccupancyResult, build_discrete_occupancy
from layauto_v2.state.occupancy import BaseOccupancy
from layauto_v2.state.regions import EffectiveDraft
from .analysis_input import LocalAnalysisReceipt
from .projection_model import _bind_model


@dataclass(frozen=True, slots=True)
class OccupancyRequest:
    fragment_budget: int
    include_effective: bool = False

    def __post_init__(self) -> None:
        if type(self.fragment_budget) is not int or self.fragment_budget < 0:
            raise ValueError('fragment_budget requires a nonnegative integer')
        if type(self.include_effective) is not bool:
            raise ValueError('include_effective requires a boolean')


@dataclass(frozen=True, slots=True)
class OccupancyUnavailable:
    status: Literal['not_evaluated', 'invalid_declaration']
    dependencies: tuple[str, ...]
    issues: tuple[EvidenceIssue, ...]
    value: None = None


def _project_local(receipt: LocalAnalysisReceipt, local: LocalAnalysis,
                   request: OccupancyRequest) -> OccupancyUnavailable | OccupancyResult:
    drawn = local.facets.drawn
    if drawn.status != 'available':
        return OccupancyUnavailable('not_evaluated', ('drawn',), drawn.issues)
    assert isinstance(drawn.value, BaseOccupancy)
    layout = drawn.value.layout
    facet = local.facets.effective
    missing_effective = request.include_effective and facet.status != 'available'
    # Coordinate binding only needs the authenticated layout and tech record.
    tech = next(record for record in receipt.evidence.records if record.kind == 'tech')
    try:
        model = _bind_model(layout, tech)
    except InputError as exc:
        if missing_effective:
            return OccupancyUnavailable('not_evaluated', ('effective', 'coordinate'),
                                        (*facet.issues, exc.issue))
        return OccupancyUnavailable('invalid_declaration', ('coordinate',), (exc.issue,))
    if missing_effective:
        return OccupancyUnavailable('not_evaluated', ('effective',), facet.issues)
    effective = None
    if request.include_effective:
        assert isinstance(facet.value, EffectiveDraft)
        effective = facet.value
    return build_discrete_occupancy(layout, model, fragment_budget=request.fragment_budget,
                                    effective=effective)
