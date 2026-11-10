from pathlib import Path
import os,subprocess,json,time,hashlib
work=Path('/workspace/work/w011-engineering');out=work/'setup';out.mkdir(exist_ok=True)
base310=work/'pythons/cpython-3.10-linux-x86_64-gnu/bin/python3.10';base312=Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
env=dict(os.environ,PIP_CACHE_DIR=str(work/'pip-cache'),PYTHONDONTWRITEBYTECODE='1')
for tag,py in [('310',base310),('312',base312)]:
 venv=work/('dev'+tag)
 for name,command in [('venv',[str(py),'-m','venv',str(venv)]),('deps',[str(venv/'bin/python'),'-m','pip','install','pytest','mypy','types-PyYAML','build','numpy','matplotlib','pyyaml','gdstk','klayout'])]:
  stem=tag+'-'+name;start=time.time()
  with (out/(stem+'.stdout.txt')).open('wb') as stdout,(out/(stem+'.stderr.txt')).open('wb') as stderr:
   p=subprocess.run(command,cwd=work,env=env,stdout=stdout,stderr=stderr)
  row={'command':command,'cwd':str(work),'exit_code':p.returncode,'elapsed_seconds':time.time()-start,'outputs':{ext:hashlib.sha256((out/(stem+'.'+ext+'.txt')).read_bytes()).hexdigest() for ext in ('stdout','stderr')}}
  (out/(stem+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
  if p.returncode:raise RuntimeError(stem+' failed')
