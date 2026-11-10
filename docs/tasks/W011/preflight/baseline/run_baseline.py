from pathlib import Path
import hashlib,json,os,subprocess,time,sys
work=Path('/workspace/work/w011-engineering');source=work/'baseline-source';out=work/'baseline';out.mkdir(exist_ok=True)
py=Path(sys.argv[1]);tag=sys.argv[2]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PIP_CACHE_DIR=str(work/'pip-cache'),MYPY_CACHE_DIR=str(work/('mypy-'+tag)),MPLCONFIGDIR=str(work/'mplconfig'))
commands=[('environment',[str(py),'-c','import sys,platform,importlib.metadata as m,json,layauto_v2,resource; print(json.dumps({"executable":sys.executable,"version":sys.version,"platform":platform.platform(),"source_package":layauto_v2.__file__,"rlimits":{n:resource.getrlimit(getattr(resource,n)) for n in ("RLIMIT_AS","RLIMIT_CPU","RLIMIT_DATA","RLIMIT_NOFILE","RLIMIT_STACK")},"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))']),('collection',[str(py),'-m','pytest','-p','no:cacheprovider','--collect-only','tests/unit','tests/contracts','-q']),('pytest',[str(py),'-m','pytest','-p','no:cacheprovider','tests/unit','tests/contracts','-q'])]
for name,cmd in commands:
 stem=name+'-'+tag;start=time.time()
 with (out/(stem+'.stdout.txt')).open('wb') as stdout,(out/(stem+'.stderr.txt')).open('wb') as stderr:
  p=subprocess.run(cmd,cwd=source,env=env,stdout=stdout,stderr=stderr)
 row={'command':cmd,'cwd':str(source),'exit_code':p.returncode,'elapsed_seconds':time.time()-start,'environment_overrides':{k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PIP_CACHE_DIR','MYPY_CACHE_DIR','MPLCONFIGDIR')},'outputs':{ext:{'path':stem+'.'+ext+'.txt','sha256':hashlib.sha256((out/(stem+'.'+ext+'.txt')).read_bytes()).hexdigest()} for ext in ('stdout','stderr')}}
 (out/(stem+'.json')).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
 if p.returncode:sys.exit(p.returncode)
