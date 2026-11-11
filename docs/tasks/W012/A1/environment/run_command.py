"""Record environment setup commands without exposing ambient environment values."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--cwd',default='/workspace/w012-a1-env');p.add_argument('argv',nargs=argparse.REMAINDER);a=p.parse_args();argv=a.argv[1:] if a.argv and a.argv[0]=='--' else a.argv
out=Path('/workspace/w012-a1-env/evidence');out.mkdir(exist_ok=True);prefix=out/a.label
if prefix.with_suffix('.json').exists():raise RuntimeError('preserve existing attempt')
overrides={'UV_NATIVE_TLS':'true','UV_CACHE_DIR':'/workspace/w012-a1-env/uv-cache','UV_PYTHON_INSTALL_DIR':'/workspace/w012-a1-env/python','PIP_CACHE_DIR':'/workspace/w012-a1-env/pip-cache','PYTHONDONTWRITEBYTECODE':'1','MPLCONFIGDIR':'/workspace/w012-a1-env/mplconfig'}
start=time.perf_counter();utc=datetime.now(timezone.utc).isoformat()
with prefix.with_suffix('.stdout.txt').open('wb') as stdout,prefix.with_suffix('.stderr.txt').open('wb') as stderr:
 r=subprocess.run(argv,cwd=a.cwd,env=dict(os.environ,**overrides),stdout=stdout,stderr=stderr)
sha=lambda suffix:hashlib.sha256(prefix.with_suffix(suffix).read_bytes()).hexdigest()
row={'argv':argv,'cwd':a.cwd,'overrides':overrides,'started_at_utc':utc,'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-start,'exit_code':r.returncode,'stdout_sha256':sha('.stdout.txt'),'stderr_sha256':sha('.stderr.txt')}
prefix.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));raise SystemExit(r.returncode)
