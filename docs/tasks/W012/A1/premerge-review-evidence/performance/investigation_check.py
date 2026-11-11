"""Supplement: original P1/P2 remains in review scope; no historical artifacts changed."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('performance_audit', HERE / 'check.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
ROOT, A1 = a.ROOT, a.A1
W012 = A1.parent


def load(path):
    return json.loads(a.raw(path))


def main():
    manifest = load(W012 / 'delivery-manifest.json')
    for name, digest in manifest['files'].items():
        a.check(a.sha(a.raw(ROOT / name)) == digest, f'original P1/P2 delivery {name}')
    changed = subprocess.check_output(['git', 'diff', '--name-only', '7f7c1304bdafd941791421cef64864fb1616303c', a.HEAD, '--',
                                       'docs/tasks/W012', ':!docs/tasks/W012/A1'], cwd=ROOT, text=True)
    a.check(not changed.strip(), 'P1/P2 attachments unchanged throughout A1')
    preflight = load(A1 / 'preflight.json')
    original = load(W012 / 'preflight.json')
    a.check(preflight['inputs'] == original['inputs'], 'same original fixed 35-input overlay')
    a.check(len(preflight['inputs']) == 35, '35 fixed mismatch inputs')
    for row in preflight['inputs']:
        data = a.raw(Path(row['origin']))
        a.check(len(data) == row['bytes'] and a.sha(data) == row['sha256'], f'fixed overlay origin {row["origin"]}')
    receipt = load(W012 / 'measurement-receipt.json')
    a.check(receipt['status'] == 'passed' and receipt['serial'] and receipt['fresh_process_per_path_per_mode'], 'P1 six fresh serial paths')
    a.check(len(receipt['commands']) == 6, 'P1 six commands retained')
    previous = None
    facts = {}
    for row in receipt['commands']:
        output = Path(row['argv'][row['argv'].index('--output') + 1])
        saved = load(output.with_suffix('.command.json'))
        a.check(saved == row, 'P1 command/receipt identity')
        for stream in ('stdout', 'stderr'):
            a.check(a.sha(a.raw(output.with_suffix('.' + stream + '.txt'))) == row[stream + '_sha256'], 'P1 original stream identity')
        a.check(row['exit_code'] == 0, 'P1 exit')
        if previous:
            a.check(previous['finished_at_utc'] <= row['started_at_utc'], 'P1 serial timing')
        previous = row
        for name, digest in row['tools'].items():
            a.check(a.sha(a.raw(W012 / name)) == digest, 'P1 tool identity')
        result = load(output)
        a.check(result['source_identity']['files'] == original['files'], 'P1 source identity')
        facts[(result['mode'], result['case'])] = result
    events = []
    totals = {}
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        b, p = facts[('baseline', case)], facts[('profile', case)]
        a.check((b['wire_bytes'], b['wire_sha256'], b['capture_sources']) == (p['wire_bytes'], p['wire_sha256'], p['capture_sources']), 'P1 baseline/profile wire/captures identity')
        phases = load(W012 / f'profile-{case}.profile.json')
        outer = phases['W011_result_encode']['wire']['bytes_to_hex']['normalization.channel_identity_codec.encode_record:ChannelIdentityResult']
        events.append(outer['calls'])
        totals[case] = {'total_stage_seconds': sum(b['wall_seconds'].values()), 'wire_bytes': b['wire_bytes'],
                        'peak_rss_kib': b['process_peak_rss_kib'], 'outer_bytes_events': outer['calls']}
    a.check(events == [222, 222, 217], 'original R01 fixed scope remains 222/222/217')
    memory = load(W012 / 'memory-profile.command.json')
    a.check(memory['exit_code'] == 0 and previous['finished_at_utc'] <= memory['started_at_utc'], 'original memory profile after six commands')
    for stream in ('stdout', 'stderr'):
        a.check(a.sha(a.raw(W012 / ('memory-profile.' + stream + '.txt'))) == memory[stream + '_sha256'], 'original memory profile stream')
    windows = load(W012 / 'memory-profile-events.json')
    a.check(len(windows) == 65 and max(r['hex_characters'] for r in windows) == 118841892, 'P1 original 65 maximum window')
    a.check(sum(r['after']['hwm_kib'] > r['before']['hwm_kib'] for r in windows) == 5, 'P1 five matcher HWM refreshes')
    result = {'status': 'passed', 'checks': a.checks, 'scope': 'P1/P2 source/tool/output manifest and original numeric records plus the 35 overlay origin bytes; no new large product run.',
              'p1_delivery_manifest_files': len(manifest['files']), 'p1_baseline_recomputed': totals,
              'overlay_origins_rechecked': 35, 'input_sha256': a.reads}
    (HERE / 'investigation-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'p1_delivery_manifest_files', 'overlay_origins_rechecked')}, indent=2))


if __name__ == '__main__':
    main()
