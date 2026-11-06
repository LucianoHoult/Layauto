"""Independent read-only W010 identity/guard audit; no historical evidence changes."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
V = ROOT / 'docs/tasks/W010/verification'
MAIN = '3be0b98359038bab6c23980b55a48987cc71a369'
PREP = '9758a157115cc22d91ce095ac2002209b9f210d3'
FROZEN = '0f5029df935bc0acd106aad1bc2be81304d4f442'
DELIVERY = 'ca39aedcb71fda02f77ffda1eb5d5dddc598226e'
HEAD = 'c4909ab679d0c0806200fcb132db8a5de1ad3e75'
checks = []
def sha(data):
    return hashlib.sha256(data).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
def read(path):
    return json.loads(Path(path).read_text())
def check(name, value, details=None):
    checks.append({'name': name, 'pass': bool(value), 'details': details})
def ids(text):
    return {line for line in text.splitlines() if line.startswith('tests/') and '::' in line}
def run(name, command, cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONPATH=str(cwd), MPLCONFIGDIR='/tmp/w010-evidence-mpl')
    start = time.monotonic()
    p = subprocess.run(command, cwd=cwd, env=env, capture_output=True)
    (OUT / f'evidence-{name}.stdout.txt').write_bytes(p.stdout)
    (OUT / f'evidence-{name}.stderr.txt').write_bytes(p.stderr)
    result = {'command': command, 'cwd': str(cwd), 'exit_code': p.returncode,
              'elapsed_seconds': time.monotonic()-start, 'environment_overrides':
              {k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONPATH','MPLCONFIGDIR')},
              'stdout_sha256': sha(p.stdout), 'stderr_sha256': sha(p.stderr)}
    (OUT / f'evidence-{name}.json').write_text(json.dumps(result, indent=2)+'\n')
    check(name+' exit', p.returncode == 0, result)
    return p.stdout.decode()

check('review HEAD identity', git('rev-parse','HEAD').decode().strip() == HEAD)
diffs = {}
for label, a, b in [('main_to_head',MAIN,HEAD),('prep_to_frozen',PREP,FROZEN),
                    ('frozen_to_head',FROZEN,HEAD),('delivery_to_head',DELIVERY,HEAD)]:
    diffs[label] = git('diff','--name-status',a,b).decode().splitlines()
check('frozen product/test/config unchanged', not git('diff',FROZEN,HEAD,'--','layauto_v2','tests','pyproject.toml','README.md'))
check('protected product/contracts/fixtures unchanged', not git('diff',MAIN,HEAD,'--','docs/architecture.md','docs/collaboration','docs/environment','tests/fixtures','legacy_mvp'))

manifest = read(V/'source-manifest.json')
errors = []
with tarfile.open(V/'source-snapshot.tar.gz') as tf:
    check('source archive unique member names',len(tf.getnames())==len(set(tf.getnames())))
    archive = {m.name:tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
for name, digest in manifest['files'].items():
    for identity, data in [('current',(ROOT/name).read_bytes()),('frozen_git',git('show',FROZEN+':'+name)),('archive',archive[name])]:
        if sha(data) != digest: errors.append([name,identity])
check('252 source files current/frozen/archive content', len(manifest['files']) == 252 and not errors, errors)
check('archive complete path set',set(archive)==set(manifest['files']))
runtime = {k.removeprefix('layauto_v2/'):v for k,v in manifest['runtime_files'].items()}
package = read(V/'package-identity.json')
for kind in ('wheel','sdist'):
    p = V/'dist'/Path(package[kind]['path']).name
    check(kind+' artifact hash',sha(p.read_bytes())==package[kind]['sha256'])
    if kind=='wheel':
        with zipfile.ZipFile(p) as z:
            check(kind+' unique member names',len(z.namelist())==len(set(z.namelist())))
            entries = {n.removeprefix('layauto_v2/'):sha(z.read(n)) for n in z.namelist() if n.startswith('layauto_v2/') and not n.endswith('/')}
    else:
        with tarfile.open(p) as tf:
            check(kind+' unique member names',len(tf.getnames())==len(set(tf.getnames())))
            entries = {m.name.split('/layauto_v2/',1)[1]:sha(tf.extractfile(m).read()) for m in tf.getmembers() if m.isfile() and '/layauto_v2/' in m.name}
    check(kind+' complete runtime content',len(entries)==94 and entries==runtime==package[kind]['runtime_files'])

receipt = read(V/'receipt.json')
check('source manifest identity',sha((V/'source-manifest.json').read_bytes())==receipt['source_manifest_sha256'])
check('source snapshot identity',sha((V/'source-snapshot.tar.gz').read_bytes())==receipt['source_snapshot_sha256'])
check('runner identity',sha((V/'prepare_final.py').read_bytes())==receipt['runner_sha256'])
check('installed smoke identity',sha((V/'installed_smoke.py').read_bytes())==receipt['smoke_sha256'])
command_errors=[]
for command in receipt['commands']:
    if command['exit_code'] != 0: command_errors.append(command['command'])
    for stream in ('stdout','stderr'):
        if sha((V/command[stream]).read_bytes()) != command[stream+'_sha256']: command_errors.append(command[stream])
    detail=read(V/command['stdout'].replace('.stdout.txt','.json'))
    if detail != command: command_errors.append(command['stdout']+' per-command receipt mismatch')
check('21 finished commands and 42 original output identities',len(receipt['commands'])==21 and not command_errors,command_errors)
evidence = read(V/'evidence-manifest.json')
errors=[]
for path, expected in evidence.items():
    data=(V/path).read_bytes()
    digest=expected if isinstance(expected,str) else expected['sha256']
    if sha(data)!=digest: errors.append(path)
check('78 engineering evidence manifest entries',len(evidence)==78 and not errors,errors)
check('engineering evidence complete file set',set(evidence)=={str(p.relative_to(V)) for p in V.rglob('*') if p.is_file() and p.name!='evidence-manifest.json'})

delivery=read(ROOT/'docs/tasks/W010/delivery-manifest.json')
errors=[]
for name, expected in delivery['files'].items():
    data=git('show',DELIVERY+':'+name)
    if sha(data)!=expected['sha256'] or len(data)!=expected['bytes']: errors.append(name)
check('old delivery manifest against ca39 Git bytes',len(delivery['files'])==218 and not errors,errors)

historical_install=read(V/'installation-identity.json')
availability={}
for version in ('310','312'):
    row=historical_install[version]
    check(version+' recorded installed runtime bytes match package',row['runtime_files']==runtime)
    check(version+' recorded artifact identity',row['artifact_sha256']==package['sdist' if version=='310' else 'wheel']['sha256'])
    install_report=read(V/f'install-{version}-report.json')
    layauto=[x for x in install_report['install'] if x['metadata']['name']=='layauto'][0]
    ai=layauto['download_info']['archive_info']
    actual_hash=ai.get('hashes',{}).get('sha256') or ai.get('hash','').removeprefix('sha256=')
    check(version+' original install report artifact hash',actual_hash==row['artifact_sha256'])
    identity=json.loads((V/f'installed-identity-{version}.stdout.txt').read_text())
    check(version+' original isolated import identity',identity['isolated']==1 and identity['package']==row['package'] and identity['executable']==row['executable'])
    check(version+' original completed full pytest',f'1465 passed' in (V/f'pytest-{version}.stdout.txt').read_text())
    check(version+' original strict typing48','Success: no issues found in 48 source files' in (V/f'typing-{version}.stdout.txt').read_text())
    smoke=read(V/f'installed-smoke-{version}.stdout.txt')
    check(version+' historical installed direct/readback outcome',smoke['package']==row['package'] and smoke['attempt_unchanged'] and all(
        [smoke[k]['nodes'],smoke[k]['edges'],smoke[k]['components'],smoke[k]['audits'],smoke[k]['local_enclosure_status']]==[14,8,6,16,'pass'] for k in ('direct','readback')))
    availability[version]={'executable_exists':Path(row['executable']).exists(),'package_exists':Path(row['package']).exists()}
availability['original_test_tree_exists']=Path('/workspace/work/w010-final-0f5029d/source').exists()

collect_cmd=[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','--collect-only','tests/unit','tests/contracts','-q']
base_root=Path('/workspace/Layauto')
base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=base_root).decode().strip()
check('baseline collection checkout identity',base_head==MAIN)
baseline=ids(run('baseline-collection',collect_cmd,base_root))
current=ids(run('current-collection',collect_cmd,ROOT))
check('actual collected original 1149 IDs retained',len(baseline)==1149 and len(current)==1465 and baseline<=current,
      {'baseline':len(baseline),'current':len(current),'added':len(current-baseline),'missing':sorted(baseline-current)})
check('historical baseline nodeids equal independently collected',baseline==ids((V/'baseline-collection.txt').read_text()))
for version in ('310','312'):
    check(version+' historical nodeids equal independently collected',current==ids((V/f'collection-{version}.stdout.txt').read_text()))

guard_path=ROOT/'tests/contracts/test_w007_contracts.py'
tree=ast.parse(guard_path.read_text())
expr=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='allowed_local_contact_state' for t in n.targets))
code=compile(ast.Expression(expr),'allowlist','eval')
guard_cases=[]
for filename in ('local_connectivity.py','local_connectivity_codec.py','unrelated.py'):
    for module,symbol in [('layauto_v2.state.local_connectivity','LocalConnectivityDraft'),('layauto_v2.state.local_connectivity','MutableState'),('layauto_v2.state.regions','EffectiveDraft'),('layauto_v2.repository','PublicationRepository'),('layauto_v2.state.anything','LocalConnectivityDraft')]:
        value=eval(code,{'ast':ast,'path':Path('normalization')/filename,'node':ast.parse(f'from {module} import {symbol}').body[0]})
        expected=(module=='layauto_v2.state.local_connectivity' and symbol=='LocalConnectivityDraft' and filename in ('local_connectivity.py','local_connectivity_codec.py')) or (module=='layauto_v2.state.regions' and symbol=='EffectiveDraft' and filename=='local_connectivity_codec.py')
        guard_cases.append({'file':filename,'module':module,'symbol':symbol,'actual':value,'expected':expected})
check('named guard allowlist positive/negative controls',all(x['actual']==x['expected'] for x in guard_cases),guard_cases)
run('guards',[sys.executable,'-B','-m','pytest','-p','no:cacheprovider','tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries','tests/contracts/test_w010_contracts.py::test_new_domain_and_state_keep_pure_dependency_direction','-q'],ROOT)

perf=read(ROOT/'docs/tasks/W010/performance.json')
check('performance probe identity',sha((ROOT/'docs/tasks/W010/performance_probe.py').read_bytes())==perf['probe_sha256'])
check('performance runtime/config identities',all(sha((ROOT/k).read_bytes())==v for k,v in perf['source_files_sha256'].items()))
performance=[{'case':r['case'],'wire_bytes':r['result_wire_bytes'],'max_pieces':r['counts']['max_pieces_per_region'],'nodes':r['counts']['nodes'],'rss_kib_cumulative':r['process_peak_rss_kib_cumulative'],'public_build_seconds':r['wall_seconds']['public_build_local_connectivity']} for r in perf['cases']]
result={'status':'pass' if all(x['pass'] for x in checks) else 'fail','head':HEAD,'python':sys.version,'checks':checks,'diffs':diffs,'historical_paths_available':availability,'performance_original_values':performance,
        'scope':'Actual byte/archive/Git/hash/AST/pytest-collection/guard audit only. Historical execution, clean installations and performance were not rerun; original installation trees absent if marked false above.'}
(OUT/'evidence-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'failures':[x for x in checks if not x['pass']],'historical_paths_available':availability,'performance_original_values':performance},indent=2))
sys.exit(0 if result['status']=='pass' else 1)
