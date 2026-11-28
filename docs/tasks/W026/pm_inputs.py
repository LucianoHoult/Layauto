"""Inspect the local and external enclosure evidence in a published W025 baseline."""
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from docs.tasks.W022.review_probe import read_rectangles
from layauto_v2.constraints import check_spacing
from layauto_v2.normalization.stage2 import Stage2AssemblyError
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w005_cases import apply_case, copy_input, read_json, rebind, write_json
from w018_cases import COORDINATE_URI, select_projection
from w022_cases import COMPLETE
from w023_cases import capture


def inspect(case: str) -> None:
    repo = PublicationRepository()
    with TemporaryDirectory() as directory:
        root = copy_input(Path(directory))
        if case == 'external_equality':
            path = root / 'body/context.json'
            document = read_json(path)
            tap, = (s for s in document['shapes'] if s['id'] == 'TN.ext')
            tap['bbox'] = [-12, 49, -8, 53]
            write_json(path, document)
        elif case != 'normal':
            apply_case(root, case)
        select_projection(root)
        copyfile(COMPLETE, root / COORDINATE_URI)
        rebind(root)
        stream = read_rectangles(root / 'source.gds')
        body = {s['id']: s['bbox'] for s in read_json(root / 'body/context.json')['shapes']}
        x0, y0, x1, y1 = body['TN.ext']
        left, bottom, right, top = body['MN.ext']
        margin = min(x0 - left, y0 - bottom, right - x1, top - y1)
        _, request = capture(repo, root, case, lineage=case, budget=400)
        if case == 'body_enclosure':
            before = repo.snapshot()
            try:
                publish_stage2(repo, request)
            except Stage2AssemblyError as exc:
                assert exc.stage == 'terminal_relations' and margin == 0
                issue, = (i for i in exc.result.issues if i.code == 'BodyTapEnclosureFailure')
                assert issue.source.uri == 'body/context.json' and issue.source.field == '/shapes/4'
                assert issue.source.sha256 == sha256((root / issue.source.uri).read_bytes()).hexdigest()
                assert repo.snapshot() == before and repo.load_head(case) is None
                print(case, 'external rail margin 0 nm, Stage 2:', issue.code, issue.source.field, 'no head')
                return
            raise AssertionError('expected Stage 2 to reject zero external enclosure')
        publish_stage2(repo, request)

    attempt = repo.load_attempt(case)
    before = repo.snapshot()
    ctx = open_constraint_context(repo, case, attempt.context_ref)
    state = ctx.snapshot.state
    records = state['geometry']['records']
    vn, = (i for i, r in records.items() if r['layer'] == 'VIA0' and r['rect'][1] == 50)
    ln, = (r for r in records.values() if r['layer'] == 'LI' and r['rect'] == (28, 30, 34, 55))
    via = records[vn]
    via_offset, li_offset = via['source']['byte_offset'], ln['source']['byte_offset']
    vx0, vy0, vx1, vy1 = stream[via_offset][2]
    lx0, ly0, lx1, ly1 = stream[li_offset][2]
    local = min(vx0 - lx0, vy0 - ly0, lx1 - vx1, ly1 - vy1)
    local_audits = state['connectivity']['enclosure']
    assert len(local_audits) == 16
    bad = [(row['connector_id'], row['layer']) for row in local_audits if row['status'] == 'violation']
    assert bad == ([(vn, 'LI')] if case == 'via_enclosure' else [])
    assert local == (-3 if case == 'via_enclosure' else 1)

    taps = state['body']['tap_audits']
    assert len(taps) == 2 and {t['tap_id'] for t in taps} == {'TN.ext', 'TP.ext'}
    tap, = (t for t in taps if t['tap_id'] == 'TN.ext')
    assert min(tap['rail_margins_nm']) == margin == (1 if case == 'external_equality' else 2)
    assert all(t['status'] == 'satisfied' for t in taps)
    assert state['body']['local_graph_union'] is False
    report = check_spacing(ctx)
    assert report.for_rule('T06.li_spacing').status == report.for_rule('T07.m1_spacing').status == 'pass'
    row = report.for_rule('T05.contact_enclosure')
    assert row.status == 'pending' and row.rule.declaration['parameters']['enclosure_nm'] == 1
    assert repo.snapshot() == before and attempt.phase == 'sealed_open'
    print(case, 'GDS VIA0/LI offsets', via_offset, li_offset, 'local margin', local,
          'nm, TN.ext rail margin', margin, 'nm, local failing sides', len(bad),
          'external failing taps', sum(t['status'] == 'violation' for t in taps), 'T05 pending')


if __name__ == '__main__':
    for name in ('normal', 'via_enclosure', 'external_equality', 'body_enclosure'):
        inspect(name)
