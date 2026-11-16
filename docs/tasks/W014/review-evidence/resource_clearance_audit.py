"""Independent resource provenance, raw receipts and final test-only delta audit.

Read bytes only. No product build, codec or matrix calls.
"""
from __future__ import annotations
import difflib
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
CASES=('normal-direct','normal-readback','extraction-mismatch')

def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads((ROOT/path).read_text())
def identity(files):return sha(json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
def read(name):return (ROOT/name).read_bytes()


def main():
 checks=[]
 def check(test,label):
  assert test,label
  checks.append(label)
 adoption=load('docs/tasks/W014/resource-adoption/adoption.json')
 for name,want in load('docs/tasks/W014/resource-adoption/manifest.json').items():
  check(sha(read('docs/tasks/W014/resource-adoption/'+name))==want,'adoption owner '+name)
 for name,receipt in adoption['evidence_files'].items():
  data=read(name)
  check(len(data)==receipt['bytes'] and sha(data)==receipt['sha256'],'retained evidence '+name)
 old_root=Path('docs/tasks/W014/resources-early')
 new_root=Path('docs/tasks/W014/resources-r2')
 old_files=None;new_files=None;ratios={}
 for case in CASES:
  pair=[]
  for rel,component,expected in ((old_root,'w013',adoption['reference_source_id']),(new_root,'w014',adoption['current_source_id'])):
   name=component+'-'+case
   report=load(rel/(name+'.json'));command=load(rel/(name+'.command.json'))
   check(report['source_id']==identity(report['files'])==expected,'source identity '+name)
   check(command['returncode']==0,'successful command '+name)
   check(sha(read(rel/(name+'.stdout.txt')))==command['stdout_sha256'],'stdout '+name)
   check(sha(read(rel/(name+'.stderr.txt')))==command['stderr_sha256'],'stderr '+name)
   check(report['public_roundtrip_equal'] is True,'roundtrip '+name)
   check(report['authentication_calls_by_phase']=={component.upper()+'_build':1,component.upper()+'_encode':1,component.upper()+'_decode':2},'auth calls '+name)
   for tool in ('resource_probe.py','source_identity.py'):
    check(sha(read(rel/tool))==command['tool_hashes'][tool],'actual tool '+name+':'+tool)
   pair.append((report,command))
  a,b=pair[0][0],pair[1][0]
  old_files=old_files or a['files'];new_files=new_files or b['files']
  check(a['files']==old_files and b['files']==new_files,'whole file manifests '+case)
  for field in ('capture_sources','retained_W010_wire_bytes','retained_W010_wire_sha256','python','executable','platform','distributions','input_site','local_counts'):
   check(a[field]==b[field],'same '+field+' '+case)
  check(pair[0][1]['environment_overrides']==pair[1][1]['environment_overrides'],'same env '+case)
  old_secs=sum(v['seconds'] for k,v in a['phases'].items() if k.startswith('W013'))
  new_secs=sum(v['seconds'] for k,v in b['phases'].items() if k.startswith('W014'))
  ratios[case]={'component_seconds_ratio':new_secs/old_secs,'wire_added_bytes':b['wire_bytes']-a['wire_bytes'],
    'peak_rss_kib':b['process_peak_rss_kib_before_postmeasurement_analysis']}
  expected_ratio=adoption['comparison'][case]
  check(ratios[case]['component_seconds_ratio']==expected_ratio['component_seconds_ratio'],'recompute ratio '+case)
  check(ratios[case]['wire_added_bytes']==expected_ratio['wire_added_bytes'],'recompute wire '+case)
 check(read(old_root/'resource_probe.py')==read(new_root/'resource_probe.py'),'same exact probe bytes')
 check(read(old_root/'source_identity.py')==read(new_root/'source_identity.py'),'same exact identity tool')
 closure=load(old_root/'attempt-closure.json')
 check(closure['status']=='failed' and closure['failure_case']=='w014-normal-readback','early failure kept')
 check(closure['not_run']==['w014-extraction-mismatch'],'early missing path not adopted')
 with tarfile.open(ROOT/old_root/'failed-source-snapshot.tar.gz','r:gz') as archive:
  original={}
  for member in archive.getmembers():
   check(member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,'safe source member '+member.name)
   stream=archive.extractfile(member)
   original[member.name]=stream.read()
 check({n:sha(d) for n,d in original.items()}==old_files,'full original snapshot identity')
 W014={'derive/body_relations.py','derive/terminal_relations.py','domain/terminal_relations.py','normalization/terminal_relations.py','normalization/terminal_relations_codec.py'}
 old_runtime={n.removeprefix('layauto_v2/'):h for n,h in old_files.items() if n.startswith('layauto_v2/')}
 count=0
 for name,h in old_runtime.items():
  if name in W014:continue
  path='layauto_v2/'+name
  check(original[path]==read(path) and sha(read(path))==new_files[path]==h,'unchanged actual W013 dependency '+path)
  count+=1
 check(count==106,'all 106 non-W014 runtime files')
 final=load('docs/tasks/W014/development/targeted-r3-source.json')
 check(identity(final['files'])==final['source_id'],'final candidate manifest self identity')
 check(all(sha(read(n))==h for n,h in final['files'].items()),'final candidate all live bytes')
 delta=[n for n in set(new_files)|set(final['files']) if new_files.get(n)!=final['files'].get(n)]
 check(sorted(delta)==['tests/contracts/test_w014_body_scope.py','tests/contracts/test_w014_contracts.py'],'exactly two final test deltas')
 contract=read('tests/contracts/test_w014_contracts.py').decode()
 added="""    changed = dict(envelope.items())
    outputs = dict(envelope['result'].items())
    outputs['status'] = 'error'
    changed['result'] = outputs
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(changed))
    changed = dict(envelope.items())
    changed['captured_input_wire'] = FrozenMap({'ref': accepted.input.value.ref.to_value()})
    with pytest.raises(ValueError):
        codec.decode_record(canonical_bytes(changed))
"""
 check(contract.count(added)==1,'specific decoder negative tests added')
 before_contract=contract.replace(added,'')
 check(sha(before_contract.encode())==new_files['tests/contracts/test_w014_contracts.py'],'contract delta reconstructed by exact old hash')
 scope=read('tests/contracts/test_w014_body_scope.py').decode()
 marker='\n\ndef test_actual_local_opposite_body_overlap_is_a_rule_violation_without_erasing_contact('
 offset=scope.index(marker)
 before_scope=scope[:offset]+'\n'
 if sha(before_scope.encode())!=new_files['tests/contracts/test_w014_body_scope.py']:
  before_scope=scope[:offset]
 check(sha(before_scope.encode())==new_files['tests/contracts/test_w014_body_scope.py'],'scope delta reconstructed by exact old hash')
 patches=[]
 for name,before,after in (('test_w014_contracts.py',before_contract,contract),('test_w014_body_scope.py',before_scope,scope)):
  patches.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='R2/'+name,tofile='final/'+name))
 (OUT/'final_test_only_delta.patch').write_text(''.join(patches))
 prior=load('docs/tasks/W013/verification-r2/receipt.json')
 limits=load('docs/tasks/W013/verification-r2/resource-limits.json')
 check(prior['status']=='passed' and prior['matrix_workers']==2 and set(prior['actual_test_counts'].values())=={1731},'prior successful dual full matrices')
 observed={n:Path(n).read_text().strip() for n in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/memory.current')}
 check(all(observed[k]==limits['cgroup'][k] for k in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/cpu.max')),'same 16GiB four-CPU cgroup')
 result={'status':'resource-and-identity-audit-passed-not-final-product-review','checks':checks,'check_count':len(checks),
 'reference_source_id':adoption['reference_source_id'],'measured_source_id':adoption['current_source_id'],
 'final_candidate_source_id':final['source_id'],'resource_to_final_test_only_delta':sorted(delta),'runtime_input_config_unchanged':True,
 'recomputed_comparison':ratios,'observed_limits':observed,'non_W014_actual_byte_identity_count':count,
 'parallel_matrices_safe_assessment':True,'limitations':['One route sample is not a full matrix memory bound.','Only two interpreter processes, each pytest serial.','No overlapping build/install/smoke/extra capture chains.','Final clearance waits for targeted pass and frozen identity.']}
 (OUT/'resource_clearance_audit.stdout.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('status','check_count','final_candidate_source_id','runtime_input_config_unchanged','parallel_matrices_safe_assessment')},indent=2))


if __name__=='__main__':main()
