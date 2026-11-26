"""Read-only inputs to a future baseline initialization transaction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal
from weakref import ReferenceType, ref

from layauto_v2.domain.circuit import SemanticCircuitDraft, TargetCircuit
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import LayerPolicy
from layauto_v2.domain.intent import TargetDifference
from layauto_v2.domain.terminal_relations import TerminalRelation
from .annotation import AnnotationDraft
from .discrete_occupancy import DiscreteOccupancy, LayerReport, ProjectionDiagnostic
from .layout_store import LayoutDraft
from .local_connectivity import LocalConnectivityDraft


@dataclass(frozen=True, slots=True)
class TargetContext:
    target: TargetCircuit
    differences: tuple[TargetDifference, ...]


@dataclass(frozen=True, slots=True)
class ProjectionGap:
    """Conditional requirements relative to LayerReport.declaration in the coordinate owner."""
    operation: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayerInitialization:
    policy: LayerPolicy
    projection: LayerReport
    drawn_reconstructed: int
    effective_pieces: int
    effective_reconstructed: int
    diagnostics: tuple[ProjectionDiagnostic, ...]
    gap: ProjectionGap | None

    @property
    def availability(self) -> str:
        if self.projection.projection in ('missing_declaration', 'projection_none'):
            return self.projection.projection
        if self.diagnostics or self.drawn_reconstructed != self.projection.record_count or (
                self.effective_reconstructed != self.effective_pieces):
            return 'incomplete'
        return 'reconstructed' if self.projection.record_count else 'no_local_records'


@dataclass(frozen=True, slots=True, init=False)
class ProposedInitialState(ABC):
    """Producer-constructed draft. All geometry resolves through the occupancy's layout."""
    _origin: tuple[ReferenceType[ProposedInitialState], object] = field(repr=False, compare=False)
    current: SemanticCircuitDraft
    target_context: TargetContext
    occupancy: DiscreteOccupancy
    connectivity: LocalConnectivityDraft
    annotation: AnnotationDraft
    terminals: tuple[TerminalRelation, ...]
    channel_observations: FrozenMap
    body: FrozenMap
    body_evidence: EvidenceRecord
    capture_binding: FrozenMap
    layers: Mapping[str, LayerInitialization]

    @abstractmethod
    def __init__(self) -> None:
        """Only the producer can supply a complete authenticated assembly."""

    def _bind_origin(self, scope: object) -> None:
        # A copied/substituted candidate cannot reuse the original object's attestation.
        object.__setattr__(self, '_origin', (ref(self), scope))

    def belongs_to(self, scope: object) -> bool:
        origin = getattr(self, '_origin', None)
        return origin is not None and origin[0]() is self and origin[1] is scope

    @property
    def layout(self) -> LayoutDraft:
        return self.occupancy.layout

    @property
    def uncovered_conductor_policy(self) -> Literal['suspect_conductor']:
        """Applies only to exact unknown conductor fragments (architecture §2.3, §4)."""
        return 'suspect_conductor'

    @property
    def rules(self) -> EvidenceRecord:
        """Captured scopes, missing-context dispositions and nonconductor coverage policy."""
        return self.connectivity.binding.rules
