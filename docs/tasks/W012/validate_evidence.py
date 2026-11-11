"""Lightweight evidence integrity check, not a product regression matrix."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    def check(condition, label):
        assert condition, label
        checks.append(label)
    history = ROOT/'docs/tasks/W011/verification'
    original = json.loads((history/'receipt.json').read_text())
    check(original['actual_test_counts'] == {'310':1605,'312':1605}, 'inherited dual1605')
    for row in original['commands']:
        check(row['exit_code'] == 0, 'inherited command exit0: '+row['stdout'])
        for stream in ('stdout','stderr'):
            check(sha(history/row[stream]) == row[stream+'_sha256'], 'inherited raw '+row[stream])
    identity = json.loads((history/'source-manifest.json').read_text())
    for name,digest in identity['files'].items():
        check(sha(ROOT/name) == digest, 'source unchanged: '+name)
    receipt = json.loads((OUT/'measurement-receipt.json').read_text())
    check(receipt['status'] == 'passed' and len(receipt['commands']) == 6, 'six complete actual paths')
    last_finish = None
    for row in receipt['commands']:
        check(row['exit_code'] == 0, 'measurement exit0: '+str(row['argv']))
        start = datetime.fromisoformat(row['started_at_utc'])
        if last_finish:
            check(last_finish <= start, 'measurement serial chronology: '+str(start))
        last_finish = datetime.fromisoformat(row['finished_at_utc'])
        for name,digest in row['tools'].items():
            check(sha(OUT/name) == digest, 'frozen measurement tool: '+name)
        prefix = Path(row['argv'][-1]).with_suffix('')
        for stream in ('stdout','stderr'):
            check(sha(prefix.with_suffix('.'+stream+'.txt')) == row[stream+'_sha256'], 'raw measurement '+str(prefix)+stream)
        data = json.loads(prefix.with_suffix('.json').read_text())
        check(data['public_roundtrip_equal'], 'complete public roundtrip: '+str(prefix))
        check(data['source_identity']['files'] == identity['files'], 'source identity: '+str(prefix))
    for case in ('normal-direct','normal-readback','extraction-mismatch'):
        baseline = json.loads((OUT/('baseline-'+case+'.json')).read_text())
        profile = json.loads((OUT/('profile-'+case+'.json')).read_text())
        check(baseline['wire_sha256'] == profile['wire_sha256'], 'baseline/profile same full wire: '+case)
        check(baseline['capture_sources'] == profile['capture_sources'], 'baseline/profile same captures: '+case)
        check(len(baseline['capture_sources']) == 31, '31 captured acquisitions: '+case)
        if case == 'normal-readback':
            check(baseline['readback_unsealed_checkpoint_unchanged_no_terminal'], 'unsealed/readback/checkpoint/no terminal')
    extra = json.loads((OUT/'memory-profile.command.json').read_text())
    check(extra['exit_code'] == 0, 'extra complete readback diagnostic exit0')
    check(datetime.fromisoformat(extra['started_at_utc']) >= last_finish, 'extra diagnostic after six serial runs')
    check(extra['tool_sha256'] == sha(OUT/'memory_probe.py'), 'extra diagnostic tool identity')
    check(extra['original_probe_sha256'] == sha(OUT/'probe.py'), 'original probe not changed for extra diagnostic')
    check(extra['selfcheck_sha256'] == sha(OUT/'memory-probe-selfcheck.json'), 'extra tool selfcheck identity')
    for stream in ('stdout','stderr'):
        check(extra[stream+'_sha256'] == sha(OUT/('memory-profile.'+stream+'.txt')), 'extra diagnostic raw '+stream)
    extra_result = json.loads((OUT/'memory-profile-normal-readback.json').read_text())
    baseline = json.loads((OUT/'baseline-normal-readback.json').read_text())
    check(extra_result['mode'] == 'memory-profile', 'extra diagnostic is not baseline')
    check(extra_result['wire_sha256'] == baseline['wire_sha256'], 'extra diagnostic complete wire equals baseline')
    check(extra_result['capture_sources'] == baseline['capture_sources'], 'extra diagnostic captures equal baseline')
    events = json.loads((OUT/'memory-profile-events.json').read_text())
    check(max(e['after']['ru_maxrss_kib'] for e in events) == extra_result['process_peak_rss_kib'], 'actual matcher window reaches final process HWM')
    paths = subprocess.check_output(['git','diff','--name-only','f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe'],cwd=ROOT,text=True).splitlines()
    paths += subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    check(all(p.startswith('docs/tasks/W012/') or p == 'docs/tasks/W012-capture-wire-performance.md' for p in paths), 'authorized paths only')
    (OUT/'validation.json').write_text(json.dumps({'status':'passed','checks':checks,'count':len(checks)},indent=2)+'\n')
    print(str(len(checks))+' lightweight evidence integrity checks passed; no product matrix rerun')


if __name__ == '__main__':
    main()
