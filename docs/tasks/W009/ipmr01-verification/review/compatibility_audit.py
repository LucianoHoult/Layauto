"""Independently bind the executor's same-capture baseline/final comparison."""
import hashlib
import json
from pathlib import Path
import subprocess

root=Path.cwd()
execution=Path('/workspace/work/w009-ipmr01/docs/tasks/W009/ipmr01-verification')
sha=lambda data:hashlib.sha256(data).hexdigest()
receipt=json.loads((execution/'compatibility.json').read_text())
assert receipt['status']=='passed'
base=json.loads((execution/'compatibility-baseline.stdout.json').read_text())
final=json.loads((execution/'compatibility-final.stdout.json').read_text())
for path,digest in receipt['outputs'].items():
    assert sha((execution/path).read_bytes())==digest
for name,value in (('baseline',base),('final',final)):
    commit=receipt['baseline_sha'] if name=='baseline' else receipt['final_sha']
    for path,digest in value['runtime_files'].items():
        assert sha(subprocess.check_output(['git','show',commit+':layauto_v2/'+path]))==digest
        assert sha((Path(value['package'])/path).read_bytes())==digest
    assert receipt['commands'][name]['exit_code']==0
    assert Path(value['package']).parent==Path(receipt['commands'][name]['PYTHONPATH'])
assert base['source_uris']==final['source_uris']
assert base['fixture']==final['fixture']
assert base['wire']==final['wire']==receipt['wire_and_digest_identical']
assert base['semantic_digest']==final['semantic_digest']==receipt['semantic_digest']
out=dict(baseline=receipt['baseline_sha'],final=receipt['final_sha'],runtime_files_per_version=len(final['runtime_files']),source_uris_identical=True,wire_and_digest_identical=final['wire'],semantic_digest=final['semantic_digest'],all_evidence_hashes_match=True,scope='Independently audited both runtime trees/Git objects and the executor comparison receipts; did not rerun the baseline comparison.')
Path('docs/tasks/W009/ipmr01-verification/review/compatibility-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
