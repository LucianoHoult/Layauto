"""Bounded final documentation/scope/identity checks, with no product imports."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path.cwd()
EVIDENCE = ROOT/'docs/tasks/W013/review-evidence/independent-premerge'
REPORT = ROOT/'docs/tasks/W013/independent-premerge-review.md'
TASK = ROOT/'docs/tasks/W013-net-annotation-coverage.md'
BASE = 'f31df3f3e6cd5df7ecef2e1f91977c3b68a9fac4'
git = lambda *args: subprocess.check_output(['git',*args],cwd=ROOT,text=True)
sha = lambda data: hashlib.sha256(data).hexdigest()
checks = {}

frozen = json.loads((ROOT/'docs/tasks/W013/verification-r2/source-manifest.json').read_text())
selected = ('layauto_v2','tests','pyproject.toml','README.md','docs/tasks/W003/examples/records.json')
names = set(git('ls-files','-z','--',*selected).split('\0'))
names.update(git('ls-files','-z','--others','--exclude-standard','--',*selected).split('\0'))
names.discard('')
files = {name:sha((ROOT/name).read_bytes()) for name in names}
assert files == frozen['files'] and len(files) == 273
checks['complete_273_current_source'] = sha(json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
assert checks['complete_273_current_source'] == frozen['source_id']

old = git('show',BASE+':docs/tasks/W013-net-annotation-coverage.md')
new = TASK.read_text()
start = new.index('### 合并前独立新会话复核（reviewer，2026-11-13）')
end = new.index('## PM 验收与交接（PM）',start)
assert new[:start]+new[end:] == old
checks['task_only_reviewer_append_preserving_pm_and_old_text'] = True

changed = set(git('diff',BASE,'--name-only').splitlines())
changed.update(git('ls-files','--others','--exclude-standard').splitlines())
allowed_files = {'docs/tasks/W013/independent-premerge-review.md','docs/tasks/W013-net-annotation-coverage.md'}
allowed_prefix = 'docs/tasks/W013/review-evidence/independent-premerge/'
assert all(name in allowed_files or name.startswith(allowed_prefix) for name in changed),sorted(changed)
checks['only_allowed_report_evidence_reviewer_paths'] = len(changed)

linked = 0
for path,text in ((REPORT,REPORT.read_text()),(EVIDENCE/'README.md',(EVIDENCE/'README.md').read_text()),(TASK,new[start:end])):
    for href in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in href or href.startswith('#'):continue
        target = unquote(href.split('#',1)[0])
        assert (path.parent/target).exists(),(path,target)
        linked += 1
checks['new_local_links_exist'] = linked
scripts = list(EVIDENCE.rglob('*.py'))
for path in scripts:ast.parse(path.read_text(),filename=str(path))
checks['archived_python_scripts_parse'] = len(scripts)

public = json.loads((EVIDENCE/'public.command.json').read_text())
header = json.loads((EVIDENCE/'header-attack.command.json').read_text())
for record,script,stdout,stderr in (
    (public,'public_probe.py','public.stdout.jsonl','public.stderr.txt'),
    (header,'header_attack.py','header-attack.stdout.json','header-attack.stderr.txt'),
):
    assert record['exit_code'] == 0
    assert record['script_sha256'] == sha((EVIDENCE/script).read_bytes())
    assert record['stdout_sha256'] == sha((EVIDENCE/stdout).read_bytes())
    assert record['stderr_sha256'] == sha((EVIDENCE/stderr).read_bytes())
assert header['helper_sha256'] == sha((EVIDENCE/'binding/mutate_receipt.py').read_bytes())
events = [json.loads(line) for line in (EVIDENCE/'public.stdout.jsonl').read_text().splitlines()]
assert events[-1]['passed'] and events[-1]['source_stable']
assert next(row for row in events if row['check']=='public_roundtrip')['old_decode_calls'] == [1,1,2]
assert len([row for row in events if row['check']=='original_exception_chain' and row['passed']]) == 4
assert all(row['rejected'] for row in json.loads((EVIDENCE/'header-attack.stdout.json').read_text())['checks'])
audit = json.loads((EVIDENCE/'evidence/stdout.json').read_text())
assert audit['status']=='passed' and audit['check_count']==59 and not audit['failures']
checks['public_probe_receipts_and_59_evidence_audit'] = True

manifest_path = EVIDENCE/'manifest.json'
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    assert all(sha((EVIDENCE/name).read_bytes())==value for name,value in manifest['files'].items())
    actual = {str(path.relative_to(EVIDENCE)) for path in EVIDENCE.rglob('*') if path.is_file() and path != manifest_path}
    assert actual == set(manifest['files'])
    checks['complete_archival_manifest'] = len(actual)
else:
    checks['complete_archival_manifest'] = 'not yet generated; check in memory after archival'
assert not git('diff',BASE,'--check')
checks['git_diff_check'] = True
print(json.dumps({'status':'passed','reviewed_head':BASE,'checks':checks},indent=2,ensure_ascii=False))
