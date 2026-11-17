"""Neutral immutable analysis evidence. Construction grants no trust or authority."""
from dataclasses import dataclass

from .codec import FrozenMap
from .evidence import EvidenceRecord, SourceFile, SourceRef
from .results import EvidenceIssue
from .terminal_relations import validate_terminal_graph


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


# These are diagnostic views, not authenticated continuation inputs.
from typing import Literal
from .circuit import SemanticCircuitDraft, Terminal
from .identifiers import DeviceId, NetId
from .regions import RegionRef
from .local_connectivity import LocalRef
from .net_annotation import AnnotationRef


@dataclass(frozen=True)
class AnalysisFinding:
    category: str
    code: str
    source: SourceRef
    affected_refs: tuple[str, ...]
    severity: Literal['error', 'unsupported', 'violation', 'mismatch', 'info']
    message: str


@dataclass(frozen=True)
class AnalysisFacet:
    status: Literal['available', 'error', 'not_evaluated']
    value: object
    issues: tuple[EvidenceIssue, ...] = ()
    dependencies: tuple[str, ...] = ()
    scope: str = 'local_readonly'
    evidence_refs: tuple[SourceRef, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in ('available', 'error', 'not_evaluated'):
            raise ValueError('invalid analysis facet status')
        if self.status == 'not_evaluated' and (self.value is not None or not self.dependencies):
            raise ValueError('unevaluated facet requires dependencies and no value')
        if self.status == 'available' and (self.value is None or self.issues or self.dependencies):
            raise ValueError('available facet requires a value without errors/dependencies')
        if self.status == 'error' and not self.issues:
            raise ValueError('error facet requires original issues')


@dataclass(frozen=True)
class AnalysisFacets:
    drawn: AnalysisFacet
    effective: AnalysisFacet
    local_graph: AnalysisFacet
    channel_fin: AnalysisFacet
    annotation: AnalysisFacet
    terminals: AnalysisFacet

    def __getitem__(self, name: str) -> AnalysisFacet:
        if name not in ('drawn', 'effective', 'local_graph', 'channel_fin', 'annotation', 'terminals'):
            raise KeyError(name)
        return getattr(self, name)  # type: ignore[no-any-return]


@dataclass(frozen=True)
class LocalAnalysis:
    receipt_ref: str
    source: SemanticCircuitDraft | None
    facets: AnalysisFacets


@dataclass(frozen=True)
class AnalysisTerminal:
    binding_ref: str
    device_id: DeviceId
    expected: Terminal
    channel_ref: RegionRef | None
    node_refs: tuple[LocalRef, ...]
    component_refs: tuple[LocalRef, ...]
    annotation_target_refs: tuple[AnnotationRef, ...]
    local_observed_net_ids: tuple[NetId, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    context_path: FrozenMap | None
    observed_net_ids: tuple[NetId, ...]
    support_status: str

    @property
    def comparison(self) -> str:
        if self.support_status != 'established':
            return 'indeterminate'
        if not self.observed_net_ids:
            return 'unknown'
        if len(self.observed_net_ids) > 1:
            return 'conflict'
        return 'equal' if self.observed_net_ids[0] == self.expected.net_id else 'mismatch'


@dataclass(frozen=True)
class SelectedAnalysis:
    status: Literal['not_selected', 'error', 'unsupported', 'evaluated', 'declared', 'not_evaluated']
    selection: FrozenMap
    value: FrozenMap | None = None
    issues: tuple[EvidenceIssue, ...] = ()
    evidence_refs: tuple[SourceRef, ...] = ()
    dependencies: tuple[str, ...] = ()
    scope: str = 'external_readonly'


@dataclass(frozen=True)
class AnalysisResult:
    request_status: Literal['completed', 'rejected', 'unsupported']
    request_ref: SourceRef
    captures: tuple[SourceFile, ...]
    completed_evidence: tuple[EvidenceRecord, ...]
    local: LocalAnalysis | None
    external_body: SelectedAnalysis
    manual_intent: SelectedAnalysis
    findings: tuple[AnalysisFinding, ...]
    missing_context: tuple[str, ...]
    blocked_operations: tuple[str, ...]
    source_comparison: str
    report_json: str
    parent_global: str = 'unknown'
    target_comparison: str = 'not_requested'
    schema_version: str = 'layauto-cell-analysis-result/1'

    def __post_init__(self) -> None:
        if self.request_status not in ('completed', 'rejected', 'unsupported') or self.schema_version != 'layauto-cell-analysis-result/1':
            raise ValueError('invalid analysis result discriminator/version')
        if self.request_status == 'completed' and self.local is None:
            raise ValueError('completed analysis requires authenticated local view')
        if self.request_status == 'rejected' and not any(f.severity in ('error', 'violation') for f in self.findings):
            raise ValueError('rejected analysis requires a located reason')
        if self.request_status == 'unsupported' and not any(f.severity == 'unsupported' for f in self.findings):
            raise ValueError('unsupported analysis requires a located reason')
        if self.parent_global != 'unknown' or self.target_comparison != 'not_requested':
            raise ValueError('analysis does not establish parent or target facts')
