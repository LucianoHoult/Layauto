"""Independent premerge evidence audit; reads stored records, runs no product path."""
from pathlib import Path
import hashlib
import json
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
A1 = ROOT / 'docs/tasks/W012/A1'
OUT = Path(__file__).resolve().parent
BASE = '0a3326aa363477724465886cd05874d0997fba3e'
HEAD = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'
reads = {}
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(message)


def raw(path):
    path = Path(path)
    data = path.read_bytes()
    reads[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data


def doc(path):
    return json.loads(raw(A1 / path))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(commit, name):
    return subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)


def run():
    expected = {
        'normal-direct': (54050313, '4d07033687223809e542ea661138fe0566ed162f6eab17fb7d4f806745377f16'),
        'normal-readback': (136471701, '1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795'),
        'extraction-mismatch': (54045042, '83713d7586b02181697f10ac45c59490f2c3aa02fcea37ecf92b740a03b8e2b1'),
    }
    frozen = doc('performance/frozen-identity.json')
    for side in ('before', 'after'):
        source = frozen['sources'][side]
        check(len(source) == (262 if side == 'before' else 263), f'{side} source count')
        for name, digest in source.items():
            check(sha(git_blob(BASE if side == 'before' else HEAD, name)) == digest,
                  f'{side} source {name}')
        check(len([name for name in source if name.startswith('layauto_v2/')]) == 100,
              f'{side} runtime count')
    for name, digest in frozen['tools'].items():
        check(sha(raw(A1 / name)) == digest, f'frozen tool {name}')

    baseline = doc('performance/receipt.json')
    profile = doc('profile/receipt.json')
    check(baseline['sources'] == profile['sources'] == frozen['sources'], 'profile/source identity')
    check(baseline['tools'] == profile['tools'] == frozen['tools'], 'profile/tool identity')
    index_omissions = []
    actual_results = {}
    all_commands = []
    fixed_environment = None
    for stage, receipt, count, mode in [('performance', baseline, 18, 'baseline'), ('profile', profile, 2, 'profile')]:
        check(receipt['status'] == 'passed' and receipt['fresh_processes'] and receipt['serial']
              and receipt['full_wire_byte_comparison'], f'{stage} receipt')
        rows = receipt['commands']
        index = doc(stage + '/commands.json')
        check(len(rows) == len(index) == count, f'{stage} sample count')
        for n, row in enumerate(rows):
            side, case, rep = row['side'], row['case'], row['rep']
            name = f'{side}-{case}-r{rep}'
            saved = doc(f'{stage}/{name}.command.json')
            check(saved == row, f'{stage}/{name} command/receipt identity')
            for key, value in index[n].items():
                check(saved[key] == value, f'{stage}/{name} index field {key}')
            missing = sorted(set(saved) - set(index[n]))
            check(missing in ([], ['actual_complete_wire_byte_comparison']), f'{stage}/{name} index additions')
            if missing:
                check(n == len(rows) - 1, 'only final index entry lacks bytecmp')
                index_omissions.append(f'{stage}/{name}')
            for stream in ('stdout', 'stderr'):
                content = raw(A1 / stage / (name + '.' + stream + '.txt'))
                check(sha(content) == row[stream + '_sha256'], f'{stage}/{name} {stream} hash')
            check(row['exit_code'] == 0, f'{stage}/{name} exit')
            result = doc(f'{stage}/{name}.json')
            check(result['source_identity']['files'] == frozen['sources'][side], f'{name} actual source')
            check(result['tool_sha256'] == frozen['tools']['probe.py'], f'{name} actual tool')
            check(result['runtime_root'] == ('/workspace/w012-a1-before' if side == 'before' else '/workspace/Layauto'), f'{name} runtime')
            check(result['package'] == result['runtime_root'] + '/layauto_v2/__init__.py', f'{name} imported package')
            check(result['mode'] == mode and result['case'] == case, f'{name} mode')
            check((result['wire_bytes'], result['wire_sha256']) == expected[case], f'{name} wire identity')
            bytecmp = saved['actual_complete_wire_byte_comparison']
            check(bytecmp == {'reference': f'/workspace/w012-a1-performance/wires/baseline/before-{case}-r1.bin',
                              'bytes': expected[case][0], 'equal': True}, f'{name} complete bytecmp record')
            check(row['started_at_utc'] <= result['started_at_utc'] <= result['finished_at_utc'] <= row['finished_at_utc'], f'{name} timing containment')
            if all_commands:
                check(all_commands[-1]['finished_at_utc'] <= row['started_at_utc'], f'{name} serial order')
            all_commands.append(row)
            env = {k: result[k] for k in ('python', 'platform', 'executable', 'gc_enabled', 'gc_threshold')}
            if fixed_environment is None:
                fixed_environment = env
            check(env == fixed_environment, f'{name} fixed interpreter/platform/GC')
            check(result['input_site'] == ('/workspace/w012-inputs/extraction-mismatch/site_config.yaml' if case == 'extraction-mismatch' else '/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml'), f'{name} fixed input URI')
            check(result['public_roundtrip_equal'], f'{name} full roundtrip')
            check(result['readback_unsealed_checkpoint_unchanged_no_terminal'] == (case == 'normal-readback'), f'{name} readback')
            facts = result['result']
            check(facts['counts'] == {'MN0': 4 if case == 'extraction-mismatch' else 5, 'MP0': 7}, f'{name} normal/mismatch')
            check(facts['difference_count'] == (1 if case == 'extraction-mismatch' else 0), f'{name} differences')
            check((facts['complete_evaluations'], facts['local_edges'], facts['local_components'], facts['T05_status'], facts['body_kind']) == (36, 8, 6, 'pass', 'body'), f'{name} preserved facts')
            actual_results[(stage, side, case, rep)] = result
        if stage == 'performance':
            expected_order = [(side, case, rep) for rep in range(1, 4) for case in expected for side in ('before', 'after')]
            check([(r['side'], r['case'], r['rep']) for r in rows] == expected_order, 'all 18 sample order')

    summary = doc('performance-summary.json')
    calculations = {}
    increases = []
    for case in expected:
        computed = {}
        ref = actual_results[('performance', 'before', case, 1)]
        for side in ('before', 'after'):
            samples = [actual_results[('performance', side, case, rep)] for rep in range(1, 4)]
            for result in samples:
                check(result['capture_sources'] == ref['capture_sources'], f'{case} capture identity')
                check(result['result'] == ref['result'], f'{case} facts/crossing identity')
            totals = [sum(r['wall_seconds'].values()) for r in samples]
            peaks = [r['process_peak_rss_kib'] for r in samples]
            stages = {stage: statistics.median(r['wall_seconds'][stage] for r in samples) for stage in samples[0]['wall_seconds']}
            computed[side] = {'totals_seconds': totals, 'median_total_seconds': statistics.median(totals),
                              'peaks_kib': peaks, 'median_peak_kib': statistics.median(peaks), 'stage_medians_seconds': stages}
            check(computed[side]['median_total_seconds'] == summary[case][side]['median_total_stage_seconds'], f'{case}/{side} median of stage totals')
            check(computed[side]['median_peak_kib'] == summary[case][side]['median_peak_rss_kib'], f'{case}/{side} peak median')
            check(stages == summary[case][side]['median_stage_seconds'], f'{case}/{side} stage medians')
        time_drop = 1 - computed['after']['median_total_seconds'] / computed['before']['median_total_seconds']
        rss_drop = 1 - computed['after']['median_peak_kib'] / computed['before']['median_peak_kib']
        check(time_drop == summary[case]['observed_time_reduction_fraction'], f'{case} time drop')
        check(rss_drop == summary[case]['observed_median_peak_reduction_fraction'], f'{case} RSS drop')
        for stage, before in computed['before']['stage_medians_seconds'].items():
            after = computed['after']['stage_medians_seconds'][stage]
            if after > before:
                increases.append({'case': case, 'stage': stage, 'before_seconds': before, 'after_seconds': after,
                                  'increase_fraction': after / before - 1})
        computed.update(time_reduction_fraction=time_drop, peak_reduction_fraction=rss_drop)
        calculations[case] = computed
    check(len(increases) == 6, 'all six observed small-stage increases retained')

    old = actual_results[('profile', 'before', 'normal-readback', 1)]
    new = actual_results[('profile', 'after', 'normal-readback', 1)]
    for p in (old, new):
        check(p['capture_sources'] == actual_results[('performance', 'before', 'normal-readback', 1)]['capture_sources'], 'profile/baseline capture identity')
    old_windows, new_windows = old['matcher_windows'], new['matcher_windows']
    check(len(old_windows) == len(new_windows) == 65, '65 original matcher windows')
    check([(r['phase'], r['hex_characters']) for r in old_windows] == [(r['phase'], r['hex_characters']) for r in new_windows], 'matcher window order/length')
    check(max(r['hex_characters'] for r in old_windows) == 118841892, 'original maximum window')
    refreshes = [sum(r['after']['hwm_kib'] > r['before']['hwm_kib'] for r in rows) for rows in (old_windows, new_windows)]
    check(refreshes == [5, 0], 'HWM refreshes 5 to 0')
    check(new['process_peak_rss_kib'] == 720336, 'new residual profile peak')
    check(max(r['after']['hwm_kib'] for r in new_windows) == 648896 < new['process_peak_rss_kib'], 'residual outside observed windows')
    calls = []
    for side in ('before', 'after'):
        raw_profile = doc(f'profile/{side}-normal-readback-r1.profile.json')
        normalized = {}
        for stage, data in raw_profile.items():
            normalized[stage] = {}
            for row in data['functions']:
                if '/layauto_v2/' not in row['file']:
                    continue
                name = 'layauto_v2/' + row['file'].split('/layauto_v2/', 1)[1]
                line = row['line']
                if side == 'after' and name == 'layauto_v2/domain/codec.py' and line >= 118:
                    line -= 2
                key = (name, line, row['function'])
                check(key not in normalized[stage], f'{side} profile function identity')
                normalized[stage][key] = (row['primitive_calls'], row['calls'])
        calls.append(normalized)
    check(calls[0] == calls[1], 'all runtime function calls identical after known codec line shift')
    old_decode, new_decode = [r['wall_seconds']['W011_result_decode'] for r in (old, new)]
    return {'status': 'passed', 'checks': checks, 'reviewed_base': BASE, 'reviewed_head': HEAD,
            'scope': 'Stored evidence hash reads, independent numeric recomputation and static identity/call-count checks; no product/benchmark run and no current large-wire byte comparison.',
            'baseline_samples': 18, 'profile_samples': 2, 'calculations': calculations, 'small_stage_increases': increases,
            'index_tail_omissions_reconciled_by_single_command_and_receipt': index_omissions,
            'profile': {'matcher_windows_per_side': 65, 'maximum_hex_characters': 118841892,
                        'hwm_refreshes_before_after': refreshes, 'runtime_call_entries_per_side': sum(map(len, calls[0].values())),
                        'decode_wall_seconds_before_after': [old_decode, new_decode], 'decode_change_fraction': new_decode / old_decode - 1,
                        'new_profile_peak_kib': new['process_peak_rss_kib'], 'max_observed_matcher_hwm_kib': 648896},
            'missing_local_original_artifacts': [name for name in ('/workspace/w012-a1-performance/wires/baseline', '/workspace/w012-a1-performance/wires/profile', '/workspace/w012-a1-before', '/workspace/w012-inputs/extraction-mismatch') if not Path(name).exists()],
            'input_sha256': reads}


if __name__ == '__main__':
    result = run()
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'baseline_samples', 'profile_samples', 'index_tail_omissions_reconciled_by_single_command_and_receipt')}, indent=2))
