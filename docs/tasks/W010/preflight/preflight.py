from pathlib import Path
import hashlib,json,os,subprocess,sys,time,tarfile
ROOT=Path('/workspace/Layauto')
OUT=ROOT/'work/w010-preflight'
SNAP=OUT/'snapshot'
OUT.mkdir(parents=True,exist_ok=True)
SNAP.mkdir(exist_ok=True)

def run(name,args,cwd=ROOT,env_extra=None):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PIP_CACHE_DIR=str(OUT/'pip-cache'),MYPY_CACHE_DIR=str(OUT/('mypy-'+name)),MPLCONFIGDIR=str(OUT/'mplconfig'))
 if env_extra: env.update(env_extra)
 start=time.time()
 with (OUT/(name+'.txt')).open('wb') as f:
  r=subprocess.run([str(a) for a in args],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 info={'command':[str(a) for a in args],'cwd':str(cwd),'exit_code':r.returncode,'elapsed_seconds':round(time.time()-start,3),'output':name+'.txt','output_sha256':hashlib.sha256((OUT/(name+'.txt')).read_bytes()).hexdigest()}
 (OUT/(name+'.json')).write_text(json.dumps(info,indent=2)+'\n')
 print(json.dumps(info),flush=True)
 return r.returncode

assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='9758a157115cc22d91ce095ac2002209b9f210d3'
with (OUT/'baseline-source.tar').open('wb') as f:
 subprocess.run(['git','archive','HEAD','layauto_v2','tests','pyproject.toml','README.md'],cwd=ROOT,stdout=f,check=True)
with tarfile.open(OUT/'baseline-source.tar') as archive: archive.extractall(SNAP,filter='data')
manifest={str(p.relative_to(SNAP)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SNAP.rglob('*') if p.is_file()}
(OUT/'baseline-manifest.json').write_text(json.dumps({'git_head':'9758a157115cc22d91ce095ac2002209b9f210d3','files':manifest},indent=2)+'\n')
uv='/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/uv'
uv_env={'UV_CACHE_DIR':str(OUT/'uv-cache'),'UV_PYTHON_INSTALL_DIR':str(OUT/'python'),'UV_PYTHON_BIN_DIR':str(OUT/'python-bin')}
assert run('python310-install',[uv,'python','install','3.10'],env_extra=uv_env)==0
base310=next((OUT/'python').glob('cpython-3.10*/bin/python3.10'))
pythons={'310':Path('/workspace/.venvs/w010-py310/bin/python'),'312':Path('/workspace/.venvs/w010-py312/bin/python')}
for tag,base in [('310',base310),('312',Path(sys.executable))]:
 venv=pythons[tag].parent.parent
 assert not venv.exists()
 assert run('venv-'+tag,[base,'-m','venv',venv])==0
 assert run('install-'+tag,[pythons[tag],'-m','pip','install','.[dev,gds]'],cwd=SNAP)==0
 run('environment-'+tag,[pythons[tag],'-c','import sys,platform,importlib.metadata as m,json; print(json.dumps({"executable":sys.executable,"version":sys.version,"platform":platform.platform(),"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))'])
 run('pip-check-'+tag,[pythons[tag],'-m','pip','check'])
 run('baseline-pytest-'+tag,[pythons[tag],'-m','pytest','-p','no:cacheprovider','tests/unit','tests/contracts','-q'],cwd=SNAP)
 run('baseline-mypy-'+tag,[pythons[tag],'-m','mypy'],cwd=SNAP)
