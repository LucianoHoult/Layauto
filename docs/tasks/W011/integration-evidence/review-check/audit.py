"""Read-only W011 integration identity and dedicated-review receipt checks."""
from pathlib import Path
import datetime
import hashlib
import io
import json
import subprocess
import tarfile

ROOT=Path('/workspace/Layauto')
OUT=Path('/workspace/work/w011-integration/review-check')
HEAD='9791c1e9eb6c7e3e1878067f045abcad4e4d0b7d'
REVIEWED='8452027e57fb1c58607640d7eb755b38ffc70716'
FROZEN='e89bdaa6a091f56cfaf7862dced7232d34e22514'
DELIVERY='3c464baade7b6ea8c712cfb84265490b8e3f754e'
MAIN='61775e8fde6e9ea247ec08a32067c44c3be48ff8'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(ref,path):return git('show',ref+':'+path)
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
checks=[]
def check(name,condition,details=None):
    if not condition:raise AssertionError(name+': '+str(details))
    checks.append(dict(check=name,details=details))

for older,newer in ((MAIN,REVIEWED),(FROZEN,REVIEWED),(DELIVERY,REVIEWED),(REVIEWED,HEAD)):
    result=subprocess.run(['git','merge-base','--is-ancestor',older,newer],cwd=ROOT)
    check('ancestry '+older[:7]+' -> '+newer[:7],result.returncode==0)
changes=git('diff','--name-only',REVIEWED,HEAD).decode().splitlines()
task='docs/tasks/W011-channel-identity-fin-count.md'
report='docs/tasks/W011/independent-premerge-review.md'
prefix='docs/tasks/W011/independent-premerge-evidence/'
check('review-only delivery paths',all(p==task or p==report or p.startswith(prefix) for p in changes),changes)
before=blob(REVIEWED,task).decode();after=blob(HEAD,task).decode()
start=after.index('### R2 独立合并前复核')
end=after.index('## PM 验收与交接',start)
check('task only appends reviewer R2',after[:start]+after[end:]==before)

source=read('docs/tasks/W011/verification/source-manifest.json')
files=source['files'];check('source count',len(files)==262)
archive=ROOT/'docs/tasks/W011/verification/source-snapshot.tar.gz'
with tarfile.open(archive,'r:gz') as tar:
    members={p.name.removeprefix('./'):p for p in tar.getmembers() if p.isfile()}
    check('source archive unique members',len(members)==sum(p.isfile() for p in tar.getmembers()))
    for path,expected in files.items():
        payloads=[(ROOT/path).read_bytes(),blob(FROZEN,path),blob(DELIVERY,path),blob(REVIEWED,path),blob(HEAD,path)]
        payloads.append(tar.extractfile(members[path]).read())
        check('source bytes '+path,all(sha(data)==expected for data in payloads))
check('runtime count',len(source['runtime_files'])==100)
for path,expected in source['runtime_files'].items():
    check('runtime equals product fix '+path,sha(blob('8917d38d916c914bfa785cb116982f3f299b38de','layauto_v2/'+path))==expected)

review=read(prefix+'review-manifest.json')
check('review manifest binding',review['base']==MAIN and review['reviewed_head']==REVIEWED and review['frozen_tested_source']==FROZEN)
for path,info in review['files'].items():
    payload=blob(HEAD,path)
    check('review manifest '+path,sha(payload)==info['sha256'] and len(payload)==info['bytes'])
review_audit=read(prefix+'evidence-audit.stdout.json')
check('297 review audit checks',review_audit['status']=='passed' and review_audit['check_count']==297 and len(review_audit['checks'])==297)
check('review audit binding',review_audit['review_head']==REVIEWED and review_audit['frozen_tested_source']==FROZEN)
regression=read(prefix+'regression.json')
check('9 captured regression exit',regression['head']==REVIEWED and regression['exit_code']==0)
for name,expected in regression['outputs'].items():
    check('regression output '+name,sha((ROOT/prefix/name).read_bytes())==expected)
check('9 captured regressions actual stdout','9 passed' in (ROOT/prefix/'regression.stdout.txt').read_text())
check('6 old malformed actual stdout','6 passed' in (ROOT/prefix/'boundary-w007-regression.stdout.txt').read_text())
boundary=read(prefix+'boundary-receipt.json')
check('boundary commands passed',all(row['exit']==0 for row in boundary['commands']))
geometry=read(prefix+'geometry-receipt.json')
check('geometry commands passed',all(row['exit_code']==0 for row in geometry['commands']))
text=blob(HEAD,report).decode()
check('no must-fix review conclusion','新增 finding 0，剩余必须修正项 0' in text)
check('resource scope explicit',all(t in text for t in ('136,461,405','7,322,828','9,257,804','不是精确进程峰值','不能当 W011 增量 RSS','当前受限集成未发现实际资源阻塞','W012')))
check('historical adoption explicit','本次没有重新安装' in text and '本次未重跑 readback codec' in text)

result=dict(checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            base=MAIN,reviewed=REVIEWED,delivery=HEAD,
            reviewed_tree=git('rev-parse',HEAD+'^{tree}').decode().strip(),
            status='passed',must_fix=0,checks=checks,check_count=len(checks),
            changed_review_paths=len(changes),source_count=262,runtime_count=100,
            review_manifest_files=len(review['files']),
            limits=['Read-only identity/output checks; no rerun of 297 original audit operations or product tests.',
                    'No build, installation, full codec/readback execution or new resource benchmark.',
                    'Review resource judgment is for bounded serial synthetic M1; no production/maximum input bound.'])
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'audit-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
