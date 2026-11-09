"""Semantic-only component boundary: no IO or run/state publication."""
from __future__ import annotations

from dataclasses import replace

from layauto_v2.domain.intent import build_differences
from .contracts import NormalizationInput, NormalizationFacts, NormalizationResult
from .semantic import build_source, build_target
from .identity import NormalizationError, admit_source, join_identities


def normalize(input: NormalizationInput) -> NormalizationResult:
    if type(input) is not NormalizationInput:
        raise ValueError('normalize requires a validated NormalizationInput')
    source = build_source(input)
    target = build_target(input)
    facts = NormalizationFacts(source, target, build_differences(source, target))
    try:
        admit_source(input, source)
        devices, nets, device_seeds, net_seeds = join_identities(input, source)
        facts = replace(facts, device_identities=devices, net_identities=nets,
                        device_seeds=device_seeds, net_seeds=net_seeds)
        return NormalizationResult('success', facts, (), facts, input)
    except NormalizationError as exc:
        problem = exc
    # Reconstruction can fail unexpectedly. Keep it outside the handled input
    # error so the original exception's context/cause/suppression survive.
    if problem.progress is not None:
        facts = replace(facts, device_identities=tuple(problem.progress.devices), net_identities=tuple(problem.progress.nets),
                        device_seeds=tuple(problem.progress.device_seeds), net_seeds=tuple(problem.progress.net_seeds))
    return NormalizationResult('error', None, (problem.issue,), facts, input)
