"""Semantic-only component boundary: no IO or run/state publication."""
from __future__ import annotations

from dataclasses import replace

from layauto_v2.domain.intent import build_differences
from layauto_v2.domain.normalization import NormalizationInput, NormalizationFacts, NormalizationResult
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
        if exc.progress is not None:
            facts = replace(facts, device_identities=tuple(exc.progress.devices), net_identities=tuple(exc.progress.nets),
                            device_seeds=tuple(exc.progress.device_seeds), net_seeds=tuple(exc.progress.net_seeds))
        return NormalizationResult('error', None, (exc.issue,), facts, input)
