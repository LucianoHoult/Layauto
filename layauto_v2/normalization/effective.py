"""Capture-bound effective regions, a pure draft component after W008.

Success records only the selected Boolean/channel/terminal operations. It does
not establish device identity, physical connectivity or run completion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import evidence_value, mapping, source_value
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.regions import RegionProblem, validate_closed_graph
from layauto_v2.state.regions import EffectiveDraft, build_effective_draft
from .geometry import GeometryResult
from . import geometry_codec
from . import codec as semantic_codec
from layauto_v2.domain import publication_codec

_INPUT_TYPES = tuple(cast(type[object], spec[0]) for registry in
                     (geometry_codec._SPEC, semantic_codec._SPEC, publication_codec._SPEC)
                     for spec in registry.values())

VERSION = 'layauto-effective-geometry-result/1'


def _physical(input: GeometryResult) -> EvidenceRecord:
    tech = next(record for record in input.completed if record.kind == 'tech')
    payload = mapping(mapping(input.input.value['tech'])['physical'])
    return EvidenceRecord('physical', payload, (tech.sources[3],))


def _require_input(input: GeometryResult) -> None:
    if type(input) is not GeometryResult or input.status != 'success' or input.value is None:
        raise ValueError('effective geometry requires a successful captured GeometryResult')
    validate_closed_graph(input, _INPUT_TYPES)
    # W008's public DTOs retain their existing validation boundaries. Require
    # their complete receipt to have closed exact values at this new boundary.
    geometry_codec.encode_record(input)


@dataclass(frozen=True)
class EffectiveGeometryResult:
    status: Literal['success', 'error']
    value: EffectiveDraft | None
    issues: tuple[EvidenceIssue, ...]
    completed: tuple[EvidenceRecord, ...]
    input: GeometryResult
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported effective geometry result schema')
        if type(self.status) is not str:
            raise ValueError('effective geometry status requires exact text')
        _require_input(self.input)
        for name, cls in (('issues', EvidenceIssue), ('completed', EvidenceRecord)):
            values = getattr(self, name)
            if type(values) is not tuple and type(values) is not list:
                raise ValueError('invalid effective result ' + name)
            copied = tuple(values)
            if any(type(value) is not cls for value in copied):
                raise ValueError('invalid effective result ' + name)
            object.__setattr__(self, name, copied)
        for record in self.completed:
            validate_closed_graph(record, (EvidenceRecord, SourceRef))
            evidence_value(record)
        for issue in self.issues:
            validate_closed_graph(issue, (EvidenceIssue, SourceRef))
            if any(type(value) is not str for value in (issue.category, issue.code, issue.message)):
                raise ValueError('effective issues require exact text fields')
            source_value(issue.source)
        if self.completed != self.input.completed:
            raise ValueError('effective result must retain all completed captured facts')
        assert self.input.value is not None
        physical = _physical(self.input)
        if self.status == 'success':
            if type(self.value) is not EffectiveDraft or self.issues:
                raise ValueError('effective success requires a complete draft and no issues')
            if self.value.base != self.input.value or self.value.physical != physical:
                raise ValueError('effective draft differs from this captured W008 input/physical owner')
        elif self.status == 'error':
            if self.value is not None:
                raise ValueError('effective error cannot carry a successful draft')
            try:
                build_effective_draft(self.input.value, physical)
            except RegionProblem as exc:
                if self.issues != (exc.issue,):
                    raise ValueError('effective error differs from the located input problem') from exc
            else:
                raise ValueError('effective error requires a reproducible input problem')
        else:
            raise ValueError('invalid effective geometry result discriminator')

    @property
    def body_evidence(self) -> EvidenceRecord:
        return self.input.body_evidence


def build_effective_geometry(input: GeometryResult) -> EffectiveGeometryResult:
    _require_input(input)
    assert input.value is not None
    try:
        value = build_effective_draft(input.value, _physical(input))
    except RegionProblem as exc:
        return EffectiveGeometryResult('error', None, (exc.issue,), input.completed, input)
    return EffectiveGeometryResult('success', value, (), input.completed, input)
