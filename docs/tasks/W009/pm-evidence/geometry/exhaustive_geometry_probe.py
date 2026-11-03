"""PM bounded independent math oracle; no fixture answers or test helpers."""
from __future__ import annotations
import hashlib, json, platform, subprocess, sys, time
from pathlib import Path
from layauto_v2.domain.geometry import Rect
from layauto_v2.state.regions import slab_difference, _groups
from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.effective import build_effective_geometry

START = time.perf_counter()
ROOT = Path('/workspace/Layauto')
stats = dict(mask_cases=0, membership_checks=0, independent_group_checks=0,
             redundant_cut_partition_checks=0, transformed_cases=0)

def expected_groups(cells):
    remaining = set(cells)
    groups = []
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        seen, pending = {first}, [first]
        while pending:
            x,y = pending.pop()
            for nxt in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if nxt in remaining:
                    remaining.remove(nxt)
                    seen.add(nxt)
                    pending.append(nxt)
        groups.append(frozenset(seen))
    return set(groups)

def inside_twice(rect,x,y):
    return 2*rect.x0 <= x < 2*rect.x1 and 2*rect.y0 <= y < 2*rect.y1

cells = tuple((x,y) for x in range(3) for y in range(3))
for mask in range(512):
    removed = {cell for i,cell in enumerate(cells) if mask & (1 << i)}
    remaining = set(cells) - removed
    cuts = [Rect(x,y,x+1,y+1) for x,y in sorted(removed)]
    target = Rect(0,0,3,3)
    out = slab_difference(target,cuts)
    assert sum(r.area for r in out) == len(remaining)
    assert out == slab_difference(target,list(reversed(cuts))+cuts)
    # Merge adjacent unit CUT cells into maximal row spans. This is an oracle
    # preserving the mask, not a call to canonical_cover or a product splitter.
    merged = []
    for y in range(3):
        x = 0
        while x < 3:
            if (x,y) not in removed:
                x += 1
                continue
            start = x
            while x < 3 and (x,y) in removed:
                x += 1
            merged.append(Rect(start,y,x,y+1))
    assert slab_difference(target,merged) == out
    stats['redundant_cut_partition_checks'] += 1
    for x in range(-1,8):
        for y in range(-1,8):
            # floor division locates the original half-open unit cell, also
            # testing boundaries/vertices and samples outside the target.
            expected = (x//2,y//2) in remaining
            assert sum(inside_twice(r,x,y) for r in out) == int(expected)
            stats['membership_checks'] += 1
    obtained_groups = set()
    for group in _groups(out):
        occupied = frozenset(cell for cell in cells
                             if any(inside_twice(r,2*cell[0]+1,2*cell[1]+1) for r in group))
        obtained_groups.add(occupied)
    assert obtained_groups == expected_groups(remaining)
    stats['independent_group_checks'] += 1
    # Every mask also tested after a very large translation and a non-unit
    # scale, proving no hidden float/raster dependence in these finite cases.
    offset = (1 if mask % 2 else -1) * 2**90
    def move(r):
        return Rect(11*r.x0+offset,11*r.y0-offset,11*r.x1+offset,11*r.y1-offset)
    assert slab_difference(move(target),[move(r) for r in cuts]) == tuple(move(r) for r in out)
    stats['transformed_cases'] += 1
    stats['mask_cases'] += 1

parsed = read_inputs(ROOT/'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'
base = build_geometry(geometry_from_parse_result(parsed))
assert base.status == 'success'
result = build_effective_geometry(base)
assert result.status == 'success' and result.value is not None
assert result.input is base and result.value.base is base.value
channels, terminals = [], []
for record in result.value.records:
    raw = result.value.base.layout.record(record.record_id)
    if record.operation == 'terminal':
        values = {region.role: region for region in record.regions}
        assert set(values) == {'channel','S','D'}
        boxes = [rect for region in values.values() for rect in region.rectangles]
        assert sum(r.area for r in boxes) == raw.rect.area
        for i,a in enumerate(boxes):
            for b in boxes[i+1:]:
                assert max(a.x0,b.x0) >= min(a.x1,b.x1) or max(a.y0,b.y0) >= min(a.y1,b.y1)
        channels.extend(r.bounds for r in values['channel'].rectangles)
        terminals.extend((role,r.bounds) for role in ('S','D') for r in values[role].rectangles)
assert sorted(channels) == [(58,20,62,70),(58,110,62,180)]
assert sorted(terminals) == [('D',(62,20,100,70)),('D',(62,110,100,180)),
                            ('S',(20,20,58,70)),('S',(20,110,58,180))]
paths = ['layauto_v2/domain/regions.py','layauto_v2/state/regions.py','layauto_v2/normalization/effective.py']
print(json.dumps(dict(status='passed', scope='PM focused geometry check, not complete premerge review',
                     python=sys.version, executable=sys.executable, platform=platform.platform(),
                     checkout=str(ROOT), head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                     counts=stats, actual_input='tests/fixtures/w003_m1/site_config.yaml',
                     normal_channels=channels, normal_terminals=terminals,
                     source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                     seconds=round(time.perf_counter()-START,3)),indent=2,sort_keys=True))
