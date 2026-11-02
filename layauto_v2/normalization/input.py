"""Adapters for already captured W005 and caller-read W006 immutable facts."""
from __future__ import annotations

from layauto_v2.domain.results import ParseResult
from layauto_v2.domain.publication import InputsReady, InputCheckpoint, ParseAudit, ToolRunResult, EvidenceAudit
from .contracts import NormalizationInput, ReadbackBinding


def from_parse_result(result: ParseResult) -> NormalizationInput:
    return NormalizationInput(result)


def from_inputs_ready(ready: InputsReady, checkpoint: InputCheckpoint, parse_audit: ParseAudit,
                      tool_run: ToolRunResult, evidence_audits: tuple[EvidenceAudit, ...]) -> NormalizationInput:
    binding = ReadbackBinding(ready, checkpoint, parse_audit, tool_run, evidence_audits)
    return NormalizationInput(parse_audit.result, binding)
