from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,subprocess,time
w=Path(__file__).resolve().parent;e=w.parent;rows=[];processes=[]
plugin=e/'w011_resource_gate.py'
(w/'w011_resource_gate.py').write_bytes(plugin.read_bytes())
for tag in ('310','312'):
 command=[str(e/f'dev{tag}/bin/python'),'-m','pytest','-p','no:cacheprovider','-p','w011_resource_gate','--w011-resource-lock',str(w/'shared.lock'),'--w011-resource-log',str(w/(tag+'.jsonl')),str(w/'test_w011_gate_fixture.py'),'-q']
 overrides={'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(w)}
 stdout=(w/(tag+'.stdout.txt')).open('wb');stderr=(w/(tag+'.stderr.txt')).open('wb')
 started=datetime.now(timezone.utc).isoformat();clock=time.perf_counter()
 process=subprocess.Popen(command,cwd=w,env=dict(os.environ,**overrides),stdout=stdout,stderr=stderr)
 processes.append((tag,command,overrides,process,stdout,stderr,started,clock))
for tag,command,overrides,process,stdout,stderr,started,clock in processes:
 code=process.wait();stdout.close();stderr.close()
 rows.append({'tag':tag,'command':command,'cwd':str(w),'environment_overrides':overrides,'started_at_utc':started,'subprocess_completion_observed_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-clock,'pid':process.pid,'exit_code':code})
 assert code==0,(tag,code)
 records=[json.loads(line) for line in (w/(tag+'.jsonl')).read_text().splitlines()]
 assert [r['event'] for r in records]==['WAIT','ACQUIRED','SESSION_FINISH_LOCK_RETAINED']
 assert all(r['lock_fd_inheritable'] is False for r in records)
 assert (w/(tag+'.jsonl.fixture.txt')).read_text().splitlines()==['session_fixture_setup_guarded','module_fixture_setup_guarded','test_body_guarded','module_fixture_teardown_guarded','session_fixture_teardown_guarded']
events={tag:[json.loads(line) for line in (w/(tag+'.jsonl')).read_text().splitlines()] for tag in ('310','312')}
identity={(r['lock_device'],r['lock_inode']) for rr in events.values() for r in rr};assert len(identity)==1
ordered=sorted(events.values(),key=lambda rr:rr[1]['observed_at_utc']);assert ordered[0][2]['observed_at_utc']<ordered[1][1]['observed_at_utc']
(w/'receipt.json').write_text(json.dumps({'status':'passed','scope':'Tiny execution-plugin probe only; not an official W011 regression or replacement for either complete matrix.','plugin_sha256':hashlib.sha256(plugin.read_bytes()).hexdigest(),'commands':rows,'events':events,'fixtures_guarded_before_setup_through_teardown':True,'same_inode':list(identity)[0]},indent=2)+'\n')
(w/'evidence-manifest.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(w.iterdir()) if p.is_file() and p.name not in ('evidence-manifest.json','shared.lock')},indent=2)+'\n')
print(json.dumps(rows,indent=2))
