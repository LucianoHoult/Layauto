"""Recompute A1 finite paired observations; never run product code here."""
import json
from pathlib import Path
from statistics import median

OUT = Path(__file__).resolve().parent


def main():
    summary = {}
    for case in ('normal-direct','normal-readback','extraction-mismatch'):
        data = {}
        for side in ('before','after'):
            rows = [json.loads((OUT/'performance'/f'{side}-{case}-r{rep}.json').read_text()) for rep in range(1,4)]
            commands = [json.loads((OUT/'performance'/f'{side}-{case}-r{rep}.command.json').read_text()) for rep in range(1,4)]
            assert all(r['wire_sha256'] == rows[0]['wire_sha256'] and r['wire_bytes'] == rows[0]['wire_bytes']
                       and r['capture_sources'] == rows[0]['capture_sources'] for r in rows)
            assert all(r['actual_complete_wire_byte_comparison']['equal'] for r in commands)
            data[side] = {'samples':[{'rep':i+1,'stage_seconds':r['wall_seconds'],
                                     'total_stage_seconds':sum(r['wall_seconds'].values()),
                                     'peak_rss_kib':r['process_peak_rss_kib']} for i,r in enumerate(rows)],
                          'median_total_stage_seconds':median(sum(r['wall_seconds'].values()) for r in rows),
                          'median_stage_seconds':{k:median(r['wall_seconds'][k] for r in rows) for k in rows[0]['wall_seconds']},
                          'all_peak_rss_kib':[r['process_peak_rss_kib'] for r in rows],
                          'median_peak_rss_kib':median(r['process_peak_rss_kib'] for r in rows),
                          'wire_bytes':rows[0]['wire_bytes'],'wire_sha256':rows[0]['wire_sha256']}
        assert data['before']['wire_sha256'] == data['after']['wire_sha256']
        data['observed_time_reduction_fraction'] = 1-data['after']['median_total_stage_seconds']/data['before']['median_total_stage_seconds']
        data['observed_median_peak_reduction_fraction'] = 1-data['after']['median_peak_rss_kib']/data['before']['median_peak_rss_kib']
        summary[case] = data
    (OUT/'performance-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for case,data in summary.items():
        print(case,'seconds',data['before']['median_total_stage_seconds'],'->',data['after']['median_total_stage_seconds'],
              'peaks',data['before']['all_peak_rss_kib'],'->',data['after']['all_peak_rss_kib'],
              'wire',data['after']['wire_bytes'],data['after']['wire_sha256'])


if __name__ == '__main__':
    main()
