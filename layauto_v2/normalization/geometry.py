"""Capture-bound drawn geometry and base occupancy; a pure Stage 2 component.

It neither runs semantic normalization nor changes its source/target/seeds.
Successful construction does not imply physical interpretation or publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from layauto_v2.domain.codec import canonical_bytes
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import GEOMETRY_COMPARATOR, evidence_value, mapping
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.state.layout_store import LayoutDraft, build_layout
from layauto_v2.state.coordinate import BasePartition, build_partition
from layauto_v2.state.occupancy import BaseOccupancy, build_occupancy
from .geometry_input import GeometryInput

VERSION = 'layauto-base-geometry-result/1'


def _evidence(input: GeometryInput) -> tuple[EvidenceRecord, EvidenceRecord, EvidenceRecord]:
    records = {record.kind: record for record in input.parse.completed}
    tech = mapping(input.value['tech'])
    return (records['gds'], EvidenceRecord('drawn', mapping(tech['drawn']), (records['tech'].sources[1],)),
            EvidenceRecord('formats', mapping(tech['formats']), (records['tech'].sources[4],)))


def _problem(input: GeometryInput) -> EvidenceIssue | None:
    formats = mapping(mapping(input.value['tech'])['formats'])
    capability = mapping(formats['geometry_capability'])
    if capability['comparator'] != GEOMETRY_COMPARATOR:
        reference = _evidence(input)[2].sources[0]
        return EvidenceIssue('unsupported', 'UnsupportedGeometryComparator',
                             'selected geometry comparator is not implemented',
                             SourceRef(reference.uri, reference.sha256, field='/geometry_capability/comparator'))
    return None


@dataclass(frozen=True)
class GeometryResult:
    status: Literal['success', 'error']
    value: BaseOccupancy | None
    issues: tuple[EvidenceIssue, ...]
    completed: tuple[EvidenceRecord, ...]
    input: GeometryInput
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if self.schema_version != VERSION or type(self.input) is not GeometryInput:
            raise ValueError('invalid geometry result schema/input')
        for name, cls in (('issues', EvidenceIssue), ('completed', EvidenceRecord)):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or any(type(value) is not cls for value in values):
                raise ValueError('invalid geometry result ' + name)
            object.__setattr__(self, name, tuple(values))
        if (canonical_bytes(tuple(evidence_value(e) for e in self.completed))
                != canonical_bytes(tuple(evidence_value(e) for e in self.input.parse.completed))):
            raise ValueError('geometry result must retain this input\'s completed parse facts')
        problem = _problem(self.input)
        if self.status == 'success':
            if type(self.value) is not BaseOccupancy or self.issues or problem is not None:
                raise ValueError('successful geometry result requires complete supported base occupancy')
            layout = self.value.layout
            actual = layout.gds, layout.drawn, layout.formats
            if any(canonical_bytes(evidence_value(a)) != canonical_bytes(evidence_value(b))
                   for a, b in zip(actual, _evidence(self.input))):
                raise ValueError('geometry draft is not bound to the captured input and selected policy owners')
        elif self.status == 'error':
            if self.value is not None or problem is None or self.issues != (problem,):
                raise ValueError('geometry error must match the located input failure, without successful state')
        else:
            raise ValueError('invalid geometry result discriminator')

    @property
    def layout(self) -> LayoutDraft | None:
        return None if self.value is None else self.value.layout

    @property
    def partition(self) -> BasePartition | None:
        return None if self.value is None else self.value.partition

    @property
    def body_evidence(self) -> EvidenceRecord:
        """Independent read-only scope, not copied into local drawn geometry."""
        return next(record for record in self.input.parse.completed if record.kind == 'body')


def build_geometry(input: GeometryInput) -> GeometryResult:
    if type(input) is not GeometryInput:
        raise ValueError('geometry builder requires a capture-validated GeometryInput')
    problem = _problem(input)
    if problem is not None:
        return GeometryResult('error', None, (problem,), input.parse.completed, input)
    layout = build_layout(*_evidence(input))
    occupancy = build_occupancy(build_partition(layout))
    return GeometryResult('success', occupancy, (), input.parse.completed, input)
