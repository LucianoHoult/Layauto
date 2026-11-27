"""Immutable rule declarations from the selected and authenticated rules owner."""
from __future__ import annotations

from dataclasses import dataclass, replace

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import mapping, sequence, text


@dataclass(frozen=True, slots=True)
class RuleRecord:
    declaration: FrozenMap
    source: SourceRef

    @property
    def id(self) -> str:
        return text(self.declaration['id'])

    @property
    def evaluator(self) -> str:
        return text(self.declaration['exact_evaluator_ref'])

    def location(self, suffix: str) -> SourceRef:
        return replace(self.source, field=f'{self.source.field}/{suffix}')


@dataclass(frozen=True, slots=True)
class RuleCatalog:
    source: SourceRef
    schema_version: str
    mandatory_policy: FrozenMap
    rules: tuple[RuleRecord, ...]

    @classmethod
    def from_owner(cls, document: FrozenMap, source: SourceRef) -> RuleCatalog:
        rows = tuple(RuleRecord(mapping(row), replace(source, field=f'/rules/{i}'))
                     for i, row in enumerate(sequence(document['rules'])))
        return cls(source, text(document['schema_version']), mapping(document['mandatory_rule_policy']), rows)
