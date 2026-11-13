"""Verify cross-source adoption of unchanged W013 reference measurements.

This does not run product code or alter original suites/source identities. It
compares preserved bytes, provenance, commands, dependencies and inputs before
rendering W013-reference/W014-product ratios at their separate source IDs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

from source_identity import files_manifest, source_id, source_names

CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')
W014_RUNTIME = {
    'derive/body_relations.py', 'derive/terminal_relations.py',
    'domain/terminal_relations.py', 'normalization/terminal_relations.py',
    'normalization/terminal_relations_codec.py',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--current', required=True, type=Path)
    parser.add_argument('--reference-source-id', required=True)
    parser.add_argument('--current-source-id', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root, reference, current, out = (getattr(args, key).resolve() for key in ('root', 'reference', 'current', 'out'))
    if out.exists():
        parser.error('Use a new adoption directory; original evidence is preserved')
    evidence: dict[str, dict[str, str]] = {}

    def read(path: Path) -> bytes:
        data = path.read_bytes()
        evidence[str(path.relative_to(root))] = {'sha256': sha(data), 'bytes': len(data)}
        return data

    def load(path: Path) -> object:
        return json.loads(read(path))

    reports: dict[str, dict[str, dict[str, object]]] = {'reference': {}, 'current': {}}
    for label, directory, component, expected_id in (
            ('reference', reference, 'w013', args.reference_source_id),
            ('current', current, 'w014', args.current_source_id)):
        for case in CASES:
            name = component + '-' + case
            report = load(directory / (name + '.json'))
            command = load(directory / (name + '.command.json'))
            assert report['source_id'] == expected_id and source_id(report['files']) == expected_id
            assert report['component'] == component and report['case'] == case
            assert report['public_roundtrip_equal'] is True and command['returncode'] == 0
            assert sha(read(directory / (name + '.stdout.txt'))) == command['stdout_sha256']
            assert sha(read(directory / (name + '.stderr.txt'))) == command['stderr_sha256']
            assert sha(read(directory / 'resource_probe.py')) == report['probe_sha256']
            assert command['tool_hashes'] == {key: sha(read(directory / key))
                                             for key in ('resource_probe.py', 'source_identity.py')}
            assert report['authentication_calls_by_phase'] == {
                component.upper() + '_build': 1, component.upper() + '_encode': 1,
                component.upper() + '_decode': 2}
            reports[label][case] = {'report': report, 'command': command}
    old = reports['reference'][CASES[0]]['report']
    new = reports['current'][CASES[0]]['report']
    for cases in reports.values():
        for pair in cases.values():
            assert pair['report']['files'] == (old['files'] if cases is reports['reference'] else new['files'])
    suite = load(current / 'suite.json')
    assert suite['source_id'] == args.current_source_id and suite['components'] == ['w014']
    assert tuple(suite['cases']) == CASES
    closure = load(reference / 'attempt-closure.json')
    assert closure['status'] == 'failed' and closure['source_id'] == args.reference_source_id
    assert closure['failure_case'] == 'w014-normal-readback'
    assert closure['not_run'] == ['w014-extraction-mismatch']
    old_manifest = load(reference / 'failed-source-manifest.json')
    assert old_manifest['source_id'] == args.reference_source_id and old_manifest['files'] == old['files']
    archive_bytes = read(reference / 'failed-source-snapshot.tar.gz')
    assert sha(archive_bytes) == closure['snapshot_sha256']
    # Read archive members directly. No extraction, execution or product calls.
    with tarfile.open(reference / 'failed-source-snapshot.tar.gz', 'r:gz') as archive:
        preserved = {}
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            stream = archive.extractfile(member)
            assert stream is not None and member.name not in preserved
            preserved[member.name] = stream.read()
    assert {name: sha(data) for name, data in preserved.items()} == old['files']
    actual = files_manifest(root, source_names(root))
    assert actual == new['files'] and source_id(actual) == args.current_source_id
    delta = [{'path': name, 'reference_sha256': old['files'].get(name), 'current_sha256': new['files'].get(name),
              'change': 'added' if name not in old['files'] else 'removed' if name not in new['files'] else 'modified'}
             for name in sorted(set(old['files']) | set(new['files']))
             if old['files'].get(name) != new['files'].get(name)]
    for row in delta:
        name = row['path']
        assert (name.removeprefix('layauto_v2/') in W014_RUNTIME if name.startswith('layauto_v2/')
                else name.startswith('tests/') and 'w014' in Path(name).name), row
    old_runtime, new_runtime = old['runtime_files'], new['runtime_files']
    old_paths, new_paths = set(old_runtime) - W014_RUNTIME, set(new_runtime) - W014_RUNTIME
    assert old_paths == new_paths
    exact_runtime: dict[str, str] = {}
    for name in sorted(old_paths):
        path = 'layauto_v2/' + name
        previous_bytes, current_bytes = preserved[path], (root / path).read_bytes()
        assert previous_bytes == current_bytes
        assert sha(previous_bytes) == old_runtime[name] == new_runtime[name]
        exact_runtime[name] = sha(previous_bytes)
    for key in ('resource_probe.py', 'source_identity.py'):
        assert read(reference / key) == read(current / key)
    comparison = {}
    for case in CASES:
        before, after = reports['reference'][case], reports['current'][case]
        a, b = before['report'], after['report']
        for field in ('python', 'executable', 'platform', 'package', 'distributions', 'cwd',
                      'input_site', 'capture_sources', 'retained_W010_wire_bytes', 'retained_W010_wire_sha256',
                      'local_counts', 'probe_sha256', 'retained_roots', 'readback_unsealed_unchanged_no_terminal'):
            assert a[field] == b[field], (case, field)
        assert before['command']['environment_overrides'] == after['command']['environment_overrides']
        old_seconds = sum(row['seconds'] for name, row in a['phases'].items() if name.startswith('W013'))
        new_seconds = sum(row['seconds'] for name, row in b['phases'].items() if name.startswith('W014'))
        comparison[case] = {
            'reference_source_id': a['source_id'], 'current_source_id': b['source_id'],
            'reference_report': str((reference / ('w013-' + case + '.json')).relative_to(root)),
            'current_report': str((current / ('w014-' + case + '.json')).relative_to(root)),
            'reference_component_seconds': old_seconds, 'current_component_seconds': new_seconds,
            'component_seconds_ratio': new_seconds / old_seconds,
            'reference_wire_bytes': a['wire_bytes'], 'current_wire_bytes': b['wire_bytes'],
            'wire_added_bytes': b['wire_bytes'] - a['wire_bytes'], 'wire_ratio': b['wire_bytes'] / a['wire_bytes'],
            'reference_peak_rss_kib': a['process_peak_rss_kib_before_postmeasurement_analysis'],
            'current_peak_rss_kib': b['process_peak_rss_kib_before_postmeasurement_analysis'],
            'peak_rss_ratio': b['process_peak_rss_kib_before_postmeasurement_analysis'] /
                              a['process_peak_rss_kib_before_postmeasurement_analysis'],
            'identical_inputs_W010_wire_interpreter_dependencies_probe_and_non_W014_runtime': True,
        }
    prior_limits = load(root / 'docs/tasks/W013/verification-r2/resource-limits.json')
    prior_receipt = load(root / 'docs/tasks/W013/verification-r2/receipt.json')
    assert prior_receipt['status'] == 'passed' and prior_receipt['matrix_workers'] == 2
    cgroup_paths = ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/cpu.max')
    cgroup = {path: Path(path).read_text().strip() for path in cgroup_paths}
    assert cgroup['/sys/fs/cgroup/memory.max'] == prior_limits['cgroup']['/sys/fs/cgroup/memory.max']
    assert cgroup['/sys/fs/cgroup/cpu.max'] == prior_limits['cgroup']['/sys/fs/cgroup/cpu.max']
    maximum_peak_bytes = max(row['current_peak_rss_kib'] for row in comparison.values()) * 1024
    reserve_bytes = 2 * 1024 ** 3
    two_samples_plus_reserve = maximum_peak_bytes * 2 + reserve_bytes
    memory_limit = int(cgroup['/sys/fs/cgroup/memory.max'])
    scheduling = {
        'cgroup_observed_at_report': cgroup,
        'prior_successful_W013_dual_matrix_workers': 2,
        'prior_test_counts': prior_receipt['actual_test_counts'],
        'prior_same_memory_and_CPU_limit': True,
        'maximum_new_route_process_peak_bytes': maximum_peak_bytes,
        'two_route_peaks_plus_2GiB_reserve_bytes': two_samples_plus_reserve,
        'memory_limit_bytes': memory_limit,
        'remaining_headroom_bytes': memory_limit - two_samples_plus_reserve,
        'sample_based_two_worker_headroom_positive': two_samples_plus_reserve < memory_limit,
        'phase_order': ['two interpreter matrices', 'build', 'serial clean installation and smokes'],
        'limitations': ['Sample HWM does not bound the full test matrix or maximal inputs.',
                       'Final runner has no xdist workers; each matrix runs its tests serially.',
                       'No package smoke or separate resource/product chain should overlap the two matrices.',
                       'Root/reviewer must make the scheduling decision; this report is not clearance.'],
    }
    result = {
        'classification': 'cross-source-unchanged-W013-reference-adoption-not-a-same-source-suite',
        'status': 'identity-and-evidence-checks-passed-pending-review',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'reference_source_id': args.reference_source_id, 'current_source_id': args.current_source_id,
        'preserved_reference_attempt_status': 'failed',
        'adopted_only': ['three individually successful W013 reference commands'],
        'not_adopted': ['early W014 direct as final product', 'failed early W014 readback', 'unrun early W014 mismatch'],
        'selected_source_delta': delta, 'byte_identical_non_W014_runtime_files': exact_runtime,
        'current_selected_files': new['files'],
        'runtime_adoption_basis': 'Only W014-specific guard/codec and W014 tests changed. The W013 reference builder, its complete old dependency runtime, captured inputs, interpreter/dependencies and probe bytes remain unchanged. Changed W014 guard/codec paths are not invoked by the W013 builder.',
        'comparison': comparison, 'matrix_scheduling_assessment': scheduling,
        'evidence_files': evidence,
        'generator_sha256': sha(Path(__file__).read_bytes()),
        'source_identity_tool_sha256': sha(Path(__file__).with_name('source_identity.py').read_bytes()),
        'limitations': ['Original source IDs and raw reports are preserved; the early attempt is not rewritten as a passing suite.',
                       'One sample per route is a checkpoint, not a stable performance improvement claim.',
                       'The separate W014 current-source suite supplies all final three product routes.'],
    }
    assert files_manifest(root, source_names(root)) == actual
    out.mkdir(parents=True)
    (out / 'adoption.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# W014 资源基线采信与比较', '',
             '这是跨源码身份采信，不是同源六路 suite。原失败、原 source_id 和原输出均保留。', '',
             '- W013 基线来源：`' + args.reference_source_id + '`，三条独立成功命令。',
             '- W014 本次三路：`' + args.current_source_id + '`，原 R2 suite。',
             '- 非 W014 runtime 实际字节相同：' + str(len(exact_runtime)) + ' 个文件；原始捕获、W010完整wire、解释器/依赖和probe字节逐项相同。', '',
             '| Case | W013 build+encode+decode (s) | W014 (s) | 耗时比 | 新增wire bytes | wire比 | W013/W014峰值MiB |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for case, row in comparison.items():
        lines.append(f"| {case} | {row['reference_component_seconds']:.3f} | {row['current_component_seconds']:.3f} | {row['component_seconds_ratio']:.4f} | {row['wire_added_bytes']} | {row['wire_ratio']:.6f} | {row['reference_peak_rss_kib']/1024:.2f}/{row['current_peak_rss_kib']/1024:.2f} |")
    lines.extend(['', '完整 selected source delta：', ''])
    lines.extend('- `' + row['path'] + '`：' + row['change'] + '；`' + str(row['reference_sha256']) + '` → `' + str(row['current_sha256']) + '`。' for row in delta)
    lines.extend(['', '双矩阵调度依据：此前 W013 在相同16GiB/4CPU限制下完成双1731全量；本轮三路最高进程峰值为'
                  + f'{maximum_peak_bytes/1024**2:.2f}MiB。两份最高样本加2GiB保留量为{two_samples_plus_reserve/1024**3:.3f}GiB，'
                  + f'相对内存限制余量{(memory_limit-two_samples_plus_reserve)/1024**3:.3f}GiB。', '',
                  '样本峰值不保证全量上界；两个矩阵各自串行测试，build与两个安装smoke必须排在矩阵后。是否采用workers=2由root/reviewer核验后另写clearance。', '',
                  '本次实跑：仅证据读取/字节核对与报告生成。按身份采信：原W013三路reference。未重跑产品链；原W014 early失败不计成功。', '',
                  '补跑触发：旧runtime/输入/依赖/probe改变，原证据缺失/失败，source delta超出W014专有路径，或发现W013 reference受新路径影响。', ''])
    (out / 'README.md').write_text('\n'.join(lines))
    (out / 'manifest.json').write_text(json.dumps({name: sha((out / name).read_bytes()) for name in ('adoption.json', 'README.md')}, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'reference_source_id': args.reference_source_id,
                      'current_source_id': args.current_source_id, 'selected_source_delta_count': len(delta),
                      'byte_identical_non_W014_runtime_file_count': len(exact_runtime),
                      'sample_based_two_worker_headroom_positive': scheduling['sample_based_two_worker_headroom_positive']}, indent=2))


if __name__ == '__main__':
    main()
