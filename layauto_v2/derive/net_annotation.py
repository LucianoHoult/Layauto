"""Recomputable summaries; net association never modifies physical components."""
from __future__ import annotations

from layauto_v2.domain.net_annotation import (
    AnnotationBinding, AnnotationFragment, NetComponentSummary, TargetEvidence,
)


def summarize_components(binding: AnnotationBinding, targets: tuple[TargetEvidence, ...],
                         fragments: tuple[AnnotationFragment, ...]) -> tuple[NetComponentSummary, ...]:
    rows: list[NetComponentSummary] = []
    for component in binding.topology:
        selected = tuple(target for target in targets if target.component_ref == component.ref)
        refs = {target.ref for target in selected}
        covered = tuple(fragment for fragment in fragments if fragment.target_ref in refs and fragment.evidence_refs)
        nets = tuple(sorted({net for fragment in covered for net in fragment.net_ids}, key=lambda net: net.id))
        evidence = tuple(sorted({item for fragment in covered for item in fragment.evidence_refs}, key=lambda item: item.sha256))
        direct = tuple(sorted({fragment.target_ref for fragment in covered}, key=lambda item: item.sha256))
        status = 'unknown' if not nets else 'associated' if len(nets) == 1 else 'conflict'
        rows.append(NetComponentSummary(component.ref, component.members, tuple(sorted(refs, key=lambda item: item.sha256)),
                                        nets, evidence, direct, status))
    return tuple(rows)
