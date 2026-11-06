"""Verify reviewer-only edits and completed evidence before commit (no product writes)."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
HEAD = 'c4909ab679d0c0806200fcb132db8a5de1ad3e75'
TASK = 'docs/tasks/W010-local-contact-connectivity.md'
REPORT = 'docs/tasks/W010/independent-premerge-review.md'
PREFIX = 'docs/tasks/W010/independent-premerge-review/'
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
original=git('show',HEAD+':'+TASK)
current=(ROOT/TASK).read_text()
start=current.index('\n### R2 独立合并前复核（2026-11-06）')
end=current.index('\n## PM验收与交接（PM）',start)
assert current[:start]+current[end:] == original, 'outside reviewer addition changed'
changed=set(git('diff','--name-only',HEAD).splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
assert all(p in (TASK,REPORT) or p.startswith(PREFIX) for p in changed), changed
assert '剩余必须修正项 **0**' in (ROOT/REPORT).read_text()
manifest=json.loads((ROOT/'docs/tasks/W010/verification/source-manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
receipts={}
for name in ('pytest','typing','pip-check'):
    r=json.loads((OUT/'validation'/f'{name}.json').read_text())
    assert r['returncode']==0 and r['head']==r['finished_head']==HEAD
    for stream,v in r['outputs'].items():
        assert sha(OUT/'validation'/v['path'])==v['sha256']
    receipts[name]={'returncode':r['returncode'],'elapsed_seconds':r['elapsed_seconds']}
assert '1465 passed' in (OUT/'validation/pytest.stdout.txt').read_text()
assert '48 source files' in (OUT/'validation/typing.stdout.txt').read_text()
assert json.loads((OUT/'source-receipt.json').read_text())['exit_code']==0
assert json.loads((OUT/'exception-results.json').read_text())['status']=='passed'
assert not json.loads((OUT/'exception-results.json').read_text())['failures']
# Relative Markdown links in all new reports must resolve inside this checkout.
links=[]
for p in [ROOT/REPORT,*OUT.glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if '://' in target or target.startswith('#'): continue
        name=target.split('#')[0]
        if not name: continue
        resolved=p.parent/name
        assert resolved.exists() or resolved.resolve() == (OUT/'delivery-audit.json').resolve(), (str(p),target)
        links.append([str(p.relative_to(ROOT)),target])
files={p:sha(ROOT/p) for p in sorted(changed) if (ROOT/p).is_file() and p!=PREFIX+'delivery-audit.json'}
result={'reviewed_head':HEAD,'source_files_unchanged':len(manifest['files']),
        'reviewer_only_task_addition':True,'allowed_paths_only':True,'checks':receipts,
        'new_report_links_verified':links,'files_sha256':files,
        'original_checkout_status':subprocess.check_output(['git','status','--short','--branch'],cwd='/workspace/Layauto',text=True),
        'status':'passed','note':'Evidence excludes this self-referential audit; review commit and remote SHA are reported after push.'}
(OUT/'delivery-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'passed','files':len(files),'source_files_unchanged':len(manifest['files'])}))
