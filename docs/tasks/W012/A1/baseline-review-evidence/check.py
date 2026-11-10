"""Independent completed-baseline identity/statistics/streamed-byte review only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path('/workspace/Layauto')
A1 = ROOT/'docs/tasks/W012/A1'
OUT = Path(__file__).resolve().parent
checks = 0


def check(condition, message):
    global checks
    assert condition, message
    checks += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_and_digest(reference, actual):
    size = 0
    digest = hashlib.sha256()
    with reference.open('rb') as left, actual.open('rb') as right:
        while True:
            a,b = left.read(1024*1024),right.read(1024*1024)
            check(a == b, 'actual complete wire chunk equal: '+str(actual))
            if not b:
                break
            size += len(b)
            digest.update(b)
    return size,digest.hexdigest()


def main():
    receipt = json.loads((A1/'performance/receipt.json').read_text())
    frozen = json.loads((A1/'performance/frozen-identity.json').read_text())
    summary = json.loads((A1/'performance-summary.json').read_text())
    check(receipt['status'] == 'passed' and receipt['stage'] == 'baseline', 'baseline complete')
    check(len(receipt['commands']) == 18 and receipt['fresh_processes'] and receipt['serial'], '18 fresh serial samples')
    check(receipt['full_wire_byte_comparison'], 'recorded actual byte comparison')
    check(receipt['sources'] == frozen['sources'] and receipt['tools'] == frozen['tools'], 'receipt freeze identity')
    before_root,after_root = Path('/workspace/w012-a1-before'),ROOT
    for side,root in (('before',before_root),('after',after_root)):
        for name,digest in frozen['sources'][side].items():
            check(sha(root/name) == digest, 'frozen source '+side+'/'+name)
    for name,digest in frozen['tools'].items():
        check(sha(A1/name) == digest, 'frozen tool '+name)
    differences = sorted(n for n in frozen['sources']['before'].keys() | frozen['sources']['after'].keys()
                         if frozen['sources']['before'].get(n) != frozen['sources']['after'].get(n))
    check(differences == ['layauto_v2/domain/codec.py','tests/contracts/test_w012_hex_validation.py'], 'only authorized code/test differences')
    old = json.loads((ROOT/'docs/tasks/W011/verification/source-manifest.json').read_text())
    check(all(frozen['sources']['before'][n] == v for n,v in old['files'].items()), 'before exact W011 source identity')
    check(frozen['input_root'] == str(ROOT) and frozen['mismatch'] == '/workspace/w012-inputs/extraction-mismatch', 'fixed input roots')
    check(frozen['python'] == '/workspace/.venvs/layauto/bin/python', 'one actual interpreter')
    old_inputs = json.loads((ROOT/'docs/tasks/W012/preflight.json').read_text())['inputs']
    new_inputs = json.loads((A1/'preflight.json').read_text())['inputs']
    check(new_inputs == old_inputs, 'original35 fixed input manifest retained')
    for row in new_inputs:
        check(Path(row['target']).read_bytes() == Path(row['origin']).read_bytes(), 'input origin bytes '+row['target'])
        check(sha(Path(row['target'])) == row['sha256'], 'input actual hash '+row['target'])
    expected_order = [(rep,case,side) for rep in (1,2,3)
                      for case in ('normal-direct','normal-readback','extraction-mismatch') for side in ('before','after')]
    check([(r['rep'],r['case'],r['side']) for r in receipt['commands']] == expected_order, 'paired order')
    samples = {}
    artifacts = {}
    previous = None
    for row in receipt['commands']:
        key = (row['rep'],row['case'],row['side'])
        prefix = A1/'performance'/f'{row["side"]}-{row["case"]}-r{row["rep"]}'
        sample = json.loads(prefix.with_suffix('.json').read_text())
        check(json.loads(prefix.with_suffix('.command.json').read_text()) == row, 'complete per-case command equals receipt')
        check(row['exit_code'] == 0, 'actual sample exit0')
        start,end = datetime.fromisoformat(row['started_at_utc']),datetime.fromisoformat(row['finished_at_utc'])
        check(start <= end, 'sample chronology')
        if previous is not None:
            check(previous <= start, 'no sample overlaps')
        previous = end
        check(row['argv'][0] == frozen['python'] and row['argv'][1] == '-B', 'same interpreter flags')
        check(row['argv'][row['argv'].index('--mode')+1] == 'baseline', 'no profile mode')
        expected_root = before_root if row['side'] == 'before' else ROOT
        check(row['argv'][row['argv'].index('--runtime-root')+1] == str(expected_root), 'explicit runtime root')
        check(sample['runtime_root'] == str(expected_root) and sample['package'] == str(expected_root/'layauto_v2/__init__.py'), 'actual package import identity')
        check(sample['mode'] == 'baseline' and 'matcher_windows' not in sample, 'uninstrumented data shape')
        check(sample['source_identity']['files'] == frozen['sources'][row['side']], 'per-sample source identity')
        check(len(sample['source_identity']['runtime_files']) == 100, 'runtime100 retained')
        check(sample['tool_sha256'] == frozen['tools']['probe.py'] == row['tools']['probe.py'], 'per-sample tool identity')
        for stream in ('stdout','stderr'):
            check(sha(prefix.with_suffix('.'+stream+'.txt')) == row[stream+'_sha256'], 'raw '+stream+' identity')
        last = json.loads(prefix.with_suffix('.stdout.txt').read_text().splitlines()[-1])
        check(all(last[n] == sample[n] for n in ('case','mode','wall_seconds','wire_bytes','wire_sha256','process_peak_rss_kib')), 'stdout actual result')
        check(len(sample['capture_sources']) == 31 and sum(s['bytes'] for s in sample['capture_sources']) == 280706, 'complete acquisition inventory')
        check(sample['gc_enabled'] and sample['gc_threshold'] == [700,10,10], 'fixed GC policy')
        check(sample['public_roundtrip_equal'], 'public complete roundtrip')
        facts = sample['result']
        mismatch = row['case'] == 'extraction-mismatch'
        check(facts['counts'] == {'MN0':4 if mismatch else 5,'MP0':7}, 'actual counts')
        check(facts['difference_count'] == (1 if mismatch else 0), 'source difference count')
        check(facts['comparison_status'] == ('mismatch' if mismatch else 'equal'), 'source comparison')
        check(facts['complete_evaluations'] == 36 and facts['local_nodes'] == 14 and facts['local_edges'] == 8
              and facts['local_components'] == 6 and facts['T05_audits'] == 16 and facts['T05_status'] == 'pass'
              and facts['body_kind'] == 'body', 'retained graph T05 body facts')
        check(len(facts['crossings']['MN0']) == (4 if mismatch else 5) and len(facts['crossings']['MP0']) == 7, 'complete crossing cardinality')
        if row['case'] == 'normal-readback':
            check(sample['readback_unsealed_checkpoint_unchanged_no_terminal'], 'readback attempt/checkpoint/terminal')
        site = Path('/workspace/w012-inputs/extraction-mismatch/site_config.yaml') if mismatch else ROOT/'tests/fixtures/w003_m1/site_config.yaml'
        check(sample['input_site'] == str(site), 'fixed actual input URI')
        reference = Path('/workspace/w012-a1-performance/wires/baseline')/f'before-{row["case"]}-r1.bin'
        wire = Path(sample['wire_artifact'])
        size,digest = compare_and_digest(reference,wire)
        check(size == sample['wire_bytes'] and digest == sample['wire_sha256'], 'stored actual wire bytes/hash')
        check(row['actual_complete_wire_byte_comparison'] == {'reference':str(reference),'bytes':size,'equal':True}, 'recorded actual comparison')
        samples[key] = sample
        artifacts[str(prefix.relative_to(A1))+'.json'] = sha(prefix.with_suffix('.json'))
    recomputed = {}
    for case,reported in summary.items():
        data = {}
        for side in ('before','after'):
            rows = [samples[(rep,case,side)] for rep in (1,2,3)]
            totals = [sum(r['wall_seconds'].values()) for r in rows]
            peaks = [r['process_peak_rss_kib'] for r in rows]
            med_total,med_peak = statistics.median(totals),statistics.median(peaks)
            check(reported[side]['median_total_stage_seconds'] == med_total, 'total median '+case+side)
            check(reported[side]['all_peak_rss_kib'] == peaks and reported[side]['median_peak_rss_kib'] == med_peak, 'all peaks '+case+side)
            for stage in rows[0]['wall_seconds']:
                check(reported[side]['median_stage_seconds'][stage] == statistics.median(r['wall_seconds'][stage] for r in rows), 'stage median '+case+side+stage)
            for rep,sample in zip((1,2,3),rows):
                check(reported[side]['samples'][rep-1] == {'rep':rep,'stage_seconds':sample['wall_seconds'],
                      'total_stage_seconds':totals[rep-1],'peak_rss_kib':peaks[rep-1]}, 'reported raw sample')
                before = samples[(rep,case,'before')]
                check(sample['capture_sources'] == before['capture_sources'] and sample['result'] == before['result'], 'paired captures/complete facts')
                check(sample['wire_bytes'] == before['wire_bytes'] and sample['wire_sha256'] == before['wire_sha256'], 'paired full wire identity')
                check((sample['python'],sample['executable'],sample['platform']) == (before['python'],before['executable'],before['platform']), 'paired execution environment')
            data[side] = {'total_median':med_total,'all_peaks_kib':peaks,'peak_median_kib':med_peak}
        reduction = 1-data['after']['total_median']/data['before']['total_median']
        peak_reduction = 1-data['after']['peak_median_kib']/data['before']['peak_median_kib']
        check(reported['observed_time_reduction_fraction'] == reduction, 'reported time reduction')
        check(reported['observed_median_peak_reduction_fraction'] == peak_reduction, 'reported peak reduction')
        regressions = {stage:(reported['before']['median_stage_seconds'][stage],after,
                              after/reported['before']['median_stage_seconds'][stage]-1)
                       for stage,after in reported['after']['median_stage_seconds'].items()
                       if after > reported['before']['median_stage_seconds'][stage]}
        recomputed[case] = {**data,'time_reduction_fraction':reduction,'peak_reduction_fraction':peak_reduction,
                            'median_stage_regressions':regressions}
    (OUT/'result.json').write_text(json.dumps({'status':'passed','checks':checks,'baseline_artifact_identities':artifacts,
        'receipt_sha256':sha(A1/'performance/receipt.json'),'summary_sha256':sha(A1/'performance-summary.json'),
        'recomputed':recomputed,'scope':'completed18 baseline samples only; no profile or final matrix claim'},indent=2)+'\n')
    print(str(checks)+' independent completed-baseline checks passed; actual stored wire chunks compared')
    print(json.dumps(recomputed,indent=2))


if __name__ == '__main__':
    main()
