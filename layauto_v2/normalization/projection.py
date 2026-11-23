"""Bind selected technology and optional effective geometry for a local Stage 2 index."""
from __future__ import annotations

from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.state.discrete_occupancy import OccupancyResult, build_discrete_occupancy as project_layout
from .effective import EffectiveGeometryResult
from .geometry import GeometryResult
from .projection_model import bind_projection_model


class ProjectionBindingError(ValueError):
    def __init__(self, issue: EvidenceIssue, geometry: GeometryResult) -> None:
        self.issue = issue
        self.geometry = geometry
        super().__init__(issue.message)


def build_discrete_occupancy(geometry: GeometryResult, *, fragment_budget: int,
                             effective: EffectiveGeometryResult | None = None) -> OccupancyResult:
    """Project authenticated local records. The caller supplies the whole-call fragment limit."""
    model = bind_projection_model(geometry)
    assert geometry.value is not None
    derived = None
    if effective is not None:
        if type(effective) is not EffectiveGeometryResult:
            raise ValueError('a captured EffectiveGeometryResult is required')
        if effective.status != 'success' or effective.value is None:
            raise ProjectionBindingError(effective.issues[0], geometry)
        if effective.input != geometry:
            raise ProjectionBindingError(EvidenceIssue(
                'binding', 'ForeignEffectiveGeometry',
                'effective regions must come from the selected geometry receipt and technology',
                effective.value.base.layout.gds.sources[0]), geometry)
        derived = effective.value
    return project_layout(geometry.value.layout, model, fragment_budget=fragment_budget, effective=derived)
