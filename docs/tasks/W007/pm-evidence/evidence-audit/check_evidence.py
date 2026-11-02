"""Read-only W007 delivery evidence audit; never imports product or executes tests."""
from pathlib import Path
import ast, base64, csv, hashlib, io, json, re, subprocess, tarfile, zipfile
from datetime import datetime, timezone
ROOT=Path('/workspace/Layauto')
OUT=Path('/workspace/work/w007-pm/evidence-audit')
E=ROOT/'docs/tasks/W007/verification'
R=ROOT/'docs/tasks/W007/review-evidence'
BASE='64b4ad2f77c017affade69374510dc12e534bc07'
TESTED='0f879f01acbeac033173d0b6c6257c376bb9272a'
DELIVERY='5e874e5e60bb74f58903080bf079796061454962'
CANDIDATE='6712cbcf0e00395a32836122639c79a88c3813b6'
checks=[]
result={'auditor':'/root/w007_accept_evidence','started_utc':datetime.now(timezone.utc).isoformat(),'baseline':BASE,'tested_product':TESTED,'delivery':DELIVERY,'scope':'Independent Git/hash/archive/receipt inspection only; no product imports, tests, mypy, build, installation or smoke executed by this auditor.'}
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT)
def obj(commit,path): return git('rev-parse',commit+':'+path).decode().strip()
def blob(commit,path): return git('show',commit+':'+path)
def load(p): return json.loads(p.read_text())
def check(name,ok,details=None):
 checks.append({'name':name,'passed':bool(ok),**({'details':details} if details is not None else {})})
def hashref(base,name,expected):
 actual=sha((base/name).read_bytes());check('hash:'+str((base/name).relative_to(ROOT)),actual==expected,{'expected':expected,'actual':actual});return actual
result['initial_head']=git('rev-parse','HEAD').decode().strip()
result['initial_git_status']=git('status','--porcelain').decode().splitlines()
check('head_is_delivery',result['initial_head']==DELIVERY)
check('initial_worktree_clean',not result['initial_git_status'])
check('tested_is_ancestor_of_delivery',subprocess.run(['git','merge-base','--is-ancestor',TESTED,DELIVERY],cwd=ROOT).returncode==0)
manifest=load(E/'source-manifest.json'); files=manifest['files']; runtime={p:h for p,h in files.items() if p.startswith('layauto_v2/')}
check('manifest_tested_commit',manifest['tested_commit']==TESTED)
check('manifest_content_digest',sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())==manifest['content_sha256'])
tracked=git('ls-tree','-r','--name-only',TESTED,'--','layauto_v2','tests/unit','tests/contracts','pyproject.toml').decode().splitlines()
check('manifest_is_exact_complete_scope',set(tracked)==set(files),{'tracked':len(tracked),'manifest':len(files),'missing':sorted(set(tracked)-set(files)),'extra':sorted(set(files)-set(tracked))})
source=[]
for p,h in files.items():
 record={'path':p,'expected_sha256':h,'tested_sha256':sha(blob(TESTED,p)),'delivery_sha256':sha(blob(DELIVERY,p)),'worktree_sha256':sha((ROOT/p).read_bytes())}
 record['matches']=all(record[k]==h for k in ['tested_sha256','delivery_sha256','worktree_sha256']); source.append(record)
