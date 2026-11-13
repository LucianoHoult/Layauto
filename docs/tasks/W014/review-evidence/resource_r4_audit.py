"""Independent read-only audit of the final original resource sample selection.

No product imports, capture, codec, tests or benchmark calls.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNER = Path('docs/tasks/W014/resource-adoption-r4')
CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')
W014 = {'derive/body_relations.py', 'derive/terminal_relations.py',
        'domain/terminal_relations.py', 'normalization/terminal_relations.py',
        'normalization/terminal_relations_codec.py'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return (ROOT / path).read_bytes()


def load(path):
    return json.loads(read(path))


def identity(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def main():
    checks = []

    def check(ok, label):
        assert ok, label
        checks.append(label)

    def referenced(receipt):
        data = read(receipt['path'])
        check(sha(data) == receipt['sha256'] and len(data) == receipt['bytes'],
              'original receipt ' + receipt['path'])
        return json.loads(data) if receipt['path'].endswith('.json') else data

    for base in (OWNER, OWNER / 'suite-identity-audit'):
        for name, want in load(base / 'manifest.json').items():
            check(sha(read(base / name)) == want, 'owner manifest ' + str(base / name))
    selection = load(OWNER / 'final-selection.json')
    adoption = load(OWNER / 'suite-identity-audit/adoption.json')
    check(selection['current_source_id'] == adoption['current_source_id'], 'same current identity owners')
    check(selection['reference_source_id'] == adoption['reference_source_id'], 'same reference identity owners')
    check(tuple(selection['cases']) == CASES, 'all three fixed cases')
    for owner in (selection, adoption):
        for name, want in owner['evidence_files'].items():
            data = read(name)
            check(sha(data) == want['sha256'] and len(data) == want['bytes'], 'retained evidence ' + name)
    old_files = None
    new_files = None
    comparisons = {}
    selected_reports = {}
    for case in CASES:
        sample = selection['selected_samples'][case]
        now = referenced(sample['report'])
        command = referenced(sample['command'])
        stdout = referenced(sample['stdout'])
        stderr = referenced(sample['stderr'])
        old = referenced(sample['baseline_report'])
        old_command = referenced(sample['baseline_command'])
        selected_reports[case] = now
        for component, report, cmd, expected in (
                ('w013', old, old_command, selection['reference_source_id']),
                ('w014', now, command, selection['current_source_id'])):
            check(report['source_id'] == identity(report['files']) == expected,
                  'complete source identity ' + component + ':' + case)
            check(report['component'] == component and report['case'] == case,
                  'actual route ' + component + ':' + case)
            check(cmd['returncode'] == 0 and report['public_roundtrip_equal'] is True,
                  'successful public command ' + component + ':' + case)
            check(report['authentication_calls_by_phase'] == {
                component.upper() + '_build': 1, component.upper() + '_encode': 1,
                component.upper() + '_decode': 2}, 'complete authentication counts ' + component + ':' + case)
            probe_path = Path('docs/tasks/W014/resources-early' if component == 'w013'
                              else 'docs/tasks/W014/resources-r4') / 'resource_probe.py'
            check(report['probe_sha256'] == sha(read(probe_path)),
                  'actual archived probe hash ' + component + ':' + case)
        old_files = old_files or old['files']
        new_files = new_files or now['files']
        check(old['files'] == old_files and now['files'] == new_files, 'same full manifest each route ' + case)
        if case == 'normal-direct':
            check(command['source_id_before'] == command['source_id_after'] == now['source_id']
                  and command['source_unchanged'] is True and command['files'] == now['files'],
                  'clean direct wrapper preserves exact source')
            check(sha(stdout) == command['logs']['stdout']['sha256']
                  and sha(stderr) == command['logs']['stderr']['sha256'], 'clean direct original logs')
        else:
            check(sha(stdout) == command['stdout_sha256'] and sha(stderr) == command['stderr_sha256'],
                  'original selected logs ' + case)
        old_base = Path(sample['baseline_report']['path']).parent
        check(sha(read(old_base / ('w013-' + case + '.stdout.txt'))) == old_command['stdout_sha256']
              and sha(read(old_base / ('w013-' + case + '.stderr.txt'))) == old_command['stderr_sha256'],
              'original baseline logs ' + case)
        for name in ('python', 'executable', 'platform', 'distributions', 'input_site',
                     'capture_sources', 'retained_W010_wire_bytes', 'retained_W010_wire_sha256', 'local_counts'):
            check(old[name] == now[name], 'same source and environment ' + case + ':' + name)
        expected_env = dict(old_command['environment_overrides'])
        actual_env = dict(command['environment_overrides'])
        if case == 'normal-direct':
            check(actual_env.pop('MYPY_CACHE_DIR', None) == '/workspace/work/w014-mypy-development',
                  'clean direct explicit inert mypy cache override')
            check('mypy' not in command['argv'], 'clean resource command is not mypy')
        check(actual_env == expected_env, 'all relevant explicit overrides match ' + case)
        before_seconds = sum(row['seconds'] for name, row in old['phases'].items() if name.startswith('W013'))
        after_seconds = sum(row['seconds'] for name, row in now['phases'].items() if name.startswith('W014'))
        comparison = selection['comparison'][case]
        check(comparison['baseline_component_seconds'] == before_seconds
              and comparison['selected_component_seconds'] == after_seconds
              and comparison['component_seconds_ratio'] == after_seconds / before_seconds,
              'recomputed selected public cost ' + case)
        check(comparison['wire_added_bytes'] == now['wire_bytes'] - old['wire_bytes'],
              'recomputed added wire ' + case)
        comparisons[case] = {'seconds': after_seconds, 'ratio': after_seconds / before_seconds,
            'wire_added_bytes': now['wire_bytes'] - old['wire_bytes'],
            'peak_rss_kib': now['process_peak_rss_kib_before_postmeasurement_analysis']}
        previous = load(Path('docs/tasks/W014/resources-r3') / ('w014-' + case + '.json'))
        original_r4 = load(Path('docs/tasks/W014/resources-r4') / ('w014-' + case + '.json'))
        for name in ('wire_bytes', 'wire_sha256', 'compact_envelope_bytes_without_input_field',
                     'authentication_calls_by_phase', 'neutral_builder_calls_by_phase',
                     'capture_sources', 'retained_W010_wire_bytes', 'retained_W010_wire_sha256'):
            check(previous[name] == original_r4[name] == now[name], 'R3/R4/selected stable ' + case + ':' + name)
    check(len(new_files) == 286 and all(sha(read(n)) == h for n, h in new_files.items()),
          'all 286 selected live bytes match measured source')
    delta = sorted(name for name in set(old_files) | set(new_files)
                   if old_files.get(name) != new_files.get(name))
    check(all(name.removeprefix('layauto_v2/') in W014 if name.startswith('layauto_v2/')
              else name.startswith('tests/') and 'w014' in Path(name).name for name in delta),
          'all reference-to-current deltas confined to W014 runtime and tests')
    check(delta == sorted(row['path'] for row in adoption['selected_source_delta']),
          'independently recomputed full source delta equals adoption')
    early = Path('docs/tasks/W014/resources-early')
    closure = load(early / 'attempt-closure.json')
    check(closure['status'] == 'failed' and closure['failure_case'] == 'w014-normal-readback'
          and closure['not_run'] == ['w014-extraction-mismatch'], 'early failure and unrun route preserved')
    preserved = {}
    with tarfile.open(ROOT / early / 'failed-source-snapshot.tar.gz', 'r:gz') as archive:
        for member in archive.getmembers():
            check(member.isfile() and not Path(member.name).is_absolute()
                  and '..' not in Path(member.name).parts and member.name not in preserved,
                  'safe original snapshot member ' + member.name)
            preserved[member.name] = archive.extractfile(member).read()
    check({name: sha(data) for name, data in preserved.items()} == old_files, 'full original reference snapshot identity')
    count = 0
    for name, wanted in old_files.items():
        if name.startswith('layauto_v2/') and name.removeprefix('layauto_v2/') not in W014:
            check(read(name) == preserved[name] and sha(read(name)) == wanted == new_files[name],
                  'actual unchanged W013 runtime ' + name)
            count += 1
    check(count == 106, 'all 106 actual W013 runtime dependencies')
    check(all(b'MYPY_CACHE_DIR' not in read(name) for name in new_files
              if name.startswith('layauto_v2/') and name.endswith('.py')), 'runtime has no mypy cache dependency')
    for name in ('resource_probe.py', 'source_identity.py'):
        check(read(early / name) == read(Path('docs/tasks/W014/resources-r4') / name), 'same original probe bytes ' + name)
    excluded = selection['original_R4_direct_overlap_and_exclusion']
    referenced(excluded['original_direct_report'])
    referenced(excluded['original_direct_command'])
    referenced(excluded['reviewer_metadata_after_stdout'])
    check(selection['selected_samples']['normal-direct']['report']['path']
          != excluded['original_direct_report']['path'], 'overlapped original direct excluded from primary cost')
    prior = load('docs/tasks/W013/verification-r2/receipt.json')
    limits = load('docs/tasks/W013/verification-r2/resource-limits.json')
    check(prior['status'] == 'passed' and prior['matrix_workers'] == 2
          and set(prior['actual_test_counts'].values()) == {1731}, 'same-host prior successful dual full matrix')
    observed = {name: Path(name).read_text().strip() for name in
                ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/cpu.max')}
    check(all(observed[name] == limits['cgroup'][name] for name in observed), 'same 16GiB four-CPU limits')
    maximum_peak = max(row['peak_rss_kib'] for row in comparisons.values()) * 1024
    check(maximum_peak * 2 + 2 * 1024 ** 3 < int(observed['/sys/fs/cgroup/memory.max']),
          'two route samples plus 2GiB reserve fit observed limit')
    result = {'status': 'resource-selection-and-identity-audit-passed-not-product-review',
        'source_id': selection['current_source_id'], 'reference_source_id': selection['reference_source_id'],
        'checks': checks, 'check_count': len(checks), 'comparison': comparisons,
        'selected_sample_receipts': selection['selected_samples'], 'non_W014_runtime_actual_byte_count': count,
        'parallel_matrices_safe_assessment': True,
        'limitations': ['No product chains were rerun by this audit.',
            'One route sample is not a full matrix or maximal-input memory bound.',
            'Only two interpreter matrices, each pytest serial; no overlapping heavy chains.',
            'Final clearance still waits for targeted success and exact frozen source.']}
    (OUT / 'resource_r4_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'source_id', 'check_count',
        'comparison', 'non_W014_runtime_actual_byte_count', 'parallel_matrices_safe_assessment')}, indent=2))


if __name__ == '__main__':
    main()
