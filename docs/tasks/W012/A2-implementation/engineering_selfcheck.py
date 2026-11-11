"""Lightweight runner guard checks; does not execute any product matrix."""
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'engineering-preparation'
result_path=OUT/'selfcheck-result.json'
if result_path.exists():
    raise RuntimeError('Preserve existing selfcheck evidence')
rows=[]
for name in ('engineering_tools.py','installed_smoke.py'):
    data=(HERE/name).read_bytes(); ast.parse(data)
    rows.append({'name':name,'sha256':hashlib.sha256(data).hexdigest(),'syntax':'parsed'})
with tempfile.TemporaryDirectory(prefix='a2-engineering-selfcheck-',dir=ROOT/'work') as directory:
    temp=Path(directory); out=temp/'out'; out.mkdir(); sentinel=out/'prior'; sentinel.write_bytes(b'keep original')
    command=[sys.executable,'-B',str(HERE/'engineering_tools.py'),'--root',str(ROOT),'--out',str(out),'--work',str(temp/'work'),'--smoke',str(HERE/'installed_smoke.py'),'--python310',sys.executable,'--python312',sys.executable,'--expected-tests','1656']
    completed=subprocess.run(command,capture_output=True)
    (OUT/'selfcheck-refusal.stdout.txt').write_bytes(completed.stdout)
    (OUT/'selfcheck-refusal.stderr.txt').write_bytes(completed.stderr)
    assert completed.returncode!=0 and b'Evidence output must be absent or empty' in completed.stderr
    assert sentinel.read_bytes()==b'keep original' and not (temp/'work').exists()
    rows.append({'check':'existing evidence refuses before new work directory','exit_code':completed.returncode,'command':command})
result={'status':'passed','at_utc':datetime.now(timezone.utc).isoformat(),'checks':rows,'heavy_matrix_run':False}
result_path.write_text(json.dumps(result,indent=2)+'\n')
print('PASS: syntax and existing-evidence guard; no product matrix executed')
