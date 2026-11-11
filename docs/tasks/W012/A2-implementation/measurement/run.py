"""Fresh serial alternating A2 before/after samples; actual full wire comparison."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from common import CASES, dump_new, environment, identity, inputs, read_json, same_bytes, sha
from prepare import tools


def run(args):
    frozen = read_json(args.freeze)
    assert frozen['tools'] == tools(), 'measurement tools changed after freeze'
    assert frozen['environment'] == environment(), 'interpreter/dependencies/environment changed'
    assert frozen['inputs'] == inputs()
    for side, root in frozen['roots'].items():
        assert identity(Path(root)) == frozen['sources'][side], 'actual source/test/config changed'
    assert len(set(args.reps)) == len(args.reps) and all(rep in (1, 2, 3) for rep in args.reps)
    receipt_path = args.out / ('receipt-' + '-'.join(map(str, args.reps)) + '.json')
    assert not receipt_path.exists(), 'never overwrite a previous run receipt'
    planned = [(rep, case, side) for rep in args.reps for case in CASES for side in ('before', 'after')]
    for rep, case, side in planned:
        prefix = args.out / f'{side}-{case}-r{rep}'
        assert not list(args.out.glob(prefix.name + '.*')), 'prior attempt exists; do not silently resume/overwrite'
        assert not (args.wires / (prefix.name + '.bin')).exists(), 'prior wire exists'
    args.out.mkdir(parents=True, exist_ok=True)
    probe = Path(__file__).resolve().with_name('probe.py')
    rows = []
    for rep, case, side in planned:
        root = Path(frozen['roots'][side])
        assert identity(root) == frozen['sources'][side]
        assert tools() == frozen['tools'] and environment() == frozen['environment'] and inputs() == frozen['inputs']
        name = f'{side}-{case}-r{rep}'
        prefix = args.out / name
        wire = args.wires / (name + '.bin')
        argv = [sys.executable, '-B', str(probe), '--runtime-root', str(root), '--case', case,
                '--output', str(prefix.with_suffix('.json')), '--wire-output', str(wire)]
        row = {'argv': argv, 'cwd': frozen['fixed_input_root'],
               'started_at_utc': datetime.now(timezone.utc).isoformat(), 'side': side, 'case': case, 'rep': rep,
               'freeze_sha256': sha(args.freeze.read_bytes()), 'tools': tools(),
               'environment_override': {'PYTHONDONTWRITEBYTECODE': '1'}}
        dump_new(prefix.with_suffix('.started.json'), row)
        print('START ' + name, flush=True)
        started = time.perf_counter()
        samples = []
        with prefix.with_suffix('.stdout.txt').open('xb') as stdout, prefix.with_suffix('.stderr.txt').open('xb') as stderr:
            proc = subprocess.Popen(argv, cwd=frozen['fixed_input_root'],
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdout=stdout, stderr=stderr)
            while proc.poll() is None:
                try:
                    fields = dict(line.split(':', 1) for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines() if ':' in line)
                    samples.append({'elapsed_seconds': time.perf_counter() - started,
                                    'VmRSS': fields.get('VmRSS', '').strip(), 'VmHWM': fields.get('VmHWM', '').strip()})
                except FileNotFoundError:
                    pass
                time.sleep(2)
        row.update({'finished_at_utc': datetime.now(timezone.utc).isoformat(),
                    'elapsed_seconds': time.perf_counter() - started, 'exit_code': proc.returncode,
                    'stdout_sha256': sha(prefix.with_suffix('.stdout.txt').read_bytes()),
                    'stderr_sha256': sha(prefix.with_suffix('.stderr.txt').read_bytes())})
        dump_new(prefix.with_suffix('.command.json'), row)
        dump_new(prefix.with_suffix('.samples.json'), samples)
        assert proc.returncode == 0, 'failed actual sample preserved: ' + name
        result = read_json(prefix.with_suffix('.json'))
        assert result['source_identity'] == frozen['sources'][side]
        assert result['environment'] == frozen['environment']
        assert result['input_identity'] == frozen['inputs'] and result['tool_sha256'] == frozen['tools']['probe.py']
        reference = args.wires / f'before-{case}-r1.bin'
        count = same_bytes(reference, wire)
        assert count == result['wire_bytes']
        if side == 'after':
            before = read_json(args.out / f'before-{case}-r{rep}.json')
            for key in ('capture_sources', 'gc_enabled', 'gc_threshold', 'result', 'wire_sha256', 'wire_bytes',
                        'sources_and_target', 'stored_refs', 'input_site', 'public_roundtrip_equal',
                        'readback_unsealed_checkpoint_unchanged_no_terminal'):
                assert result[key] == before[key], 'before/after invariant differs: ' + key
        comparison = {'reference': str(reference), 'candidate': str(wire), 'bytes': count, 'equal': True,
                      'reference_sha256': sha(reference.read_bytes()), 'candidate_sha256': sha(wire.read_bytes()),
                      'comparison_outside_product_timers': True}
        dump_new(prefix.with_suffix('.comparison.json'), comparison)
        rows.append({**row, 'actual_complete_wire_byte_comparison': comparison})
        print('DONE ' + name, flush=True)
    dump_new(receipt_path, {'schema': 'w012-a2-implementation-performance/1', 'status': 'passed',
                           'reps': args.reps, 'commands': rows, 'fresh_processes': True, 'serial': True,
                           'alternating': 'before/after per case per rep', 'full_wire_byte_comparison': True,
                           'wire_reduction': 0, 'freeze_sha256': sha(args.freeze.read_bytes())})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--wires', type=Path, required=True)
    parser.add_argument('--reps', nargs='+', type=int, required=True)
    run(parser.parse_args())
