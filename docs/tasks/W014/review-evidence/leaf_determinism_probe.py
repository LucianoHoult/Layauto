"""Fresh processes use distinct hash seeds; only small public W014 leaf wire."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
code='''from leaf_storage_probe import make
from layauto_v2.normalization.terminal_relations_codec import encode_record,decode_record,record_digest
import hashlib,json
row=make()
wire=encode_record(row)
restored=decode_record(wire)
assert restored==row and encode_record(restored)==wire
assert record_digest(row)==hashlib.sha256(wire).hexdigest()
print(json.dumps({'wire_sha256':hashlib.sha256(wire).hexdigest(),'relation_ref':row.ref.sha256,'wire_bytes':len(wire)}))
'''
results=[]
for seed in ('11','997'):
 env=dict(os.environ,PYTHONHASHSEED=seed,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root))
 done=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True,check=True)
 results.append({'hash_seed':seed,**json.loads(done.stdout)})
assert results[0]['wire_sha256']==results[1]['wire_sha256']
assert results[0]['relation_ref']==results[1]['relation_ref']
print(json.dumps({'fresh_processes':results,'status':'passed'},indent=2))
