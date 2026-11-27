"""Swap two valid checkpoint payloads one at a time and observe the public reader."""
from collections import Counter
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from layauto_v2.constraints import check_m1_spacing
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w023_cases import capture, sample


def main():
    repo = PublicationRepository()
    with TemporaryDirectory() as directory:
        root = sample(Path(directory))
        first, request = capture(repo, root, 'creator', budget=400)
        original = publish_stage2(repo, request)
        second, request = capture(repo, root, 'reuse', head=original.head_ref.id, budget=400)
        reused = publish_stage2(repo, request)
    assert not root.exists() and original.head_ref == reused.head_ref

    creator, reuse = first.checkpoint_ref, second.checkpoint_ref
    expected_snapshot = repo.read(original.head_ref).snapshot_ref
    good = repo._root
    contents = dict(good.contents)
    for ref in (creator, reuse):
        assert sha256(contents[ref]).hexdigest() == ref.digest and repo.read(ref).run_id == ref.run_id
    assert creator.digest != reuse.digest
    failures = []
    for bad, donor in ((None, None), (creator, reuse), (reuse, creator)):
        stored = good if bad is None else replace(good, contents=tuple(
            (ref, contents[donor] if ref == bad else payload) for ref, payload in good.contents))
        with patch.object(repo, '_root', stored):
            before = repo.snapshot()
            if bad is not None:
                try:
                    repo.read(bad)
                except RepositoryConflict as exc:
                    assert exc.code == 'RefConflict' and bad.id in str(exc) and 'digest mismatch' in str(exc)
                else:
                    raise AssertionError(f'direct read accepted {bad.id}')
            for ready in (first, second):
                run = ready.run_id
                attempt = repo.load_attempt(run)
                assert attempt.phase == 'sealed_open'
                required = {creator, ready.checkpoint_ref}
                with patch.object(repo, 'read', wraps=repo.read) as reads:
                    try:
                        context = open_constraint_context(repo, run, attempt.context_ref)
                    except RepositoryConflict as exc:
                        assert bad in required and exc.code == 'RefConflict'
                        assert bad.id in str(exc) and 'digest mismatch' in str(exc)
                        print('rejected', run, exc)
                    else:
                        report = check_m1_spacing(context)
                        result = report.for_rule('T07.m1_spacing')
                        assert result.status == 'pass' and len(result.pairs) == 6
                        assert min(p.distance_squared_nm2 for p in result.pairs) == 25
                        version = report.version
                        assert version.original_checkpoint_ref == creator and version.checkpoint_ref == ready.checkpoint_ref
                        assert version.tool_ref == ready.tool_ref and version.snapshot_ref == expected_snapshot
                        counts = Counter(call.args[0] for call in reads.call_args_list if call.args[0].kind == 'checkpoint')
                        print('pass', run, '5 nm; checkpoint reads', {ref.run_id: n for ref, n in counts.items()})
                        if counts != Counter(required):
                            failures.append(f'{run}: expected one read per distinct checkpoint')
                        if bad in required:
                            failures.append(f'{run}: opened with damaged {bad.id}')
                assert repo._root is stored and repo.snapshot() == before
                assert repo.load_head('L') == original.head_ref and repo.load_attempt(run) == attempt
        assert repo._root is good
    assert not failures, failures


if __name__ == '__main__':
    main()
