from pathlib import Path
import json,os,subprocess,sys,time
base=Path(__file__).parent
name,cwd,*command=sys.argv[1:]
env=os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE='1',PIP_CACHE_DIR=str(base/'pip-cache'),UV_CACHE_DIR=str(base/'uv-cache'),MYPY_CACHE_DIR=str(base/('mypy-cache-'+name)))
with (base/'commands.txt').open('a') as f: f.write(json.dumps({'name':name,'cwd':cwd,'argv':command,'env':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PIP_CACHE_DIR','UV_CACHE_DIR','MYPY_CACHE_DIR')}},ensure_ascii=False)+'\n')
start=time.time()
with (base/(name+'.txt')).open('w') as log:
 p=subprocess.run(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
text=(base/(name+'.txt')).read_text()
print(text)
(base/(name+'.result.json')).write_text(json.dumps({'name':name,'returncode':p.returncode,'duration_seconds':round(time.time()-start,3),'command':command,'cwd':cwd},indent=2)+'\n')
sys.exit(p.returncode)
