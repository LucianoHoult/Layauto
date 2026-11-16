"""Run W013 references and W014 cases serially, preserving original outputs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mismatch-dir', type=Path, default=Path('/workspace/work/w014-resource-inputs/extraction-mismatch'))
    parser.add_argument('--components', choices=('both', 'w013', 'w014'), default='both')
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Output must be new or empty; prior attempts are retained')
    out.mkdir(parents=True, exist_ok=True)
    source_probe = Path(__file__).with_name('resource_probe.py').resolve()
    probe = out / 'resource_probe.py'
    identity = out / 'source_identity.py'
    shutil.copyfile(source_probe, probe)
    shutil.copyfile(source_probe.with_name('source_identity.py'), identity)
    tool_hashes = {path.name: sha(path) for path in (probe, identity)}
    rows = []

    def run(name: str, arguments: list[str]) -> None:
        argv = [str(args.python), '-B', str(probe), '--root', str(root),
                '--mismatch-dir', str(args.mismatch_dir.resolve()), *arguments]
        overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root),
                     'MPLCONFIGDIR': '/workspace/work/w014-env/mplconfig'}
        started, tick = datetime.now(timezone.utc).isoformat(), time.monotonic()
        print('START ' + name, flush=True)
        with (out / (name + '.stdout.txt')).open('xb') as stdout, (out / (name + '.stderr.txt')).open('xb') as stderr:
            process = subprocess.run(argv, cwd=root, env=dict(os.environ, **overrides), stdout=stdout, stderr=stderr)
        row = {'argv': argv, 'cwd': str(root), 'environment_overrides': overrides,
               'started_at_utc': started, 'seconds': time.monotonic() - tick, 'returncode': process.returncode,
               'tool_hashes': tool_hashes, 'stdout_sha256': sha(out / (name + '.stdout.txt')),
               'stderr_sha256': sha(out / (name + '.stderr.txt'))}
        with (out / (name + '.command.json')).open('x') as stream:
            stream.write(json.dumps(row, indent=2) + '\n')
        rows.append(row)
        print('DONE ' + name + ' ' + str(process.returncode), flush=True)
        if process.returncode:
            raise RuntimeError('Checkpoint failed: ' + name)
        if {path.name: sha(path) for path in (probe, identity)} != tool_hashes:
            raise RuntimeError('Copied checkpoint tools changed while executing')

    run('prepare-fixed-mismatch', ['--prepare-fixed-mismatch', '--out', str(out / 'fixed-inputs.json')])
    components = ('w013', 'w014') if args.components == 'both' else (args.components,)
    for component in components:
        for case in CASES:
            name = component + '-' + case
            run(name, ['--component', component, '--case', case, '--out', str(out / (name + '.json'))])
    reports = {component: {case: json.loads((out / (component + '-' + case + '.json')).read_text())
                           for case in CASES} for component in components}
    source_ids = {report['source_id'] for cases in reports.values() for report in cases.values()}
    if len(source_ids) != 1:
        raise RuntimeError('Checkpoint cases used different complete source identities')
    comparison = {}
    if components == ('w013', 'w014'):
        for case in CASES:
            old, new = reports['w013'][case], reports['w014'][case]
            if old['capture_sources'] != new['capture_sources'] or old['retained_W010_wire_sha256'] != new['retained_W010_wire_sha256']:
                raise RuntimeError('Reference and W014 do not bind the same complete upstream inputs')
            old_seconds = sum(row['seconds'] for name, row in old['phases'].items() if name.startswith('W013'))
            new_seconds = sum(row['seconds'] for name, row in new['phases'].items() if name.startswith('W014'))
            comparison[case] = {'reference_component_seconds': old_seconds, 'new_component_seconds': new_seconds,
                                'component_seconds_ratio': new_seconds / old_seconds,
                                'wire_added_bytes': new['wire_bytes'] - old['wire_bytes'],
                                'wire_ratio': new['wire_bytes'] / old['wire_bytes'],
                                'peak_rss_ratio': new['process_peak_rss_kib_before_postmeasurement_analysis'] /
                                                  old['process_peak_rss_kib_before_postmeasurement_analysis'],
                                'same_complete_W010_wire': True}
    with (out / 'suite.json').open('x') as stream:
        stream.write(json.dumps({'classification': 'resource-measurement-not-PM-clearance',
                                 'source_id': next(iter(source_ids)), 'components': list(components),
                                 'cases': list(CASES), 'commands': rows, 'comparison': comparison}, indent=2) + '\n')


if __name__ == '__main__':
    main()
