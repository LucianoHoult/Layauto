"""PM independent static engineering evidence audit; no product imports."""
from pathlib import Path
import hashlib, io, json, re, subprocess, tarfile, zipfile, sys
from datetime import datetime, timezone

ROOT=Path('/workspace/Layauto')
BASE=ROOT/'docs/tasks/W011'
OUT=Path(__file__).parent
V=BASE/'verification'; R=BASE/'resources'
SOURCE='e89bdaa6a091f56cfaf7862dced7232d34e22514'
HEAD='3c464baade7b6ea8c712cfb84265490b8e3f754e'
checks=[]; issues=[]
def sha(b): return hashlib.sha256(b).hexdigest()
def h(p): return sha(p.read_bytes())
def j(p): return json.loads(p.read_text())
def check(name,ok,detail=None):
    checks.append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:issues.append(name)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def index(directory,name='evidence-manifest.json'):
    expected=j(directory/name)
    actual={str(p.relative_to(directory)):h(p) for p in directory.rglob('*') if p.is_file() and p.name!=name}
    check(str(directory.relative_to(BASE))+' index exact',actual==expected,{'files':len(expected),'sha256':h(directory/name)})
def command(d,row):
    check(str(d.relative_to(BASE))+': '+row.get('case',row.get('stdout','command'))+' exit/times',
          row['exit_code']==0 and row['started_at_utc']<row['finished_at_utc'])
    for s in ('stdout','stderr'):
        name=row.get(s,row.get('case','')+'.'+s+'.txt')
        check(name+' bytes',h(d/name)==row[s+'_sha256'])

check('head identity',git('rev-parse','HEAD').decode().strip()==HEAD)
meta=j(V/'source-manifest.json'); files=meta['files']; runtime=meta['runtime_files']
check('source manifest count/version',meta['git_head']==SOURCE and len(files)==262 and len(runtime)==100)
check('all262 current bytes',all(h(ROOT/p)==v for p,v in files.items()))
check('all262 frozen Git bytes',all(sha(git('show',SOURCE+':'+p))==v for p,v in files.items()))
check('all262 delivery Git bytes',all(sha(git('show',HEAD+':'+p))==v for p,v in files.items()))
with tarfile.open(V/'source-snapshot.tar.gz') as a:
    members=[m for m in a.getmembers() if m.isfile()]
    actual={m.name:sha(a.extractfile(m).read()) for m in members}
    check('snapshot262 exact unique',len(members)==len(actual)==262 and actual==files)
check('runtime unchanged since repaired product',not git('diff','8917d38',SOURCE,'--','layauto_v2'))
check('fixture and current-work unchanged by execution',not git('diff','81e01da',HEAD,'--','tests/fixtures','docs/current-work.md'))

rec=j(V/'receipt.json')
check('engineering commands count',len(rec['commands'])==21)
for item,key in [('source-manifest.json','source_manifest_sha256'),('source-snapshot.tar.gz','source_snapshot_sha256'),('baseline-collection.txt','baseline_collection_sha256'),('prepare_final.py','runner_sha256'),('installed_smoke.py','smoke_sha256')]:
    check('receipt identity '+item,h(V/item)==rec[key])
for row in rec['commands']:
    command(V,row)
    check('command index '+row['stdout'],j(V/(row['stdout'].removesuffix('.stdout.txt')+'.json'))==row)
