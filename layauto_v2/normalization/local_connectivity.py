"""Pure capture-bound local contact graph and independent local T05 audit.

A successful graph may carry enclosure violations. Neither outcome establishes
external body connectivity, complete mandatory checks, or a published run.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import evidence_value, mapping, source_value
from layauto_v2.domain.local_connectivity import ContactProblem, LOCAL_TYPES
from layauto_v2.domain.regions import validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain import publication_codec
from layauto_v2.state.local_connectivity import (
    DRAFT_TYPES, LocalConnectivityDraft, build_local_connectivity_draft,
)
from . import codec as semantic_codec
from . import effective_codec, geometry_codec
from .effective import EffectiveGeometryResult

VERSION = 'layauto-local-connectivity-result/1'
_INPUT_TYPES = tuple(cast(type[object], spec[0]) for registry in
                     (effective_codec._SPEC, geometry_codec._SPEC,
                      semantic_codec._SPEC, publication_codec._SPEC)
                     for spec in registry.values())


def _require_input(input: EffectiveGeometryResult) -> None:
    if type(input) is not EffectiveGeometryResult:
        raise ValueError('local connectivity requires a successful captured W009 result')
    # Inspect the original graph before encoding can copy a mutable/subclass
    # value. Decode then authenticates the full retained captured receipt.
    validate_closed_graph(input, _INPUT_TYPES)
    if input.status != 'success' or input.value is None:
        raise ValueError('local connectivity requires a successful captured W009 result')
    restored = effective_codec.decode_record(effective_codec.encode_record(input))
    if restored != input:
        raise ValueError('local connectivity input differs from its rebuilt captured receipt')


def _rules(input: EffectiveGeometryResult) -> EvidenceRecord:
    geometry_input = input.input.input
    tech = next(record for record in input.completed if record.kind == 'tech')
    payload = mapping(mapping(geometry_input.value['tech'])['rules'])
    # W008 authenticates this fixed role against the same captured tech bundle.
    return EvidenceRecord('rules', payload, (tech.sources[6],))


@dataclass(frozen=True)
class LocalConnectivityResult:
    status: Literal['success', 'error']
    value: LocalConnectivityDraft | None
    issues: tuple[EvidenceIssue, ...]
    completed: tuple[EvidenceRecord, ...]
    input: EffectiveGeometryResult
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported local connectivity result schema')
        if type(self.status) is not str:
            raise ValueError('local connectivity result requires exact status text')
        _require_input(self.input)
        for name, cls in (('issues', EvidenceIssue), ('completed', EvidenceRecord)):
            values = getattr(self, name)
            if type(values) is not tuple and type(values) is not list:
                raise ValueError('invalid local connectivity result ' + name)
            copied = tuple(values)
            if any(type(value) is not cls for value in copied):
                raise ValueError('invalid local connectivity result ' + name)
            object.__setattr__(self, name, copied)
        for record in self.completed:
            validate_closed_graph(record, (EvidenceRecord, SourceRef))
            evidence_value(record)
        for issue in self.issues:
            validate_closed_graph(issue, (EvidenceIssue, SourceRef))
            if any(type(value) is not str for value in (issue.category, issue.code, issue.message)):
                raise ValueError('local connectivity issues require exact text')
            source_value(issue.source)
        if self.completed != self.input.completed:
            raise ValueError('local result must retain all captured completed facts')
        assert self.input.value is not None
        if self.status == 'success':
            if type(self.value) is not LocalConnectivityDraft or self.issues:
                raise ValueError('local success requires a complete draft and no input issues')
            validate_closed_graph(self.value, DRAFT_TYPES + LOCAL_TYPES)
            expected = build_local_connectivity_draft(self.input.value, _rules(self.input))
            if self.value != expected:
                raise ValueError('local graph/audit differs from this captured input or rules owner')
        elif self.status == 'error':
            if self.value is not None:
                raise ValueError('local error cannot carry a successful draft')
            try:
                build_local_connectivity_draft(self.input.value, _rules(self.input))
            except ContactProblem as exc:
                if self.issues != (exc.issue,):
                    raise ValueError('local error differs from its located input problem') from exc
            else:
                raise ValueError('local error requires a reproducible input problem')
        else:
            raise ValueError('invalid local connectivity result discriminator')

    @property
    def body_evidence(self) -> EvidenceRecord:
        return self.input.body_evidence


def build_local_connectivity(input: EffectiveGeometryResult) -> LocalConnectivityResult:
    _require_input(input)
    assert input.value is not None
    try:
        value = build_local_connectivity_draft(input.value, _rules(input))
    except ContactProblem as exc:
        issues = (exc.issue,)
    else:
        return LocalConnectivityResult('success', value, (), input.completed, input)
    # Re-authentication can itself fail unexpectedly. Construct outside the
    # handled policy exception so Python cannot replace that failure's existing
    # __context__ with a ContactProblem from the preceding computation.
    return LocalConnectivityResult('error', None, issues, input.completed, input)
