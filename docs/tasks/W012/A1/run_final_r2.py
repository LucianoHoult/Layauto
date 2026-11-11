"""Fresh complete engineering retry after environment interruption; retain telemetry."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012/A1'


def main():
    prefix = OUT/'final-r2-runner'
    if any(OUT.glob('final-r2-runner.*')):
        raise RuntimeError('Prior retry output exists; never overwrite an attempt')
    argv = [sys.executable,'-B',str(OUT/'verification-tools/prepare_final.py'),
            '--root',str(ROOT),'--out',str(OUT/'verification-r2'),'--work','/workspace/w012-a1-final-r2',
            '--smoke',str(OUT/'verification-tools/installed_smoke.py'),
            '--python310','/workspace/w012-a1-env/dev310/bin/python',
            '--python312','/workspace/w012-a1-env/dev312/bin/python','--expected-tests','1656',
            '--baseline-test-count','1605','--matrix-workers','2','--allow-parallel-without-gate']
    start = time.perf_counter()
    row = {'argv':argv,'cwd':str(ROOT),'started_at_utc':datetime.now(timezone.utc).isoformat(),
           'source_commit':'ca1f810c3c97376f71089d8b4054760ff198012f',
           'runner_sha256':hashlib.sha256((OUT/'verification-tools/prepare_final.py').read_bytes()).hexdigest(),
           'launch_status':'started; completed status is recorded only after process exit'}
    prefix.with_suffix('.command.json').write_text(json.dumps(row,indent=2)+'\n')
    with prefix.with_suffix('.stdout.txt').open('wb') as stdout,prefix.with_suffix('.stderr.txt').open('wb') as stderr, prefix.with_suffix('.samples.jsonl').open('w') as samples:
        proc = subprocess.Popen(argv,cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
        while proc.poll() is None:
            members = []
            for path in Path('/proc').iterdir():
                if not path.name.isdigit():
                    continue
                try:
                    stat = (path/'stat').read_text().rsplit(') ',1)[1].split()
                    if int(stat[2]) != proc.pid:
                        continue
                    status = dict(line.split(':',1) for line in (path/'status').read_text().splitlines() if ':' in line)
                    members.append({'pid':int(path.name),'rss_kib':int(status.get('VmRSS','0 kB').split()[0]),
                                    'name':status.get('Name','').strip()})
                except (FileNotFoundError,ProcessLookupError):
                    continue
            samples.write(json.dumps({'elapsed_seconds':time.perf_counter()-start,'members':members,
                'cgroup_memory_current_bytes':int(Path('/sys/fs/cgroup/memory.current').read_text())})+'\n')
            samples.flush()
            time.sleep(2)
    row.update({'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-start,
                'exit_code':proc.returncode,'launch_status':'completed',
                'stdout_sha256':hashlib.sha256(prefix.with_suffix('.stdout.txt').read_bytes()).hexdigest(),
                'stderr_sha256':hashlib.sha256(prefix.with_suffix('.stderr.txt').read_bytes()).hexdigest()})
    prefix.with_suffix('.command.json').write_text(json.dumps(row,indent=2)+'\n')
    assert proc.returncode == 0, 'Engineering retry failed; all original outputs retained'


if __name__ == '__main__':
    main()
