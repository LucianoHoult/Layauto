"""Confirm reviewer-only additions and unchanged product/history before commit."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root=Path.cwd()
head='73e38df8f932bbb5bd9caf074b442ad2f5c286e9'
task='docs/tasks/W009-effective-geometry-terminals.md'
report='docs/tasks/W009/ipmr01-fix-review.md'
prefix='docs/tasks/W009/ipmr01-verification/review/'
tracked=subprocess.check_output(['git','diff','--name-only',head],text=True).splitlines()
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
paths=sorted(set(tracked+untracked))
assert all(p in (task,report) or p.startswith(prefix) for p in paths),paths
current=(root/task).read_text()
before=subprocess.check_output(['git','show',head+':'+task],text=True)
start=current.index('### R4 IPMR-01')
end=current.index('## PM 验收与交接（PM）',start)
assert current[:start]+current[end:]==before,'Edits outside new reviewer section'
manifest=json.loads((root/'docs/tasks/W009/ipmr01-verification/review/version-scope.json').read_text())
assert manifest['head']==head
for name,entry in manifest['sources'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==entry['sha256']
links=[]
for document in (task,report):
    text=(root/document).read_text()
    if document==task:
        text=text[start:end]
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):
            continue
        path=target.split('#',1)[0]
        assert (root/document).parent.joinpath(path).exists(),(document,target)
        links.append(dict(document=document,target=target))
outputs={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths if p!=prefix+'delivery-audit.json'}
result=dict(reviewed_product=head,reviewer_only_paths=True,only_new_reviewer_task_section=True,original_118_source_items_unchanged=True,local_links_resolve=True,links=links,path_count=len(paths),outputs=outputs)
(root/(prefix+'delivery-audit.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('outputs','links')},indent=2))
