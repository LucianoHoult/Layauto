"""Render existing resource measurements; never executes product code."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Preserve an existing summary; choose a new output')
    evidence = args.evidence.resolve()
    suite_path = evidence / 'suite.json'
    suite = json.loads(suite_path.read_text())
    lines = ['# W014 resource measurements', '',
             'Source identity: `' + suite['source_id'] + '`.', '',
             'These are fresh-process samples. They do not establish a stable performance improvement or PM clearance.', '',
             '| Component | Case | Build / encode / decode (s) | Wire (bytes) | Compact envelope (bytes) | Peak RSS (MiB) | W010 decode calls |',
             '| --- | --- | --- | ---: | ---: | ---: | --- |']
    for component in suite['components']:
        for case in suite['cases']:
            report = json.loads((evidence / (component + '-' + case + '.json')).read_text())
            prefix = component.upper()
            seconds = ' / '.join(f"{report['phases'][prefix + '_' + phase]['seconds']:.3f}" for phase in ('build', 'encode', 'decode'))
            calls = ' / '.join(str(report['authentication_calls_by_phase'][prefix + '_' + phase]) for phase in ('build', 'encode', 'decode'))
            lines.append('| ' + ' | '.join((component, case, seconds, str(report['wire_bytes']),
                         str(report['compact_envelope_bytes_without_input_field']),
                         f"{report['process_peak_rss_kib_before_postmeasurement_analysis'] / 1024:.2f}", calls)) + ' |')
    if suite['comparison']:
        lines.extend(['', '| Case | Component elapsed ratio | Wire ratio | New wire bytes | Peak ratio |',
                      '| --- | ---: | ---: | ---: | ---: |'])
        for case, row in suite['comparison'].items():
            lines.append(f"| {case} | {row['component_seconds_ratio']:.4f} | {row['wire_ratio']:.6f} | {row['wire_added_bytes']} | {row['peak_rss_ratio']:.4f} |")
    lines.extend(['', 'Peak is fixed before packet decomposition and source bookkeeping. Inclusive nested call timers must not be summed as disjoint work.', '',
                  'Original suite SHA-256: `' + hashlib.sha256(suite_path.read_bytes()).hexdigest() + '`.', ''])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        stream.write('\n'.join(lines))


if __name__ == '__main__':
    main()
