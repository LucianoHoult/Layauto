"""Preserve each A2 sample and medians; no performance acceptance threshold."""
from __future__ import annotations

import argparse
from pathlib import Path
import statistics

from common import CASES, dump_new, read_json, sha


def failed_commands(directories):
    """Aggregate failed actual commands across retained attempts without duplicate paths."""
    failures = []
    paths = {path.resolve() for directory in directories for path in directory.glob('*.command.json')}
    for path in sorted(paths):
        row = read_json(path)
        if row['exit_code'] != 0:
            failures.append({'path': str(path), **row})
    return failures


def summarize(args):
    data = {}
    failure_directories = sorted({args.samples.resolve(), *(path.resolve() for path in args.failure_samples)})
    failures = failed_commands(failure_directories)
    for case in CASES:
        per_side = {}
        for side in ('before', 'after'):
            rows = []
            for rep in args.reps:
                prefix = args.samples / f'{side}-{case}-r{rep}'
                command = read_json(prefix.with_suffix('.command.json'))
                assert command['exit_code'] == 0
                sample = read_json(prefix.with_suffix('.json'))
                comparison = read_json(prefix.with_suffix('.comparison.json'))
                assert comparison['equal'] and comparison['bytes'] == sample['wire_bytes']
                stages = sample['wall_seconds']
                total = sum(stages.values())
                build = total - stages['W011_result_encode'] - stages['W011_result_decode']
                rows.append({'rep': rep, 'sample': str(prefix.with_suffix('.json')),
                             'sample_sha256': sha(prefix.with_suffix('.json').read_bytes()),
                             'stages': stages, 'all_build_seconds': build,
                             'W011_build_seconds': stages['W011_build'],
                             'encode_seconds': stages['W011_result_encode'],
                             'decode_seconds': stages['W011_result_decode'], 'total_seconds': total,
                             'peak_rss_kib': sample['process_peak_rss_kib'],
                             'wire_bytes': sample['wire_bytes'], 'wire_sha256': sample['wire_sha256']})
            per_side[side] = rows
        medians = {side: {key: statistics.median(row[key] for row in rows)
                          for key in ('all_build_seconds', 'W011_build_seconds', 'encode_seconds',
                                      'decode_seconds', 'total_seconds', 'peak_rss_kib')}
                   for side, rows in per_side.items()}
        changes = {key: {'before': medians['before'][key], 'after': medians['after'][key],
                         'after_minus_before': medians['after'][key] - medians['before'][key],
                         'improvement_percent': (1 - medians['after'][key] / medians['before'][key]) * 100}
                   for key in medians['before']}
        stage_changes = {}
        for stage in per_side['before'][0]['stages']:
            before = statistics.median(row['stages'][stage] for row in per_side['before'])
            after = statistics.median(row['stages'][stage] for row in per_side['after'])
            stage_changes[stage] = {'before': before, 'after': after, 'after_minus_before': after - before,
                                    'improvement_percent': (1 - after / before) * 100}
        all_rows = per_side['before'] + per_side['after']
        assert len({row['wire_bytes'] for row in all_rows}) == 1
        assert len({row['wire_sha256'] for row in all_rows}) == 1
        data[case] = {'each_actual_sample': per_side, 'medians_and_changes': changes,
                      'each_stage_median_and_changes': stage_changes,
                      'wire_bytes': all_rows[0]['wire_bytes'], 'wire_sha256': all_rows[0]['wire_sha256'],
                      'wire_reduction_percent': 0}
    result = {'schema': 'w012-a2-implementation-performance-summary/1', 'reps': args.reps,
              'samples_per_side_per_path': len(args.reps), 'all_observed_failed_commands': failures,
              'scanned_failure_directories': [str(path) for path in failure_directories],
              'paths': data, 'median_rule': 'sum actual stages for each run first, then median runs',
              'scope': 'Uninstrumented complete public pipeline stages only; no product acceptance decision.'}
    dump_new(args.output, result)
    for case, row in data.items():
        print(case, {key: round(value['improvement_percent'], 3)
                     for key, value in row['medians_and_changes'].items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=Path, required=True)
    parser.add_argument('--reps', nargs='+', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--failure-samples', nargs='+', type=Path, default=())
    summarize(parser.parse_args())
