"""PM read-only audit: parse retained JSON/bytes only, no Layauto imports/runs."""
from pathlib import Path
from datetime import datetime, timezone
from statistics import median
import ast
import hashlib
import json
import subprocess

ROOT = Path('/workspace/Layauto')
A1 = ROOT / 'docs/tasks/W012/A1'
OUT = Path('/workspace/work/w012-a1-pm/evidence')
checks = []
observations = []


def check(condition, label):
    checks.append({'label': label, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(label)


def read(rel):
    return json.loads((A1 / rel).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dt(value):
    return datetime.fromisoformat(value)


def audit_stage(name, stage, expected):
    receipt = read(name + '/receipt.json')
    frozen = read(name + '/frozen-identity.json')
    commands_index = read(name + '/commands.json')
    check(receipt['status'] == 'passed' and receipt['stage'] == stage, name + ': closed receipt')
    check(all(receipt[k] is True for k in ('fresh_processes', 'serial', 'full_wire_byte_comparison')), name + ': explicit process/comparison flags')
    check(receipt['sources'] == frozen['sources'], name + ': frozen source map matches receipt')
    check(receipt['tools'] == frozen['tools'], name + ': frozen tool map matches receipt')
    check(frozen['differences'] == ['layauto_v2/domain/codec.py', 'tests/contracts/test_w012_hex_validation.py'], name + ': authorized source differences')
    check(len(receipt['sources']['before']) == 262 and len(receipt['sources']['after']) == 263, name + ': full source counts')
    for tool, expected_hash in receipt['tools'].items():
        check(sha(A1 / tool) == expected_hash, name + ': current tool ' + tool)
    check(len(receipt['commands']) == len(expected), name + ': complete invocation count')
    check(len(commands_index) == len(expected), name + ': command index count')
    rows = {}
    previous = None
    index_observations = []
    for i, (side, case, rep) in enumerate(expected):
        tag = f'{side}-{case}-r{rep}'
        command = read(f'{name}/{tag}.command.json')
        row = read(f'{name}/{tag}.json')
        check(command == receipt['commands'][i], tag + ': single command equals final receipt')
        check((command['side'], command['case'], command['rep']) == (side, case, rep), tag + ': execution order')
        check(command['exit_code'] == 0, tag + ': exit0')
        for stream in ('stdout', 'stderr'):
            check(sha(A1 / name / f'{tag}.{stream}.txt') == command[stream + '_sha256'], tag + ': raw ' + stream + ' hash')
        check(command['tools'] == receipt['tools'], tag + ': tools frozen')
        check(row['source_identity']['files'] == receipt['sources'][side], tag + ': actually imported source identity')
        check(len(row['source_identity']['runtime_files']) == 100, tag + ': runtime identity count')
        check(row['tool_sha256'] == receipt['tools']['probe.py'], tag + ': actually imported probe')
        check(row['runtime_root'] == ('/workspace/w012-a1-before' if side == 'before' else str(ROOT)), tag + ': runtime root')
        check(row['package'] == row['runtime_root'] + '/layauto_v2/__init__.py', tag + ': package path')
        check(row['mode'] == stage and row['case'] == case, tag + ': actual mode/case')
        check(row['executable'] == frozen['python'], tag + ': interpreter path')
        check(command['argv'][0] == row['executable'] and command['argv'][1] == '-B', tag + ': fresh process argv')
        check('--input-root' in command['argv'] and command['argv'][command['argv'].index('--input-root') + 1] == str(ROOT), tag + ': fixed input root')
        check(dt(command['started_at_utc']) <= dt(row['started_at_utc']) < dt(row['finished_at_utc']) <= dt(command['finished_at_utc']), tag + ': nested timestamps')
        if previous:
            check(dt(previous['finished_at_utc']) <= dt(command['started_at_utc']), tag + ': serialized after prior process')
        previous = command
        compare = command['actual_complete_wire_byte_comparison']
        check(compare == {'reference': '/workspace/w012-a1-performance/wires/baseline/before-' + case + '-r1.bin', 'bytes': row['wire_bytes'], 'equal': True}, tag + ': original bytecmp receipt')
        index_row = commands_index[i]
        if index_row != command:
            check({k:v for k,v in command.items() if k != 'actual_complete_wire_byte_comparison'} == index_row and i == len(expected) - 1, tag + ': index has only final comparison lag')
            index_observations.append(tag)
        check(row['public_roundtrip_equal'] is True, tag + ': complete roundtrip equality')
        check(row['readback_unsealed_checkpoint_unchanged_no_terminal'] is (case == 'normal-readback'), tag + ': readback boundary')
        info = row['result']
        check(info['counts'] == {'MN0': 4 if case == 'extraction-mismatch' else 5, 'MP0': 7}, tag + ': actual counts')
        check(info['comparison_status'] == ('mismatch' if case == 'extraction-mismatch' else 'equal') and info['difference_count'] == (1 if case == 'extraction-mismatch' else 0), tag + ': source mismatch result')
        check(info['complete_evaluations'] == 36 and (info['local_nodes'], info['local_edges'], info['local_components']) == (14, 8, 6), tag + ': complete FIN and graph')
        check((info['T05_audits'], info['T05_status'], info['body_kind']) == (16, 'pass', 'body'), tag + ': T05/body')
        check('not covered by these fixed inputs' in info['partial_unknown'], tag + ': scope limitation retained')
        check(row['gc_enabled'] and row['gc_threshold'] == [700, 10, 10], tag + ': GC condition')
        if side == 'after':
            before = rows[('before', case, rep)]
            for key in ('capture_sources', 'python', 'executable', 'platform', 'input_site', 'gc_enabled', 'gc_threshold', 'result', 'wire_bytes', 'wire_sha256'):
                check(row[key] == before[key], tag + ': paired ' + key)
        rows[(side, case, rep)] = row
    if index_observations:
        observations.append({'severity': 'nonblocking', 'kind': 'command-index-final-comparison-lag', 'stage': name, 'entries': index_observations, 'impact': 'Single command JSON and final receipt contain the complete comparison; aggregate commands.json was written before appending the final comparison field.'})
    return receipt, rows


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    check(head == 'db07a16fb7cbbac030adae84a9eb88cc0c8aa650', 'received full head')
    check(status in ('', '?? docs/tasks/W012/A1/independent-premerge-prompt.md\n'), 'repository has only parent PM documented parallel handoff draft, if any')
    baseline_order = [(s, c, r) for r in range(1, 4) for c in ('normal-direct', 'normal-readback', 'extraction-mismatch') for s in ('before', 'after')]
    base_receipt, rows = audit_stage('performance', 'baseline', baseline_order)
    profile_receipt, profile_rows = audit_stage('profile', 'profile', [(s, 'normal-readback', 1) for s in ('before', 'after')])
    preflight = read('preflight.json')
    check(preflight['executable'] == '/workspace/.venvs/layauto/bin/python' and preflight['packages']['PyYAML'] == '6.0.3', 'preflight performance environment inventory')
    check('Existing /workspace/.venvs/layauto was not changed' in read('environment/evidence/receipt.json')['scope'], 'engineering setup explicitly preserves performance environment')
    for r in list(rows.values()) + list(profile_rows.values()):
        check(r['python'] == preflight['python'] and r['executable'] == preflight['executable'], r['case'] + ': same recorded performance interpreter')
    for side in ('before', 'after'):
        p = profile_rows[(side, 'normal-readback', 1)]
        b = rows[(side, 'normal-readback', 1)]
        check(all(p[k] == b[k] for k in ('capture_sources','result','wire_bytes','wire_sha256','input_site','gc_enabled','gc_threshold')), side + ': attribution uses same readback conditions')
    check(dt(base_receipt['commands'][-1]['finished_at_utc']) <= dt(profile_receipt['commands'][0]['started_at_utc']), 'baseline finished before attribution profiles')
    check(dt(profile_receipt['commands'][-1]['finished_at_utc']) <= dt(read('verification-attempt-01/environment-310.json')['started_at_utc']), 'profiles finished before first engineering attempt')
    summary = {}
    regressions = []
    saved = read('performance-summary.json')
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        case_summary = {}
        for side in ('before', 'after'):
            data = [rows[(side, case, r)] for r in range(1, 4)]
            check(all(all(d[k] == data[0][k] for k in ('capture_sources','result','wire_bytes','wire_sha256','python','platform','input_site')) for d in data), case + '/' + side + ': repetition conditions/results/wire')
            side_summary = {
                'samples': [{'rep': i + 1, 'stage_seconds': d['wall_seconds'], 'total_stage_seconds': sum(d['wall_seconds'].values()), 'peak_rss_kib': d['process_peak_rss_kib']} for i, d in enumerate(data)],
                'median_total_stage_seconds': median(sum(d['wall_seconds'].values()) for d in data),
                'median_stage_seconds': {k: median(d['wall_seconds'][k] for d in data) for k in data[0]['wall_seconds']},
                'all_peak_rss_kib': [d['process_peak_rss_kib'] for d in data],
                'median_peak_rss_kib': median(d['process_peak_rss_kib'] for d in data),
                'wire_bytes': data[0]['wire_bytes'], 'wire_sha256': data[0]['wire_sha256'],
            }
            case_summary[side] = side_summary
        case_summary['observed_time_reduction_fraction'] = 1 - case_summary['after']['median_total_stage_seconds'] / case_summary['before']['median_total_stage_seconds']
        case_summary['observed_median_peak_reduction_fraction'] = 1 - case_summary['after']['median_peak_rss_kib'] / case_summary['before']['median_peak_rss_kib']
        check(case_summary == saved[case], case + ': independent recomputation equals saved summary exactly')
        for stage, before in case_summary['before']['median_stage_seconds'].items():
            after = case_summary['after']['median_stage_seconds'][stage]
            if after > before:
                regressions.append({'case': case, 'stage': stage, 'before': before, 'after': after, 'delta_seconds': after - before, 'increase_fraction': after / before - 1})
        summary[case] = case_summary
    check(len(regressions) == 6, 'all six observed small-stage increases disclosed')
    profiles = {s: read(f'profile/{s}-normal-readback-r1.profile.json') for s in ('before', 'after')}
    counts = {}
    all_runtime_calls = {}
    windows = {}
    expected_names = ('__init__', '__post_init__', '_require_input', '_evaluate', '_analyze', 'normalize', 'encode_record', 'decode_record')
    for phase in profiles['before']:
        selected = {}
        entire = {}
        for side in ('before', 'after'):
            root = profile_rows[(side, 'normal-readback', 1)]['runtime_root'] + '/'
            runtime_functions = [f for f in profiles[side][phase]['functions'] if f['file'].startswith(root + 'layauto_v2/')]
            selected[side] = {f['file'][len(root):] + ':' + str(f['line']) + ':' + f['function']: f['calls'] for f in runtime_functions if f['function'] in expected_names}
            def normalized(f):
                file = f['file'][len(root):]
                line = f['line'] - (2 if side == 'after' and file == 'layauto_v2/domain/codec.py' and f['line'] >= 118 else 0)
                return file + ':' + str(line) + ':' + f['function']
            entire[side] = {normalized(f): (f['calls'], f['primitive_calls']) for f in runtime_functions}
        check(selected['before'] == selected['after'], phase + ': constructor/authentication/codec call counts')
        check(entire['before'] == entire['after'], phase + ': all localizable runtime calls after known line shift')
        counts[phase] = selected['after']
        all_runtime_calls[phase] = len(entire['after'])
    for side in ('before', 'after'):
        row = profile_rows[(side, 'normal-readback', 1)]
        events = row['matcher_windows']
        windows[side] = {'events': len(events), 'large_string_lengths': [e['hex_characters'] for e in events], 'peak_refreshes': [e for e in events if e['after']['hwm_kib'] > e['before']['hwm_kib']], 'largest_input_window': max(events, key=lambda e: e['hex_characters']), 'process_peak_rss_kib': row['process_peak_rss_kib'], 'sum_observed_matcher_seconds': sum(e['matcher_seconds'] for e in events)}
    original_profile_summary = read('profile-summary.json')
    check(counts == original_profile_summary['calls'] and windows == original_profile_summary['matcher_windows'], 'profile summary recomputed from raw functions/windows')
    check(windows['before']['events'] == windows['after']['events'] == 65 and windows['before']['large_string_lengths'] == windows['after']['large_string_lengths'], '65 matcher windows same ordered input lengths')
    check(len(windows['before']['peak_refreshes']) == 5 and not windows['after']['peak_refreshes'], 'HWM refreshes 5 to 0')
    after_windows = profile_rows[('after', 'normal-readback', 1)]['matcher_windows']
    after_window_hwm = max(max(e['before']['hwm_kib'], e['after']['hwm_kib']) for e in after_windows)
    check(after_window_hwm == 648896 and windows['after']['process_peak_rss_kib'] == 720336, 'residual profile peak correctly retained')
    input_rows = read('preflight.json')['inputs']
    check(len(input_rows) == 35, '35 mismatch input origins recorded')
    for r in input_rows:
        check(sha(Path(r['origin'])) == r['sha256'] and Path(r['origin']).stat().st_size == r['bytes'], 'mismatch origin: ' + r['origin'])
    mismatch_origins = {r['target']: r['origin'] for r in input_rows}
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        row = rows[('before', case, 1)]
        check(len(row['capture_sources']) == 31, case + ': complete capture source count')
        for capture in row['capture_sources']:
            path = Path(capture['uri'])
            if not path.is_absolute():
                path = Path(row['input_site']).parent / path
            path = Path(mismatch_origins.get(str(path), str(path)))
            check(path.stat().st_size == capture['bytes'] and sha(path) == capture['sha256'], case + ': retained capture identity ' + capture['uri'])
    interruption = read('interruption-01.json')
    check(len(interruption['files']) == 26, 'first interrupted attempt archive count')
    for rel, digest in interruption['files'].items():
        check(sha(A1 / 'verification-attempt-01' / rel) == digest, 'preserved interrupted artifact ' + rel)
    check(not (A1/'verification-attempt-01/receipt.json').exists(), 'partial attempt has no completed receipt')
    check('39%' in interruption['not_claimed_passed'][0] and '43%' in interruption['not_claimed_passed'][1], 'partial percentages do not claim pass')
    check('exit_code' not in read('final-r2-runner.command.json'), 'outer polling wrapper exit remains unknown')
    check(read('completion-observation.json')['outer_polling_wrapper_exit_code'].startswith('unknown'), 'completion based on internal commands only')
    prior = read('early-review-evidence/runner-R01-reproduction.json')
    fix = read('early-review-evidence/runner-R01-fix-verification.json')
    check(sha(A1/'early-review-evidence/run_performance-before-R01.py.txt') == prior['source_sha256'], 'original faulty runner preserved')
    check(prior['interrupted_stdout_overwritten'] and prior['frozen_identity_overwritten'], 'original R01 reproduction retained')
    check(sha(A1/'run_performance.py') == fix['source_sha256'] == base_receipt['tools']['run_performance.py'], 'fixed runner is actual baseline runner')
    check(fix['all_prior_stage_files_preserved'] and fix['no_process_started'] and fix['status'] == 'passed', 'independent R01 closure result retained')
    tree = ast.parse((A1/'run_performance.py').read_text())
    main_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    source = (A1/'run_performance.py').read_text()
    guard_pos = source.index("if directory.exists() and any(directory.iterdir()):")
    check(guard_pos < source.index('directory.mkdir(exist_ok=True)') < source.index("dump(directory/'frozen-identity.json'"), 'R01 guard statically precedes any stage mutation')
    check("assert not wire.exists(), 'never overwrite a prior complete wire artifact'" in source, 'complete wire overwrite guard retained')
    check(next(n for n in main_node.body if isinstance(n, ast.If) and ast.unparse(n.test) == 'args.selfcheck').body[-1].__class__ is ast.Return, 'selfcheck returns before stage creation')
    for prefix, checker in [('fix', 'verify_runner_fix.py'), ('reproduce', 'reproduce_runner.py')]:
        command = read('early-review-evidence/' + prefix + '.command.json')
        check(command['exit_code'] == 0 and command['checker_sha256'] == sha(A1/'early-review-evidence'/checker), prefix + ': original independent checker identity')
        for stream in ('stdout', 'stderr'):
            check(command[stream + '_sha256'] == sha(A1/'early-review-evidence'/f'{prefix}.{stream}.txt'), prefix + ': original ' + stream)
    manifest = read('handoff-artifact-manifest.json')
    for rel, digest in manifest.items():
        check(sha(A1/rel) == digest, 'handoff manifest ' + rel)
    access = {p: Path(p).exists() for p in ['/workspace/w012-a1-performance/wires/baseline', '/workspace/w012-a1-performance/wires/profile', '/workspace/w012-a1-before', '/workspace/w012-inputs/extraction-mismatch', '/workspace/.venvs/layauto/bin/python', '/workspace/w012-a1-final-r2']}
    check(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True) == status, 'repository unchanged after audit')
    result = {'status': 'passed', 'utc': datetime.now(timezone.utc).isoformat(), 'head': head, 'scope': 'Parse and hash retained source/evidence only. No product imports, codec, tests, build/install or performance reruns.', 'checks': len(checks), 'must_fix_findings': 0, 'observations': observations, 'performance': summary, 'stage_increases': regressions, 'profile': {'constructor_authentication_counts_equal': True, 'all_localizable_runtime_calls_equal': True, 'runtime_function_counts_by_phase': all_runtime_calls, 'windows': windows, 'after_max_window_hwm_kib': after_window_hwm, 'profile_decode_increase_fraction': profile_rows[('after','normal-readback',1)]['wall_seconds']['W011_result_decode'] / profile_rows[('before','normal-readback',1)]['wall_seconds']['W011_result_decode'] - 1}, 'handoff_manifest_entries_hashed': len(manifest), 'original_external_paths_accessible_here': access, 'wire_claim_basis': 'Original per-invocation commands and closed receipts record 1MiB actual complete byte comparison for all18 baseline and2 profile runs; original independent reviewer also recorded actual complete comparison. Their actual huge wire files are absent here, so this PM audit does not claim a fresh bytecmp.', 'details': checks}
    (OUT/'performance-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['performance','profile','details']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
