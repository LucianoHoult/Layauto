from pathlib import Path
import os,sys,subprocess,time,json,hashlib
w=Path('/workspace/work/w011-engineering');out=w/'preliminary-smoke-01';source=out/'source'
command=[str(w/'dev312/bin/python'),'-B',str(out/'preflight_smoke.py'),str(source/'tests/fixtures/w003_m1')]
env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1');started=time.time()
with (out/'run.stdout.txt').open('wb') as stdout,(out/'run.stderr.txt').open('wb') as stderr:
 p=subprocess.run(command,cwd=source,env=env,stdout=stdout,stderr=stderr)
row={'command':command,'cwd':str(source),'environment_overrides':{'PYTHONPATH':str(source),'PYTHONDONTWRITEBYTECODE':'1'},'execution_kind':'source_preflight_not_clean_install','exit_code':p.returncode,'elapsed_seconds':time.time()-started,'outputs':{ext:hashlib.sha256((out/('run.'+ext+'.txt')).read_bytes()).hexdigest() for ext in ('stdout','stderr')}}
(out/'run.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True);sys.exit(p.returncode)
