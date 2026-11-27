"""From actual input files to two published, traceable whole-cell T07 reports."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from layauto_v2.constraints import check_m1_spacing
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w023_cases import capture
from w024_cases import stage


def shape(witness):
    return {'record_id': witness.record_id, 'rect_dbu': witness.rect.bounds, **asdict(witness.source)}


def run(case):
    repo = PublicationRepository()
    with TemporaryDirectory() as tmp:
        root = stage(Path(tmp), case)
        ready, request = capture(repo, root, case, lineage=case, budget=400)
        sealed = publish_stage2(repo, request)
        del ready, request
    # The files and the original Stage 2 candidate are gone. Only refs survive.
    attempt = repo.load_attempt(case)
    before = repo.snapshot()
    start = perf_counter()
    ctx = open_constraint_context(repo, case, attempt.context_ref)
    opened = perf_counter()
    report = check_m1_spacing(ctx)
    checked = perf_counter()
    assert repo.snapshot() == before and sealed.head_ref == repo.load_head(case)
    assert attempt.phase == 'sealed_open'
    t07 = report.for_rule('T07.m1_spacing')
    assert len(t07.pairs) == 6 and sum(row.status == 'pending' for row in report.checks) == 9
    nearest = min(t07.pairs, key=lambda pair: pair.distance_squared_nm2)
    assert sorted([nearest.first.source.byte_offset, nearest.second.source.byte_offset]) == [2480, 2544]
    assert nearest.distance_nm == {'normal': 5, 'c14': 4}[case]
    assert t07.status == {'normal': 'pass', 'c14': 'violation'}[case]
    assert len(t07.violations) == (case == 'c14') and t07.threshold_nm == 5
    v = report.version
    return {
        'run': v.run_id, 'phase': attempt.phase, 'version': v.version, 'baseline_run': v.snapshot_ref.run_id,
        'context': v.context_ref.id, 'head': v.head_ref.id, 'snapshot': v.snapshot_ref.id,
        'checkpoint': v.checkpoint_ref.id, 'original_checkpoint': v.original_checkpoint_ref.id, 'tool': v.tool_ref.id,
        'context_seconds': round(opened - start, 6), 't07_seconds': round(checked - opened, 6),
        'rule_owner': asdict(report.catalog.source), 'owner_schema': report.catalog.schema_version,
        'mandatory_policy': report.catalog.mandatory_policy,
        'rules': [dict(c.rule.declaration, status=c.status, pointer=c.rule.source.field) for c in report.checks],
        'T07': {
            'status': t07.status, 'threshold_nm': t07.threshold_nm,
            'threshold_source': asdict(t07.rule.location('parameters/min_distance_nm')),
            'pair_count': len(t07.pairs), 'violation_count': len(t07.violations),
            'nearest': {'dx_dbu': nearest.dx_dbu, 'dy_dbu': nearest.dy_dbu, 'nm_per_dbu': nearest.nm_per_dbu,
                        'distance_squared_nm2': nearest.distance_squared_nm2, 'distance_nm': nearest.distance_nm,
                        'status': nearest.status, 'records': [shape(nearest.first), shape(nearest.second)]},
        },
    }


def json_value(value):
    if isinstance(value, FrozenMap):
        return dict(value)
    raise TypeError(type(value).__name__)


if __name__ == '__main__':
    print(json.dumps([run('normal'), run('c14')], indent=2, default=json_value))
