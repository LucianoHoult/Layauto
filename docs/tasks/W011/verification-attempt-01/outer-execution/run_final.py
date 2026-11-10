from pathlib import Path
import hashlib,json,os,subprocess,time,sys,datetime
w=Path('/workspace/work/w011-engineering');plan=json.loads((w/'final-launch-plan.json').read_text());root=Path(plan['cwd'])
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert head==plan['expected_source_commit'],(head,plan['expected_source_commit'])
assert not subprocess.check_output(['git','status','--short','--','layauto_v2','tests','pyproject.toml','README.md'],cwd=root,text=True)
started=time.time();started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
print('Starting final W011 matrix: '+head+'; 1605 tests per interpreter; matrix_workers=1.',flush=True)
with (w/'final-runner.stdout.txt').open('wb') as stdout,(w/'final-runner.stderr.txt').open('wb') as stderr:
 p=subprocess.run(plan['command'],cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
receipt={'command':plan['command'],'cwd':str(root),'source_commit_at_launch':head,'started_at_utc':started_at,'exit_code':p.returncode,'elapsed_seconds':time.time()-started,'stdout_sha256':hashlib.sha256((w/'final-runner.stdout.txt').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((w/'final-runner.stderr.txt').read_bytes()).hexdigest()}
(w/'final-launch-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True);sys.exit(p.returncode)
