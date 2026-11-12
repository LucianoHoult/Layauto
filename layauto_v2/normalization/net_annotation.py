"""Same-capture local net overlay; no IO, publication, or topology mutation.

The public result derives all output fields from its authenticated W010 input.
Coverage gaps remain explicit facts, not complete run or extraction assurance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.domain.geometry import mapping
from layauto_v2.domain.net_annotation import AnnotationProblem, NetEvidence
from layauto_v2.domain.publication import ContentRef
from layauto_v2.domain.publication_codec import content_ref
from layauto_v2.domain.regions import validate_closed_graph
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.annotation.net_regions import build_net_annotation_draft
from layauto_v2.state.annotation import AnnotationDraft
from . import codec as semantic_codec
from . import local_connectivity_codec
from .component import normalize
from .contracts import NormalizationInput
from .local_connectivity import LocalConnectivityResult

VERSION = 'layauto-net-annotation-result/1'


def _require_input(input: LocalConnectivityResult) -> None:
    if type(input) is not LocalConnectivityResult:
        raise ValueError('net annotation requires a successful captured W010 result')
    validate_closed_graph(input, local_connectivity_codec._ALL_TYPES)
    if input.status != 'success' or input.value is None:
        raise ValueError('net annotation requires a successful captured W010 result')
    restored = local_connectivity_codec.decode_record(local_connectivity_codec.encode_record(input))
    if restored != input:
        raise ValueError('net annotation input differs from its rebuilt captured receipt')


def _ref_value(reference: ContentRef) -> FrozenMap:
    return FrozenMap({'kind': reference.kind, 'run_id': reference.run_id, 'digest': reference.digest})


def _capture_binding(input: NormalizationInput) -> FrozenMap:
    readback = input.readback
    run = None if readback is None else FrozenMap({
        'run_id': readback.ready.run_id,
        'request_digest': content_ref(readback.ready.attempt.request).digest,
        'attempt_digest': content_ref(readback.ready.attempt).digest,
        'checkpoint_ref': _ref_value(readback.ready.checkpoint_ref),
        'parse_ref': _ref_value(readback.ready.parse_ref),
        'tool_ref': _ref_value(readback.ready.tool_ref),
    })
    return FrozenMap({
        'schema': 'layauto-net-capture-binding/1',
        'normalization_input_sha256': semantic_codec.record_digest(input),
        'sources': tuple(FrozenMap({'uri': source.uri, 'sha256': source.sha256})
                         for source in input.parse.sources),
        'readback': run,
    })


def _evaluate(input: LocalConnectivityResult) -> tuple[AnnotationDraft | None, tuple[EvidenceIssue, ...], bool]:
    geometry_input = input.input.input.input
    semantic = normalize(geometry_input.semantic_input)
    if semantic.status == 'error':
        return None, tuple(EvidenceIssue('binding' if issue.category == 'identity' else issue.category,
                                         issue.code, issue.message, issue.source)
                           for issue in semantic.issues), True
    assert input.value is not None and semantic.value is not None
    facts = semantic.value
    identities = {identity.query_key: identity for identity in facts.net_identities}
    evidence = tuple(NetEvidence(seed.semantic_id, seed.query_key, seed.record,
                                 identities[seed.query_key].provenance)
                     for seed in facts.net_seeds)
    tech = next(record for record in input.completed if record.kind == 'tech')
    derived = EvidenceRecord('derived', mapping(mapping(geometry_input.value['tech'])['derived']),
                             (tech.sources[2],))
    try:
        draft = build_net_annotation_draft(input.value, facts.source, evidence, derived,
                                           _capture_binding(geometry_input.semantic_input))
    except AnnotationProblem as exc:
        issues = (exc.issue,)
    else:
        return draft, tuple(row.issue for row in draft.issues), any(row.severity == 'error' for row in draft.issues)
    # The expected failure handler has unwound before callers freeze any result.
    # Unexpected exceptions keep their original object, context and suppression.
    return None, issues, True


@dataclass(frozen=True)
class NetAnnotationResult:
    input: LocalConnectivityResult
    schema_version: str = VERSION
    status: Literal['success', 'error'] = field(init=False)
    value: AnnotationDraft | None = field(init=False)
    issues: tuple[EvidenceIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not str or self.schema_version != VERSION:
            raise ValueError('unsupported net annotation result schema')
        _require_input(self.input)
        draft, issues, failed = _evaluate(self.input)
        object.__setattr__(self, 'value', draft)
        object.__setattr__(self, 'issues', issues)
        object.__setattr__(self, 'status', 'error' if failed else 'success')

    @property
    def completed(self) -> tuple[EvidenceRecord, ...]:
        return self.input.completed

    @property
    def body_evidence(self) -> EvidenceRecord:
        return self.input.body_evidence


def build_net_annotation(input: LocalConnectivityResult) -> NetAnnotationResult:
    return NetAnnotationResult(input)