index(V)
ids=lambda p:[line for line in p.read_text().splitlines() if line.startswith('tests/') and '::' in line]
old=set(ids(V/'baseline-collection.txt'))
matrix={}; gate=j(V/'resource-gate-validation.json')
for tag in ('310','312'):
    case_ids=ids(V/f'collection-{tag}.stdout.txt')
    actual=set(case_ids)
    check('matrix IDs '+tag,len(case_ids)==len(actual)==1605 and len(old)==1465 and old<=actual and len(actual-old)==140)
    check('all extra IDs W011 '+tag,all('/test_w011_' in p for p in actual-old))
    text=(V/f'pytest-{tag}.stdout.txt').read_text()
    summary=re.findall(r'^(\d+) passed in ([\d.]+)s',text,re.M)
    check('actual pytest stdout '+tag,len(summary)==1 and summary[0][0]=='1605')
    check('actual typing stdout '+tag,(V/f'typing-{tag}.stdout.txt').read_text().strip()=='Success: no issues found in 54 source files')
    events=[json.loads(line) for line in (V/f'resource-gate-{tag}.jsonl').read_text().splitlines()]
    check('actual gate events '+tag,events==gate['events'][tag] and [p['event'] for p in events]==['WAIT','ACQUIRED','SESSION_FINISH_LOCK_RETAINED','RELEASED'])
    wait=(datetime.fromisoformat(events[1]['observed_at_utc'])-datetime.fromisoformat(events[0]['observed_at_utc'])).total_seconds()
    matrix[tag]={'test_count':len(actual),'baseline_count':len(old),'extra_count':len(actual-old),'pytest_seconds':float(summary[0][1]),'command_seconds':j(V/f'pytest-{tag}.json')['elapsed_seconds'],'gate_wait_seconds':wait}
check('gate correct source',h(V/'w011_resource_gate.py')==rec['resource_gate']['sha256'])
check('gate W011 serialized',gate['events']['312'][2]['observed_at_utc']<gate['events']['310'][1]['observed_at_utc'])

packages=j(V/'package-identity.json')
for kind,entry in packages.items():
    p=V/'dist'/Path(entry['path']).name
    check('artifact bytes '+kind,h(p)==entry['sha256'])
    if kind=='wheel':
        with zipfile.ZipFile(p) as a:
            names=[n for n in a.namelist() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))]
            pairs={n.removeprefix('layauto_v2/'):sha(a.read(n)) for n in names}
            count=len(names)
    else:
        with tarfile.open(p) as a:
            members=[m for m in a.getmembers() if m.isfile() and '/layauto_v2/' in m.name and (m.name.endswith('.py') or m.name.endswith('/py.typed'))]
            pairs={m.name.split('/layauto_v2/',1)[1]:sha(a.extractfile(m).read()) for m in members};count=len(members)
    check('artifact100 exact '+kind,count==len(pairs)==100 and pairs==entry['runtime_files']==runtime)
install=j(V/'installation-identity.json'); installations={}
for tag,entry in install.items():
    p=Path(entry['package']).parent
    exists=p.is_dir()
    check('archived install100 provenance '+tag,entry['runtime_files']==runtime and len(entry['runtime_files'])==100 and entry['fresh_environment'] is True and entry['isolated']==1 and entry['artifact_sha256']==packages['sdist' if tag=='310' else 'wheel']['sha256'] and 'site-packages' in p.parts)
    if exists:
        pairs={str(f.relative_to(p)):h(f) for f in p.rglob('*') if f.is_file() and (f.suffix=='.py' or f.name=='py.typed')}
        check('actual existing install100 '+tag,pairs==runtime)
    smoke=j(V/f'installed-smoke-{tag}.stdout.txt'); cmd=j(V/f'installed-smoke-{tag}.json')
    check('archived isolated source-external smoke '+tag,cmd['command'][1:3]==['-I','-B'] and smoke['package']==entry['package'] and smoke['attempt_unchanged'] and cmd['cwd']=='/workspace/work/w011-final-e89bdaa/installed-cwd')
    for case in ('direct','readback','extraction_mismatch'):
        s=smoke[case]
        check('archived smoke facts '+tag+' '+case,s['counts']=={'MN0':4 if case=='extraction_mismatch' else 5,'MP0':7} and s['difference_count']==(1 if case=='extraction_mismatch' else 0) and s['comparison_status']==('mismatch' if case=='extraction_mismatch' else 'equal'))
    installations[tag]={'actual_tree_exists_here':exists,'archived_runtime_files':100,'package':str(p),'new_installation_performed':False}

