"""Same-capture channel identity and exact FIN measurements, without IO.

A source parameter mismatch is a measured fact, not a component failure. An
error may retain a complete diagnostic draft whose affected counts are unknown.
Neither outcome establishes complete extraction or publication assurance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from layauto_v2.domain.channel_identity import CHANNEL_TYPES, ChannelProblem, ChannelSeed
from layauto_v2.domain.evidence import EvidenceRecord, SourceRef
from layauto_v2.domain.geometry import evidence_value, mapping, source_value
from layauto_v2.domain.local_connectivity import record_tuple
from layauto_v2.domain.regions import validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.derive.channel_identity import (
    DRAFT_TYPES, ChannelIdentityDraft, build_channel_identity_draft,
)
from . import local_connectivity_codec
from .component import normalize
from .contracts import NormalizationResult
from .local_connectivity import LocalConnectivityResult

VERSION = 'layauto-channel-identity-result/1'


def _require_input(input: LocalConnectivityResult) -> None:
    if type(input) is not LocalConnectivityResult:
        raise ValueError('channel identity requires a successful captured W010 result')
    validate_closed_graph(input, local_connectivity_codec._ALL_TYPES)
    if input.status != 'success' or input.value is None:
        raise ValueError('channel identity requires a successful captured W010 result')
    restored = local_connectivity_codec.decode_record(local_connectivity_codec.encode_record(input))
    if restored != input:
        raise ValueError('channel input differs from its rebuilt captured receipt')


def _derived(input: LocalConnectivityResult) -> EvidenceRecord:
    geometry_input = input.input.input.input
    tech = next(record for record in input.completed if record.kind == 'tech')
    # W008 authenticates both payload and the fixed captured derived owner role.
    return EvidenceRecord('derived', mapping(mapping(geometry_input.value['tech'])['derived']),
                          (tech.sources[2],))


def _evaluate(input: LocalConnectivityResult) -> tuple[
        NormalizationResult, ChannelIdentityDraft | None, tuple[EvidenceIssue, ...]]:
    semantic = normalize(input.input.input.input.semantic_input)
    if semantic.status == 'error':
        # The original W007 issue is retained unchanged in semantic. Its identity
        # category maps to the neutral evidence binding category here.
        return semantic, None, tuple(EvidenceIssue('binding' if issue.category == 'identity' else issue.category,
                                                  issue.code, issue.message, issue.source)
                                     for issue in semantic.issues)
    assert input.value is not None and semantic.value is not None
    facts = semantic.value
    identities = {identity.device_id: identity for identity in facts.device_identities}
    seeds = tuple(ChannelSeed(seed.semantic_id, seed.query_key, seed.record,
                              identities[seed.semantic_id].provenance)
                  for seed in facts.device_seeds)
    try:
        draft = build_channel_identity_draft(input.value, facts.source, seeds, _derived(input))
    except ChannelProblem as exc:
        issues = (exc.issue,)
    else:
        return semantic, draft, draft.issues
    # Callers construct/re-authenticate after this handler has unwound. Unexpected
    # failures retain their original context, cause and suppression flag.
    return semantic, None, issues


@dataclass(frozen=True)
class ChannelIdentityResult:
    status: Literal['success', 'error']
    value: ChannelIdentityDraft | None
    issues: tuple[EvidenceIssue, ...]
    completed: tuple[EvidenceRecord, ...]
    input: LocalConnectivityResult
    semantic: NormalizationResult
    schema_version: str = VERSION

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported channel identity result schema')
        if type(self.status) is not str or self.status not in ('success', 'error'):
            raise ValueError('invalid channel identity status')
        _require_input(self.input)
        object.__setattr__(self, 'issues', record_tuple(self.issues, EvidenceIssue, 'channel issues'))
        object.__setattr__(self, 'completed', record_tuple(self.completed, EvidenceRecord, 'channel completed'))
        for record in self.completed:
            validate_closed_graph(record, (EvidenceRecord, SourceRef))
            evidence_value(record)
        for issue in self.issues:
            validate_closed_graph(issue, (EvidenceIssue, SourceRef))
            if any(type(text) is not str for text in (issue.category, issue.code, issue.message)):
                raise ValueError('channel issues require exact text')
            source_value(issue.source)
        if self.completed != self.input.completed:
            raise ValueError('channel result must retain all captured completed facts')
        if type(self.semantic) is not NormalizationResult:
            raise ValueError('channel result requires its same-capture semantic result')
        validate_closed_graph(self.semantic, local_connectivity_codec._ALL_TYPES)
        if self.value is not None:
            if type(self.value) is not ChannelIdentityDraft:
                raise ValueError('channel result requires a typed draft')
            validate_closed_graph(self.value, DRAFT_TYPES + CHANNEL_TYPES)
        semantic, draft, issues = _evaluate(self.input)
        status = 'error' if issues else 'success'
        if (self.semantic != semantic or self.value != draft or self.issues != issues
                or self.status != status):
            raise ValueError('channel result differs from complete same-capture reconstruction')

    @property
    def body_evidence(self) -> EvidenceRecord:
        return self.input.body_evidence


def build_channel_identity(input: LocalConnectivityResult) -> ChannelIdentityResult:
    _require_input(input)
    semantic, draft, issues = _evaluate(input)
    return ChannelIdentityResult('error' if issues else 'success', draft, issues,
                                 input.completed, input, semantic)
