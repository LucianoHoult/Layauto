"""PM read-only receipt audit; no product test, package build or repo mutation."""
from __future__ import annotations
import hashlib,json,pathlib,re,subprocess
from datetime import datetime,timezone
ROOT=pathlib.Path('/workspace/Layauto')
OUT=pathlib.Path('/workspace/work/w008-integration/premerge-audit.json')
BASE='131f66dfadd77b5fb9073db999d6939051c3addf'
HEAD='eb15a666010cf7f5fa82c97880a4d0e8f023fa8f'
DELIVERY='aced62b0adda35fe7bcd8284a7354badc5b03649'
PREFIX='docs/tasks/W008/independent-premerge-review/'
TASK='docs/tasks/W008-geometry-base-occupancy.md'
REPORT='docs/tasks/W008/independent-premerge-review.md'
checks=[]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def sha(data):return hashlib.sha256(data).hexdigest()
def blob(path,ref=HEAD):return git('show',ref+':'+path)
def doc(path):return json.loads(blob(path))
def check(name,ok,**detail):checks.append(dict(name=name,passed=bool(ok),**detail))
changes=[line.split('\t') for line in git('diff','--name-status',BASE,HEAD).decode().splitlines()]
check('review_only_scope',len(changes)==42 and all((s=='M' and p==TASK) or (s=='A' and (p==REPORT or p.startswith(PREFIX))) for s,p in changes),changed_paths=len(changes))
before=blob(TASK,BASE).decode();after=blob(TASK).decode()
new_start=after.index('\n\n### R2 独立合并前复核')
new_end=after.index('\n## PM 验收与交接（PM）',new_start)
removed=after[:new_start]+after[new_end:]
check('task_reviewer_insertion_only',removed==before,PM_section_unchanged=after.split('## PM 验收与交接（PM）',1)[1]==before.split('## PM 验收与交接（PM）',1)[1])
receipt=doc(PREFIX+'review-receipt.json')
check('receipt_review_identity',receipt['reviewed_head']==BASE and receipt['delivery']==DELIVERY and receipt['new_findings']==0 and receipt['remaining_must_fix']==0)
bad=[p for p,h in receipt['files_sha256'].items() if sha(blob(PREFIX+p))!=h]
check('all_review_attachment_hashes',not bad,count=len(receipt['files_sha256']),mismatches=bad)
check('report_and_task_hashes',sha(blob(REPORT))==receipt['report_sha256'] and sha(blob(TASK))==receipt['task_sha256'])
source_path='docs/tasks/W008/verification/source-manifest.json'
manifest=doc(source_path)
bad_current=[p for p,h in manifest.items() if sha((ROOT/p).read_bytes())!=h]
bad_review=[p for p,h in manifest.items() if sha(blob(p,BASE))!=h]
bad_delivery=[p for p,h in manifest.items() if sha(blob(p,DELIVERY))!=h]
check('source_manifest_binding',len(manifest)==235 and sha(blob(source_path))==receipt['source_manifest_sha256'] and not bad_current and not bad_review and not bad_delivery,count=len(manifest),current_mismatches=bad_current,review_mismatches=bad_review,delivery_mismatches=bad_delivery)
validation=[]
for name in ('pytest','mypy','pip-check','environment','scope','remote-before','remote-after-review'):
 r=doc(PREFIX+'validation/'+name+'.json');out=blob(PREFIX+'validation/'+r['output'])
 validation.append({'name':name,'exit_code':r['exit_code'],'output_hash_matches':sha(out)==r['output_sha256']})
check('validation_command_output_bindings',all(r['exit_code']==0 and r['output_hash_matches'] for r in validation),commands=validation)
check('recorded_full_suite_and_typing','730 passed in 550.32s' in blob(PREFIX+'validation/pytest.txt').decode() and '40 source files' in blob(PREFIX+'validation/mypy.txt').decode(),evidence_basis='Adopted independent reviewer executions; not rerun in this receipt audit')
r=doc(PREFIX+'input/receipt.json');bad=[p for p,h in r['sha256'].items() if sha(blob(PREFIX+'input/'+p))!=h]
text=blob(PREFIX+'input/output.txt').decode()
check('input_probe_receipt',r['reviewed_head']==BASE and r['exit_code']==0 and r['checks']==24 and not bad and 'PASS preserved CR-01 reproducer now rejects with location and completed facts' in text and 'PASS body second source rejects foreign URI' in text,mismatches=bad)
r=doc(PREFIX+'geometry/receipt.json');results=[]
for c in r['commands']:
 script=pathlib.Path(c['argv'][2]).name
 results.append(c['exit_code']==0 and sha(blob(PREFIX+'geometry/'+c['output']))==c['output_sha256'] and sha(blob(PREFIX+'geometry/'+script))==c['script_sha256'])
check('geometry_probe_receipts',r['review_head']==BASE and all(results),commands=len(results))
r=doc(PREFIX+'evidence/audit-receipt.json');summary=doc(PREFIX+'evidence/audit-output.txt')
check('evidence_audit_receipt',r['returncode']==0 and sha(blob(PREFIX+'evidence/audit-output.txt'))==r['output_sha256'] and sha(blob(PREFIX+'evidence/audit.py'))==r['script_sha256'] and summary['checks_passed']==29 and summary['checks_total']==29 and not summary['must_fix_findings'])
report=blob(REPORT).decode()
check('report_closure_and_limitations_recorded',all(s in report for s in ('IR-01','CR-01','未验证最大允许 record 数下所有极端重叠集的资源上界','未重新构建/安装历史包','U06','本轮没有实现可选模式','不代替 PM 最终验收')))
links=[]
for target in re.findall(r'\]\(([^)]+)\)',report):
 if '://' in target or target.startswith('#'):continue
 path=(ROOT/pathlib.Path(REPORT).parent/target.split('#')[0]);links.append((target,path.exists()))
check('report_relative_links',all(ok for _,ok in links),count=len(links),missing=[p for p,ok in links if not ok])
result={'auditor':'/root/w008_merge_receipt_check','audited_utc':datetime.now(timezone.utc).isoformat(),'scope':'PM read-only independent premerge-review receipt check','repository':str(ROOT),'reviewed_head':BASE,'review_delivery':HEAD,'product_delivery':DELIVERY,'observed_checkout_head':git('rev-parse','HEAD').decode().strip(),'checks_total':len(checks),'checks_passed':sum(c['passed'] for c in checks),'must_fix_findings':[c for c in checks if not c['passed']],'checks':checks,'adopted_not_rerun':['Independent reviewer Linux Python 3.12.14 full 730 tests/40-file typing/pip check','Independent input 24 checks and geometry 600 partitions/21314 points/4 derived builds','Independent reviewer archive/installation audits; no package-byte reaudit in this limited task'],'preserved_limitations':['Extreme allowed record-count overlap resource upper bound unverified','Original Mac dual interpreter/build/install executions adopted, not rerun','Full technology coordinates/physical connectivity/body/extraction/baseline/Stage6 and real EDA/PDK/production remain outside W008','U06 missing external body/power context requirement remains future work'],'verdict':'No receipt or scope mismatch found; supports PM integration with combined verification, not final acceptance by this audit.'}
result['script_sha256']=sha(pathlib.Path(__file__).read_bytes())
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('checks_total','checks_passed','must_fix_findings','verdict')},ensure_ascii=False))
