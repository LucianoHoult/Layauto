"""A1 serial fresh-process paired baselines; profiles are a separate stage."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012/A1'
PROBE = OUT/'probe.py'
PYTHON = '/workspace/.venvs/layauto/bin/python'
RUNTIMES = {'before':Path('/workspace/w012-a1-before'), 'after':ROOT}
WORK = Path('/workspace/w012-a1-performance')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data,indent=2)+'\n')


def identity(root):
    old = json.loads((ROOT/'docs/tasks/W011/verification/source-manifest.json').read_text())
    names = set(old['files'])
    names.update(str(p.relative_to(root)) for p in (root/'tests').rglob('*.py'))
    return {name:sha(root/name) for name in sorted(names)}


def same_bytes(left, right):
    count = 0
    with left.open('rb') as a, right.open('rb') as b:
        while True:
            x,y = a.read(1024*1024),b.read(1024*1024)
            assert x == y, 'actual complete wire bytes differ'
            count += len(x)
            if not x:
                return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=('baseline','profile'),required=True)
    parser.add_argument('--selfcheck',action='store_true')
    args = parser.parse_args()
    assert json.loads((OUT/'selfcheck.json').read_text())['tool_sha256'] == sha(PROBE)
    directory = OUT/('performance' if args.stage == 'baseline' else 'profile')
    sources = {side:identity(path) for side,path in RUNTIMES.items()}
    tools = {name:sha(OUT/name) for name in ('probe.py','run_performance.py')}
    differences = sorted(name for name in sources['before'].keys()|sources['after'].keys()
                         if sources['before'].get(name) != sources['after'].get(name))
    assert differences == ['layauto_v2/domain/codec.py','tests/contracts/test_w012_hex_validation.py']
    if args.selfcheck:
        with tempfile.TemporaryDirectory(prefix='w012-a1-selfcheck-') as temp:
            a,b = Path(temp)/'a',Path(temp)/'b'
            a.write_bytes(b'\x00\xffsame');b.write_bytes(b'\x00\xffsame')
            assert same_bytes(a,b) == 6
            b.write_bytes(b'\x00\xffother')
            try:
                same_bytes(a,b)
            except AssertionError:
                pass
            else:
                raise AssertionError('byte mismatch not detected')
        dump(OUT/'runner-selfcheck.json',{'status':'passed','tools':tools,'differences':differences,
             'checks':['only authorized product/test differences','actual byte comparison detects changes',
                       'original probe selfcheck identity matches']})
        print('A1 serial runner lightweight selfcheck passed')
        return
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError('Stage contains prior evidence; do not overwrite or silently resume it')
    directory.mkdir(exist_ok=True)
    dump(directory/'frozen-identity.json',{'sources':sources,'tools':tools,'differences':differences,
         'python':PYTHON,'input_root':str(ROOT),'mismatch':'/workspace/w012-inputs/extraction-mismatch'})
    rows = []
    reps = range(1,4) if args.stage == 'baseline' else (1,)
    cases = ('normal-direct','normal-readback','extraction-mismatch') if args.stage == 'baseline' else ('normal-readback',)
    for rep in reps:
        for case in cases:
            for side,runtime in RUNTIMES.items():
                assert identity(runtime) == sources[side], 'source changed after performance freeze'
                assert {name:sha(OUT/name) for name in tools} == tools
                name = f'{side}-{case}-r{rep}'
                prefix = directory/name
                assert not prefix.with_suffix('.command.json').exists(), 'never overwrite an attempt'
                wire = WORK/'wires'/args.stage/(name+'.bin')
                assert not wire.exists(), 'never overwrite a prior complete wire artifact'
                argv = [PYTHON,'-B',str(PROBE),'--runtime-root',str(runtime),'--input-root',str(ROOT),
                        '--case',case,'--mode',args.stage,'--output',str(prefix.with_suffix('.json')),
                        '--wire-output',str(wire)]
                start = time.perf_counter()
                row = {'argv':argv,'cwd':str(ROOT),'started_at_utc':datetime.now(timezone.utc).isoformat(),
                       'side':side,'case':case,'rep':rep,'tools':tools,'environment_override':{'PYTHONDONTWRITEBYTECODE':'1'}}
                print('START '+name+' '+args.stage,flush=True)
                samples = []
                with prefix.with_suffix('.stdout.txt').open('wb') as stdout,prefix.with_suffix('.stderr.txt').open('wb') as stderr:
                    proc = subprocess.Popen(argv,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
                    while proc.poll() is None:
                        try:
                            fields = dict(line.split(':',1) for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines() if ':' in line)
                            samples.append({'elapsed_seconds':time.perf_counter()-start,
                                            'VmRSS':fields.get('VmRSS','').strip(),'VmHWM':fields.get('VmHWM','').strip()})
                        except FileNotFoundError:
                            pass
                        time.sleep(2)
                row.update({'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-start,
                            'exit_code':proc.returncode,'stdout_sha256':sha(prefix.with_suffix('.stdout.txt')),
                            'stderr_sha256':sha(prefix.with_suffix('.stderr.txt'))})
                dump(prefix.with_suffix('.command.json'),row)
                dump(prefix.with_suffix('.samples.json'),samples)
                rows.append(row)
                dump(directory/'commands.json',rows)
                assert proc.returncode == 0, 'failed actual sample preserved: '+name
                result = json.loads(prefix.with_suffix('.json').read_text())
                assert result['source_identity']['files'] == sources[side]
                assert result['tool_sha256'] == tools['probe.py']
                reference = WORK/'wires'/'baseline'/f'before-{case}-r1.bin'
                count = same_bytes(reference,wire)
                assert count == result['wire_bytes']
                row['actual_complete_wire_byte_comparison'] = {'reference':str(reference),'bytes':count,'equal':True}
                if side == 'after':
                    before = json.loads((directory/f'before-{case}-r{rep}.json').read_text())
                    assert result['capture_sources'] == before['capture_sources']
                    assert result['gc_enabled'] == before['gc_enabled'] and result['gc_threshold'] == before['gc_threshold']
                    assert result['result'] == before['result'] and result['wire_sha256'] == before['wire_sha256']
                dump(prefix.with_suffix('.command.json'),row)
                print('DONE '+name,flush=True)
    dump(directory/'receipt.json',{'status':'passed','stage':args.stage,'sources':sources,'tools':tools,'commands':rows,
                                 'fresh_processes':True,'serial':True,'full_wire_byte_comparison':True})


if __name__ == '__main__':
    main()
