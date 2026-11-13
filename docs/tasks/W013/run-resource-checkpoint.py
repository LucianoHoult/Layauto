"""Run the fixed W013 cases serially in fresh processes, retaining every attempt."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path('/workspace/Layauto')
    args.out.mkdir(parents=True, exist_ok=True)
    probe = args.out / 'resource-probe.py'
    if not probe.exists():
        shutil.copyfile(root / 'docs/tasks/W013/resource-probe.py', probe)
    probe_sha = hashlib.sha256(probe.read_bytes()).hexdigest()
    commands = []
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        output = args.out / (case + '.json')
        if output.exists():
            raise RuntimeError('Existing result must be preserved: ' + str(output))
        argv = [str(args.python), '-B', str(probe), '--case', case, '--out', str(output)]
        overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root)}
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic()
        print('START ' + case, flush=True)
        with (args.out / (case + '.stdout.txt')).open('xb') as stdout, (args.out / (case + '.stderr.txt')).open('xb') as stderr:
            completed = subprocess.run(argv, cwd=root, env=dict(os.environ, **overrides), stdout=stdout, stderr=stderr)
        row = {'argv': argv, 'cwd': str(root), 'environment_overrides': overrides,
               'utc_start': started, 'seconds': time.monotonic() - tick,
               'returncode': completed.returncode, 'probe_sha256': probe_sha,
               'stdout_sha256': hashlib.sha256((args.out / (case + '.stdout.txt')).read_bytes()).hexdigest(),
               'stderr_sha256': hashlib.sha256((args.out / (case + '.stderr.txt')).read_bytes()).hexdigest()}
        with (args.out / (case + '.command.json')).open('x') as stream:
            stream.write(json.dumps(row, indent=2) + '\n')
        commands.append(row)
        print('DONE ' + case + ' ' + str(completed.returncode), flush=True)
        if completed.returncode:
            raise RuntimeError('Resource checkpoint failed: ' + case)
        if hashlib.sha256(probe.read_bytes()).hexdigest() != probe_sha:
            raise RuntimeError('Probe changed while running')
    results = [json.loads((args.out / (case + '.json')).read_text())
               for case in ('normal-direct', 'normal-readback', 'extraction-mismatch')]
    if len({item['source_id'] for item in results}) != 1:
        raise RuntimeError('Resource cases used different actual source identities')
    with (args.out / 'suite.json').open('x') as stream:
        stream.write(json.dumps({'source_id': results[0]['source_id'], 'commands': commands,
                                 'cases': [item['case'] for item in results]}, indent=2) + '\n')


if __name__ == '__main__':
    main()