check('all_101_sources_match_tested_delivery_worktree',all(x['matches'] for x in source),{'count':len(source),'mismatches':[x['path'] for x in source if not x['matches']]})
result['source_files']=source
result['manifest_counts']={'runtime':len(runtime),'unit':sum(p.startswith('tests/unit/') for p in files),'contracts':sum(p.startswith('tests/contracts/') for p in files),'config':sum(p=='pyproject.toml' for p in files),'total':len(files)}
post=git('diff','--name-only',TESTED,DELIVERY).decode().splitlines()
check('only_W007_records_after_tested_product',all(p.startswith('docs/tasks/W007/') or p=='docs/tasks/W007-semantic-identity-normalization.md' for p in post),{'count':len(post)})
result['post_product_changed_paths']=post
package=load(E/'package-identity.json')
check('package_identity_tested_commit',package['tested_commit']==TESTED)
hashref(E,'source-manifest.json',package['source_manifest_sha256'])
artifacts=[]
for name,meta in package['artifacts'].items():
 p=ROOT/meta['repository_path'];data=p.read_bytes();info={'path':str(p.relative_to(ROOT)),'sha256':sha(data),'size':len(data)}
 check('package_bytes:'+name,info['sha256']==meta['sha256'] and info['size']==meta['size_bytes'])
 check('package_matches_committed_blob:'+name,data==blob(DELIVERY,meta['repository_path']))
 if name.endswith('.whl'):
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   names=z.namelist(); members={n:z.read(n) for n in names if n.startswith('layauto_v2/') and not n.endswith('/')}
   check('wheel_has_no_duplicate_members',len(names)==len(set(names)))
   check('wheel_excludes_tests_legacy',not any(n.startswith(('tests/','legacy_mvp/')) for n in names))
   records=list(csv.reader(io.StringIO(z.read('layauto-0.2.0.dist-info/RECORD').decode())))
   record_ok=True
   for path,digest,size in records:
    if digest:
     alg,expected=digest.split('=',1)
     record_ok &= alg=='sha256' and base64.urlsafe_b64encode(hashlib.sha256(z.read(path)).digest()).decode().rstrip('=')==expected and len(z.read(path))==int(size)
   check('wheel_RECORD_all_hashes',record_ok,{'entries':len(records)})
 else:
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as z:
   entries=[m for m in z.getmembers() if m.isfile()]; names=[m.name for m in entries]
   members={m.name.removeprefix('layauto-0.2.0/'):z.extractfile(m).read() for m in entries if m.name.startswith('layauto-0.2.0/layauto_v2/')}
   check('sdist_has_no_duplicate_file_members',len(names)==len(set(names)))
   check('sdist_pyproject_matches_final',z.extractfile('layauto-0.2.0/pyproject.toml').read()==blob(TESTED,'pyproject.toml'))
 check('package_exact_runtime_set:'+name,set(members)==set(runtime),{'actual':len(members),'expected':len(runtime),'extra':sorted(set(members)-set(runtime)),'missing':sorted(set(runtime)-set(members))})
 check('package_runtime_bytes_match_final:'+name,all(sha(members[p])==h for p,h in runtime.items() if p in members),{'files':len(members)})
 check('obsolete_domain_normalization_absent:'+name,not any(p.startswith('layauto_v2/domain/') and 'normalization' in p for p in members))
 info['runtime_files']=len(members);artifacts.append(info)
result['packages']=artifacts
protected=load(E/'protected-paths.json'); protection=[]
check('protected_identity',protected['baseline_commit']==BASE and protected['tested_commit']==TESTED)
for entry in protected['protected_paths']:
 p=entry['path'];a,b,c=obj(BASE,p),obj(TESTED,p),obj(DELIVERY,p);diff=git('diff','--name-only',DELIVERY,'--',p).decode().splitlines()
 record={'path':p,'baseline_object':a,'tested_object':b,'delivery_object':c,'worktree_diff':diff}
 record['matches']=a==b==c==entry['base_object']==entry['tested_object'] and not diff;protection.append(record)
check('all_14_protected_paths_unchanged',all(x['matches'] for x in protection),{'count':len(protection)})
result['protected_paths']=protection
extra_paths=['docs/tasks/W003-input-fixtures.md','docs/tasks/W004-fixture-revision.md','docs/tasks/W005-input-reading-binding.md','docs/tasks/W006-precontext-run-audit.md']
existing=set(git('ls-tree','-r','--name-only',BASE,'--','docs/tasks').decode().splitlines())
extra_paths=[p for p in extra_paths if p in existing]
check('prior_task_records_unchanged',not git('diff','--name-only',BASE,DELIVERY,'--',*extra_paths),{'paths':extra_paths})
oldtests=set(git('ls-tree','-r','--name-only',BASE,'--','tests/unit','tests/contracts').decode().splitlines())
check('all_preexisting_unit_contracts_unchanged',all(blob(BASE,p)==blob(DELIVERY,p) for p in oldtests),{'files':len(oldtests)})
receipt=load(E/'receipt.json');check('aggregate_receipt_identity',receipt['tested_commit']==TESTED)
for field in ['source_manifest','package_identity','environment','smoke_script']:
 hashref(E,receipt[field],receipt[field+'_sha256'])
