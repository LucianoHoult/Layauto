"""Read-only A1 integration review receipt and frozen source identity check."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path('/workspace/Layauto')
OUT = Path(__file__).resolve().parent
BASE = '0a3326aa363477724465886cd05874d0997fba3e'
REVIEW_BASE = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'
DELIVERY = '1a1459e3179e7bd234e4971c1969a6a78f387fd2'
MERGE = '08dd232139918dc97b0a6d255aad237eb844686a'
MERGE_TREE = 'dc7f3ee70aa35a708abbea4a204f4b60810cbcd4'
REFS = [
    'ca1f810c3c97376f71089d8b4054760ff198012f',
    '44a91c472fdeba5bb4b8a6071c0580313336c379',
    'db07a16fb7cbbac030adae84a9eb88cc0c8aa650',
    REVIEW_BASE, DELIVERY, MERGE,
]
TASK = 'docs/tasks/W012-capture-wire-performance.md'
REPORT = 'docs/tasks/W012/A1/independent-premerge-review.md'
PREFIX = 'docs/tasks/W012/A1/premerge-review-evidence/'


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree(ref: str) -> dict[str, tuple[str, str, str]]:
    rows = {}
    for item in git('ls-tree', '-rz', '--full-tree', ref).split(b'\0'):
        if item:
            descriptor, path = item.split(b'\t', 1)
            rows[path.decode()] = tuple(descriptor.decode().split())
    return rows


def main() -> None:
    started_head = git('rev-parse', 'HEAD').decode().strip()
    started_status = git('status', '--porcelain=v1').decode()
    assert started_head == MERGE, started_head
    assert not started_status, started_status
    assert git('rev-parse', DELIVERY + '^').decode().strip() == REVIEW_BASE
    parents = git('rev-list', '--parents', '-n', '1', MERGE).decode().split()
    assert parents == [MERGE, BASE, DELIVERY], parents
    actual_merge_tree = git('rev-parse', MERGE + '^{tree}').decode().strip()
    assert actual_merge_tree == MERGE_TREE
    assert git('rev-parse', DELIVERY + '^{tree}').decode().strip() == actual_merge_tree
    assert git('rev-parse', 'refs/heads/main').decode().strip() == MERGE
    records = []
    for line in git('diff', '--name-status', REVIEW_BASE, DELIVERY).decode().splitlines():
        status, path = line.split('\t')
        assert (status == 'M' and path == TASK) or (status == 'A' and (path == REPORT or path.startswith(PREFIX))), line
        records.append({'status': status, 'path': path})
    assert len(records) == 72, len(records)
    original = git('show', REVIEW_BASE + ':' + TASK).decode()
    delivered = git('show', DELIVERY + ':' + TASK).decode()
    block_start = delivered.index('\n### A1 合并前独立 session review\n')
    block_end = delivered.index('\n## PM 验收与交接（PM）\n', block_start)
    review_append = delivered[block_start:block_end]
    assert delivered[:block_start] + delivered[block_end:] == original
    assert review_append.count('\n') == 8
    unchanged_paths = ['docs/current-work.md', 'docs/README.md', 'README.md', 'docs/architecture.md', 'AGENTS.md', 'docs/collaboration/rules.md']
    for name in unchanged_paths:
        assert git('show', REVIEW_BASE + ':' + name) == git('show', DELIVERY + ':' + name), name
    manifest_paths = [f'docs/tasks/W012/A1/{part}/source-manifest.json' for part in ('verification-attempt-01', 'verification-r2')]
    manifests = [json.loads((ROOT / name).read_text()) for name in manifest_paths]
    files = manifests[1]['files']
    runtime = manifests[1]['runtime_files']
    assert len(files) == 263 and len(runtime) == 100
    assert manifests[0]['files'] == files and manifests[0]['runtime_files'] == runtime
    current_hashes = {name: sha((ROOT / name).read_bytes()) for name in files}
    assert current_hashes == files
    assert {name.removeprefix('layauto_v2/'): digest for name, digest in files.items() if name.startswith('layauto_v2/')} == runtime
    trees = {ref: tree(ref) for ref in REFS}
    frozen = trees[REFS[0]]
    for ref, entries in trees.items():
        assert all(entries[name] == frozen[name] for name in files), ref
    tar_checks = []
    for name in manifest_paths:
        tar_path = ROOT / Path(name).parent / 'source-snapshot.tar.gz'
        with tarfile.open(tar_path, 'r:gz') as archive:
            members = archive.getmembers()
            assert len(members) == 263 and all(member.isfile() for member in members)
            assert len({member.name for member in members}) == 263
            identities = {member.name: sha(archive.extractfile(member).read()) for member in members}
            assert identities == files
        tar_checks.append({'path': str(tar_path.relative_to(ROOT)), 'members': len(members), 'all_263_equal_manifest_and_current': True, 'sha256': sha(tar_path.read_bytes())})
    for left, right in zip([BASE] + REFS, REFS):
        subprocess.run(['git', 'merge-base', '--is-ancestor', left, right], cwd=ROOT, check=True)
    end_head = git('rev-parse', 'HEAD').decode().strip()
    end_status = git('status', '--porcelain=v1').decode()
    assert end_head == started_head and end_status == started_status
    result = {
        'status': 'passed', 'review_base': REVIEW_BASE, 'delivery': DELIVERY, 'main_base': BASE,
        'integration_commit': MERGE, 'integration_parents': parents[1:], 'integration_tree': actual_merge_tree,
        'integration_full_tree_equal_delivery': True, 'local_main_points_to_integration': True,
        'delivery_parent_is_review_base': True, 'review_delivery_paths': len(records),
        'review_only_added_files': sum(row['status'] == 'A' for row in records),
        'task_reviewer_append_lines': review_append.count('\n'),
        'task_original_bytes_preserved_by_removing_only_new_reviewer_section': True,
        'unchanged_pm_and_normative_paths': unchanged_paths,
        'source_manifest_files': len(files), 'runtime_files': len(runtime),
        'both_source_manifests_equal': True,
        'source_identity_equal_commits': REFS,
        'all_263_current_sha256_equal_manifest': True,
        'all_263_git_blob_ids_and_modes_equal_across_refs': True,
        'tar_checks': tar_checks,
        'source_manifest_sha256': {name: sha((ROOT / name).read_bytes()) for name in manifest_paths},
        'source_files': files, 'runtime_files_manifest': runtime,
        'review_delivery_changes': records,
        'started_head': started_head, 'ended_head': end_head,
        'started_git_status_porcelain': started_status, 'ended_git_status_porcelain': end_status,
        'new_mandatory_findings': 0, 'remaining_mandatory_findings': 0,
        'limitations': ['Read-only evidence receipt/source check; no product, engineering matrix, benchmark or large-wire rerun.', 'PM runs actual merged-version combination validation separately.'],
    }
    (OUT / 'source-scope-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('source_files', 'runtime_files_manifest', 'review_delivery_changes')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
