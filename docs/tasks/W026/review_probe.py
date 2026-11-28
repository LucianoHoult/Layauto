"""Independent remapping of three fixture facts, checked through Stage 2/3 public APIs."""
from pathlib import Path
from tempfile import TemporaryDirectory

from docs.tasks.W022.review_probe import read_rectangles
from layauto_v2.constraints import check_rules
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import FIXTURE, rebind, sha
from w023_cases import capture
from w024_cases import stage


def run(parent):
    root = stage(parent, 'c14')
    path = root / 'source.gds'
    # C14 changes only @2544. Bring in only VN's 64-byte BOUNDARY from the other drawing.
    stream = bytearray(path.read_bytes())
    shifted = (FIXTURE / 'failures/via_enclosure/source.gds').read_bytes()
    stream[2096:2160] = shifted[2096:2160]
    path.write_bytes(stream)
    target = root / 'target.cdl'
    assert target.read_text().count('TOY_N') == 1
    target.write_text(target.read_text().replace('TOY_N', 'TOY_P'))
    rebind(root)
    original = read_rectangles(path)
    via, wire = original[2096][2], original[1648][2]
    margins = via[0] - wire[0], via[1] - wire[1], wire[2] - via[2], wire[3] - via[3]
    gap = original[2544][2][0] - original[2480][2][2]
    assert wire[2] - via[0] == 1 and margins == (5, 20, -3, 1) and gap == 4

    repo = PublicationRepository()
    _, request = capture(repo, root, 'ir', lineage='ir', budget=400)
    sealed = publish_stage2(repo, request)
    attempt = repo.load_attempt('ir')
    before = repo.snapshot()
    view = open_constraint_context(repo, 'ir', attempt.context_ref)
    result = check_rules(view)
    failures = {'T03.recognition', 'T05.contact_enclosure', 'T07.m1_spacing'}
    assert len(result.checks) == 10
    for row in result.checks:
        assert row.status == ('violation' if row.rule.id in failures else 'pass'), (row.rule.id, row.issue)
    changed = tuple(o for o in result.for_rule('T03.recognition').observations if o.status == 'violation')
    assert changed and all(o.kind == 'device_model' for o in changed)
    assert all(o.object_ids[0] == 'MN0' and o.facts['target_model'] == 'TOY_P' for o in changed)
    assert {s.sha256 for o in changed for s in o.sources} >= {sha(root / 'source.cdl'), sha(target)}
    bad, = (o for o in result.for_rule('T05.contact_enclosure').observations if o.status == 'violation')
    assert bad.facts['margins_nm'] == margins and bad.facts['side_layer'] == 'LI'
    assert bad.facts['edge_id'] in view.snapshot.state['connectivity']['edges']
    assert [(s.sha256, s.byte_offset) for s in bad.sources[:2]] == [(sha(path), 2096), (sha(path), 1648)]
    metal, = result.for_rule('T07.m1_spacing').violations
    assert metal.distance_nm == gap and metal.threshold_nm == 5
    assert sorted([metal.first.source.byte_offset, metal.second.source.byte_offset]) == [2480, 2544]
    assert repo.snapshot() == before and repo.load_attempt('ir') == attempt
    assert repo.load_head('ir') == sealed.head_ref == result.version.head_ref
    assert repo.read(result.version.snapshot_ref) == view.snapshot
    print('T03 MN0 target model TOY_P; T05 VN/LI', margins, 'nm; T07 M1', gap,
          'nm; other seven pass; sealed version', result.version.version)


if __name__ == '__main__':
    with TemporaryDirectory() as tmp:
        run(Path(tmp))
