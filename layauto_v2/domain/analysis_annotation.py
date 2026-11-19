"""Independent analysis annotation binding, never a normalization receipt."""
from dataclasses import dataclass, fields
from .codec import FrozenMap, digest
from .evidence import EvidenceRecord, SourceRef
from .geometry import GeometryRef, GeometryRecordId, mapping, sequence
from .identifiers import CellId
from .local_connectivity import LocalRef, ContactComponent
from .regions import RegionRef
from .net_annotation import (AnnotationRef, NET_TYPES, records, sha, text, _value,
                             validate_binding_operands, validate_members)
from .terminal_relations import validate_terminal_graph

@dataclass(frozen=True)
class AnalysisAnnotationBinding:
    local_ref: LocalRef
    effective_ref: RegionRef
    geometry_ref: GeometryRef
    unit_ref: GeometryRef
    partition_ref: GeometryRef
    tick_nm: int
    top: str
    source_cell: CellId
    source_digest: str
    source_ref: SourceRef
    derived: EvidenceRecord
    drawn: EvidenceRecord
    topology: tuple[ContactComponent, ...]
    drawn_record_ids: tuple[GeometryRecordId, ...]
    evidence_refs: tuple[AnnotationRef, ...]
    capture_binding: FrozenMap
    scope: str = 'local_readonly_analysis/1'
    validity: str = 'source_evidence'
    schema_version: str = 'layauto-analysis-annotation/1'

    def __post_init__(self) -> None:
        validate_terminal_graph(self, NET_TYPES + (AnalysisAnnotationBinding,))
        validate_binding_operands(self)
        capture = self.capture_binding
        if set(capture) != {'schema', 'local_receipt_sha256', 'sources'} or capture['schema'] != 'layauto-analysis-capture-binding/1':
            raise ValueError('invalid analysis capture binding')
        sha(capture['local_receipt_sha256'])
        sources = tuple(mapping(x) for x in sequence(capture['sources']))
        if not sources or len({s['uri'] for s in sources}) != len(sources):
            raise ValueError('missing or duplicate analysis sources')
        for source in sources:
            if set(source) != {'uri', 'sha256'}:
                raise ValueError('invalid analysis source fields')
            text(source['uri']); sha(source['sha256'])
        if self.scope != 'local_readonly_analysis/1' or self.validity != 'source_evidence' or self.schema_version != 'layauto-analysis-annotation/1':
            raise ValueError('invalid analysis annotation scope/version')
        for field in fields(self):
            validate_members(getattr(self, field.name))

    def to_value(self) -> FrozenMap:
        validate_terminal_graph(self, NET_TYPES + (AnalysisAnnotationBinding,))
        return FrozenMap({'type': 'AnalysisAnnotationBinding', 'fields': {
            field.name: _value(getattr(self, field.name)) for field in fields(self)}})

    @property
    def ref(self) -> AnnotationRef:
        return AnnotationRef('binding', digest(self.to_value()))
