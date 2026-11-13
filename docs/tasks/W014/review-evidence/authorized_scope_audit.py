"""Current tracked/untracked W014 scope audit; not final engineering review.

Uses Git metadata, original bytes, and current file paths only. No product,
test, codec, capture or benchmark calls. Live verification logs may still grow.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = '8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4'
COMMITS = ('40559e0186f7d80bb8a7f3256c900e0fadd66191',
           '66f5b1e5369549ed8df361f89f099acfd2f39e17')
TASK = 'docs/tasks/W014-terminal-body-relations.md'
RUNTIME = {'layauto_v2/domain/terminal_relations.py',
    'layauto_v2/derive/terminal_relations.py', 'layauto_v2/derive/body_relations.py',
    'layauto_v2/normalization/terminal_relations.py',
    'layauto_v2/normalization/terminal_relations_codec.py',
    'layauto_v2/normalization/__init__.py', 'pyproject.toml'}
TESTS = {'tests/contracts/test_w014_body_scope.py', 'tests/contracts/test_w014_contracts.py',
    'tests/contracts/test_w014_evidence_storage.py', 'tests/contracts/test_w014_readback_storage.py',
    'tests/contracts/test_w014_relations.py', 'tests/contracts/w014_cases.py',
    'tests/unit/test_w014_body.py', 'tests/unit/test_w014_terminal_values.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    checks = []

    def check(ok, label):
        assert ok, label
        checks.append(label)

    head = git('rev-parse', 'HEAD').decode().strip()
    branch = git('branch', '--show-current').decode().strip()
    check(head == COMMITS[-1] and branch == 'codex/w014-terminal-body-relations', 'expected freeze HEAD and requested branch')
    check(git('rev-list', '--reverse', BASE + '..HEAD').decode().splitlines() == list(COMMITS),
          'exactly the plan and product commits since preparation head')
    tracked_changed = git('diff', '--name-only', '-z', BASE, '--').decode().split('\0')
    tracked_changed = sorted(name for name in tracked_changed if name)
    untracked = sorted(name for name in git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0') if name)
    classified = {}
    for name in sorted(set(tracked_changed) | set(untracked)):
        if name in RUNTIME:
            owner = 'authorized runtime/export/typing configuration'
        elif name in TESTS:
            owner = 'authorized W014 tests/helper'
        elif name == TASK:
            owner = 'task execution and reviewed plan handoff; PM-owned sections checked separately'
        elif name.startswith('docs/tasks/W014/'):
            owner = 'W014 plan/design/execution/review/evidence/tool materials'
        elif name.startswith('work/w014-engineering/'):
            owner = 'temporary W014 engineering preflight execution evidence'
        elif name.startswith(('work/w014-independent-frame-', 'work/w014-review-body-')):
            owner = 'temporary fixture copies from the archived independent W014 body/frame probes'
        else:
            raise AssertionError('outside authorized W014 scope: ' + name)
        path = ROOT / name
        check(path.is_file() and not path.is_symlink(), 'authorized ordinary file ' + name)
        classified[name] = {'owner': owner, 'git_state': 'untracked' if name in untracked else 'tracked difference'}
    original = git('show', BASE + ':' + TASK)
    current = (ROOT / TASK).read_bytes()
    plan_marker = '## 方案与决定（执行准备，PM接收）'.encode()
    pm_marker = '## PM验收与交接（PM）'.encode()
    review_marker = '## Review结论（reviewer）'.encode()
    check(original.partition(plan_marker)[0] == current.partition(plan_marker)[0],
          'PM requirements, task phase and entire pre-plan prefix byte-identical')
    check(original.partition(pm_marker)[2] == current.partition(pm_marker)[2]
          and original.count(pm_marker) == current.count(pm_marker) == 1,
          'PM acceptance/handoff suffix byte-identical')
    check(original.partition(review_marker)[2].partition(pm_marker)[0]
          == current.partition(review_marker)[2].partition(pm_marker)[0],
          'task Review conclusion remains untouched during matrix')
    archive_bytes = git('archive', '--format=tar', BASE, '--', 'docs/architecture.md',
                        'docs/roadmap.md', 'docs/current-work.md', 'tests/fixtures', 'layauto_v2')
    protected = {}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:') as archive:
        for member in archive.getmembers():
            if not member.isfile() or member.name == 'layauto_v2/normalization/__init__.py':
                continue
            data = archive.extractfile(member).read()
            check((ROOT / member.name).read_bytes() == data, 'protected original bytes ' + member.name)
            protected[member.name] = sha(data)
    check(all(not name.startswith('tests/fixtures/') for name in untracked), 'no new untracked fixed fixture or answer')
    check("prefix='w014-review-body-'" in (OUT / 'body_scope_probe.py').read_text()
          and "prefix='w014-independent-frame-'" in (OUT / 'body_conflict_frame_probe.py').read_text(),
          'temporary fixture-copy prefixes are attributable to the archived independent probes')
    old_wire = sorted(name for name in protected if name.startswith('layauto_v2/')
                      and ('codec' in Path(name).name))
    check(len(old_wire) == 8, 'all eight old canonical/wire codec sources retained byte-identical')
    identities = {}
    for commit in COMMITS:
        author, committer = git('show', '-s', '--format=%ae%n%ce', commit).decode().splitlines()
        check(author == committer == 'LucianoHoult@users.noreply.github.com',
              'project noreply author and committer ' + commit)
        identities[commit] = {'author_email': author, 'committer_email': committer,
            'paths': git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()}
    frozen = json.loads((ROOT / 'docs/tasks/W014/development/frozen-source.json').read_bytes())
    check(all(sha((ROOT / name).read_bytes()) == wanted for name, wanted in frozen['files'].items()),
          'all selected frozen source/test/config bytes still unchanged while matrices run')
    counts = Counter(row['owner'] for row in classified.values())
    result = {'status': 'current-authorized-scope-audit-passed-not-final-engineering-or-product-review',
        'observed_at_utc': datetime.now(timezone.utc).isoformat(), 'base': BASE, 'head': head,
        'branch': branch, 'source_id': frozen['source_id'], 'check_count': len(checks), 'checks': checks,
        'tracked_changed_count': len(tracked_changed), 'untracked_count': len(untracked),
        'owner_counts': dict(counts), 'classified_current_changes': classified,
        'protected_original_file_count': len(protected), 'protected_original_sha256': protected,
        'old_wire_sources': old_wire, 'commit_identities': identities,
        'limitations': ['Current Git-visible tracked/untracked scope only; ignored caches are not deliverables.',
            'Final verification is still running and its append-only logs can grow after this path snapshot.',
            'No product/test/capture/codec/benchmark was executed; no frozen tool or PM conclusion was modified.',
            'This scope audit is not final matrix, installed smoke, product review or PM acceptance.']}
    (OUT / 'authorized_scope_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'base', 'head', 'source_id',
        'check_count', 'tracked_changed_count', 'untracked_count', 'owner_counts', 'protected_original_file_count')}, indent=2))


if __name__ == '__main__':
    main()
