"""Check final review document ownership and unchanged frozen inputs; read only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = '8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    checks = []

    def check(ok, label):
        assert ok, label
        checks.append(label)

    task = Path('docs/tasks/W014-terminal-body-relations.md')
    before = subprocess.check_output(['git', 'show', BASE + ':' + str(task)], cwd=ROOT)
    current = (ROOT / task).read_bytes()
    plan = '## 方案与决定（执行准备，PM接收）'.encode()
    pm = '## PM验收与交接（PM）'.encode()
    review = '## Review结论（reviewer）'.encode()
    check(before.count(plan) == current.count(plan) == before.count(pm) == current.count(pm) == 1,
          'exact PM section markers retained')
    check(before.partition(plan)[0] == current.partition(plan)[0], 'PM requirements and task phase prefix byte-identical')
    check(before.partition(pm)[2] == current.partition(pm)[2], 'PM acceptance and handoff suffix byte-identical')
    review_text = current.partition(review)[2].partition(pm)[0].decode()
    check('独立review通过，未关闭必须项0，交PM验收' in review_text, 'authorized reviewer section updated with bounded verdict')
    frozen = json.loads((ROOT / 'docs/tasks/W014/development/frozen-source.json').read_bytes())
    for name, wanted in frozen['files'].items():
        check(sha((ROOT / name).read_bytes()) == wanted, 'unchanged final selected source/test/config ' + name)
    scope = json.loads((OUT / 'authorized_scope_audit.stdout.json').read_bytes())
    for name, wanted in scope['protected_original_sha256'].items():
        check(sha((ROOT / name).read_bytes()) == wanted, 'unchanged protected original ' + name)
    tools = json.loads((ROOT / 'docs/tasks/W014/verification/tool-identity.json').read_bytes())
    for name, receipt in tools.items():
        check(sha(Path(receipt['source']).read_bytes()) == receipt['sha256'], 'unchanged frozen tool ' + name)
    check(sha((ROOT / 'docs/tasks/W014/resource-clearance.json').read_bytes())
          == 'b9c699e9d2284fbc40a32641c98a89f4293e9c244ee50f203f5298f0153a2222',
          'original clearance unchanged')
    audit = json.loads((OUT / 'final_engineering_audit.stdout.json').read_bytes())
    check(audit['status'] == 'passed' and audit['check_count'] == 840
          and audit['source_id'] == frozen['source_id'], 'actual independent final engineering audit applies')
    for document in (task, Path('docs/tasks/W014/code-review.md'), Path('docs/tasks/W014/resource-review.md')):
        text = (ROOT / document).read_text()
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if '://' in target or target.startswith('#'):
                continue
            path = (ROOT / document.parent / target.split('#', 1)[0]).resolve()
            check(path.is_file(), 'accessible review link ' + str(document) + ':' + target)
    result = {'status': 'passed', 'classification': 'final-review-owner-and-link-check',
        'source_id': frozen['source_id'], 'freeze_commit': audit['freeze_commit'],
        'check_count': len(checks), 'checks': checks,
        'limitations': ['No product/test/capture/codec/build/install rerun.',
            'Review verdict does not change PM requirements, phase or acceptance.']}
    (OUT / 'final_review_owner_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'classification', 'source_id', 'check_count')}, indent=2))


if __name__ == '__main__':
    main()
