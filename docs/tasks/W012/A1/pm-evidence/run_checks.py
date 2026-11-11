import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path('/workspace/Layauto')
OUT=Path('/workspace/work/w012-a1-pm')
PYTHON='/workspace/work/w005-pm-check-env/bin/python'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT))
commands=[
 ('targeted',[PYTHON,'-B','-m','pytest','-p','no:cacheprovider','-q',
              'tests/contracts/test_w012_hex_validation.py','tests/contracts/test_w005_contracts.py']),
 ('typing',[PYTHON,'-B','-m','mypy','--cache-dir',str(OUT/'mypy-cache')]),
 ('readback',[PYTHON,'-B',str(ROOT/'docs/tasks/W012/A1/probe.py'),
              '--runtime-root',str(ROOT),'--input-root',str(ROOT),'--case','normal-readback',
              '--mode','baseline','--output',str(OUT/'readback-result.json')])
]
for name,argv in commands:
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
    with (OUT/(name+'.stdout.txt')).open('wb') as stdout,(OUT/(name+'.stderr.txt')).open('wb') as stderr:
        result=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    receipt=dict(argv=argv,cwd=str(ROOT),started_utc=start,
                 finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 elapsed_seconds=time.monotonic()-clock,returncode=result.returncode,
                 tested_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 environment_overrides={key:env[key] for key in ('PYTHONDONTWRITEBYTECODE','PYTHONPATH')},
                 interpreter=subprocess.check_output([PYTHON,'--version'],text=True).strip())
    for suffix in ('stdout.txt','stderr.txt'):
        path=OUT/(name+'.'+suffix)
        receipt[suffix]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT/(name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(name=name,returncode=result.returncode,elapsed_seconds=receipt['elapsed_seconds'])),flush=True)
    if result.returncode:raise SystemExit(result.returncode)
if 'readback' in [name for name,_ in commands]:
    record=json.loads((OUT/'readback-result.json').read_text())
    assert record['wire_bytes']==136471701
    assert record['wire_sha256']=='1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795'
    assert record['public_roundtrip_equal'] and record['readback_unsealed_checkpoint_unchanged_no_terminal']
    print('complete readback hash/roundtrip/state boundary matches frozen original',flush=True)
