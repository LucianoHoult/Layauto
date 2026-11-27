"""PM check: compare first publication and head reuse after one stored record is lost."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from layauto_v2.constraints import check_m1_spacing
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w023_cases import capture
from w024_cases import stage


def inspect_run(repo, name):
    attempt = repo.load_attempt(name)
    assert attempt.phase == 'sealed_open'
    ctx = open_constraint_context(repo, name, attempt.context_ref)
    report = check_m1_spacing(ctx)
    result = report.for_rule('T07.m1_spacing')
    assert result.status == 'pass' and len(result.pairs) == 6
    assert min(p.distance_squared_nm2 for p in result.pairs) == 25
    return report.version


def main():
    repo = PublicationRepository()
    with TemporaryDirectory() as directory:
        root = stage(Path(directory), 'normal')
        _, first = capture(repo, root, 'creator', lineage='L', budget=400)
        publish_stage2(repo, first)
        head = repo.load_head('L')
        _, second = capture(repo, root, 'reuse', lineage='L', head=head.id, budget=400)
        publish_stage2(repo, second)
    assert not root.exists()
    original, reused = (inspect_run(repo, run) for run in ('creator', 'reuse'))
    assert original.head_ref == reused.head_ref == head
    assert original.snapshot_ref == reused.snapshot_ref
    assert original.checkpoint_ref != reused.checkpoint_ref
    ref = reused.original_checkpoint_ref
    assert original.checkpoint_ref == ref and repo.read(ref).outcome == 'inputs_ready'
    print('healthy: both runs pass, 6 pairs, minimum 5 nm, same head and snapshot; distinct run checkpoints')
    print('original:', ref.id)
    clean = repo._root
    missing = replace(clean, contents=tuple((r, b) for r, b in clean.contents if r != ref))
    assert len(missing.contents) == len(clean.contents) - 1
    unexpected = []
    with patch.object(repo, '_root', missing):
        try:
            repo.read(ref)
        except RepositoryConflict as exc:
            assert exc.code == 'RefConflict' and ref.id in str(exc)
            print('direct read:', exc.code, str(exc))
        else:
            raise AssertionError('missing record remained readable')
        assert repo.read(reused.checkpoint_ref).outcome == 'inputs_ready'
        for run in ('creator', 'reuse'):
            try:
                version = inspect_run(repo, run)
            except RepositoryConflict as exc:
                assert exc.code == 'RefConflict' and ref.id in str(exc)
                print(run, 'rejected:', exc.code, str(exc))
            else:
                assert version.original_checkpoint_ref == ref
                print(run, 'unexpected pass; original_checkpoint_ref points to missing record')
                unexpected.append(run)
        assert repo._root is missing and repo.load_head('L') == head
    assert repo._root is clean
    assert not unexpected, f'missing original checkpoint accepted by {unexpected}'


if __name__ == '__main__':
    main()
