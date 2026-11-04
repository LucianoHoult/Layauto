from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
root=Path.cwd()
out=Path('/workspace/work/w009-ipmr01-audit')
name=sys.argv[1]
command=sys.argv[2:]
started=time.time()
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(root)
with (out/(name+'.stdout.txt')).open('wb') as stdout, (out/(name+'.stderr.txt')).open('wb') as stderr:
    result=subprocess.run(command,env=env,stdout=stdout,stderr=stderr)
(out/(name+'.receipt.json')).write_text(json.dumps({'cwd':str(root),'command':command,'exit_code':result.returncode,'elapsed_seconds':time.time()-started},indent=2)+'\n')
print(name,result.returncode,flush=True)
sys.exit(result.returncode)
