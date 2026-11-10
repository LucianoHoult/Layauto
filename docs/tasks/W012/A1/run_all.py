"""Run frozen paired performance, attribution, then final engineering checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012/A1'
LOGS = OUT/'run-final-01'


def main():
    if LOGS.exists() and any(LOGS.iterdir()):
        raise RuntimeError('Prior orchestration output exists; preserve the complete attempt')
    LOGS.mkdir(exist_ok=True)
    commands = []
    stages = (
        ('performance', ['/workspace/.venvs/layauto/bin/python','-B',str(OUT/'run_performance.py'),'--stage','baseline']),
        ('profile', ['/workspace/.venvs/layauto/bin/python','-B',str(OUT/'run_performance.py'),'--stage','profile']),
        ('final-verification', [sys.executable,'-B',str(OUT/'verification-tools/prepare_final.py'),
            '--root',str(ROOT),'--out',str(OUT/'verification'),'--work','/workspace/w012-a1-final',
            '--smoke',str(OUT/'verification-tools/installed_smoke.py'),
            '--python310','/workspace/w012-a1-env/dev310/bin/python',
            '--python312','/workspace/w012-a1-env/dev312/bin/python','--expected-tests','1656',
            '--baseline-test-count','1605','--matrix-workers','2',
            '--resource-gate',str(ROOT/'docs/tasks/W011/verification/w011_resource_gate.py')]),
    )
    for name,argv in stages:
        started = time.perf_counter()
        row = {'argv':argv,'cwd':str(ROOT),'started_at_utc':datetime.now(timezone.utc).isoformat(),
               'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
        print('START '+name,flush=True)
        with (LOGS/(name+'.stdout.txt')).open('wb') as stdout,(LOGS/(name+'.stderr.txt')).open('wb') as stderr:
            result = subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
        row.update({'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,
                    'exit_code':result.returncode,
                    'stdout_sha256':hashlib.sha256((LOGS/(name+'.stdout.txt')).read_bytes()).hexdigest(),
                    'stderr_sha256':hashlib.sha256((LOGS/(name+'.stderr.txt')).read_bytes()).hexdigest()})
        commands.append(row)
        (LOGS/(name+'.command.json')).write_text(json.dumps(row,indent=2)+'\n')
        (LOGS/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
        assert result.returncode == 0, 'Stage failed, original outputs preserved: '+name
        print('DONE '+name,flush=True)


if __name__ == '__main__':
    main()
