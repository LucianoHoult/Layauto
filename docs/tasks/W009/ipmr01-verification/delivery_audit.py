"""Read-only final delivery audit; excludes this audit's own output hash."""
from pathlib import Path
import hashlib,json,re,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE='cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa'
PRODUCT='73e38df8f932bbb5bd9caf074b442ad2f5c286e9'
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def read(name):return json.loads((OUT/name).read_text())
source=read('source-manifest.json')
assert source['git_head']==PRODUCT
assert all(sha((ROOT/name).read_bytes())==value==sha(git('show',PRODUCT+':'+name)) for name,value in source['files'].items())
with tarfile.open(OUT/'source-snapshot.tar.gz') as archive:
    snapshot={m.name:sha(archive.extractfile(m).read()) for m in archive if m.isfile()}
assert snapshot==source['files']
compat_before=read('compatibility-baseline.stdout.json')
compat_after=read('compatibility-final.stdout.json')
assert compat_before['wire']==compat_after['wire']
assert compat_before['semantic_digest']==compat_after['semantic_digest']
assert compat_before['source_uris']==compat_after['source_uris']
assert compat_after['runtime_files']==source['runtime_files']
assert all(value==sha(git('show',BASE+':layauto_v2/'+name)) for name,value in compat_before['runtime_files'].items())
receipt=read('receipt.json')
assert receipt['status']=='passed' and receipt['source_identity_rechecked_after_all_commands']
assert receipt['head']==receipt['finished_head']==PRODUCT
assert receipt['source_manifest_sha256']==sha((OUT/'source-manifest.json').read_bytes())
assert receipt['source_snapshot_sha256']==sha((OUT/'source-snapshot.tar.gz').read_bytes())
assert receipt['source_file_count']==245 and receipt['runtime_count']==90
assert receipt['runner_sha256']==sha((OUT/'runner.py').read_bytes())
assert receipt['resumption']['status']=='passed'
assert receipt['resumption']['source_manifest_sha256']==receipt['source_manifest_sha256']
assert receipt['resumption']['script_sha256']==sha((OUT/'resume_verification.py').read_bytes())
for name,value in receipt['resumption']['archived_partial_outputs'].items():
    assert sha((OUT/'environment-disconnect-20261103'/name).read_bytes())==value
assert receipt['actual_test_counts']['312']==1149
assert receipt['typing_source_counts']=={'310':44,'312':44}
assert all(c['exit_code']==0 for c in receipt['commands'])
for command in receipt['commands']:
    for stream in command['outputs'].values():
        assert sha((OUT/stream['path']).read_bytes())==stream['sha256']
paths=read('exception-paths.json')
assert paths['observed']=={'case_count':99,'same_object_count':99,'identity_failures':[]}
assert paths['passed'] and read('historical-minimal.json')['passed']
for name,expected_exit in [('exception-paths.json',0),('historical-minimal.json',1)]:
    row=read(name)
    assert row['head']==PRODUCT and row['exit_code']==expected_exit
    assert row['source_manifest_sha256']==receipt['source_manifest_sha256']
    for stream in row['outputs'].values():
        assert sha((OUT/stream['path']).read_bytes())==stream['sha256']
package=read('package-identity.json')
installs=read('installation-identity.json')
assert package['runtime_count']==len(source['runtime_files'])==90
for kind in ('wheel','sdist'):
    row=package[kind]
    assert sha(Path(row['path']).read_bytes())==row['sha256'] and row['runtime_files']==source['runtime_files']
assert set(installs)=={'310','312'}
for tag,row in installs.items():
    kind='wheel' if tag=='312' else 'sdist'
    assert row['source_artifact']==package[kind]['path']
    assert row['source_sha256']==package[kind]['sha256']
    assert row['runtime_files']==source['runtime_files']
    assert sha(Path(row['source_artifact']).read_bytes())==row['source_sha256']
    assert all(sha((Path(row['installed_package']).parent/name).read_bytes())==value for name,value in source['runtime_files'].items())
