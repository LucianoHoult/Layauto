"""Compare like-for-like attribution runs, separately from baseline statistics."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def main():
    receipts = {side:json.loads((OUT/'profile'/f'{side}-normal-readback-r1.json').read_text())
                for side in ('before','after')}
    profiles = {side:json.loads((OUT/'profile'/f'{side}-normal-readback-r1.profile.json').read_text())
                for side in ('before','after')}
    assert receipts['before']['wire_sha256'] == receipts['after']['wire_sha256']
    calls = {}
    for phase in profiles['before']:
        counts = {}
        for side in ('before','after'):
            base = receipts[side]['runtime_root']+'/'
            counts[side] = {r['file'].removeprefix(base)+':'+str(r['line'])+':'+r['function']:r['calls']
                            for r in profiles[side][phase]['functions']
                            if r['file'].startswith(base+'layauto_v2/') and r['function'] in
                            ('__init__','__post_init__','_require_input','_evaluate','_analyze','normalize','encode_record','decode_record')}
        assert counts['before'] == counts['after'], ('constructor/authentication calls changed',phase)
        calls[phase] = counts['after']
    windows = {}
    for side,r in receipts.items():
        events = r['matcher_windows']
        largest = max(events,key=lambda e:e['hex_characters'])
        windows[side] = {'events':len(events),'large_string_lengths':[e['hex_characters'] for e in events],
                         'peak_refreshes':[e for e in events if e['after']['hwm_kib']>e['before']['hwm_kib']],
                         'largest_input_window':largest,'process_peak_rss_kib':r['process_peak_rss_kib'],
                         'sum_observed_matcher_seconds':sum(e['matcher_seconds'] for e in events)}
    assert windows['before']['large_string_lengths'] == windows['after']['large_string_lengths']
    (OUT/'profile-summary.json').write_text(json.dumps({'status':'passed','constructor_authentication_call_counts_equal':True,
        'calls':calls,'matcher_windows':windows,'scope':'Profile/observer timings are attribution only, not uninstrumented performance or net allocations'},indent=2)+'\n')
    print('Constructor/authentication counts equal in all phases; actual hex window lengths equal')
    for side,row in windows.items():
        print(side,row['events'],'refreshes',len(row['peak_refreshes']),'peak',row['process_peak_rss_kib'],
              'largest',row['largest_input_window'])


if __name__ == '__main__':
    main()
