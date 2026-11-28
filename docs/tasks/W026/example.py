"""Publish real W026 inputs once each. Print all rule decisions and representative witnesses.

From the repository root:
    PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/example.py

Use --all-witnesses to print every observation and spacing pair.
"""
import argparse
import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from layauto_v2.constraints import check_rules
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w023_cases import capture


def inspect_published(root: Path, run_id: str):
    repo = PublicationRepository()
    start = perf_counter()
    ready, request = capture(repo, root, run_id, lineage=run_id, budget=400)
    captured = perf_counter()
    sealed = publish_stage2(repo, request)
    published = perf_counter()
    del ready, request

    attempt = repo.load_attempt(run_id)
    before = repo.snapshot()
    head_ref = repo.load_head(run_id)
    assert head_ref == sealed.head_ref
    snapshot_ref = repo.read(head_ref).snapshot_ref
    snapshot = repo.read(snapshot_ref)
    opening = perf_counter()
    ctx = open_constraint_context(repo, run_id, attempt.context_ref)
    opened = perf_counter()
    report = check_rules(ctx)
    checked = perf_counter()

    assert report.version == ctx.version and report.catalog == ctx.catalog
    assert report.version.run_id == run_id and report.version.version == 0
    assert report.version.snapshot_ref == snapshot_ref and report.version.head_ref == head_ref
    assert report.version.context_ref == attempt.context_ref
    assert repo.read(snapshot_ref) == snapshot == ctx.snapshot
    assert repo.load_head(run_id) == head_ref and repo.load_attempt(run_id) == attempt
    assert repo.snapshot() == before and attempt.phase == 'sealed_open'

    timings = {'capture_s': captured - start, 'publish_s': published - captured,
               'open_s': opened - opening, 'check_s': checked - opened}
    return ctx, report, {k: round(v, 6) for k, v in timings.items()}


def json_value(value):
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return {f.name: getattr(value, f.name) for f in fields(value)}
    if isinstance(value, Fraction):
        return value.numerator if value.denominator == 1 else str(value)
    raise TypeError(type(value).__name__)


def rule_summary(check, all_witnesses):
    row = {'rule': check.rule.id, 'status': check.status, 'declaration': check.rule.source}
    if check.issue:
        row['issue'] = check.issue
    if check.pairs:
        pairs = check.pairs if all_witnesses else check.violations or (
            min(check.pairs, key=lambda pair: pair.distance_squared_nm2),)
        row['pair_count'] = len(check.pairs)
        row['witnesses'] = [{'squared_distance_nm2': pair.distance_squared_nm2, 'pair': pair}
                            for pair in pairs]
    else:
        observations = check.observations
        row['observation_count'] = len(observations)
        row['witnesses'] = observations if all_witnesses else (
            tuple(o for o in observations if o.status == 'violation') or observations[:1])
    return row


def main():
    from w026_cases import stage_rules

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-witnesses', action='store_true')
    parser.add_argument('cases', nargs='*', default=['normal', 'combined'],
                        help='normal, via_enclosure, external_equality, c14, combined or cut_gap')
    args = parser.parse_args()
    for case in args.cases:
        with TemporaryDirectory() as directory:
            root = stage_rules(Path(directory), case)
            _, report, timings = inspect_published(root, case)
        result = {
            'sample': case, 'version': report.version, 'seconds': timings,
            'rules': [rule_summary(check, args.all_witnesses) for check in report.checks],
        }
        print(json.dumps(result, default=json_value, ensure_ascii=False))


if __name__ == '__main__':
    main()
