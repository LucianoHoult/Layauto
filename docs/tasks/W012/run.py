"""Serial fresh-process launcher; preserve failures, raw output and RSS samples."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/workspace/Layauto')
OUT = ROOT / 'docs/tasks/W012'
PYTHON = '/workspace/.venvs/layauto/bin/python'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    assert json.loads((OUT/'selfcheck.json').read_text())['tool_sha256'] == sha(OUT/'probe.py')
    tools = {name: sha(OUT/name) for name in ('probe.py','run.py')}
    write(OUT/'tool-identity.json', tools)
    commands = []
    for mode in ('baseline','profile'):
        for case in ('normal-direct','normal-readback','extraction-mismatch'):
            assert tools == {name: sha(OUT/name) for name in tools}, 'tool changed during runs'
            prefix = OUT / (mode + '-' + case)
            assert not prefix.with_suffix('.command.json').exists(), 'do not overwrite old attempts'
            argv = [PYTHON, '-B', str(OUT/'probe.py'), '--case', case, '--mode', mode,
                    '--output', str(prefix.with_suffix('.json'))]
            row = {'argv': argv, 'cwd': str(ROOT), 'started_at_utc': datetime.now(timezone.utc).isoformat(),
                   'git_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                   'tools': tools, 'environment_override': {'PYTHONDONTWRITEBYTECODE': '1'}}
            print('START ' + mode + ' ' + case, flush=True)
            started = time.perf_counter()
            samples = []
            with prefix.with_suffix('.stdout.txt').open('wb') as stdout, prefix.with_suffix('.stderr.txt').open('wb') as stderr:
                proc = subprocess.Popen(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), stdout=stdout, stderr=stderr)
                while proc.poll() is None:
                    try:
                        fields = dict(line.split(':',1) for line in Path(f'/proc/{proc.pid}/status').read_text().splitlines() if ':' in line)
                        samples.append({'elapsed_seconds': time.perf_counter()-started,
                                        'VmRSS': fields.get('VmRSS','').strip(), 'VmHWM': fields.get('VmHWM','').strip(),
                                        'cgroup_memory_current': Path('/sys/fs/cgroup/memory.current').read_text().strip()})
                    except FileNotFoundError:
                        pass
                    time.sleep(2)
            row.update({'finished_at_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': time.perf_counter()-started,
                        'exit_code': proc.returncode, 'stdout_sha256': sha(prefix.with_suffix('.stdout.txt')),
                        'stderr_sha256': sha(prefix.with_suffix('.stderr.txt'))})
            write(prefix.with_suffix('.command.json'), row)
            write(prefix.with_suffix('.samples.json'), samples)
            commands.append(row)
            write(OUT/'commands.json', commands)
            print('DONE ' + mode + ' ' + case + ' exit=' + str(proc.returncode), flush=True)
            if proc.returncode:
                raise RuntimeError('retained failed attempt: ' + str(prefix))
    write(OUT/'measurement-receipt.json', {'status': 'passed', 'commands': commands, 'tools': tools,
          'fresh_process_per_path_per_mode': True, 'serial': True})


if __name__ == '__main__':
    main()