check('aggregate_manifest_content_and_count',receipt['source_manifest_content_sha256']==manifest['content_sha256'] and receipt['runtime_test_config_files']==len(files))
receipt_results=[]
for rec in receipt['checks']:
 hashref(E,rec['receipt'],rec['receipt_sha256']);hashref(E,rec['log'],rec['log_sha256'])
 individual=load(E/rec['receipt']); fields=['command','cwd','started_utc','duration_seconds','exit_code','log']
 check('receipt_mapping:'+rec['name'],all(individual[k]==rec[k] for k in fields) and individual['git_head']==TESTED and rec['exit_code']==0)
 dirty_products=[]
 for line in individual['git_status']:
  path=line[3:]
  if not (path.startswith('docs/tasks/W007/') or path=='docs/tasks/W007-semantic-identity-normalization.md'):dirty_products.append(path)
 check('execution_worktree_only_records:'+rec['name'],not dirty_products,dirty_products)
 log=(E/rec['log']).read_text()
 if rec['name'].startswith('pytest-'):check('result:'+rec['name'],bool(re.search(r'553 passed in ',log)))
 elif rec['name'].startswith('mypy-'):check('result:'+rec['name'],'Success: no issues found in 33 source files' in log)
 elif rec['name'].startswith('pip-check-'):check('result:'+rec['name'],'No broken requirements found.' in log)
 elif rec['name']=='build':check('result:build','Successfully built layauto-0.2.0.tar.gz and layauto-0.2.0-py3-none-any.whl' in log)
 elif rec['name'].startswith('install-wheel-'):check('result:'+rec['name'],'Successfully installed' in log and 'layauto-0.2.0' in log)
 elif rec['name'].startswith('wheel-smoke-'):
  smoke=json.loads(log);v='3.10' if rec['name'].endswith('310') else '3.12'
  check('result:'+rec['name'],smoke['python'].startswith(v) and '/site-packages/layauto_v2/__init__.py' in smoke['installed'] and 'w007-final-wheel' in smoke['installed'] and smoke['cwd']==rec['cwd'] and smoke['outcomes']['normal']['status']=='success' and smoke['outcomes']['cardinality']=='UnsupportedDeviceCardinality' and smoke['outcomes']['target_length']['axis']=='channel_length' and smoke['outcomes']['w006_readback']=='success')
 receipt_results.append({'name':rec['name'],'receipt_sha256':rec['receipt_sha256'],'log_sha256':rec['log_sha256'],'exit_code':rec['exit_code'],'command':rec['command'],'cwd':rec['cwd']})
result['execution_receipts']=receipt_results
check('expected_13_receipts',len(receipt_results)==13 and len({r['name'] for r in receipt_results})==13)
env=load(E/'environment-final.json');check('environment_tested_identity',env['tested_commit']==TESTED)
for name,interpreter in env['interpreters'].items():
 actual=interpreter['runtime']; want='3.10.22' if 'minimum' in name else '3.12.14'
 check('environment_version:'+name,actual['version'].startswith(want) and actual['executable']==interpreter['path'])
 if name.startswith('clean_wheel'):
  check('wheel_environment_not_editable:'+name,all('editable_project_location' not in p for p in interpreter['packages']))
result['recorded_environments']={k:{'version':v['runtime']['version'],'executable':v['path'],'packages':len(v['packages'])} for k,v in env['interpreters'].items()}
review=load(R/'final-review.json');check('final_review_identity',review['tested_commit']==TESTED and review['source_manifest_files']==len(files))
hashref(E,'source-manifest.json',review['source_manifest_sha256'])
for rec in review['checks']:
 hashref(R,rec['output'],rec['output_sha256']);log=(R/rec['output']).read_text()
 if rec['name'] in ['original-probe','original-relabel']:check('review_expected_rejection:'+rec['name'],rec['returncode']==1 and '\nValueError:' in log and 'ImportError' not in log)
 else:check('review_success_receipt:'+rec['name'],rec['returncode']==0)
 if rec['name']=='w007-tests':check('review_148_passed','148 passed in 136.16s' in log)
