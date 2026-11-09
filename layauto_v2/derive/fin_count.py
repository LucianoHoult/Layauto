"""Read-only exact FIN/channel qualification, without record deduplication."""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import Literal

from layauto_v2.domain.channel_identity import ChannelMeasurement, ChannelRef, FinEvaluation, FinRelation
from layauto_v2.domain.geometry import DrawnRecord
from layauto_v2.domain.regions import ExactRegion
from layauto_v2.domain.results import EvidenceIssue


def evaluate_fins(channels: tuple[ExactRegion, ...], drawn: tuple[DrawnRecord, ...],
                  tick_nm: int, binding_ref: ChannelRef
                  ) -> tuple[tuple[ChannelMeasurement, ...], tuple[FinRelation, ...], tuple[EvidenceIssue, ...]]:
    """Retain every channel × FIN decision and all duplicate/overlap relations."""
    if type(tick_nm) is not int or tick_nm <= 0:
        raise ValueError('FIN measurement requires exact positive canonical DBU')
    by_id = {record.id: record for record in drawn}
    fins = tuple(sorted((record for record in drawn if record.layer == 'FIN'), key=lambda record: record.id.sha256))
    relations: list[FinRelation] = []
    for index, left in enumerate(fins):
        for right in fins[index + 1:]:
            intersection = left.rect.intersection(right.rect)
            if intersection is None:
                continue
            affected = tuple(sorted((channel.ref for channel in channels
                                      if any(piece.intersection(record.rect) is not None
                                             for piece in channel.rectangles for record in (left, right))),
                                     key=lambda ref: ref.sha256))
            relation_kind: Literal['duplicate', 'overlap'] = 'duplicate' if left.rect == right.rect else 'overlap'
            relations.append(FinRelation(left.id, right.id, relation_kind, intersection, affected, binding_ref))
    measurements: list[ChannelMeasurement] = []
    issues: list[EvidenceIssue] = []
    for channel in channels:
        if channel.role != 'channel' or len(channel.rectangles) != 1 or channel.owner_id not in by_id:
            raise ValueError('FIN count requires one recognized channel and its real active')
        active = by_id[channel.owner_id]
        if active.layer != 'OD':
            raise ValueError('channel owner is not active geometry')
        box = channel.rectangles[0]
        evaluations: list[FinEvaluation] = []
        for fin in fins:
            crossing = box.intersection(fin.rect)
            status: Literal['outside', 'touch', 'qualified', 'partial']
            if crossing is None:
                width = min(box.x1, fin.rect.x1) - max(box.x0, fin.rect.x0)
                height = min(box.y1, fin.rect.y1) - max(box.y0, fin.rect.y0)
                status = 'touch' if width >= 0 and height >= 0 else 'outside'
            elif (fin.rect.x0 <= box.x0 and box.x1 <= fin.rect.x1
                  and active.rect.y0 <= fin.rect.y0 and fin.rect.y1 <= active.rect.y1):
                status = 'qualified'
            else:
                status = 'partial'
                issues.append(EvidenceIssue('unsupported', 'PartialFinCrossing',
                              'positive-area FIN does not span channel X and lie wholly within active Y',
                              replace(fin.source, field='/fin_channel_qualification')))
            evaluations.append(FinEvaluation(fin.id, channel.ref, status, crossing,
                    Fraction((fin.rect.y1 - fin.rect.y0) * tick_nm), fin.source, binding_ref))
        unresolved = tuple(relation.ref for relation in relations if channel.ref in relation.channel_refs)
        for relation in relations:
            if channel.ref in relation.channel_refs:
                issues.append(EvidenceIssue('unsupported', 'UnprovenIndependentFins',
                              'duplicate/overlapping FIN records have no proven independent physical count: '
                              + relation.left_id.sha256 + ',' + relation.right_id.sha256,
                              replace(by_id[relation.left_id].source, field='/independent_fin_records')))
        count = None if unresolved or any(item.status == 'partial' for item in evaluations) else sum(item.status == 'qualified' for item in evaluations)
        measurements.append(ChannelMeasurement(channel.ref, active.id, Fraction((box.x1 - box.x0) * tick_nm),
                            tuple(evaluations), count, unresolved, binding_ref))
    return tuple(measurements), tuple(relations), tuple(issues)
