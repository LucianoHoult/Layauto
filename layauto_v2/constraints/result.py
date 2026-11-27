"""Whole-cell rule observations, with exact measurements and immutable backlinks."""
from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Literal

from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect
from layauto_v2.tech.rules import RuleCatalog, RuleRecord
from .drc_context import CheckedVersion

RuleStatus = Literal['pending', 'pass', 'violation', 'indeterminate', 'error']


@dataclass(frozen=True, slots=True)
class ShapeWitness:
    record_id: str
    rect: Rect
    source: SourceRef


@dataclass(frozen=True, slots=True)
class PairMeasurement:
    first: ShapeWitness
    second: ShapeWitness
    dx_dbu: int
    dy_dbu: int
    nm_per_dbu: int
    threshold_nm: int
    same_layer_contact: bool

    @property
    def distance_squared_dbu2(self) -> int:
        return self.dx_dbu ** 2 + self.dy_dbu ** 2

    @property
    def distance_squared_nm2(self) -> int:
        return self.distance_squared_dbu2 * self.nm_per_dbu ** 2

    @property
    def status(self) -> Literal['pass', 'violation', 'same_layer_contact']:
        if self.same_layer_contact:
            return 'same_layer_contact'
        return 'violation' if self.distance_squared_nm2 < self.threshold_nm ** 2 else 'pass'

    @property
    def distance_nm(self) -> int | None:
        """Exact integral distance if available; the squared value is always exact."""
        squared = self.distance_squared_nm2
        root = isqrt(squared)
        return root if root * root == squared else None


@dataclass(frozen=True, slots=True)
class RuleIssue:
    code: str
    message: str
    source: SourceRef


@dataclass(frozen=True, slots=True)
class MissingRule:
    """The requested ID and the location of the catalog that omitted it."""
    id: str
    source: SourceRef


@dataclass(frozen=True, slots=True)
class RuleCheck:
    rule: RuleRecord | MissingRule
    status: RuleStatus
    pairs: tuple[PairMeasurement, ...] = ()
    threshold_nm: int | None = None
    issue: RuleIssue | None = None
    policy_action: str | None = None

    @property
    def violations(self) -> tuple[PairMeasurement, ...]:
        return tuple(pair for pair in self.pairs if pair.status == 'violation')


@dataclass(frozen=True, slots=True)
class RuleReport:
    version: CheckedVersion
    catalog: RuleCatalog
    checks: tuple[RuleCheck, ...]

    def for_rule(self, rule_id: str) -> RuleCheck:
        for check in self.checks:
            if check.rule.id == rule_id:
                return check
        raise KeyError(f'{self.catalog.source.uri}#/rules: {rule_id} is not declared')
