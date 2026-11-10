"""Launch the exact reviewed engineering plan and retain original outer output."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,subprocess,sys,time
work=Path(__file__).resolve().parent
plan=json.loads((work/'final-launch-plan.json').read_text())
root=Path(plan['cwd'])
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head==plan['expected_source_commit'],(head,plan['expected_source_commit'])
assert not subprocess.check_output(['git','status','--short','--','layauto_v2','tests','pyproject.toml','README.md'],cwd=root,text=True)
for item in plan['scripts']:
 assert sha(item['path'])==item['sha256'],item['path']
for name in ('launch-start.json','final-launch-receipt.json','final-runner.stdout.txt','final-runner.stderr.txt'):
 assert not (work/name).exists(),name
started_at=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
print('Starting complete gated W011 dual matrix: '+head,flush=True)
with (work/'final-runner.stdout.txt').open('wb') as stdout,(work/'final-runner.stderr.txt').open('wb') as stderr:
 process=subprocess.Popen(plan['command'],cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
 launch={'command':plan['command'],'cwd':str(root),'source_commit_at_launch':head,'started_at_utc':started_at,'pid':process.pid,'scripts':plan['scripts'],'environment_overrides':{'PYTHONDONTWRITEBYTECODE':'1'}}
 (work/'launch-start.json').write_text(json.dumps(launch,indent=2)+'\n')
 code=process.wait()
receipt={**launch,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,'exit_code':code,'stdout_sha256':sha(work/'final-runner.stdout.txt'),'stderr_sha256':sha(work/'final-runner.stderr.txt')}
(work/'final-launch-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
sys.exit(code)
