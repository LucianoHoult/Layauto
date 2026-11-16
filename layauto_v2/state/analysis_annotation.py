"""Analysis annotation view with the same complete neutral consistency checks."""
from dataclasses import dataclass, fields, replace
from layauto_v2.domain.codec import FrozenMap, digest
from layauto_v2.domain.analysis_annotation import AnalysisAnnotationBinding
from layauto_v2.domain.net_annotation import (AnnotationRef, NetEvidence, TargetEvidence,
    MatchEvidence, AnnotationFragment, LayerCoverage, NetComponentSummary, RecordClassification,
    AnnotationIssue, NET_TYPES, validate_members, _value)
from layauto_v2.domain.terminal_relations import validate_terminal_graph
from .annotation import (_validate_inputs, _validate_matches, _validate_fragments,
                         _validate_components, _validate_coverage, _validate_issues)

@dataclass(frozen=True)
class AnalysisAnnotationDraft:
    binding: AnalysisAnnotationBinding
    evidence: tuple[NetEvidence, ...]
    targets: tuple[TargetEvidence, ...]
    matches: tuple[MatchEvidence, ...]
    fragments: tuple[AnnotationFragment, ...]
    coverage: tuple[LayerCoverage, ...]
    components: tuple[NetComponentSummary, ...]
    classifications: tuple[RecordClassification, ...]
    issues: tuple[AnnotationIssue, ...]
    schema_version: str = 'layauto-analysis-annotation/1'


    def __post_init__(self) -> None:
        if type(self.binding) is not AnalysisAnnotationBinding or self.schema_version != 'layauto-analysis-annotation/1':
            raise ValueError('invalid analysis annotation draft')
        validate_terminal_graph(self, NET_TYPES + (AnalysisAnnotationBinding, AnalysisAnnotationDraft))
        if replace(self.binding) != self.binding:
            raise ValueError('analysis binding differs from reconstruction')
        for field in fields(self):
            validate_members(getattr(self, field.name))
        for check in (_validate_inputs, _validate_matches, _validate_fragments, _validate_components, _validate_coverage, _validate_issues):
            check(self)

    def to_value(self) -> FrozenMap:
        self.__post_init__()
        return FrozenMap({'type': 'AnalysisAnnotationDraft', 'fields': {
            field.name: self.binding.to_value() if field.name == 'binding' else _value(getattr(self, field.name)) for field in fields(self)}})

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('draft', digest(self.to_value()))