for rec in review['probe_adaptations']:
 hashref(R,rec['original'],rec['original_sha256']);hashref(R,rec['adapted'],rec['adapted_sha256'])
 # Normalize only the explicitly approved bootstrap depth and internal module moves.
 original=(R/rec['original']).read_text()
 adapted=(R/rec['adapted']).read_text()
 expected=original.replace('REPOSITORY = Path(__file__).resolve().parents[4]', 'REPOSITORY = Path(__file__).resolve().parents[5]').replace('from layauto_v2.domain.normalization_codec import ', 'from layauto_v2.normalization.codec import ').replace('from layauto_v2.domain.normalization import ', 'from layauto_v2.normalization.contracts import ')
 check('probe_logic_unchanged:'+rec['original'],expected==adapted)

audit=load(R/'delivery-audit.json');check('independent_audit_identity',audit['tested_commit']==TESTED and audit['source_manifest_sha256']==sha((E/'source-manifest.json').read_bytes()) and audit['source_manifest_content_sha256']==manifest['content_sha256'] and audit['verified_source_files']==len(files) and audit['verified_runtime_files_per_package']==len(runtime) and audit['verified_protected_paths']==len(protection))
hashref(E,'protected-paths.json',audit['protected_paths_manifest_sha256'])
execution_map={r['name']:r for r in receipt_results}
check('review_audit_13_receipt_hashes',len(audit['checks'])==13 and all(r['receipt_sha256']==execution_map[r['name']]['receipt_sha256'] and r['output_sha256']==execution_map[r['name']]['log_sha256'] and r['exit_code']==0 for r in audit['checks']))
old=E/'candidate-6712cbc';old_manifest=load(old/'source-manifest.json');old_package=load(old/'package-identity.json')
check('historical_candidate_distinct_identity',old_manifest['tested_commit']==old_package['tested_commit']==CANDIDATE and old_manifest['content_sha256']!=manifest['content_sha256'])
for name,meta in old_package['artifacts'].items():
 p=old/'packages'/name
 check('historical_candidate_package_preserved_distinct:'+name,sha(p.read_bytes())==meta['sha256'] and meta['sha256']!=package['artifacts'][name]['sha256'])
result['historical_candidate']={'commit':CANDIDATE,'manifest_files':len(old_manifest['files']),'runtime_files':old_package['runtime_files'],'final_evidence_uses_candidate':False,'historical_paths_retained_as_explained_in_candidate_README':True}
result['recorded_review']={'W007_tests':148,'checks':len(review['checks']),'adapted_probes':len(review['probe_adaptations'])}
result['limits']=['Audit verifies identity and recorded results; this subagent did not rerun product tests, mypy, build, install or smoke.','Execution logs record Linux x86_64 Python 3.12.14 and 3.10.22; reviewer reran W007-specific 148, not the complete engineering matrix.','Wheel smoke ran from outside source and checked loaded module is under sys.prefix; commands use -B, not -I.','The verified synthetic component does not cover real EDA/PDK, full geometry/physical state/body/extraction, baseline/seal, full-run no_change/terminal, ECO or Stage 6.']
result['checks']=checks;result['passed_checks']=sum(x['passed'] for x in checks);result['failed_checks']=[x for x in checks if not x['passed']]
result['final_git_status']=git('status','--porcelain').decode().splitlines();result['completed_utc']=datetime.now(timezone.utc).isoformat()
(OUT/'checks.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'checks':len(checks),'passed':result['passed_checks'],'failed':result['failed_checks'],'manifest_counts':result['manifest_counts'],'packages':artifacts,'post_product_changed_paths':len(post),'output':str(OUT/'checks.json')},indent=2))
