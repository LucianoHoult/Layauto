"""Publish two full-cell LI/CUT inputs and inspect the operands available to W025."""
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from layauto_v2.constraints import check_m1_spacing
from layauto_v2.pipeline import open_constraint_context, publish_stage2
from layauto_v2.repository import PublicationRepository
from w010_cases import append_records
from w018_cases import COORDINATE_URI
from w023_cases import capture
from w024_cases import stage


def stage_gap(parent: Path, gap_nm: int) -> Path:
    """The LI input is identical. Only the right edge of its CUT varies."""
    if gap_nm not in (1, 2):
        raise ValueError('expected a 1 or 2 nm example')
    root = stage(parent, 'normal')
    path = root / COORDINATE_URI
    config = yaml.safe_load(path.read_bytes())
    axes = config['coordinate_projection']['layers']['LI']
    axes['x_edges'].update(pitch_dbu=32, cells=5)
    axes['y_edges'].update(pitch_dbu=16, cells=13)
    path.write_text(yaml.safe_dump(config), encoding='utf-8')
    append_records(root, [('LI', (130, 20, 150, 24)), ('CUT', (139, 18, 139 + gap_nm, 26))])
    return root


def inspect_gap(gap_nm: int) -> None:
    run = f'li-gap-{gap_nm}'
    repo = PublicationRepository()
    with TemporaryDirectory() as directory:
        root = stage_gap(Path(directory), gap_nm)
        _, request = capture(repo, root, run, lineage=run, budget=400)
        publish_stage2(repo, request)
    attempt = repo.load_attempt(run)
    before = repo.snapshot()
    ctx = open_constraint_context(repo, run, attempt.context_ref)
    state = ctx.snapshot.state
    geo = state['geometry']
    owner, = (ref for ref, r in geo['records'].items()
              if r['layer'] == 'LI' and r['rect'] == (130, 20, 150, 24))
    cut, = (ref for ref, r in geo['records'].items() if r['layer'] == 'CUT')
    row = geo['effective_by_record'][owner]
    assert row['contributors'] == (cut,) and len(row['region_ids']) == 2
    regions = [geo['regions'][ref] for ref in row['region_ids']]
    assert all(r['owner_id'] == owner and r['contributors'] == (cut,) for r in regions)
    expected = [(130, 20, 139, 24), (139 + gap_nm, 20, 150, 24)]
    assert sorted(rect for r in regions for rect in r['rectangles']) == expected
    fragments = [f for f in state['occupancy'] if f['view'] == 'effective' and f['record_id'] == owner]
    assert {f['indices'] for f in fragments} == {(4, 1)}
    assert sorted(f['rect'] for f in fragments) == expected
    rule, = (r for r in ctx.catalog.rules if r.id == 'T06.li_spacing')
    assert rule.declaration['parameters']['min_distance_nm'] == 2
    t07 = check_m1_spacing(ctx).for_rule('T07.m1_spacing')
    assert t07.status == 'pass' and min(p.distance_squared_nm2 for p in t07.pairs) == 25
    assert attempt.phase == 'sealed_open' and repo.snapshot() == before
    offsets = [geo['records'][ref]['source']['byte_offset'] for ref in (owner, cut)]
    print(run, 'region rectangles', expected, 'cell (4,1)', 'GDS offsets LI/CUT', offsets,
          'T06 threshold 2 nm', 'T07 minimum 5 nm')


if __name__ == '__main__':
    for gap in (2, 1):
        inspect_gap(gap)
