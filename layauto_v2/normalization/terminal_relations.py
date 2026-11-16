"""Same-capture ordered terminals and separate read-only body relations.

One unchanged W010 receipt owns the captured input. W011/W013 neutral builders
share its geometry and semantic facts. No state or run is published here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast

from layauto_v2.domain.channel_identity import ChannelProblem, ChannelSeed
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import mapping
from layauto_v2.domain.net_annotation import AnnotationProblem, NetEvidence
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.domain.terminal_relations import TerminalProblem, validate_terminal_graph
from layauto_v2.derive.body_relations import BodyProblem
from layauto_v2.derive.terminal_relations import (
    DRAFT_TYPES, TerminalRelationsDraft, build_terminal_relations_draft,
)
from . import codec as semantic_codec
from . import local_connectivity_codec
from .component import normalize
from .contracts import NormalizationFacts
from .local_connectivity import LocalConnectivityResult
from .net_annotation import _capture_binding

VERSION = 'layauto-terminal-relations-result/1'


def _types() -> tuple[type[object], ...]:
    return (DRAFT_TYPES + local_connectivity_codec._ALL_TYPES
            + tuple(cast(type[object], entry[0]) for entry in semantic_codec._SPEC.values())
            + (TerminalRelationsResult,))


def _require_input(input: LocalConnectivityResult) -> None:
    if type(input) is not LocalConnectivityResult:
        raise ValueError('terminal relations require a successful captured W010 result')
    # Check retained storage before an older codec could copy a forged map.
    validate_terminal_graph(input, local_connectivity_codec._ALL_TYPES)
    if input.status != 'success' or input.value is None:
        raise ValueError('terminal relations require a successful captured W010 result')
    rebuilt = local_connectivity_codec.decode_record(local_connectivity_codec.encode_record(input))
    if rebuilt != input:
        raise ValueError('terminal input differs from complete captured reconstruction')


def _evaluate(input: LocalConnectivityResult) -> tuple[
        NormalizationFacts, TerminalRelationsDraft | None, tuple[EvidenceIssue, ...]]:
    geometry = input.input.input.input
    semantic = normalize(geometry.semantic_input)
    if semantic.status == 'error':
        return semantic.completed, None, tuple(
            EvidenceIssue('binding' if issue.category == 'identity' else issue.category,
                          issue.code, issue.message, issue.source) for issue in semantic.issues)
    facts = semantic.completed
    devices = {identity.device_id: identity for identity in facts.device_identities}
    nets = {identity.query_key: identity for identity in facts.net_identities}
    channel_seeds = tuple(ChannelSeed(seed.semantic_id, seed.query_key, seed.record,
                                     devices[seed.semantic_id].provenance)
                          for seed in facts.device_seeds)
    net_evidence = tuple(NetEvidence(seed.semantic_id, seed.query_key, seed.record,
                                    nets[seed.query_key].provenance) for seed in facts.net_seeds)
    tech = next(record for record in input.completed if record.kind == 'tech')
    derived = EvidenceRecord('derived', mapping(mapping(geometry.value['tech'])['derived']),
                             (tech.sources[2],))
    assert input.value is not None
    try:
        draft = build_terminal_relations_draft(input.value, facts.source, channel_seeds,
                    net_evidence, derived, input.body_evidence,
                    _capture_binding(geometry.semantic_input))
    except (ChannelProblem, AnnotationProblem, BodyProblem, TerminalProblem) as exc:
        issues = (exc.issue,)
    else:
        return facts, draft, draft.issues
    # Expected input handlers must unwind before another constructor executes.
    # Unexpected errors and process interrupts retain their original history.
    return facts, None, issues


@dataclass(frozen=True)
class TerminalRelationsResult:
    input: LocalConnectivityResult
    schema_version: str = VERSION
    status: Literal['success', 'error'] = field(init=False)
    semantic_facts: NormalizationFacts = field(init=False)
    value: TerminalRelationsDraft | None = field(init=False)
    issues: tuple[EvidenceIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported terminal relations result schema')
        _require_input(self.input)
        facts, draft, issues = _evaluate(self.input)
        object.__setattr__(self, 'semantic_facts', facts)
        object.__setattr__(self, 'value', draft)
        object.__setattr__(self, 'issues', issues)
        object.__setattr__(self, 'status', 'error' if issues else 'success')

    @property
    def completed(self) -> tuple[EvidenceRecord, ...]:
        return self.input.completed

    @property
    def body_evidence(self) -> EvidenceRecord:
        return self.input.body_evidence


def build_terminal_relations(input: LocalConnectivityResult) -> TerminalRelationsResult:
    return TerminalRelationsResult(input)
