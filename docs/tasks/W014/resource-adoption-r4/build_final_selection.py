"""Select original R4 reports transparently; stdlib-only, no product execution.

The primary direct sample is the independent clean rerun. Readback and mismatch
remain the original R4 reports. This creates an evidence selection, not a suite.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')
CURRENT_ID = '998aa8052b3a6c89e3f87e029134ef8f6601535616c8b327d5ada44a29351a84'
REFERENCE_ID = '803b4c4f444f6c32f68966799d25fe8dffad31a914138633b0ed383eaa102bce'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    evidence = {}
    def blob(path: Path) -> bytes:
        data = path.read_bytes()
        evidence[str(path.relative_to(ROOT))] = {'sha256': sha(data), 'bytes': len(data)}
        return data
    def load(path: Path) -> object:
        return json.loads(blob(path))
    def ref(path: Path) -> dict[str, object]:
        data = blob(path)
        return {'path': str(path.relative_to(ROOT)), 'sha256': sha(data), 'bytes': len(data)}
    audited = load(OUT / 'suite-identity-audit/adoption.json')
    assert audited['reference_source_id'] == REFERENCE_ID and audited['current_source_id'] == CURRENT_ID
    assert len(audited['byte_identical_non_W014_runtime_files']) == 106
    selected = {}
    comparison = {}
    r3_r4 = {}
    for case in CASES:
        old_report_path = ROOT / 'docs/tasks/W014/resources-early' / ('w013-' + case + '.json')
        baseline = load(old_report_path)
        original_r4_path = ROOT / 'docs/tasks/W014/resources-r4' / ('w014-' + case + '.json')
        original_r4 = load(original_r4_path)
        r3_path = ROOT / 'docs/tasks/W014/resources-r3' / ('w014-' + case + '.json')
        r3 = load(r3_path)
        assert original_r4['source_id'] == CURRENT_ID
        for field in ('wire_sha256', 'wire_bytes', 'retained_W010_wire_sha256', 'retained_W010_wire_bytes',
                      'compact_envelope_bytes_without_input_field', 'authentication_calls_by_phase',
                      'python', 'executable', 'distributions', 'probe_sha256', 'capture_sources', 'input_site'):
            assert r3[field] == original_r4[field], (case, field)
        assert original_r4['authentication_calls_by_phase'] == {'W014_build': 1, 'W014_encode': 1, 'W014_decode': 2}
        r3_r4[case] = {'r3_report': ref(r3_path), 'original_r4_report': ref(original_r4_path),
                       'same_valid_wire_sha256': original_r4['wire_sha256'],
                       'same_valid_wire_bytes': original_r4['wire_bytes'],
                       'same_compact_envelope_bytes': original_r4['compact_envelope_bytes_without_input_field'],
                       'same_authentication_counts': original_r4['authentication_calls_by_phase'],
                       'r3_phases': {key: row for key, row in r3['phases'].items() if key.startswith('W014')},
                       'original_r4_phases_not_primary_if_direct': {key: row for key, row in original_r4['phases'].items() if key.startswith('W014')}}
        if case == 'normal-direct':
            directory = ROOT / 'docs/tasks/W014/resources-r4-direct-clean'
            report_path = directory / 'w014-normal-direct.json'
            command_path = directory / 'run.command.json'
            stdout_path, stderr_path = directory / 'run.stdout.txt', directory / 'run.stderr.txt'
            reason = 'Clean exclusive rerun selected; original R4 direct overlapped the reviewer metadata after probe during its startup window.'
        else:
            directory = ROOT / 'docs/tasks/W014/resources-r4'
            report_path = original_r4_path
            command_path = directory / ('w014-' + case + '.command.json')
            stdout_path, stderr_path = directory / ('w014-' + case + '.stdout.txt'), directory / ('w014-' + case + '.stderr.txt')
            reason = 'Original exclusive R4 route retained without rerun.'
        report, command = load(report_path), load(command_path)
        assert report['source_id'] == CURRENT_ID and report['public_roundtrip_equal'] is True
        assert command['returncode'] == 0
        if case == 'normal-direct':
            assert command['source_id_before'] == command['source_id_after'] == CURRENT_ID
            assert command['source_unchanged'] is True
            assert sha(blob(stdout_path)) == command['logs']['stdout']['sha256']
            assert sha(blob(stderr_path)) == command['logs']['stderr']['sha256']
        else:
            assert sha(blob(stdout_path)) == command['stdout_sha256']
            assert sha(blob(stderr_path)) == command['stderr_sha256']
        for field in ('files', 'runtime_files', 'wire_sha256', 'wire_bytes', 'retained_W010_wire_sha256',
                      'retained_W010_wire_bytes', 'compact_envelope_bytes_without_input_field',
                      'authentication_calls_by_phase', 'python', 'executable', 'platform', 'package',
                      'distributions', 'probe_sha256', 'capture_sources', 'input_site', 'local_counts'):
            assert report[field] == original_r4[field], (case, field)
        for field in ('python', 'executable', 'platform', 'package', 'distributions', 'probe_sha256',
                      'capture_sources', 'retained_W010_wire_sha256', 'retained_W010_wire_bytes', 'input_site', 'local_counts'):
            assert report[field] == baseline[field], (case, field)
        phases = {key: row for key, row in report['phases'].items() if key.startswith('W014')}
        before_seconds = sum(row['seconds'] for key, row in baseline['phases'].items() if key.startswith('W013'))
        after_seconds = sum(row['seconds'] for row in phases.values())
        selected[case] = {'source_id': CURRENT_ID, 'report': ref(report_path), 'command': ref(command_path),
                          'stdout': ref(stdout_path), 'stderr': ref(stderr_path), 'selection_reason': reason,
                          'baseline_source_id': REFERENCE_ID, 'baseline_report': ref(old_report_path),
                          'baseline_command': ref(ROOT / 'docs/tasks/W014/resources-early' / ('w013-' + case + '.command.json')),
                          'public_phases_including_complete_metadata_validation': phases,
                          'authentication_calls_by_phase': report['authentication_calls_by_phase'],
                          'wire_bytes': report['wire_bytes'], 'wire_sha256': report['wire_sha256'],
                          'process_peak_rss_kib': report['process_peak_rss_kib_before_postmeasurement_analysis']}
        comparison[case] = {'baseline_component_seconds': before_seconds, 'selected_component_seconds': after_seconds,
                            'component_seconds_ratio': after_seconds / before_seconds,
                            'baseline_wire_bytes': baseline['wire_bytes'], 'selected_wire_bytes': report['wire_bytes'],
                            'wire_added_bytes': report['wire_bytes'] - baseline['wire_bytes'],
                            'wire_ratio': report['wire_bytes'] / baseline['wire_bytes'],
                            'baseline_peak_rss_kib': baseline['process_peak_rss_kib_before_postmeasurement_analysis'],
                            'selected_peak_rss_kib': report['process_peak_rss_kib_before_postmeasurement_analysis']}
    metadata_path = ROOT / 'docs/tasks/W014/review-evidence/evidence_wrapper_versions.after.stdout.txt'
    metadata_text = blob(metadata_path).decode()
    metadata = json.JSONDecoder().raw_decode(metadata_text[metadata_text.index('{'):])[0]
    original_direct_command_path = ROOT / 'docs/tasks/W014/resources-r4/w014-normal-direct.command.json'
    original_direct_command = load(original_direct_command_path)
    overlap = {'original_direct_report': ref(ROOT / 'docs/tasks/W014/resources-r4/w014-normal-direct.json'),
               'original_direct_command': ref(original_direct_command_path),
               'reviewer_metadata_after_stdout': ref(metadata_path),
               'reviewer_metadata_elapsed_seconds': metadata['elapsed_seconds'],
               'reviewer_metadata_stdout_mtime_observed_utc': datetime.fromtimestamp(metadata_path.stat().st_mtime, timezone.utc).isoformat(),
               'original_direct_started_at_utc': original_direct_command['started_at_utc'],
               'fact': 'Root and reviewer identified startup-window overlap. The metadata probe elapsed field is about6.30s; available records do not identify its complete process start interval.',
               'disposition': 'Keep original direct for correctness/identity and R3-to-R4 valid-wire checks; exclude its timing from the final primary sample. Clean direct is the only replaced primary route.'}
    peak_bytes = max(row['process_peak_rss_kib'] for row in selected.values()) * 1024
    memory_limit = int(Path('/sys/fs/cgroup/memory.max').read_text().strip())
    scheduling = {**audited['matrix_scheduling_assessment'],
                  'maximum_new_route_process_peak_bytes': peak_bytes,
                  'two_route_peaks_plus_2GiB_reserve_bytes': peak_bytes * 2 + 2 * 1024**3,
                  'remaining_headroom_bytes': memory_limit - peak_bytes * 2 - 2 * 1024**3,
                  'sample_based_two_worker_headroom_positive': peak_bytes * 2 + 2 * 1024**3 < memory_limit,
                  'assessment_basis': 'Final selected clean direct and original exclusive R4 readback/mismatch; original overlapped direct excluded.'}
    result = {'classification': 'final-original-report-selection-with-cross-source-W013-reference-adoption-not-a-suite',
              'status': 'identity-and-selection-checks-passed-pending-review',
              'current_source_id': CURRENT_ID, 'reference_source_id': REFERENCE_ID,
              'cases': list(CASES), 'selected_samples': selected, 'comparison': comparison,
              'original_R4_direct_overlap_and_exclusion': overlap,
              'R3_to_R4_three_route_valid_wire_and_authentication_stability': r3_r4,
              'selected_source_delta_from_reference': audited['selected_source_delta'],
              'byte_identical_non_W014_runtime_files': audited['byte_identical_non_W014_runtime_files'],
              'cross_source_identity_audit': ref(OUT / 'suite-identity-audit/adoption.json'),
              'matrix_scheduling_assessment': scheduling, 'evidence_files': evidence,
              'metadata_cost_interpretation': 'Every selected R4 public build/encode/decode phase includes the complete metadata and retained-field validation on the real chain. The frozen probe does not separately time that helper. Single-sample phase differences are not an isolated helper cost or stable performance claim.',
              'generator_sha256': sha(Path(__file__).read_bytes()),
              'not_run_by_this_report': ['product chain', 'resource probes', 'tests', 'typing', 'final matrix', 'installed smoke'],
              'limitations': ['No report is copied or relabeled as a new suite; every selected report keeps its original path/hash/source ID.',
                             'Early W014 readback remains failed and its missing mismatch remains unrun.',
                             'Sample process peaks are not full-matrix or maximal-input guarantees.']}
    for name in ('final-selection.json', 'adoption.json', 'README.md'):
        assert not (OUT / name).exists(), name
    (OUT / 'final-selection.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'adoption.json').write_text(json.dumps({'classification': result['classification'], 'status': result['status'],
        'current_source_id': CURRENT_ID, 'reference_source_id': REFERENCE_ID,
        'final_selection': {'path': str((OUT / 'final-selection.json').relative_to(ROOT)), 'sha256': sha((OUT / 'final-selection.json').read_bytes())},
        'selected_source_delta': audited['selected_source_delta'],
        'byte_identical_non_W014_runtime_files': audited['byte_identical_non_W014_runtime_files'],
        'comparison': comparison, 'matrix_scheduling_assessment': scheduling}, indent=2) + '\n')
    lines = ['# W014 R4 最终资源选择与基线采信', '',
             '本文件选择原报告，不创建或重标新suite。source为`' + CURRENT_ID + '`；W013 reference保留原`' + REFERENCE_ID + '`。', '',
             '主样本：direct采用独占clean补测；readback/mismatch保留原R4，不重复运行。原R4 direct启动窗口与reviewer metadata after probe交叠，原件仍作正确性/身份核对，耗时不进入最终主样本。', '',
             '| Case | 原始报告路径 | W013 / W014公开三阶段(s) | 耗时比 | 新增wire bytes | W014峰值MiB |',
             '| --- | --- | ---: | ---: | ---: | ---: |']
    for case, row in comparison.items():
        lines.append(f"| {case} | `{selected[case]['report']['path']}` | {row['baseline_component_seconds']:.3f} / {row['selected_component_seconds']:.3f} | {row['component_seconds_ratio']:.4f} | {row['wire_added_bytes']} | {row['selected_peak_rss_kib']/1024:.2f} |")
    lines.extend(['', '全部106个非W014 runtime已由early保存snapshot与当前文件实际逐字节核相同；完整selected source delta只包含W014专有runtime/tests，详细列表见suite-identity-audit/adoption.json。每条命令、原stdout/stderr、report及hash/source身份都在final-selection.json中逐项引用。原资源目录和上代报告保持原样。', '',
                  'R3→R4原三路validwire的SHA、bytes、compact以及W010公开认证次数1/1/2均不变；clean direct与原R4 direct的这些字段也完全相同。metadata完整验证的实际成本已经包含在各公开phase中；原probe没有独立helper计时，不从单样本差异推导helper净成本或稳定性能提升。', '',
                  '最终主样本最高进程峰值' + f'{peak_bytes/1024**2:.2f}MiB；两份最高样本加2GiB reserve为{(peak_bytes*2+2*1024**3)/1024**3:.3f}GiB，'
                  + f'相对16GiB余量{scheduling["remaining_headroom_bytes"]/1024**3:.3f}GiB。旧W013在相同4CPU/16GiB完成双1731矩阵，仍只作调度依据；样本不保证全量上界。build和安装smoke在矩阵后串行。', '',
                  '本次仅轻量读证据并生成报告；未运行产品链。最终resource clearance和workers=2决定仍由root/reviewer核验。', ''])
    (OUT / 'README.md').write_text('\n'.join(lines))
    audit_readme = OUT / 'suite-identity-audit/README.md'
    audit_readme.write_text(audit_readme.read_text().replace('原 R2 suite', '原 R4 suite') + '\n本子报告核原R4 suite身份；最终主样本使用上层final-selection.json，原direct耗时被clean补测替换。\n')
    audit_manifest = OUT / 'suite-identity-audit/manifest.json'
    audit_manifest.write_text(json.dumps({name: sha((audit_manifest.parent / name).read_bytes()) for name in ('adoption.json', 'README.md')}, indent=2) + '\n')
    (OUT / 'manifest.json').write_text(json.dumps({str(path.relative_to(OUT)): sha(path.read_bytes()) for path in sorted(OUT.rglob('*'))
        if path.is_file() and path != OUT / 'manifest.json'}, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'source_id': CURRENT_ID,
                      'selected_reports': {case: row['report']['path'] for case, row in selected.items()},
                      'R3_R4_valid_wire_unchanged': True, 'maximum_selected_peak_MiB': peak_bytes/1024**2}, indent=2))


if __name__ == '__main__':
    main()
