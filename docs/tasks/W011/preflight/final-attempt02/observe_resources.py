"""Read-only sampled process/cgroup observations; no timing or memory maxima claim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,time
work=Path(__file__).resolve().parent
start=json.loads((work/'launch-start.json').read_text());runner=start['pid']
clock=lambda:datetime.now(timezone.utc).isoformat()
def read(path):
 try:return Path(path).read_text().strip()
 except OSError:return None

def processes():
 rows=[]
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   stat=(path/'stat').read_text();tail=stat[stat.rfind(')')+2:].split();status=(path/'status').read_text().splitlines()
   rss=next((int(line.split()[1]) for line in status if line.startswith('VmRSS:')),0)
   command=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()
   rows.append({'pid':int(path.name),'ppid':int(tail[1]),'state':tail[0],'rss_kib':rss,'command':command})
  except (OSError,ValueError):continue
 selected={runner};found=[r for r in rows if r['pid']==runner]
 while True:
  extra=[r for r in rows if r['ppid'] in selected and r['pid'] not in selected]
  if not extra:return found
  found.extend(extra);selected.update(r['pid'] for r in extra)

before={name:read('/sys/fs/cgroup/'+name) for name in ('memory.max','cpu.max','memory.events','memory.peak')}
started=clock();peaks={};sample_count=0;cgroup_peak=0
with (work/'resource-observations.jsonl').open('w') as output:
 while True:
  rows=processes();current=read('/sys/fs/cgroup/memory.current')
  if current is not None:cgroup_peak=max(cgroup_peak,int(current))
  for row in rows:
   key=str(row['pid'])
   if key not in peaks or peaks[key]['rss_kib']<row['rss_kib']:peaks[key]={**row,'observed_at_utc':clock()}
  output.write(json.dumps({'observed_at_utc':clock(),'processes':rows,'cgroup_memory_current_bytes':int(current) if current is not None else None,'cgroup_memory_events':read('/sys/fs/cgroup/memory.events')})+'\n');output.flush();sample_count+=1
  if (work/'final-launch-receipt.json').exists():break
  time.sleep(10)
summary={'schema':'layauto-resource-observations/1','command':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'started_at_utc':started,'finished_at_utc':clock(),'sample_count':sample_count,'sampling_interval_seconds':10,'scope':'Shared session cgroup and runner descendant processes, sampled only; sampled RSS is not a guaranteed maximum. No test, fixture or process scheduling is changed.','initial_limits_and_cumulative_events':before,'final_cumulative_events':{name:read('/sys/fs/cgroup/'+name) for name in ('memory.events','memory.peak')},'max_sampled_cgroup_memory_bytes':cgroup_peak,'max_sampled_process_rss_by_pid':peaks,'raw_sha256':hashlib.sha256((work/'resource-observations.jsonl').read_bytes()).hexdigest()}
(work/'resource-observations-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'sample_count':sample_count,'max_sampled_cgroup_memory_bytes':cgroup_peak,'summary':str(work/'resource-observations-summary.json')}),flush=True)
