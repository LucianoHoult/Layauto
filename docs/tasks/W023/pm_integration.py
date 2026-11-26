"""Read the same M1 line ends from the published normal and C14 baselines."""
from itertools import combinations
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from layauto_v2.pipeline import publish_stage2
from layauto_v2.repository import PublicationRepository, RepositoryConflict
from w005_cases import apply_case, copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE
from w023_cases import capture


def stage(directory, case):
    root = copy_input(directory)
    if case == 'c14':
        apply_case(root, 'count_correct_rule_wrong')
    select_projection(root)
    copyfile(COMPLETE, root / COORDINATE_URI)
    rebind(root)
    return root


def exercise(repository, root, case, expected_gap):
    ready, request = capture(repository, root, case, lineage=case, budget=400)
    context = publish_stage2(repository, request)
    assert repository.load_head(case) == context.head_ref
    head = repository.read(context.head_ref)
    snap = repository.read(head.snapshot_ref)
    assert repository.read(head.event_ref).snapshot_ref == head.snapshot_ref
    assert head.eco_commits == () and snap.version == 0
    assert repository.load_attempt(ready.run_id).phase == 'sealed_open'
    assert repository.read(context.target_ref).differences == ()
    after = repository.snapshot()
    assert publish_stage2(repository, request) == context and repository.snapshot() == after

    metal = [r for r in snap.state['geometry']['records'].values() if r['layer'] == 'M1']
    pairs = []
    for a, b in combinations(metal, 2):
        ax, ay, ar, at = a['rect']
        bx, by, br, bt = b['rect']
        dx = max(0, ax - br, bx - ar)
        dy = max(0, ay - bt, by - at)
        locations = tuple(sorted((a['source']['byte_offset'], b['source']['byte_offset'])))
        pairs.append((dx*dx + dy*dy, locations))
    min_squared, offsets = min(pairs)
    assert len(pairs) == 6 and min_squared == expected_gap**2 and offsets == (2480, 2544)
    print(case, 'snapshot', snap.version, 'nearest_pair_dbu2', min_squared,
          'offsets', offsets, 'fragments', len(snap.state['occupancy']), flush=True)
    return context.head_ref


if __name__ == '__main__':
    repo = PublicationRepository()
    with TemporaryDirectory() as normal, TemporaryDirectory() as changed:
        a = stage(Path(normal), 'normal')
        b = stage(Path(changed), 'c14')
        initial = exercise(repo, a, 'normal', 5)
        _, second = capture(repo, a, 'reuse', lineage='normal', head=initial.id, budget=400)
        assert publish_stage2(repo, second).head_ref == initial
        exercise(repo, b, 'c14', 4)
        before, mismatch = capture(repo, b, 'mismatch', lineage='normal', head=initial.id, budget=400)
        old = repo.snapshot()
        try:
            publish_stage2(repo, mismatch)
        except RepositoryConflict as exc:
            assert exc.code == 'BindingConflict', exc
        else:
            raise AssertionError('changed geometry was accepted for the original head')
        assert repo.snapshot() == old and repo.load_attempt('mismatch') == before.attempt
        print('identical capture reused original head; C14 reuse refused; published versions unchanged')
