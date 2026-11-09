"""Independent first-observation UTCs, never presented as command start/end UTC."""
from pathlib import Path
from datetime import datetime,timezone
import json,time
w=Path('/workspace/work/w011-engineering');out=Path('/workspace/Layauto/docs/tasks/W011/verification');target=w/'final-observations.json';seen=set();rows=[]
start=datetime.now(timezone.utc).isoformat()
while True:
 for path in sorted(out.glob('*.json')):
  if path.name in seen:
   continue
  try:
   record=json.loads(path.read_text())
  except (OSError,json.JSONDecodeError):
   continue
  if not isinstance(record,dict) or 'command' not in record or 'exit_code' not in record:
   continue
  seen.add(path.name)
  rows.append({'receipt':path.name,'first_observed_at_utc':datetime.now(timezone.utc).isoformat(),'receipt_mtime_ns':path.stat().st_mtime_ns,'command_elapsed_seconds':record.get('elapsed_seconds'),'exit_code':record['exit_code']})
  target.write_text(json.dumps({'schema':'layauto-command-observations/1','monitor_started_at_utc':start,'meaning':'First observed completed command receipt, not the command exact start/end UTC. Receipt records retain actual command elapsed seconds.','observations':rows,'state':'observing'},indent=2)+'\n')
 receipt=w/'final-launch-receipt.json'
 if receipt.exists():
  try:
   final=json.loads(receipt.read_text())
  except (OSError,json.JSONDecodeError):
   pass
  else:
   target.write_text(json.dumps({'schema':'layauto-command-observations/1','monitor_started_at_utc':start,'meaning':'First observed completed command receipt, not the command exact start/end UTC. Receipt records retain actual command elapsed seconds.','observations':rows,'state':'completed_receipt_observed','runner_observed_completion_at_utc':datetime.now(timezone.utc).isoformat(),'runner_receipt_mtime_ns':receipt.stat().st_mtime_ns,'runner_started_at_utc_from_launcher':final['started_at_utc'],'runner_elapsed_seconds':final['elapsed_seconds'],'runner_exit_code':final['exit_code']},indent=2)+'\n')
   break
 time.sleep(5)