protected=['docs/architecture.md','docs/current-work.md','docs/roadmap.md','tests/fixtures','tests/support','legacy_mvp','docs/tasks/W003','docs/tasks/W005','docs/tasks/W006','docs/tasks/W007','docs/tasks/W008','docs/tasks/W009/verification','docs/tasks/W009/independent-premerge-review.md','docs/tasks/W009/independent-premerge-review','docs/tasks/W009/ipmr01-fix-task.md','docs/tasks/W009/ipmr01-pm-confirmation']
assert not git('diff',BASE,'--',*protected)
task='docs/tasks/W009-effective-geometry-terminals.md'
old=git('show',BASE+':'+task).decode()
new=(ROOT/task).read_text()
pm='## PM 验收与交接（PM）'
assert new.split(pm,1)[1]==old.split(pm,1)[1]
assert new.split('## 执行结果（执行）',1)[0]==old.split('## 执行结果（执行）',1)[0]
for label,next_label in [('## 执行结果（执行）','## Review 结论（reviewer）'),('## Review 结论（reviewer）',pm)]:
    original=old.split(label,1)[1].split(next_label,1)[0].strip()
    assert new.split(label,1)[1].split(next_label,1)[0].strip().startswith(original)
changes=git('diff','--name-only',BASE).decode().splitlines()
untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
allowed_runtime={'layauto_v2/domain/evidence.py','layauto_v2/domain/publication_codec.py','layauto_v2/domain/results.py','layauto_v2/normalization/_validation.py','layauto_v2/normalization/codec.py','layauto_v2/normalization/contracts.py','layauto_v2/normalization/geometry_codec.py','layauto_v2/state/layout_store.py'}
allowed_tests={'tests/contracts/test_w009_captured_decode_exceptions.py','tests/contracts/test_w009_nested_base_decode.py','tests/contracts/test_w009_nested_receipt_exceptions.py'}
for path in changes+untracked:
    assert path in allowed_runtime|allowed_tests|{task,'docs/tasks/W009/ipmr01-fix.md','docs/tasks/W009/ipmr01-fix-review.md'} or path.startswith('docs/tasks/W009/ipmr01-verification/'),path
commits=git('log','--format=%H %ae %ce',BASE+'..HEAD').decode().splitlines()
assert all(line.split()[1:]==['LucianoHoult@users.noreply.github.com']*2 for line in commits)
link_checks=[]
for document in (ROOT/'docs/tasks/W009/ipmr01-fix.md',ROOT/'docs/tasks/W009/ipmr01-fix-review.md',OUT/'README.md'):
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',document.read_text()):
        if '://' in target or target.startswith('#'):
            continue
        local=target.split('#',1)[0].strip('<>')
        assert (document.parent/local).exists(),(document,target)
        link_checks.append({'document':str(document.relative_to(ROOT)),'target':target})
artifacts={str(p.relative_to(OUT)):sha(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='delivery-audit.json'}
result={'status':'passed','base_sha':BASE,'product_sha':PRODUCT,'delivery_head_before_audit':git('rev-parse','HEAD').decode().strip(),'source_file_count':len(source['files']),'runtime_file_count':90,'source_manifest_sha256':sha((OUT/'source-manifest.json').read_bytes()),'source_snapshot_sha256':sha((OUT/'source-snapshot.tar.gz').read_bytes()),'actual_test_counts':receipt['actual_test_counts'],'typing_source_counts':receipt['typing_source_counts'],'protected_paths':protected,'protected_paths_unchanged':True,'pm_and_task_requirements_unchanged':True,'original_execution_and_review_text_retained':True,'modified_and_new_paths':sorted(set(changes+untracked)),'commits':commits,'local_links_checked':link_checks,'evidence_files':artifacts,'note':'Audit excludes its own output hash and any future Git commit SHA. Remote full SHA is verified after push and reported separately; this is execution evidence, not PM acceptance.'}
(OUT/'delivery-audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('evidence_files','local_links_checked','modified_and_new_paths','commits','protected_paths')},indent=2))
