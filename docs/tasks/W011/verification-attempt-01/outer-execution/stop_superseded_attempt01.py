from pathlib import Path
from datetime import datetime, timezone
import json,os,signal,time
work=Path('/workspace/work/w011-engineering')
out=Path('/workspace/Layauto/docs/tasks/W011/verification')
runner_pid=12362
receipt=out/'pytest-310.json'
def utc(): return datetime.now(timezone.utc).isoformat()
def process(pid):
 try:
  stat=Path(f'/proc/{pid}/stat').read_text();tail=stat[stat.rfind(')')+2:].split()
  return {'pid':pid,'ppid':int(tail[1]),'state':tail[0], 'command':Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()}
 except (OSError,ValueError): return None
def descendants(pid):
 rows=[r for p in Path('/proc').iterdir() if p.name.isdigit() and (r:=process(int(p.name)))]
 selected={pid};found=[]
 while True:
  extra=[r for r in rows if r['ppid'] in selected and r['pid'] not in selected]
  if not extra:return found
  found.extend(extra);selected.update(r['pid'] for r in extra)
start=utc()
while not receipt.exists():
 if not process(runner_pid): raise SystemExit('runner exited before pytest-310 command receipt exists')
 time.sleep(1)
record=json.loads(receipt.read_text())
if record['exit_code']==0:raise SystemExit('pytest310 passed; superseded stop not authorized')
state={'schema':'layauto-superseded-run/1','watcher_started_at_utc':start,'failure_receipt_first_observed_at_utc':utc(),'trigger_receipt':str(receipt),'trigger':record,'reason':'Final attempt 01 uses frozen 02725e2. target-only regression setup has wrong CDL token order and asserts before measurement; parent authorized preserving complete failed 310 and terminating superseded queued/running 312 after the failure receipt. Source/runtime is unchanged; replacement complete dual matrix will use independently reviewed corrected test setup.','runner':process(runner_pid),'signals':[]}
for sig in (signal.SIGSTOP,):
 try:os.kill(runner_pid,sig);state['signals'].append({'pid':runner_pid,'signal':sig.name,'sent_at_utc':utc()})
 except ProcessLookupError:state['signals'].append({'pid':runner_pid,'signal':sig.name,'already_exited_at_utc':utc()})
state['descendants_before_stop']=descendants(runner_pid)
for row in reversed(state['descendants_before_stop']):
 try:os.kill(row['pid'],signal.SIGTERM);state['signals'].append({'pid':row['pid'],'signal':'SIGTERM','sent_at_utc':utc()})
 except ProcessLookupError:state['signals'].append({'pid':row['pid'],'signal':'SIGTERM','already_exited_at_utc':utc()})
for sig in (signal.SIGTERM,signal.SIGCONT):
 try:os.kill(runner_pid,sig);state['signals'].append({'pid':runner_pid,'signal':sig.name,'sent_at_utc':utc()})
 except ProcessLookupError:state['signals'].append({'pid':runner_pid,'signal':sig.name,'already_exited_at_utc':utc()})
time.sleep(2)
state['observed_after_signals_at_utc']=utc()
state['remaining_processes']=[r for row in [state['runner']]+state['descendants_before_stop'] if row and (r:=process(row['pid']))]
(work/'superseded-attempt01.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(state,indent=2),flush=True)
