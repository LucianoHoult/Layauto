"""Run the original probes unchanged; check their contractual meaning explicitly."""
import hashlib,json,os,platform,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/workspace/work/w009-ipmr01')
OUT=ROOT/'docs/tasks/W009/ipmr01-verification'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,path,expected_exit):
    command=[sys.executable,'-B',str(path)]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT))
    start=time.monotonic()
    with (OUT/(name+'.stdout.txt')).open('wb') as stdout,(OUT/(name+'.stderr.txt')).open('wb') as stderr:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
    row={'command':command,'cwd':str(ROOT),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'script_sha256':sha(path),'exit_code':result.returncode,'expected_exit_code':expected_exit,'elapsed_seconds':round(time.monotonic()-start,3),'finished_utc':datetime.now(timezone.utc).isoformat(),'source_manifest_sha256':sha(OUT/'source-manifest.json'),'outputs':{s:{'path':name+'.'+s+'.txt','sha256':sha(OUT/(name+'.'+s+'.txt'))} for s in ('stdout','stderr')}}
    if name=='exception-paths':
        data=json.loads((OUT/(name+'.stdout.txt')).read_text())
        row['observed']={k:data[k] for k in ('case_count','same_object_count','identity_failures')}
        row['contract_passed']=data['case_count']==99 and data['same_object_count']==99 and data['identity_failures']==[]
    else:
        row['meaning']='The unchanged historical script asserts the defect is present; its old ValueError observation assertion must fail after repair. New formal tests assert the correct same-object behavior.'
        err=(OUT/(name+'.stderr.txt')).read_text()
        row['old_defect_assertion_failed']='assert observation ==' in err and 'AssertionError' in err
        row['contract_passed']=row['old_defect_assertion_failed']
    row['passed']=result.returncode==expected_exit and row['contract_passed']
    (OUT/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    assert row['passed'],row
    print(json.dumps(row),flush=True)
run('exception-paths',ROOT/'docs/tasks/W009/independent-premerge-review/provenance-exceptions/exception_paths.py',0)
run('historical-minimal',ROOT/'docs/tasks/W009/independent-premerge-review/validation/nested_base_confirmation.py',1)
