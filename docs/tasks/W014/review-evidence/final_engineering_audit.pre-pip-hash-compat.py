"""Independent read-only audit of completed W014 final engineering evidence.

This never imports product modules or reruns tests/build/install/smokes.
A missing/failed final receipt cannot produce a passing audit.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

TAGS=('310','312')
CASES={'normal-direct','normal-readback','extraction-mismatch'}


def sha(data):return hashlib.sha256(data).hexdigest()
def sid(files):return sha(json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())


def archive_files(path, *, source_distribution=False):
 result={}
 with tarfile.open(path,'r:gz') as archive:
  for member in archive.getmembers():
   parts=Path(member.name).parts
   assert not Path(member.name).is_absolute() and '..' not in parts,member.name
   if member.isdir():continue
   assert member.isfile() and not member.issym() and not member.islnk(),member.name
   name=member.name
   if source_distribution:
    if len(parts)<3 or parts[1]!='layauto_v2' or not (parts[-1].endswith('.py') or parts[-1]=='py.typed'):continue
    name='/'.join(parts[2:])
   assert name not in result,name
   stream=archive.extractfile(member)
   data=stream.read()
   assert len(data)==member.size,name
   result[name]=sha(data)
 return result


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',required=True,type=Path)
 p.add_argument('--evidence',required=True,type=Path)
 p.add_argument('--source-id',required=True)
 p.add_argument('--freeze-commit')
 p.add_argument('--out',required=True,type=Path)
 args=p.parse_args()
 root=args.root.resolve(); evidence=args.evidence.resolve()
 assert not args.out.exists(),'Preserve earlier audit outputs with a new --out'
 checked=[]
 def check(test,label):
  assert test,label
  checked.append(label)
 def data(name):return (evidence/name).read_bytes()
 def load(name):return json.loads(data(name))
 receipt=load('receipt.json')
 check(receipt['status']=='passed','actual final receipt passed')
 check(receipt['source_id']==args.source_id,'final receipt source identity')
 check(not (evidence/'failure.json').exists(),'no hidden failed-attempt marker')
 manifest=load('source-manifest.json');files=manifest['files'];runtime=manifest['runtime_files']
 check(manifest['source_id']==sid(files)==args.source_id,'full selected source identity')
 check(sha(data('source-manifest.json'))==receipt['source_manifest_sha256'],'source manifest original bytes')
 check(sha(data('source-snapshot.tar.gz'))==receipt['source_snapshot_sha256'],'source archive original bytes')
 check(archive_files(evidence/'source-snapshot.tar.gz')==files,'all source archive members and bytes')
 check(len(files)==receipt['source_file_count'],'source file count')
 check(len(runtime)==receipt['runtime_file_count'],'runtime file count')
 check({n.removeprefix('layauto_v2/'):h for n,h in files.items() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))}==runtime,'source/runtime manifest agreement')
 for name,want in files.items():check(sha((root/name).read_bytes())==want,'live source '+name)
 if args.freeze_commit:
  raw=subprocess.check_output(['git','archive',args.freeze_commit,'--',*files],cwd=root)
  git_files={}
  with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
   for member in archive.getmembers():
    if member.isdir():continue
    check(member.isfile() and member.name not in git_files,'git archive member '+member.name)
    git_files[member.name]=sha(archive.extractfile(member).read())
  check(git_files==files,'full frozen Git source bytes')
 evidence_manifest=load('evidence-manifest.json')
 actual_names={str(q.relative_to(evidence)) for q in evidence.rglob('*') if q.is_file() and q.name!='evidence-manifest.json'}
 check(set(evidence_manifest)==actual_names,'complete evidence manifest membership')
 for name,want in evidence_manifest.items():check(sha(data(name))==want,'evidence hash '+name)
 tools=load('tool-identity.json')
 check(receipt['tool_hashes']=={name:item['sha256'] for name,item in tools.items()},'tool identity summary')
 copied={'runner':'prepare_final.py','source_identity':'source_identity.py','smoke':'installed_smoke.py'}
 for name,target in copied.items():check(sha(data(target))==tools[name]['sha256'],'copied tool '+name)
 check(receipt['runner_sha256']==tools['runner']['sha256'],'runner identity')
 check(receipt['smoke_sha256']==tools['smoke']['sha256'],'smoke identity')
 clearance=load('resource-clearance.json')
 decision=clearance['decision']
 check(clearance['sha256']==receipt['resource_clearance_sha256'],'clearance owner identity')
 check(decision['status']=='passed' and decision['source_id']==args.source_id and set(decision['cases'])==CASES,'clearance exact source and routes')
 check(receipt['matrix_workers'] in (1,2),'legal matrix workers')
 if receipt['matrix_workers']==2:check(decision['parallel_matrices_safe'] is True,'reviewed parallel clearance')
 check(receipt['package_smokes_after_matrices'] is True,'smokes ordered after matrices')
 baseline=data('baseline-collection.txt')
 check(sha(baseline)==receipt['baseline_collection_sha256'],'baseline identity')
 check(baseline==(root/'docs/tasks/W013/verification-r2/collection-312.stdout.txt').read_bytes(),'original accepted baseline owner')
 ids=lambda content:{s for s in content.decode().splitlines() if s.startswith('tests/') and '::' in s}
 baseline_ids=ids(baseline)
 check(len(baseline_ids)==receipt['retained_baseline_test_count']==1731,'all accepted 1731 baseline IDs')
 expected=receipt['expected_test_count']
 expected_names={'build'}|{prefix+'-'+tag for tag in TAGS for prefix in ('environment','collection','pytest','typing','pip-check','create-install','install','installed-pip-check','installed-identity','installed-smoke')}
 commands=receipt['commands'];name_to_row={Path(row['stdout']).name.removesuffix('.stdout.txt'):row for row in commands}
 check(len(commands)==len(name_to_row)==21 and set(name_to_row)==expected_names,'exactly all 21 actual commands')
 for name,row in name_to_row.items():
  check(row==load(name+'.json'),'command receipt owner '+name)
  check(row['exit_code']==0,'command exit '+name)
  check(sha(data(row['stdout']))==row['stdout_sha256'],'command stdout '+name)
  check(sha(data(row['stderr']))==row['stderr_sha256'],'command stderr '+name)
 count_summary={};typing_summary={};environment={}
 matrix_cwds=set()
 for tag in TAGS:
  env=load('environment-'+tag+'.stdout.txt');environment[tag]=env
  check(env['version'].startswith('3.10.' if tag=='310' else '3.12.'),'actual interpreter '+tag)
  matrix_cwd=Path(name_to_row['environment-'+tag]['cwd'])
  matrix_cwds.add(matrix_cwd)
  check(Path(env['source_package'])==matrix_cwd/'layauto_v2/__init__.py','matrix imports selected source '+tag)
  check(name_to_row['pytest-'+tag]['command'][0]==receipt['python_environments'][tag],'matrix uses recorded interpreter '+tag)
  current=ids(data('collection-'+tag+'.stdout.txt'));scope=load('pytest-scope-'+tag+'.json')
  check(baseline_ids<=current and len(current)==expected,'complete collection '+tag)
  check(scope['missing_baseline_ids']==[] and scope['current_test_count']==expected and scope['baseline_test_count']==1731 and scope['added_test_count']==expected-1731,'scope receipt '+tag)
  raw=data('pytest-'+tag+'.stdout.txt').decode()
  passed=re.findall(r'^(\d+) passed',raw,re.MULTILINE)
  check(len(passed)==1 and int(passed[0])==expected==receipt['actual_test_counts'][tag],'actual full pytest result '+tag)
  argv=name_to_row['pytest-'+tag]['command']
  check(argv[1:]==['-m','pytest','-p','no:cacheprovider','tests/unit','tests/contracts','-q'],'full pytest invocation '+tag)
  typed=data('typing-'+tag+'.stdout.txt').decode()
  typing_count=re.findall(r'Success: no issues found in (\d+) source files?',typed)
  check(len(typing_count)==1,'actual strict typing result '+tag)
  check(name_to_row['typing-'+tag]['command'][1:]==['-m','mypy'],'configured strict typing invocation '+tag)
  count_summary[tag]=int(passed[0]);typing_summary[tag]=int(typing_count[0])
 check(len(matrix_cwds)==1,'one common frozen source tree')
 matrix_cwd=next(iter(matrix_cwds))
 matrix_end=max(datetime.fromisoformat(name_to_row[prefix+'-'+tag]['finished_at_utc']) for prefix in ('environment','collection','pytest','typing','pip-check') for tag in TAGS)
 check(datetime.fromisoformat(name_to_row['build']['started_at_utc'])>=matrix_end,'actual build starts after both matrices')
 package=load('package-identity.json')
 check(set(package)=={'wheel','sdist'},'exactly two package kinds')
 check(len(list((evidence/'dist').glob('*.whl')))==len(list((evidence/'dist').glob('*.tar.gz')))==1,'no stale extra artifacts')
 for kind,item in package.items():
  artifact=evidence/'dist'/Path(item['path']).name
  check(artifact.is_file() and sha(artifact.read_bytes())==item['sha256'],'actual built artifact '+kind)
  if kind=='wheel':
   with zipfile.ZipFile(artifact) as archive:
    check(len(archive.namelist())==len(set(archive.namelist())),'unique wheel archive members')
    actual={name.removeprefix('layauto_v2/'):sha(archive.read(name)) for name in archive.namelist() if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
  else:actual=archive_files(artifact,source_distribution=True)
  check(actual==item['runtime_files']==runtime,'complete package runtime bytes '+kind)
 install=load('installation-identity.json');smokes={}
 for tag in TAGS:
  item=install[tag];kind='sdist' if tag=='310' else 'wheel'
  check(item['artifact_sha256']==package[kind]['sha256'],'installed exact artifact '+tag)
  check(name_to_row['install-'+tag]['command'][-1]==item['artifact'],'pip installs recorded artifact '+tag)
  pip_report=load('install-'+tag+'-report.json')
  package_rows=[row for row in pip_report['install'] if row['metadata']['name'].lower()=='layauto']
  check(len(package_rows)==1 and package_rows[0]['download_info']['archive_info']['hashes']['sha256']==item['artifact_sha256'],'pip original artifact hash '+tag)
  check(item['runtime_files']==runtime and item['fresh_environment'] is True,'full original installed runtime receipt '+tag)
  raw_identity=load('installed-identity-'+tag+'.stdout.txt')
  check(raw_identity['package']==item['package'] and raw_identity['executable']==item['executable'] and raw_identity['version']==item['version'] and raw_identity['isolated']==item['isolated']==1,'actual installed identity '+tag)
  check('site-packages' in Path(item['package']).parts,'installed package resolution '+tag)
  check(item['version'].startswith('3.10.' if tag=='310' else '3.12.'),'clean installed interpreter '+tag)
  command=name_to_row['installed-smoke-'+tag]['command']
  check(command[1:3]==['-I','-B'] and Path(command[3]).name=='installed_smoke.py','isolated source-external smoke invocation '+tag)
  cwd=Path(name_to_row['installed-smoke-'+tag]['cwd'])
  check(not cwd.is_relative_to(root) and not cwd.is_relative_to(matrix_cwd),'smoke cwd outside checkout and frozen source '+tag)
  check(Path(command[4])==matrix_cwd/'tests/fixtures/w003_m1','smoke uses same frozen input fixture '+tag)
  smoke=load('installed-smoke-'+tag+'.stdout.txt');smokes[tag]=smoke
  check(smoke['package']==item['package'] and smoke['executable']==item['executable'],'smoke uses actual clean package '+tag)
  check(set(smoke['cases'])==CASES,'all three actual smoke routes '+tag)
  check(smoke['attempt_unchanged'] and smoke['checkpoint_unchanged'] and smoke['terminal_absent'],'actual readback lifecycle retained '+tag)
  for case,result in smoke['cases'].items():
   check(result['public_roundtrip_equal'] and result['terminal_count']==8 and result['local_terminal_count']==6 and result['independent_body_count']==2,'actual eight-terminal public smoke '+tag+'/'+case)
   check(result['local_nodes_edges_components']==[14,8,6] and result['unknown_local_body_components']==2,'actual local graph retained '+tag+'/'+case)
   check(result['retained_MN0_fin_count']==(4 if case=='extraction-mismatch' else 5) and result['retained_MN0_source_fin_count']==5,'actual source mismatch retained '+tag+'/'+case)
  current_tree=Path(item['package']).parent
  if current_tree.is_dir():
   current_files={str(q.relative_to(current_tree)):sha(q.read_bytes()) for q in current_tree.rglob('*') if q.is_file() and (q.suffix=='.py' or q.name=='py.typed')}
   check(current_files==runtime,'still-accessible installed runtime bytes '+tag)
 check(datetime.fromisoformat(name_to_row['create-install-310']['started_at_utc'])>=datetime.fromisoformat(name_to_row['build']['finished_at_utc']),'actual install waits for build')
 check(datetime.fromisoformat(name_to_row['create-install-312']['started_at_utc'])>=datetime.fromisoformat(name_to_row['installed-smoke-310']['finished_at_utc']),'actual installation smokes serial')
 check(receipt['source_identity_rechecked_after_all_commands'] is True,'runner rechecked full source identity')
 result={'status':'passed','classification':'independent-read-only-final-engineering-evidence-audit','source_id':args.source_id,'freeze_commit':args.freeze_commit,
 'check_count':len(checked),'checks':checked,'actual_test_counts':count_summary,'actual_typing_source_counts':typing_summary,
 'source_file_count':len(files),'runtime_file_count':len(runtime),'actual_command_count':len(commands),
 'evidence_manifest_sha256':sha(data('evidence-manifest.json')),'receipt_sha256':sha(data('receipt.json')),
 'auditor_sha256':sha(Path(__file__).read_bytes()),'limitations':['No tests, package build, installation, capture or codec rerun by this audit.','Product correctness and PM acceptance remain separate reviews.']}
 args.out.parent.mkdir(parents=True,exist_ok=True)
 args.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({key:result[key] for key in ('status','check_count','source_id','actual_test_counts','actual_typing_source_counts','actual_command_count')},indent=2))


if __name__=='__main__':main()
