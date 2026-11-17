"""Run one required check on frozen source, preserving original output and identity.

Usage: python verify_frozen.py LABEL OUTDIR -- COMMAND ...
Long processes run in a shell session; this driver does not shorten the checks.
"""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    label,out,*command=sys.argv[1:]
    if command[0]=='--':command=command[1:]
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    source_manifest=Path('docs/tasks/W016/evidence/resumed/completed-source-identity.json')
    identity=json.loads(source_manifest.read_text())
    def check():
        bad=[p for p,h in identity['files'].items() if sha(Path(p))!=h]
        if bad:raise RuntimeError('frozen source changed: '+repr(bad))
    check()
    stdout=output/(label+'.stdout.txt');stderr=output/(label+'.stderr.txt');meta=output/(label+'.json')
    check_cwd=os.environ.get('W016_CHECK_CWD',str(Path.cwd()))
    started=datetime.now(timezone.utc).isoformat();start=time.monotonic()
    (output/(label+'.started.json')).write_text(json.dumps({'command':command,'cwd':check_cwd,
        'started_at_utc':started,'source_manifest_sha256':sha(source_manifest),
        'driver_sha256':sha(Path(__file__))},indent=2)+'\n')
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','MPLCONFIGDIR':'/tmp/w016-mplconfig'}
    with stdout.open('xb') as out_file,stderr.open('xb') as err_file:
        try:
            status=subprocess.call(command,stdout=out_file,stderr=err_file,env=environment,cwd=check_cwd)
        except KeyboardInterrupt:
            status=130

    check()
    result={'label':label,'command':command,'cwd':check_cwd,'driver_cwd':str(Path.cwd()),'started_at_utc':started,
        'finished_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,
        'exit_code':status,'source_manifest_sha256':sha(source_manifest),
        'stdout':stdout.name,'stderr':stderr.name,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),
        'environment_overrides':{k:environment[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONUNBUFFERED','MPLCONFIGDIR')}}
    meta.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    raise SystemExit(status)

if __name__=='__main__':main()
