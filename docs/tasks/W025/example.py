"""Publish three temporary cells and query each through the combined spacing API.

From the repository root:
    PYTHONPATH=.:tests/contracts python -B docs/tasks/W025/example.py
"""
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from layauto_v2.constraints import check_spacing
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w023_cases import capture
from w025_cases import stage_spacing


def witness(shape, records):
    owner = {
        'record_id': shape.record_id, 'rect_dbu': records[shape.record_id]['rect'],
        'source': asdict(shape.source),
    }
    if shape.region_id is None:
        return owner
    return {
        'region_id': shape.region_id, 'piece_id': shape.piece_id, 'piece_rect_dbu': shape.rect.bounds,
        'drawn_li': owner,
        'cuts': [{'record_id': cut.record_id, 'rect_dbu': cut.rect.bounds, 'source': asdict(cut.source)}
                 for cut in shape.cuts],
    }


def summarize(check, records):
    nearest = min(check.pairs, key=lambda pair: pair.distance_squared_nm2)
    return {
        'status': check.status, 'threshold_nm': check.threshold_nm,
        'threshold_source': asdict(check.rule.location('parameters/min_distance_nm')),
        'predicate': check.rule.declaration['predicate'], 'unit': check.rule.declaration['unit'],
        'pair_count': len(check.pairs), 'violation_count': len(check.violations),
        'nearest': {
            'distance_nm': nearest.distance_nm, 'distance_squared_nm2': nearest.distance_squared_nm2,
            'dx_dbu': nearest.dx_dbu, 'dy_dbu': nearest.dy_dbu, 'nm_per_dbu': nearest.nm_per_dbu,
            'same_layer_contact': nearest.same_layer_contact, 'status': nearest.status,
            'first': witness(nearest.first, records), 'second': witness(nearest.second, records),
        },
    }


def run(gap_nm, threshold_nm):
    run_id = f'cut-{gap_nm}-threshold-{threshold_nm}'
    repo = PublicationRepository()
    with TemporaryDirectory() as tmp:
        root = stage_spacing(Path(tmp), gap_nm, threshold_nm)
        ready, request = capture(repo, root, run_id, lineage=run_id, budget=400)
        publish_stage2(repo, request)
        del ready, request

    attempt = repo.load_attempt(run_id)
    before = repo.snapshot()
    start = perf_counter()
    ctx = open_constraint_context(repo, run_id, attempt.context_ref)
    opened = perf_counter()
    report = check_spacing(ctx)
    checked = perf_counter()
    assert repo.load_attempt(run_id) == attempt and attempt.phase == 'sealed_open'
    assert repo.snapshot() == before

    records = ctx.snapshot.state['geometry']['records']
    li = summarize(report.for_rule('T06.li_spacing'), records)
    metal = summarize(report.for_rule('T07.m1_spacing'), records)
    assert li['pair_count'] == 10 and li['violation_count'] == int(gap_nm < threshold_nm)
    assert li['threshold_nm'] == threshold_nm and li['nearest']['distance_nm'] == gap_nm
    assert li['status'] == ('violation' if gap_nm < threshold_nm else 'pass')
    assert metal['status'] == 'pass' and metal['nearest']['distance_nm'] == 5
    return {
        'run': run_id, 'version': report.version.version, 'snapshot': report.version.snapshot_ref.id,
        'context': report.version.context_ref.id, 'attempt_phase': attempt.phase,
        'open_seconds': round(opened - start, 6), 'check_spacing_seconds': round(checked - opened, 6),
        'rule_statuses': {item.rule.id: item.status for item in report.checks},
        'T06': li, 'T07': metal,
    }


if __name__ == '__main__':
    print(json.dumps([run(gap, threshold) for gap, threshold in ((2, 2), (1, 2), (2, 3))], indent=2))
