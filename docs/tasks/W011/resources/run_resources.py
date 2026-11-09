"""Sequential final resource probes, bound to the completed matrix source."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys,time

ROOT: Path
VERIFICATION: Path
OUT: Path
WORK: Path
PYTHON: Path
PROBE: Path


def sha(data):
 return hashlib.sha256(data).hexdigest()


def runtime_files(base):
 return {str(path.relative_to(base)):sha(path.read_bytes()) for path in sorted(base.rglob('*'))
         if path.is_file() and (path.suffix=='.py' or path.name=='py.typed')}


def write(name,value):
 (OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def main():
 global ROOT,VERIFICATION,OUT,WORK,PYTHON,PROBE
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('root','verification','out','work','python','probe'):
  parser.add_argument('--'+name,type=Path,required=True)
 parser.add_argument('--expected-source-commit',required=True)
 parser.add_argument('--expected-tests',type=int,required=True)
 args=parser.parse_args()
 ROOT,VERIFICATION,OUT,WORK,PROBE=(getattr(args,key).resolve() for key in ('root','verification','out','work','probe'))
 PYTHON=args.python.absolute()
 verified=json.loads((VERIFICATION/'receipt.json').read_text())
 assert verified['status']=='passed' and verified['actual_test_counts']=={'310':args.expected_tests,'312':args.expected_tests}
 source=json.loads((VERIFICATION/'source-manifest.json').read_text())
 assert source['git_head']==args.expected_source_commit
 for tag in ('310','312'):
  assert json.loads((VERIFICATION/f'installed-smoke-{tag}.json').read_text())['exit_code']==0
 assert not OUT.exists() or not any(OUT.iterdir())
 assert not WORK.exists()
 OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True)
 probe_sha=sha(PROBE.read_bytes())
 expected_runtime=source['runtime_files']
 expected_probe_sources={**{'layauto_v2/'+name:digest for name,digest in expected_runtime.items()},
                         'pyproject.toml':source['files']['pyproject.toml']}
 def check_source():
  actual=runtime_files(ROOT/'layauto_v2')
  assert actual==expected_runtime,'runtime differs from completed matrix snapshot'
  assert sha((ROOT/'pyproject.toml').read_bytes())==source['files']['pyproject.toml']
  assert sha(PROBE.read_bytes())==probe_sha,'resource probe changed during verification'
  return actual
 check_source()
 source_identity={'tested_source_commit':source['git_head'],
                  'verification_source_manifest_sha256':sha((VERIFICATION/'source-manifest.json').read_bytes()),
                  'verification_receipt_sha256':sha((VERIFICATION/'receipt.json').read_bytes()),
                  'runtime_files':expected_runtime,'probe_sha256':probe_sha,
                  'launcher_sha256':sha(Path(__file__).read_bytes()),
                  'launcher_command':[sys.executable,*sys.argv],
                  'expected_test_count':args.expected_tests}
 write('source-identity.json',source_identity)
 (OUT/'resource_probe.py').write_bytes(PROBE.read_bytes())
 (OUT/'run_resources.py').write_bytes(Path(__file__).read_bytes())
 rows=[]
 for case in ('normal-direct','normal-readback','extraction-mismatch'):
  check_source()
  head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
  command=[str(PYTHON),'-B',str(PROBE),'--root',str(ROOT),'--case',case,
           '--output',str(OUT/(case+'.json')),'--work',str(WORK)]
  started_at=datetime.now(timezone.utc).isoformat();started=time.perf_counter()
  print('Starting resource probe '+case+' against '+source['git_head'],flush=True)
  with (OUT/(case+'.stdout.txt')).open('wb') as stdout,(OUT/(case+'.stderr.txt')).open('wb') as stderr:
   process=subprocess.run(command,cwd=WORK,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=stdout,stderr=stderr)
  finished_at=datetime.now(timezone.utc).isoformat()
  row={'case':case,'command':command,'cwd':str(WORK),'started_at_utc':started_at,'finished_at_utc':finished_at,
       'elapsed_seconds':time.perf_counter()-started,'exit_code':process.returncode,
       'live_git_head_at_launch':head,'tested_source_commit':source['git_head'],
       'stdout_sha256':sha((OUT/(case+'.stdout.txt')).read_bytes()),
       'stderr_sha256':sha((OUT/(case+'.stderr.txt')).read_bytes())}
  write(case+'.command.json',row);rows.append(row)
  if process.returncode:
   write('failure.json',{'status':'failed','case':case,'commands':rows});raise RuntimeError(case+' resource probe failed')
  check_source()
  result=json.loads((OUT/(case+'.json')).read_text())
  assert result['source_unchanged_during_probe'] and result['source_manifest']==expected_probe_sources
  assert result['probe_sha256']==probe_sha
  row['runtime_matches_verified_snapshot_before_and_after']=True
  write(case+'.command.json',row)
  print('Completed resource probe '+case,flush=True)
 for name,digest in source['files'].items():
  assert sha((ROOT/name).read_bytes())==digest,'source/test/config changed: '+name
 write('receipt.json',{'status':'passed','source_identity':source_identity,'commands':rows,
                       'one_fresh_process_per_case':True,'full_source_tests_config_unchanged':True})
 write('evidence-manifest.json',{str(path.relative_to(OUT)):sha(path.read_bytes()) for path in sorted(OUT.rglob('*'))
                                  if path.is_file() and path.name!='evidence-manifest.json'})
 print('All final finite resource probes passed.',flush=True)


if __name__=='__main__':
 main()
