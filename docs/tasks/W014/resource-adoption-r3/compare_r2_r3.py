"""Compare preserved W014 R2/R3 measurements; stdlib only, no product execution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
R2_ID = 'd75b1b03b90e1eb010806a689a828fdcdeb715fdc20eb493a5bfd2219ae7f8a9'
R3_ID = '2d46bbdaccd858af936d37427ec8bad11d0bb11074d92cddb901da6197ecf639'
CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    evidence = {}
    def read(path: Path) -> object:
        data = path.read_bytes()
        evidence[str(path.relative_to(ROOT))] = sha(data)
        return json.loads(data)
    suites = {tag: read(ROOT / 'docs/tasks/W014' / ('resources-' + tag) / 'suite.json') for tag in ('r2', 'r3')}
    assert suites['r2']['source_id'] == R2_ID and suites['r3']['source_id'] == R3_ID
    assert all(suite['components'] == ['w014'] and tuple(suite['cases']) == CASES for suite in suites.values())
    comparison = {}
    old_files = new_files = None
    for case in CASES:
        old = read(ROOT / 'docs/tasks/W014/resources-r2' / ('w014-' + case + '.json'))
        new = read(ROOT / 'docs/tasks/W014/resources-r3' / ('w014-' + case + '.json'))
        assert old['source_id'] == R2_ID and new['source_id'] == R3_ID
        for key in ('wire_bytes', 'wire_sha256', 'retained_W010_wire_bytes', 'retained_W010_wire_sha256',
                    'compact_envelope_bytes_without_input_field', 'authentication_calls_by_phase',
                    'python', 'executable', 'platform', 'package', 'distributions', 'probe_sha256',
                    'input_site', 'capture_sources', 'local_counts', 'retained_roots'):
            assert old[key] == new[key], (case, key)
        assert old['public_roundtrip_equal'] is new['public_roundtrip_equal'] is True
        assert new['authentication_calls_by_phase'] == {'W014_build': 1, 'W014_encode': 1, 'W014_decode': 2}
        for tag in ('r2', 'r3'):
            directory = ROOT / 'docs/tasks/W014' / ('resources-' + tag)
            command = read(directory / ('w014-' + case + '.command.json'))
            assert command['returncode'] == 0
            for kind in ('stdout', 'stderr'):
                data = (directory / ('w014-' + case + '.' + kind + '.txt')).read_bytes()
                digest = sha(data)
                evidence[str((directory / ('w014-' + case + '.' + kind + '.txt')).relative_to(ROOT))] = digest
                assert digest == command[kind + '_sha256']
        phases = {}
        for phase in ('build', 'encode', 'decode'):
            a, b = old['phases']['W014_' + phase]['seconds'], new['phases']['W014_' + phase]['seconds']
            phases[phase] = {'r2_seconds': a, 'r3_seconds_including_full_retained_validation': b,
                             'delta_seconds': b - a, 'ratio': b / a}
        old_total = sum(row['r2_seconds'] for row in phases.values())
        new_total = sum(row['r3_seconds_including_full_retained_validation'] for row in phases.values())
        comparison[case] = {'identical_valid_wire_sha256': old['wire_sha256'], 'identical_valid_wire_bytes': old['wire_bytes'],
                            'identical_compact_envelope_bytes': old['compact_envelope_bytes_without_input_field'],
                            'identical_authentication_counts': new['authentication_calls_by_phase'],
                            'phases': phases, 'r2_component_seconds': old_total, 'r3_component_seconds': new_total,
                            'component_ratio': new_total / old_total,
                            'r2_process_peak_rss_kib': old['process_peak_rss_kib_before_postmeasurement_analysis'],
                            'r3_process_peak_rss_kib': new['process_peak_rss_kib_before_postmeasurement_analysis']}
        if old_files is None:
            old_files, new_files = old['files'], new['files']
        assert old['files'] == old_files and new['files'] == new_files
    delta = [{'path': path, 'r2_sha256': old_files.get(path), 'r3_sha256': new_files.get(path)}
             for path in sorted(set(old_files) | set(new_files)) if old_files.get(path) != new_files.get(path)]
    assert [row['path'] for row in delta] == ['layauto_v2/normalization/terminal_relations_codec.py',
                                              'tests/contracts/test_w014_body_scope.py',
                                              'tests/contracts/test_w014_contracts.py']
    adoption = read(OUT / 'adoption.json')
    assert adoption['current_source_id'] == R3_ID
    result = {'classification': 'R2-to-R3-valid-wire-and-observed-public-cost-comparison-not-product-rerun',
              'status': 'passed', 'r2_source_id': R2_ID, 'r3_source_id': R3_ID,
              'all_three_valid_wire_SHA_and_bytes_unchanged': True,
              'all_three_authentication_counts_unchanged_1_1_2': True,
              'selected_source_delta': delta, 'comparison': comparison, 'evidence_files': evidence,
              'generator_sha256': sha(Path(__file__).read_bytes()),
              'cost_interpretation': 'The R3 public encode measurements include the new complete retained-field validation. The original probe did not time _retained separately. End-to-end phase samples include process scheduling/noise; faster samples do not establish negative check cost or a performance improvement.',
              'not_run': ['product chain', 'resource probes', 'typing', 'tests', 'final matrices', 'installed smoke']}
    with (OUT / 'r2-r3-comparison.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    lines = ['# W014 R2→R3 valid wire 与实际公开成本', '',
             'R2 source：`' + R2_ID + '`；R3 source：`' + R3_ID + '`。原测量身份和原文件均保留。', '',
             '三路 valid wire 的 SHA-256 和 bytes 完全相同，完整 W010 wire、compact bytes、输入、解释器/依赖、probe字节也相同。公开W010认证调用仍为build/encode/decode=1/1/2。', '',
             '| Case | Phase | R2 (s) | R3（含完整retained检查）(s) | 差值(s) |',
             '| --- | --- | ---: | ---: | ---: |']
    for case, row in comparison.items():
        for phase, value in row['phases'].items():
            lines.append(f"| {case} | {phase} | {value['r2_seconds']:.3f} | {value['r3_seconds_including_full_retained_validation']:.3f} | {value['delta_seconds']:+.3f} |")
    lines.extend(['', '原probe未单独对 `_retained` 计时；这里是包含新完整检查的实际公开调用成本，不把单样本变快归因为检查负成本或稳定性能收益。', '',
                  'R2→R3完整selected源差异只有以下三项，唯一runtime变化是新codec：', ''])
    lines.extend('- `' + row['path'] + '`：`' + row['r2_sha256'] + '` → `' + row['r3_sha256'] + '`。' for row in delta)
    lines.extend(['', '本次只读取原报告、日志和suite作轻量证据核对；没有重跑任何产品链。', ''])
    with (OUT / 'r2-r3-comparison.md').open('x') as stream:
        stream.write('\n'.join(lines))
    readme = OUT / 'README.md'
    generated = readme.read_text()
    assert '原 R2 suite' in generated
    (OUT / 'README.generated-before-label-correction.md').write_text(generated)
    readme.write_text(generated.replace('原 R2 suite', '原 R3 suite') + '\n新增codec检查的valid-wire不变和各phase成本见[r2-r3-comparison](r2-r3-comparison.md)。\n')
    (OUT / 'manifest.json').write_text(json.dumps({str(path.relative_to(OUT)): sha(path.read_bytes())
        for path in sorted(OUT.iterdir()) if path.is_file() and path.name != 'manifest.json'}, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'all_valid_wires_identical': True, 'authentication_counts': '1/1/2',
                      'r2_r3_selected_source_delta_count': len(delta)}, indent=2))


if __name__ == '__main__':
    main()
