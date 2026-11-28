"""Read-only view of one published version and one run's bound technology."""
from __future__ import annotations

from dataclasses import InitVar, dataclass

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.publication import BaselineSnapshot, BaselineTarget, ContentRef
from layauto_v2.tech.rules import RuleCatalog


@dataclass(frozen=True, slots=True)
class CheckedVersion:
    context_ref: ContentRef
    checkpoint_ref: ContentRef
    tool_ref: ContentRef
    head_ref: ContentRef
    snapshot_ref: ContentRef
    original_checkpoint_ref: ContentRef
    version: int

    @property
    def run_id(self) -> str:
        return self.context_ref.run_id


_PUBLISHED = object()


@dataclass(frozen=True, slots=True)
class ConstraintContext:
    _issuer: InitVar[object]
    version: CheckedVersion
    snapshot: BaselineSnapshot
    catalog: RuleCatalog
    physical: EvidenceRecord
    inputs: FrozenMap
    source_circuit: FrozenMap
    target: BaselineTarget
    eco_commits: tuple[ContentRef, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PUBLISHED:
            raise ValueError('constraint context requires a readback of the sealed publication')

    @classmethod
    def _published(cls, version: CheckedVersion, snapshot: BaselineSnapshot, catalog: RuleCatalog,
                   physical: EvidenceRecord, inputs: FrozenMap, source_circuit: FrozenMap,
                   target: BaselineTarget, eco_commits: tuple[ContentRef, ...]) -> ConstraintContext:
        return cls(_PUBLISHED, version, snapshot, catalog, physical, inputs, source_circuit, target, eco_commits)
