"""Resume only missing regression/type checks after environment disconnection.

Completed R3 package/install/smoke receipts are retained and verified against the
same frozen source. Interrupted pytest output is archived, never counted as a
complete run. This script does not rebuild or reinstall passed artifacts.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tarfile
import threading
import uuid

OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ipmr01_frozen_runner', OUT/'runner.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PRODUCT='73e38df8f932bbb5bd9caf074b442ad2f5c286e9'

def read(path):return json.loads(path.read_text())

def main():
    assert not (OUT/'receipt.json').exists(), 'Do not overwrite a completed run'
    source=read(OUT/'source-manifest.json')
    token=m.sha((OUT/'source-manifest.json').read_bytes())
    assert m.git('rev-parse','HEAD')==source['git_head']==PRODUCT
    assert len(source['files'])==245 and len(source['runtime_files'])==90
    assert m.selected_paths()==list(source['files'])
    assert {name:m.sha((m.ROOT/name).read_bytes()) for name in source['files']}==source['files']
    with tarfile.open(OUT/'source-snapshot.tar.gz') as archive:
        assert {f.name:m.sha(archive.extractfile(f).read()) for f in archive if f.isfile()}==source['files']
    package=read(OUT/'package-identity.json')
    installs=read(OUT/'installation-identity.json')
    assert set(installs)=={'310','312'}
    for kind in ('wheel','sdist'):
        row=package[kind]
        assert row['runtime_files']==source['runtime_files']
        assert m.sha(Path(row['path']).read_bytes())==row['sha256']
    for tag,row in installs.items():
        kind='wheel' if tag=='312' else 'sdist'
        assert row['source_sha256']==package[kind]['sha256']
        assert row['runtime_files']==m.runtime_manifest(Path(row['installed_package']).parent)==source['runtime_files']
    adopted=[]
    replaced={'environment-310','environment-312','pytest-310','pytest-312','typing-310','typing-312','pip-check-310','pip-check-312'}
    for path in sorted(OUT.glob('*.json')):
        row=read(path)
        if not isinstance(row,dict) or 'command' not in row or 'outputs' not in row or path.stem in replaced:
            continue
        if path.stem in ('exception-paths','historical-minimal'):
            continue  # separately retained contractual probes, not runner commands
        assert row['exit_code']==0 and row['head']==row['finished_head']==PRODUCT
        assert row['source_manifest_sha256']==token
        for stream in row['outputs'].values():
            assert m.sha((OUT/stream['path']).read_bytes())==stream['sha256']
        adopted.append((path.name,row))
    assert {name for name,_ in adopted}>={'build.json','installed-smoke-310.json','installed-smoke-312.json'}
    archived=OUT/'environment-disconnect-20261103'
    assert not archived.exists()
    archived.mkdir()
    archived_files={}
    for prefix in sorted(replaced|{'pytest-scope-310','pytest-scope-312'}):
        for path in OUT.glob(prefix+'.*'):
            if path.is_file():
                archived_files[path.name]=m.sha(path.read_bytes())
                shutil.copy2(path,archived/path.name)
    for name in ('final-r3-runner.stdout.txt','final-r3-runner.stderr.txt'):
        path=m.ENV/name
        shutil.copy2(path,archived/name)
        archived_files[name]=m.sha(path.read_bytes())
    resumed=datetime.now(timezone.utc).isoformat()
    metadata={'status':'resuming','product_sha':PRODUCT,'source_manifest_sha256':token,
              'resumed_utc':resumed,'source_files_revalidated':245,'runtime_files_revalidated':90,
              'both_packages_and_existing_install_trees_revalidated':True,
              'adopted_completed_command_receipts':[name for name,_ in adopted],
              'archived_partial_outputs':archived_files,
              'interruption':'Environment became unavailable; no pytest/typing final receipt existed and no runner process was alive at reconnect. The interrupted pytest exit codes are unavailable, and partial outputs are not full regression passes.',
              'scope':'Only missing full pytest/type/development pip checks rerun; prior completed build/install/smoke and independent probes remain bound to unchanged source.',
              'script_sha256':m.sha(Path(__file__).read_bytes())}
    (archived/'interruption.json').write_text(json.dumps(metadata,indent=2)+'\n')
    r=m.Runner.__new__(m.Runner)
    r.args=argparse.Namespace(out=OUT,base_sha=m.BASE,py310_path=['tests/contracts','tests/unit/test_w006_publication.py'],expected_312_count=1149,expected_310_count=None)
    r.out=OUT
    r.head=PRODUCT
    r.started=source['started_utc']
    r.commands=[row for _,row in adopted]
    r.identities={}
    r.lock=threading.Lock()
    r.test_counts={}
    r.test_scopes={}
    r.typing_counts={}
    r.run_id='resume-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    r.scratch=m.ENV/'runs'/r.run_id
    r.scratch.mkdir()
    r.smoke_cwd=r.scratch/'installed-cwd'
    r.smoke_cwd.mkdir()
    r.smoke=OUT/'installed_smoke.py'
    r.source=source
    r.source_sha=token
    r.snapshot_sha=m.sha((OUT/'source-snapshot.tar.gz').read_bytes())
    r.errors=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(r.matrix,tag) for tag in m.PY]
        for job in as_completed(jobs):
            try:job.result()
            except BaseException as exc:r.errors.append(type(exc).__name__+': '+str(exc))
    r.finish()
    receipt=read(OUT/'receipt.json')
    metadata['status']='passed' if not r.errors else 'failed'
    receipt['resumption']=metadata
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    (OUT/'resumption.json').write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
    assert not r.errors,r.errors
    print('Resumed final regression/type verification completed.',flush=True)

if __name__=='__main__':main()
