"""Capture the final serial resource launcher after the full matrix receipt."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
work=Path(__file__).resolve().parent
plan=json.loads((work/'resources-launch-plan.json').read_text());root=Path(plan['cwd'])
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
for item in plan['scripts']:assert sha(item['path'])==item['sha256'],item['path']
verified=json.loads((root/'docs/tasks/W011/verification/receipt.json').read_text())
assert verified['status']=='passed' and verified['actual_test_counts']=={'310':1605,'312':1605}
for name in ('resources-launch-start.json','resources-launch-receipt.json','resources-runner.stdout.txt','resources-runner.stderr.txt'):assert not (work/name).exists(),name
started_at=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
with (work/'resources-runner.stdout.txt').open('wb') as stdout,(work/'resources-runner.stderr.txt').open('wb') as stderr:
 process=subprocess.Popen(plan['command'],cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
 launch={'command':plan['command'],'cwd':str(root),'tested_source_commit':plan['expected_source_commit'],'started_at_utc':started_at,'pid':process.pid,'scripts':plan['scripts'],'environment_overrides':{'PYTHONDONTWRITEBYTECODE':'1'}}
 (work/'resources-launch-start.json').write_text(json.dumps(launch,indent=2)+'\n')
 code=process.wait()
receipt={**launch,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,'exit_code':code,'stdout_sha256':sha(work/'resources-runner.stdout.txt'),'stderr_sha256':sha(work/'resources-runner.stderr.txt')}
(work/'resources-launch-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True);sys.exit(code)
