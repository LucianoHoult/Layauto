"""PM read-only content and execution-receipt audit of W009 delivery."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path('/workspace/Layauto')
V = ROOT / 'docs/tasks/W009/verification'
EXPECTED_HEAD = '5b1d9b5196a7c5181822c4dd0f1bd2f678475116'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read(name):
    return json.loads((V / name).read_text())

def stream(data):
    values = []
    decoder = json.JSONDecoder()
    while data.strip():
        value, end = decoder.raw_decode(data.lstrip())
        values.append(value)
        data = data.lstrip()[end:]
    return values

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert head == EXPECTED_HEAD
manifest = read('source-manifest.json')
receipt = read('receipt.json')
assert sha((V/'source-manifest.json').read_bytes()) == receipt['source_manifest_sha256']
for name, digest in manifest['files'].items():
    assert sha((ROOT/name).read_bytes()) == digest, name
tracked = subprocess.check_output(['git','ls-files','layauto_v2','tests','README.md','pyproject.toml'], cwd=ROOT,text=True).splitlines()
relevant = {p for p in tracked if p.startswith('layauto_v2/') and (p.endswith('.py') or p.endswith('/py.typed')) or p.startswith(('tests/unit/','tests/contracts/')) and p.endswith('.py') or p in {'README.md','pyproject.toml'}}
assert relevant <= set(manifest['files']), sorted(relevant-set(manifest['files']))
runtime = {str(p.relative_to(ROOT/'layauto_v2')):sha(p.read_bytes()) for p in (ROOT/'layauto_v2').rglob('*') if p.is_file() and (p.suffix=='.py' or p.name=='py.typed')}
assert runtime == manifest['runtime_files']
with tarfile.open(V/'source-snapshot.tar.gz') as archive:
    snapshot = {m.name:sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
assert snapshot == manifest['files']
assert sha((V/'source-snapshot.tar.gz').read_bytes()) == receipt['source_snapshot_sha256']
evidence = read('evidence-manifest.json')['sha256']
for name, digest in evidence.items():
    assert sha((V/name).read_bytes()) == digest, name
commands=[]
assert receipt['status']=='passed' and len(receipt['commands'])==15
for cmd in receipt['commands']:
    assert cmd['exit_code']==0
    data=(V/cmd['output']).read_bytes()
    assert sha(data)==cmd['output_sha256']
    if cmd['output'].startswith('pytest-'):
        assert re.search(rb'914 passed',data)
    if cmd['output'].startswith('typing-'):
        assert b'Success: no issues found in 44 source files' in data
    commands.append({'output':cmd['output'],'sha256':sha(data),'exit_code':cmd['exit_code']})
assert sha((V/'verify_final.py').read_bytes()) == receipt['runner_sha256']
packages=read('package-identity.json')
for kind, item in packages.items():
    path=V/'dist'/Path(item['path']).name
    assert sha(path.read_bytes())==item['sha256']
    if kind=='wheel':
        with zipfile.ZipFile(path) as archive:
            files={n[len('layauto_v2/'):]:sha(archive.read(n)) for n in archive.namelist() if n.startswith('layauto_v2/') and (n.endswith('.py') or n.endswith('/py.typed'))}
    else:
        with tarfile.open(path) as archive:
            files={}
            for m in archive.getmembers():
                parts=Path(m.name).parts
                if m.isfile() and len(parts)>2 and parts[1]=='layauto_v2' and (parts[-1].endswith('.py') or parts[-1]=='py.typed'):
                    files['/'.join(parts[2:])]=sha(archive.extractfile(m).read())
    assert files == item['runtime_files'] == runtime
installs=read('installation-identity.json')
install_checks={}
for tag,item in installs.items():
    assert item['runtime_files']==runtime
    artifact=V/'dist'/Path(item['source_artifact']).name
    assert sha(artifact.read_bytes())==item['source_sha256']
    report=read('install-'+tag+'-report.json')
    package=next(x for x in report['install'] if x['metadata']['name'].lower()=='layauto')
    assert package['download_info']['url']==Path(item['source_artifact']).as_uri()
    info=package['download_info']['archive_info']
    digest=info.get('hashes',{}).get('sha256') or info['hash'].removeprefix('sha256=')
    assert digest==item['source_sha256']
    smoke=read('installed-smoke-'+tag+'.json')
    assert smoke['exit_code']==0 and '-I' in smoke['command'] and '-B' in smoke['command']
    assert not Path(smoke['cwd']).is_relative_to(ROOT)
    log=(V/smoke['output']).read_bytes()
    assert sha(log)==smoke['output_sha256']
    records=stream(log.decode())
    env,checks=records[0]['environment'],records[-1]['checks']
    assert env['isolated']==1 and env['dont_write_bytecode']
    assert env['package_manifest']==runtime and 'site-packages' in Path(env['installed_package']).parts
    assert checks['status']=='passed'
    install_checks[tag]={'log_and_record_consistent':True,'historical_installed_tree_present':Path(item['installed_package']).exists(),'installed_package':item['installed_package'],'smoke_cwd':smoke['cwd'],'source_artifact_sha256':item['source_sha256']}
protected = subprocess.check_output(['git','diff','--name-only','4975e565a33d9594782645b6ad0f944b78ee6ae8..'+head,'--','tests/fixtures','docs/tasks/W003','docs/tasks/W004*','docs/tasks/W005*','docs/tasks/W006*','docs/tasks/W007*','docs/tasks/W008*'], cwd=ROOT,text=True).splitlines()
assert not protected
review=ROOT/'docs/tasks/W009/review'
proofs=json.loads((review/'final-probe-identity-audit.json').read_text())
for name,item in proofs.items():
    actual=json.loads((review/name).read_text())
    assert item['all_match'] and actual['source_sha256']==item['source_sha256']
    for path,digest in item['source_sha256'].items():
        assert manifest['files'][path]==digest
performance=read('performance.json')
for path,digest in performance['source_sha256'].items():
    assert manifest['files'][path]==digest
assert sha((ROOT/'docs/tasks/W009/plan.md').read_bytes())=='b14226b6aa68dae2f9d305b57adf5f5bb27eaa6e61c4eb625847786133d37deb'
for tag in ['310','312']:
    assert b'67 passed' in (review/f'cr02-final{tag}.txt').read_bytes()
print(json.dumps({'status':'passed','head':head,'python':sys.version,'source_manifest_sha256':receipt['source_manifest_sha256'],'source_files':len(manifest['files']),'all_tracked_runtime_unit_contract_python_covered':True,'source_archive_files':len(snapshot),'runtime_files':len(runtime),'evidence_files':len(evidence),'commands':commands,'packages':{k:v['sha256'] for k,v in packages.items()},'installation_records':install_checks,'protected_changed_paths':protected,'final_probe_identities_checked':list(proofs),'plan_review_final_hash_matches':True,'performance_final_source_identity_matches':True,'limitations':['No new full pytest, mypy, build or installation was performed by this evidence audit.','Historical installed trees are absent on this host; prior independent installation-byte audit is adopted, not reproduced.','Current audit checks repository content, archive/package bytes and consistency of archived command/output/install records; it does not independently observe historical command execution.']},indent=2,sort_keys=True))
