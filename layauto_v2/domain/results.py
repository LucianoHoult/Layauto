"""Neutral component outcomes, separate from execution and StageFailure."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .codec import FrozenMap, freeze_map
from .evidence import EvidenceRecord, SourceFile, SourceRef

Category = Literal['read', 'config', 'parse', 'unsupported', 'binding']


@dataclass(frozen=True)
class EvidenceIssue:
    category: Category
    code: str
    message: str
    source: SourceRef

    def __post_init__(self) -> None:
        if self.category not in ('read', 'config', 'parse', 'unsupported', 'binding'):
            raise ValueError('invalid issue category')
        if not isinstance(self.code, str) or not self.code or not isinstance(self.message, str) or not self.message or not isinstance(self.source, SourceRef):
            raise ValueError('issue requires reason and source')


class InputError(Exception):
    """Expected input failure; caught only by the public component facade."""
    def __init__(self, category: Category, code: str, message: str, source: SourceRef) -> None:
        self.issue = EvidenceIssue(category, code, message, source)
        super().__init__(message)


@dataclass(frozen=True)
class ParseResult:
    status: Literal['success', 'error']
    value: FrozenMap | None
    issues: tuple[EvidenceIssue, ...]
    completed: tuple[EvidenceRecord, ...]
    sources: tuple[SourceFile, ...]
    tool_run_id: str | None = None
    schema_version: str = 'layauto-parse-result/1'

    def __post_init__(self) -> None:
        if self.schema_version != 'layauto-parse-result/1' or self.status not in ('success', 'error'):
            raise ValueError('invalid parse discriminator/version')
        for name, cls in (('issues', EvidenceIssue), ('completed', EvidenceRecord), ('sources', SourceFile)):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or any(not isinstance(value, cls) for value in values):
                raise ValueError('invalid parse record fields')
            object.__setattr__(self, name, tuple(values))
        by_uri = {source.uri: source.sha256 for source in self.sources}
        if len(by_uri) != len(self.sources):
            raise ValueError('duplicate source URI')
        for record in self.completed:
            if any(by_uri.get(ref.uri) != ref.sha256 for ref in record.sources):
                raise ValueError('completed evidence references unread bytes')
        for issue in self.issues:
            if issue.source.sha256 is not None and by_uri.get(issue.source.uri) != issue.source.sha256:
                raise ValueError('issue references unread bytes')
        if self.status == 'success':
            if self.value is None or self.issues:
                raise ValueError('success requires value and no issues')
            object.__setattr__(self, 'value', freeze_map(self.value))
        elif self.value is not None or not self.issues:
            raise ValueError('error requires issues and no final value')
        if self.tool_run_id is not None and (not isinstance(self.tool_run_id, str) or not self.tool_run_id):
            raise ValueError('invalid external tool run link')
