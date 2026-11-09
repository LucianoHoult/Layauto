from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
root=Path('/workspace/Layauto');work=Path('/workspace/work/w011-engineering')
source=root/'docs/tasks/W011/verification';target=root/'docs/tasks/W011/verification-attempt-01'
preflight=root/'docs/tasks/W011/preflight'
launch=json.loads((work/'final-launch-receipt.json').read_text())
stop=json.loads((work/'superseded-attempt01.json').read_text())
observe=json.loads((work/'final-observations.json').read_text())
assert launch['exit_code']!=0 and observe['state']=='completed_receipt_observed'
pytest=json.loads((source/'pytest-310.json').read_text());assert pytest['exit_code']!=0
assert not target.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source/'prepare_final.py')=='347c0017bc27b09d7ca135d6aaa92f58733a8f0dab078cc2ab5e8b576ca15050'
source_identity=json.loads((source/'source-manifest.json').read_text())
frozen=Path('/workspace/work/w011-final-02725e2/source')
assert all(sha(frozen/name)==digest for name,digest in source_identity['files'].items())
extra=source/'outer-execution';extra.mkdir()
for name in ('run_final.py','final-launch-plan.json','final-launch-receipt.json','final-runner.stdout.txt','final-runner.stderr.txt','observe_final.py','final-observations.json','stop_superseded_attempt01.py','superseded-attempt01.json'):
 shutil.copyfile(work/name,extra/name)
closure={'schema':'layauto-failed-attempt-closure/1','status':'failed_and_superseded','archived_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':source_identity['git_head'],'pytest310_receipt':'pytest-310.json','pytest310_exit_code':pytest['exit_code'],'source_snapshot_unchanged':True,'source_file_count':len(source_identity['files']),'scope':'Full Python 3.10 pytest completed with the failures shown in the retained original summary. Any queued/running Python 3.12 phase was terminated only after the 3.10 failure receipt. No final successful W011 claim, build or installation claim comes from this attempt.','termination_receipt':'outer-execution/superseded-attempt01.json','launcher_receipt':'outer-execution/final-launch-receipt.json','time_semantics':'Launcher started_at_utc is actual. Command elapsed times are actual. Observer timestamps are first observations, not inferred exact command start/end timestamps.','historical_output_path':str(source),'archived_output_path':str(target),'pytest310_summary_tail':(source/'pytest-310.stdout.txt').read_text()[-5000:],'memory_events_at_archive':Path('/sys/fs/cgroup/memory.events').read_text()}
(source/'attempt-closure.json').write_text(json.dumps(closure,indent=2)+'\n')
(source/'evidence-manifest.json').write_text(json.dumps({str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file() and p.name!='evidence-manifest.json'},indent=2)+'\n')
source.rename(target)
shutil.copyfile(Path(__file__),preflight/'archive_attempt01.py')
(preflight/'archive-manifest.json').write_text(json.dumps({str(p.relative_to(preflight)):sha(p) for p in sorted(preflight.rglob('*')) if p.is_file() and p.name!='archive-manifest.json'},indent=2)+'\n')
print(json.dumps({'archived_to':str(target),'source_commit':source_identity['git_head'],'exit_code':pytest['exit_code'],'manifest_sha256':sha(target/'evidence-manifest.json')},indent=2))
