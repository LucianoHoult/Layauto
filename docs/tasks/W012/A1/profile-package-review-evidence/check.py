"""Independent completed-profile and reconstructed before-package review."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path('/workspace/Layauto')
A1 = ROOT/'docs/tasks/W012/A1'
OUT = Path(__file__).resolve().parent
checks = 0


def check(condition, label):
    global checks
    assert condition,label
    checks += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bytes_same_and_sha(reference,actual):
    count = 0
    digest = hashlib.sha256()
    with reference.open('rb') as left,actual.open('rb') as right:
        while True:
            a,b = left.read(1024*1024),right.read(1024*1024)
            check(a == b, 'actual profile wire bytes')
            if not b:
                return count,digest.hexdigest()
            digest.update(b)
            count += len(b)


def main():
    baseline = json.loads((A1/'performance/receipt.json').read_text())
    receipt = json.loads((A1/'profile/receipt.json').read_text())
    summary = json.loads((A1/'profile-summary.json').read_text())
    check(receipt['status'] == summary['status'] == 'passed', 'complete profile and summary')
    check(len(receipt['commands']) == 2 and receipt['serial'] and receipt['fresh_processes'], 'two fresh serial profile paths')
    check(receipt['sources'] == baseline['sources'] and receipt['tools'] == baseline['tools'], 'profile source/tool same as baseline')
    previous = datetime.fromisoformat(baseline['commands'][-1]['finished_at_utc'])
    samples,profiles = {},{}
    for row in receipt['commands']:
        side = row['side']
        prefix = A1/'profile'/f'{side}-normal-readback-r1'
        sample = json.loads(prefix.with_suffix('.json').read_text())
        profiles[side] = json.loads(prefix.with_suffix('.profile.json').read_text())
        check(row['exit_code'] == 0 and row['case'] == 'normal-readback' and row['rep'] == 1, 'complete readback attribution run')
        check(previous <= datetime.fromisoformat(row['started_at_utc']), 'profile serial and after all baselines')
        previous = datetime.fromisoformat(row['finished_at_utc'])
        check(json.loads(prefix.with_suffix('.command.json').read_text()) == row, 'per-case profile command complete')
        for stream in ('stdout','stderr'):
            check(sha(prefix.with_suffix('.'+stream+'.txt')) == row[stream+'_sha256'], 'profile raw '+stream)
        check(sample['mode'] == 'profile' and sample['tool_sha256'] == receipt['tools']['probe.py'], 'profile mode/tool')
        check(sample['source_identity']['files'] == receipt['sources'][side], 'profile frozen source')
        reference = Path('/workspace/w012-a1-performance/wires/baseline/before-normal-readback-r1.bin')
        length,digest = bytes_same_and_sha(reference,Path(sample['wire_artifact']))
        check(length == sample['wire_bytes'] == 136471701 and digest == sample['wire_sha256'], 'complete profile actual stored wire hash')
        samples[side] = sample
    check(samples['before']['wire_sha256'] == samples['after']['wire_sha256'], 'profile full wire identity')
    check(samples['before']['capture_sources'] == samples['after']['capture_sources'], 'profile capture identity')
    check(samples['before']['result'] == samples['after']['result'], 'profile complete measured facts')
    check(set(profiles['before']) == set(profiles['after']), 'all stages paired')
    selected = ('__init__','__post_init__','_require_input','_evaluate','_analyze','normalize','encode_record','decode_record')
    selected_counts = {}
    all_runtime_counts = {}
    for phase in profiles['before']:
        pairs,all_pairs = {},{}
        for side in ('before','after'):
            base = samples[side]['runtime_root']+'/'
            pairs[side] = {}
            all_pairs[side] = Counter()
            for row in profiles[side][phase]['functions']:
                if not row['file'].startswith(base+'layauto_v2/'):
                    continue
                relative = row['file'][len(base):]
                if row['function'] in selected:
                    key = relative+':'+str(row['line'])+':'+row['function']
                    pairs[side][key] = row['calls']
                # The only product edit inserted two comment lines before the
                # codec condition, shifting later codec function locations.
                line = row['line']-2 if side == 'after' and relative == 'layauto_v2/domain/codec.py' and row['line'] > 110 else row['line']
                all_pairs[side][(relative,line,row['function'])] += row['calls']
        check(pairs['before'] == pairs['after'], 'explicit constructor/authentication calls '+phase)
        check(pairs['after'] == summary['calls'][phase], 'reported explicit calls '+phase)
        check(all_pairs['before'] == all_pairs['after'], 'all runtime function calls unchanged after line normalization '+phase)
        selected_counts[phase] = pairs['after']
        all_runtime_counts[phase] = len(all_pairs['after'])
    event_signatures = {}
    window_result = {}
    for side,sample in samples.items():
        events = sample['matcher_windows']
        check(len(events) == 65, '65 existing large hex calls '+side)
        signature = [(e['phase'],e['hex_characters']) for e in events]
        event_signatures[side] = signature
        pattern = r'(?:[0-9a-f]{2})*' if side == 'before' else r'[0-9a-f]*'
        check(all(e['pattern'] == pattern for e in events), 'actual old/new matcher pattern '+side)
        previous_hwm = 0
        for event in events:
            check(previous_hwm <= event['before']['hwm_kib'] <= event['after']['hwm_kib'] <= sample['process_peak_rss_kib'], 'monotone HWM window '+side)
            previous_hwm = event['after']['hwm_kib']
        refreshes = [e for e in events if e['after']['hwm_kib'] > e['before']['hwm_kib']]
        largest = max(events,key=lambda e:e['hex_characters'])
        record = summary['matcher_windows'][side]
        check(record['events'] == len(events) and record['peak_refreshes'] == refreshes, 'reported refreshes '+side)
        check(record['largest_input_window'] == largest and record['process_peak_rss_kib'] == sample['process_peak_rss_kib'], 'reported largest/whole peak '+side)
        check(record['sum_observed_matcher_seconds'] == sum(e['matcher_seconds'] for e in events), 'reported matcher elapsed '+side)
        check(len(refreshes) == (5 if side == 'before' else 0), 'old5/new0 actual window refreshes')
        check(largest['hex_characters'] == 118841892, 'same maximum actual input')
        window_result[side] = {'largest':largest,'refreshes':len(refreshes),'peak':sample['process_peak_rss_kib'],
                               'max_window_hwm':max(e['after']['hwm_kib'] for e in events),'last_window':events[-1],
                               'decode_wall_seconds':sample['wall_seconds']['W011_result_decode']}
    check(event_signatures['before'] == event_signatures['after'], 'phase/length/order of all65 actual calls identical')
    check(window_result['before']['largest']['after']['hwm_kib'] == window_result['before']['peak'], 'old maximum window reaches final measured peak')
    check(window_result['after']['peak'] > window_result['after']['max_window_hwm'], 'new residual peak outside recorded matcher windows')
    first_matrix = json.loads((A1/'verification-attempt-01/environment-310.json').read_text())
    check(previous <= datetime.fromisoformat(first_matrix['started_at_utc']), 'original engineering started after profiles')

    package = A1/'before-package'
    evidence = json.loads((package/'evidence-manifest.json').read_text())
    for name,digest in evidence.items():
        check(sha(package/name) == digest, 'before package attachment '+name)
    source = json.loads((package/'before-source-identity.json').read_text())
    identity = json.loads((package/'package-identity.json').read_text())
    old = json.loads((ROOT/'docs/tasks/W011/verification/source-manifest.json').read_text())
    check(identity['status'] == 'passed' and identity['source_git_revision'] == source['source_git_revision'] == '7f7c1304bdafd941791421cef64864fb1616303c', 'before new reconstruction revision')
    check(source['W011_source_manifest_sha256'] == sha(ROOT/'docs/tasks/W011/verification/source-manifest.json'), 'before W011 upstream manifest hash')
    check(source['performance_frozen_identity_sha256'] == sha(A1/'performance/frozen-identity.json'), 'before measured source upstream hash')
    check(source['runtime_files'] == old['runtime_files'] and len(source['runtime_files']) == 100, 'before runtime100 exact W011')
    check(len(source['selected_files']) == 102, 'archive102 selected source files')
    with tarfile.open(package/'before-source.tar') as archive:
        files = {m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive if m.isfile()}
    check(files == source['selected_files'], 'actual archived source102 bytes')
    check(all(baseline['sources']['before'][name] == digest for name,digest in files.items()), 'archive source equals measured before')
    actual_packages = {}
    for kind in ('wheel','sdist'):
        row = identity[kind]
        artifact = package/'dist'/Path(row['path']).name
        check(artifact.stat().st_size == row['bytes'] and sha(artifact) == row['sha256'], 'actual before '+kind+' identity')
        if kind == 'wheel':
            with zipfile.ZipFile(artifact) as archive:
                runtime = {n.removeprefix('layauto_v2/'):hashlib.sha256(archive.read(n)).hexdigest()
                           for n in archive.namelist() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))}
        else:
            with tarfile.open(artifact) as archive:
                runtime = {'/'.join(Path(m.name).parts[2:]):hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                           for m in archive if m.isfile() and len(Path(m.name).parts)>2 and Path(m.name).parts[1]=='layauto_v2'
                           and (m.name.endswith('.py') or m.name.endswith('/py.typed'))}
        check(runtime == row['runtime_files'] == source['runtime_files'], 'all100 actual '+kind+' members equal source')
        actual_packages[kind] = {'sha256':row['sha256'],'runtime_files':len(runtime),'bytes':row['bytes']}
    for row in identity['commands']:
        check(row['exit_code'] == 0, 'before reconstruction command completed')
        for stream in ('stdout','stderr'):
            check(sha(package/row[stream]) == row[stream+'_sha256'], 'before reconstruction raw '+stream)
    check('New packages rebuilt' in identity['classification'] and 'not original W011' in identity['classification'], 'before package provenance accurately classified')
    result = {'status':'passed','checks':checks,'profile_receipt_sha256':sha(A1/'profile/receipt.json'),
              'profile_summary_sha256':sha(A1/'profile-summary.json'),'window_results':window_result,
              'all_runtime_function_count_keys_by_stage':all_runtime_counts,'before_actual_packages':actual_packages,
              'scope':'complete attribution and before-package evidence only; final engineering not yet complete'}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(checks)+' independent profile/before-package checks passed; no product sample rerun')
    print(json.dumps(window_result,indent=2))


if __name__ == '__main__':
    main()
