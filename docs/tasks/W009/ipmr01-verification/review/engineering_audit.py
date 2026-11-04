"""Independent source/archive/package/actual-installed-tree identity audit."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import zipfile

root=Path.cwd()
execution=Path('/workspace/work/w009-ipmr01/docs/tasks/W009/ipmr01-verification')
out=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
head='73e38df8f932bbb5bd9caf074b442ad2f5c286e9'
observed_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
subprocess.run(['git','merge-base','--is-ancestor',head,observed_head],check=True)
manifest=json.loads((execution/'source-manifest.json').read_text())
assert manifest['git_head']==head
assert len(manifest['files'])==245 and len(manifest['runtime_files'])==90
for name,digest in manifest['files'].items():
    raw=(root/name).read_bytes()
    assert sha(raw)==digest,(name,'review source mismatch')
    assert raw==subprocess.check_output(['git','show',head+':'+name]),(name,'git mismatch')
with tarfile.open(execution/'source-snapshot.tar.gz','r:gz') as archive:
    members=archive.getmembers()
    assert all(entry.isfile() for entry in members)
    assert {entry.name:sha(archive.extractfile(entry).read()) for entry in members}==manifest['files']
package=json.loads((execution/'package-identity.json').read_text())
assert package['source_manifest_sha256']==sha((execution/'source-manifest.json').read_bytes())
packages={}
for kind in ('wheel','sdist'):
    artifact=Path(package[kind]['path'])
    assert sha(artifact.read_bytes())==package[kind]['sha256']
    if kind=='wheel':
        with zipfile.ZipFile(artifact) as archive:
            actual={name[len('layauto_v2/'):]:sha(archive.read(name)) for name in archive.namelist() if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
    else:
        with tarfile.open(artifact,'r:gz') as archive:
            actual={entry.name.split('/layauto_v2/',1)[1]:sha(archive.extractfile(entry).read()) for entry in archive.getmembers() if entry.isfile() and '/layauto_v2/' in entry.name and (entry.name.endswith('.py') or entry.name.endswith('/py.typed'))}
    assert actual==manifest['runtime_files']==package[kind]['runtime_files']
    packages[kind]=dict(path=str(artifact),sha256=package[kind]['sha256'],runtime_files=len(actual))

identity_code='''import hashlib,importlib.metadata,json,pathlib,sys,layauto_v2
p=pathlib.Path(layauto_v2.__file__).resolve().parent
d=importlib.metadata.distribution("layauto")
print(json.dumps({"python":sys.version,"executable":sys.executable,"package":str(p),"sys_path":sys.path,"direct_url":json.loads(d.read_text("direct_url.json")),"runtime":{str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob("*") if f.is_file() and (f.suffix==".py" or f.name=="py.typed")}},sort_keys=True,indent=2))'''
installations=json.loads((execution/'installation-identity.json').read_text())
observed={}
for tag,installation in installations.items():
    command=[installation['python'],'-I','-B','-c',identity_code]
    raw=subprocess.check_output(command,cwd=installation['cwd'])
    (out/('actual-installed-'+tag+'.json')).write_bytes(raw)
    value=json.loads(raw)
    assert value['runtime']==manifest['runtime_files']==installation['runtime_files']
    package_path=Path(value['package'])
    assert 'site-packages' in package_path.parts
    assert not package_path.is_relative_to(root)
    assert not package_path.is_relative_to(execution.parents[3])
    assert str(root) not in value['sys_path'] and str(execution.parents[3]) not in value['sys_path']
    direct=value['direct_url']
    assert direct['url']==Path(installation['source_artifact']).as_uri()
    info=direct['archive_info']
    digest=info.get('hashes',{}).get('sha256',info.get('hash','').removeprefix('sha256='))
    assert installation['source_sha256']==sha(Path(installation['source_artifact']).read_bytes())
    if digest:
        assert digest==installation['source_sha256']
    assert sha((execution/installation['pip_report']).read_bytes())==installation['pip_report_sha256']
    pip_report=json.loads((execution/installation['pip_report']).read_text())
    layauto_rows=[row for row in pip_report['install'] if row['metadata']['name'].lower()=='layauto']
    assert len(layauto_rows)==1
    download=layauto_rows[0]['download_info']
    assert download['url']==direct['url']
    report_info=download['archive_info']
    report_sha=report_info.get('hashes',{}).get('sha256',report_info.get('hash','').removeprefix('sha256='))
    assert report_sha==installation['source_sha256']
    observed[tag]=dict(command=command,cwd=installation['cwd'],python=value['python'],package=value['package'],runtime_files=len(value['runtime']),direct_url=direct,installed_metadata_archive_hash_present=bool(digest),source_artifact_sha256=installation['source_sha256'])

if '--packages-only' in sys.argv:
    partial=dict(head=head,source_manifest_sha256=sha((execution/'source-manifest.json').read_bytes()),source_files=len(manifest['files']),runtime_files=90,packages=packages,actual_installations=observed,scope='Actual source/snapshot/package/installed runtime and direct_url metadata audited; engineering receipt still pending.')
    (out/'package-install-audit.json').write_text(json.dumps(partial,indent=2,sort_keys=True)+'\n')
    print(json.dumps(partial,indent=2,sort_keys=True))
    raise SystemExit(0)
receipt=json.loads((execution/'receipt.json').read_text())
assert receipt['status']=='passed' and not receipt['errors']
assert receipt['head']==head==receipt['finished_head']
assert receipt['source_identity_rechecked_after_all_commands']
assert receipt['source_manifest_sha256']==sha((execution/'source-manifest.json').read_bytes())
assert receipt['source_snapshot_sha256']==sha((execution/'source-snapshot.tar.gz').read_bytes())
assert receipt['actual_test_counts']['312']==1149
assert receipt['typing_source_counts']=={'310':44,'312':44}
assert receipt['python310_complete_v2_rerun'] is False
assert receipt['test_scopes']=={
    '310':{'paths':['tests/contracts','tests/unit/test_w006_publication.py'],'complete_v2':False},
    '312':{'paths':['tests/contracts','tests/unit'],'complete_v2':True},
}
assert receipt['runner_sha256']==sha((execution/'runner.py').read_bytes())
assert receipt['smoke_script_sha256']==sha((execution/'installed_smoke.py').read_bytes())
resumption=receipt['resumption']
assert resumption==json.loads((execution/'resumption.json').read_text())
assert resumption['status']=='passed'
assert resumption['product_sha']==head
assert resumption['source_manifest_sha256']==receipt['source_manifest_sha256']
assert resumption['source_files_revalidated']==245 and resumption['runtime_files_revalidated']==90
assert resumption['both_packages_and_existing_install_trees_revalidated'] is True
assert resumption['script_sha256']==sha((execution/'resume_verification.py').read_bytes())
archive=execution/'environment-disconnect-20261103'
interruption=json.loads((archive/'interruption.json').read_text())
assert interruption==dict(resumption,status='resuming')
for name,digest in resumption['archived_partial_outputs'].items():
    assert sha((archive/name).read_bytes())==digest,(name,'interrupted evidence mismatch')
adopted=set(resumption['adopted_completed_command_receipts'])
expected_adopted={'build-environment-312.json','build.json'}|{
    prefix+'-'+tag+'.json' for tag in ('310','312') for prefix in (
        'clean-environment-before-install','clean-environment-installed','create-install',
        'install','installed-identity','installed-pip-check','installed-smoke')
}
assert adopted==expected_adopted
rerun={prefix+'-'+tag+'.json' for tag in ('310','312') for prefix in ('environment','pytest','typing','pip-check')}
seen=set()
for row in receipt['commands']:
    assert row['exit_code']==0
    assert row['head']==row['finished_head']==head
    assert row['source_manifest_sha256']==receipt['source_manifest_sha256']
    stdout=Path(row['outputs']['stdout']['path'])
    assert stdout.name.endswith('.stdout.txt') and stdout.parent==Path('.')
    name=stdout.name.removesuffix('.stdout.txt')+'.json'
    assert name not in seen
    seen.add(name)
    assert row==json.loads((execution/name).read_text()),(name,'combined receipt row mismatch')
    assert row['started_utc'] < resumption['resumed_utc'] if name in adopted else row['started_utc'] >= resumption['resumed_utc']
    for stream,value in row['outputs'].items():
        assert sha((execution/value['path']).read_bytes())==value['sha256']
assert seen==adopted|rerun
for tag in ('310','312'):
    summary=(execution/('pytest-'+tag+'.stdout.txt')).read_text()
    assert re.findall(r'(\d+) passed(?:,|\s+in)',summary)==[str(receipt['actual_test_counts'][tag])]
    assert not re.search(r'\d+ (?:failed|errors?|skipped|xfailed|xpassed)',summary)
    assert re.search(r'Success: no issues found in 44 source files?',(execution/('typing-'+tag+'.stdout.txt')).read_text())
result=dict(head=head,source_manifest_sha256=receipt['source_manifest_sha256'],source_files=len(manifest['files']),snapshot_sha256=receipt['source_snapshot_sha256'],runtime_files=90,packages=packages,actual_installations=observed,command_count=len(receipt['commands']),all_command_outputs_match=True,test_counts=receipt['actual_test_counts'],typing_counts=receipt['typing_source_counts'],python310_complete_v2_rerun=receipt['python310_complete_v2_rerun'],test_scopes=receipt['test_scopes'],resumption_audit=dict(resumed_utc=resumption['resumed_utc'],adopted_completed_commands=sorted(adopted),rerun_commands=sorted(rerun),archived_partial_outputs_count=len(resumption['archived_partial_outputs']),archived_partial_outputs_rehashed=True,partial_pytest_not_counted_as_pass=True,resume_script_sha256=resumption['script_sha256']),scope='Reviewer read archive/package bytes and actual installed trees/direct_url metadata; build/install and full test runs are independently audited executor receipts, not reviewer reruns. Completed November 3 build/install/smoke commands were adopted only for identical frozen source; missing pytest/typing/development pip checks were rerun November 4, and interrupted partial output is archived without a regression pass claim.')
(out/'engineering-audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
