from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
import subprocess, sys, time

ROOT=Path('/workspace/work/w012-a2/engineering')
BASE=Path('/workspace/work/w012-a2/envs')
OUT=ROOT/'docs/tasks/W012/A2-implementation/engineering-preparation'
OUT.mkdir(parents=True, exist_ok=True)
BASE.mkdir(parents=True, exist_ok=True)
env=dict(os.environ,UV_CACHE_DIR=str(BASE/'uv-cache'), UV_PYTHON_INSTALL_DIR=str(BASE/'python'), UV_PYTHON_BIN_DIR=str(BASE/'bin'), PIP_CACHE_DIR=str(BASE/'pip-cache'), PYTHONDONTWRITEBYTECODE='1', UV_NO_PROGRESS='1')
rows=[]
def run(name, args):
    paths=[OUT/(name+s) for s in ('.stdout.txt','.stderr.txt','.command.json')]
    if any(p.exists() for p in paths): raise RuntimeError('Preserve prior attempt: '+name)
    start=datetime.now(timezone.utc).isoformat(); clock=time.perf_counter()
    with paths[0].open('wb') as stdout, paths[1].open('wb') as stderr:
        result=subprocess.run([str(x) for x in args],cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    row=dict(command=[str(x) for x in args],cwd=str(ROOT),exit_code=result.returncode,started_at_utc=start,finished_at_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.perf_counter()-clock,environment_overrides={k:env[k] for k in ('UV_CACHE_DIR','UV_PYTHON_INSTALL_DIR','UV_PYTHON_BIN_DIR','PIP_CACHE_DIR','PYTHONDONTWRITEBYTECODE','UV_NO_PROGRESS')},stdout=paths[0].name,stderr=paths[1].name,stdout_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256(paths[1].read_bytes()).hexdigest())
    paths[2].write_text(json.dumps(row,indent=2)+'\n'); rows.append(row)
    print(name, result.returncode, flush=True)
    if result.returncode: raise RuntimeError(name+' failed: '+paths[1].read_text()[-2500:])
try:
    run('python310-install',['uv','python','install','3.10','--no-bin'])
    python310=next((BASE/'python').glob('cpython-3.10.*/bin/python3.10'))
    pythons={'310':python310,'312':Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')}
    for tag,py in pythons.items():
        target=BASE/('dev'+tag)
        run('venv-'+tag,['uv','venv','--seed','--python',py,target])
        run('install-'+tag,[target/'bin/python','-m','pip','install','numpy','matplotlib','pyyaml','pytest','mypy','types-PyYAML','build','setuptools','wheel'])
        run('pip-check-'+tag,[target/'bin/python','-m','pip','check'])
        run('environment-'+tag,[target/'bin/python','-c','import json,sys,importlib.metadata as m; print(json.dumps({"executable":sys.executable,"version":sys.version,"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))'])
finally:
    (OUT/'preparation-receipt.json').write_text(json.dumps({'heavy_matrix_run':False,'commands':rows},indent=2)+'\n')