resource=j(R/'receipt.json'); src=j(R/'source-identity.json')
check('resource proof same frozen source',src==resource['source_identity'] and src['tested_source_commit']==SOURCE and src['verification_receipt_sha256']==h(V/'receipt.json') and src['verification_source_manifest_sha256']==h(V/'source-manifest.json') and src['runtime_files']==runtime)
check('resource scripts',src['probe_sha256']==h(R/'resource_probe.py') and src['launcher_sha256']==h(R/'run_resources.py'))
check('resource process scope',resource['one_fresh_process_per_case'] is True and resource['full_source_tests_config_unchanged'] is True)
resource_cases={}
for row in resource['commands']:
    command(R,row)
    case=row['case'];data=j(R/(case+'.json'));facts=data['result']
    check('resource same source '+case,data['git_head']==SOURCE and data['source_unchanged_during_probe'] and row['runtime_matches_verified_snapshot_before_and_after'])
    check('resource result actual '+case,facts['public_roundtrip_equal'] and facts['status']=='success' and facts['raw_capture_count']==len(facts['capture_sources'])==31 and facts['raw_capture_bytes']==sum(p['bytes'] for p in facts['capture_sources'])==280706 and facts['FIN_evaluations']==36 and facts['counts']=={'MN0':4 if case=='extraction-mismatch' else 5,'MP0':7})
    resource_cases[case]={'wire_bytes':facts['result_wire_bytes'],'peak_rss_kib':data['process_peak_rss_kib'],'peak_rss_gib':data['process_peak_rss_kib']/1024**2,'wall_seconds':data['wall_seconds'],'command_seconds':row['elapsed_seconds'],'raw_capture_bytes':facts['raw_capture_bytes']}
index(R)
obs=BASE/'preflight/final-attempt02'; summary=j(obs/'resource-observations-summary.json'); samples=[json.loads(line) for line in (obs/'resource-observations.jsonl').read_text().splitlines()]
check('resource observer original bytes',h(obs/'resource-observations.jsonl')==summary['raw_sha256'])
check('observer sample count',len(samples)==summary['sample_count']==1399)
check('observer maximum cgroup',max(s['cgroup_memory_current_bytes'] for s in samples)==summary['max_sampled_cgroup_memory_bytes'])
peaks={}
for s in samples:
    for p in s['processes']: peaks[str(p['pid'])]=max(peaks.get(str(p['pid']),0),p['rss_kib'])
check('observer maximum process recomputed',peaks=={k:p['rss_kib'] for k,p in summary['max_sampled_process_rss_by_pid'].items()})
old_dir=BASE/'verification-attempt-01'
check('old failed matrix retained honestly',j(old_dir/'pytest-310.json')['exit_code']==1 and '2 failed, 1603 passed in 9500.70s' in (old_dir/'pytest-310.stdout.txt').read_text())
index(old_dir)
result={'schema':'w011-pm-static-evidence-audit/1','at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'command':[sys.executable,*sys.argv],'script_sha256':h(Path(__file__)),'delivery_head':HEAD,'frozen_source':SOURCE,'checks':checks,'must_fix':issues,'source_files':len(files),'runtime_files':len(runtime),'source_manifest_sha256':h(V/'source-manifest.json'),'matrix':matrix,'installations':installations,'resource_cases':resource_cases,'observer':{'sample_count':len(samples),'max_sampled_cgroup_bytes':summary['max_sampled_cgroup_memory_bytes'],'max_sampled_processes':summary['max_sampled_process_rss_by_pid']},'limitations':['Static bytes/archive/log/provenance audit only, no product imports, no heavy codec, pytest, build or reinstall.','Archived installation manifests and smoke output audited; absent original installation trees cannot be re-observed.','Fresh-process ru_maxrss covers whole process, not incremental W011 allocations; long-running matrix/smoke discrete samples have different scope.','Finite resource observations are not production input or concurrency bounds.']}
(OUT/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'must_fix':issues,'resource_cases':resource_cases,'installations':installations},ensure_ascii=False,indent=2))
raise SystemExit(bool(issues))
