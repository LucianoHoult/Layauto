"""Neutral immutable analysis evidence. Construction grants no trust or authority."""
from dataclasses import dataclass
from pathlib import Path

from .codec import FrozenMap
from .evidence import EvidenceRecord, SourceFile, SourceRef
from .results import EvidenceIssue
from .terminal_relations import validate_terminal_graph


@dataclass(frozen=True)
class AnalysisRequest:
    manifest_path: Path


@dataclass(frozen=True)
class LocalAnalysisEvidence:
    root: str
    manifest_uri: str
    captures: tuple[SourceFile, ...]
    aliases: FrozenMap
    probes: FrozenMap
    records: tuple[EvidenceRecord, ...]
    value: FrozenMap | None
    issues: tuple[EvidenceIssue, ...] = ()
    schema_version: str = 'layauto-local-analysis-evidence/1'

    def __post_init__(self) -> None:
        validate_terminal_graph(self, (LocalAnalysisEvidence, SourceFile, SourceRef, EvidenceRecord, EvidenceIssue))
        if self.schema_version != 'layauto-local-analysis-evidence/1':
            raise ValueError('unsupported analysis evidence version')
        if not self.root or not self.manifest_uri:
            raise ValueError('missing analysis acquisition root')
        if len({s.uri for s in self.captures}) != len(self.captures):
            raise ValueError('duplicate capture URI')
        sources = {s.uri: s.sha256 for s in self.captures}
        for source in self.captures:
            if SourceFile(source.uri, source.data) != source:
                raise ValueError('capture differs from actual bytes')
        for record in self.records:
            if any(sources.get(ref.uri) != ref.sha256 for ref in record.sources):
                raise ValueError('record references uncaptured bytes')
        if (self.value is None) != bool(self.issues):
            raise ValueError('inconsistent analysis evidence outcome')
