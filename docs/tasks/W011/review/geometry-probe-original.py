"""Independent review probes; no runtime or accepted fixture edits."""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import tempfile
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from time import perf_counter

REPO = Path('/workspace/Layauto')
sys.path[:0] = [str(REPO), str(REPO / 'tests/contracts')]
from w005_cases import FIXTURE, apply_case
from w007_cases import ready_copy, mutable
from w010_cases import build_local, append_records
from layauto_v2.normalization import build_channel_identity
from layauto_v2.annotation.channel_identity import rational_cover, locate_channels
from layauto_v2.derive.fin_count import evaluate_fins
from layauto_v2.domain.channel_identity import RationalRect, ChannelSeed
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.geometry import Rect

def say(name, **value):
    print(json.dumps({'probe': name, **value}, sort_keys=True), flush=True)

say('identity', head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
    python=sys.version, executable=sys.executable,
    product={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((REPO/'layauto_v2').rglob('*.py'))})

def build(root):
    start = perf_counter()
    local = build_local(root)
    result = build_channel_identity(local)
    assert result.value is not None
    draft = result.value
    assert draft.local is local.value
    assert result.body_evidence == local.body_evidence
    assert result.completed == local.completed
    by_channel = {m.channel_ref: m for m in draft.measurements}
    counts = {a.device_id.name: by_channel[a.channel_ref].count for a in draft.associations}
    say(str(root.name), status=result.status, counts=counts,
        issues=[x.code for x in result.issues], differences=[(x.device_id.name, x.axis, str(x.measured),str(x.declared.exact)) for x in draft.differences],
        seconds=round(perf_counter()-start, 4))
    return result, counts

normal, counts = build(FIXTURE)
assert counts == {'MN0': 5, 'MP0': 7}
d = normal.value
layout = d.local.effective.base.layout
channels = tuple(r.regions[0] for r in d.local.effective.records if r.operation == 'terminal')
by_channel = {m.channel_ref: m for m in d.measurements}
hand_y = {'MN0': [24,34,44,54,64], 'MP0': [114,124,134,144,154,164,174]}
for a in d.associations:
    m = by_channel[a.channel_ref]
    assert len(m.evaluations) == 18
    assert sorted(layout.record(x.fin_id).rect.y0 for x in m.crossings) == hand_y[a.device_id.name]
    assert m.length_nm == F(4)
    assert all(x.width_nm == F(2) for x in m.crossings)
    assert a.coverage_fraction == 1
assert len(d.topology)==2 and d.topology[0].gate_nodes == d.topology[1].gate_nodes
assert len({x for row in d.topology for x in (row.source_node,row.drain_node)}) == 4
assert not d.differences and d.comparison_status == 'equal'
say('normal_full_sets_topology', result='PASS', all_fins=18, qualified=12)

for name in ['extraction_mismatch', 'via_enclosure', 'duplicate', 'partial', 'touch']:
    with tempfile.TemporaryDirectory(prefix=name+'-', dir='/workspace/work/w011-review-geometry') as tmp:
        root = ready_copy(Path(tmp))
        if name in ('extraction_mismatch', 'via_enclosure'):
            apply_case(root,name)
        else:
            box = {'duplicate':(10,24,110,26), 'partial':(59,30,61,32), 'touch':(62,30,65,32)}[name]
            append_records(root,[('FIN',box)])
        result, actual = build(root)
        draft = result.value
        if name=='extraction_mismatch':
            assert actual == {'MN0':4, 'MP0':7}
            assert [(x.device_id.name,x.axis,x.measured,x.declared.exact) for x in draft.differences] == [('MN0','fins_per_finger',F(4),F(5))]
        elif name=='via_enclosure':
            assert actual == {'MN0':5, 'MP0':7}
            assert draft.local.audits == result.input.value.audits
            assert any(a.status=='violation' for a in draft.local.audits)
        elif name in ('duplicate','partial'):
            assert actual == {'MN0':None,'MP0':7}
            assert result.status == 'error'
            assert len(draft.measurements[0].evaluations)==19
        else:
            assert actual == {'MN0':5,'MP0':7} and result.status=='success'
        say(name, result='PASS')

# Exact rational union via exhaustive open-cell occupancy, not x-slab merging.
rng=random.Random(11032026)
for case in range(300):
    boxes=[]
    for _ in range(rng.randrange(0,9)):
        x0,x1=sorted(rng.sample(range(-12,13),2)); y0,y1=sorted(rng.sample(range(-12,13),2))
        boxes.append(RationalRect(F(x0,6),F(y0,6),F(x1,6),F(y1,6)))
    covered=rational_cover(tuple(boxes))
    # 1/6-spaced cells exactly tessellate every permitted input and output.
    def cells(rects):
        return {(i,j) for i in range(-12,12) for j in range(-12,12)
                if any(r.x0 < F(2*i+1,12) < r.x1 and r.y0 < F(2*j+1,12) < r.y1 for r in rects)}
    assert cells(boxes)==cells(covered)
    assert sum((r.area for r in covered),F(0)) == F(len(cells(boxes)),36)
    assert all(a.intersection(b) is None for i,a in enumerate(covered) for b in covered[i+1:])
    assert rational_cover(tuple(reversed(boxes))+tuple(boxes))==covered
say('fraction_union_atom_oracle', result='PASS', random_cases=300, denominator=6)

selected=next(c for c in d.source.cells if c.id==d.source.selected_cell)
source_locations=tuple(layout.record(c.owner_id).source for c in channels)
nseed=next(s for s in d.seeds if s.device_id.name=='MN0')
pseed=next(s for s in d.seeds if s.device_id.name=='MP0')
def seed(box, ordinal):
    row=mutable(nseed.record)
    x0,y0,x1,y1=map(F,box)
    def rat(v): return {'numerator':v.numerator,'denominator':v.denominator}
    row['record_id']='review-seed-'+str(ordinal)
    row['bbox_nm']=dict(zip(('x_min','y_min','x_max','y_max'),map(rat,(x0,y0,x1,y1))))
    row['vertices_nm']=[{'x':rat(x),'y':rat(y)} for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
    return ChannelSeed(nseed.device_id,nseed.query_key,FrozenMap(row),nseed.identity_provenance)
seed_cases=[('partial',[(58,20,F(121,2),70)],F(5,8),None),
            ('union',[(58,20,62,50),(58,40,62,70)],F(1),None),
            ('ambiguous',[(58,20,62,180)],None,'AmbiguousSeedChannel'),
            ('edge',[(58,70,62,80)],None,'MissingSeedChannel'),
            ('conflict',[(58,20,62,70),(58,110,62,180)],None,'ConflictingDeviceSeeds')]
for name,boxes,want,issue in seed_cases:
    seeds=tuple(seed(b,i) for i,b in enumerate(boxes))+(pseed,)
    locations,associations,issues=locate_channels(selected.devices,channels,seeds,1,d.binding_ref,source_locations)
    n=tuple(a for a in associations if a.device_id.name=='MN0')
    if issue:
        assert not n and issue in {x.code for x in issues}
    else:
        assert len(n)==1 and n[0].coverage_fraction==want and not issues
    assert len(locations)==len(seeds)
    say('seed_'+name,result='PASS', coverage=str(want), issues=[x.code for x in issues])

# Per-FIN qualification against integer open-cell sets. Neutral algorithm probe,
# separately from the genuine captured-input builds above.
base_fin=next(r for r in layout.records if r.layer=='FIN')
actives=tuple(r for r in layout.records if r.layer=='OD')
for case in range(250):
    x0,x1=sorted(rng.sample(range(54,67),2)); y0,y1=sorted(rng.sample(range(16,76),2))
    rect=Rect(x0,y0,x1,y1)
    xy=((x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0))
    preserve=mutable(base_fin.preservation); preserve['xy']=xy; preserve['bbox']=rect.bounds
    fin=replace(base_fin,rect=rect,raw_xy=xy,preservation=FrozenMap(preserve))
    measurements,relations,issues=evaluate_fins(channels,actives+(fin,),1,d.binding_ref)
    for c,m in zip(channels,measurements):
        box=c.rectangles[0]; active=layout.record(c.owner_id).rect
        fx=set(range(x0,x1)); fy=set(range(y0,y1)); cx=set(range(box.x0,box.x1)); cy=set(range(box.y0,box.y1))
        area=(fx&cx) and (fy&cy)
        closedx=set(range(x0,x1+1))&set(range(box.x0,box.x1+1))
        closedy=set(range(y0,y1+1))&set(range(box.y0,box.y1+1))
        expected=('qualified' if cx<=fx and fy<=set(range(active.y0,active.y1)) else 'partial') if area else ('touch' if closedx and closedy else 'outside')
        assert m.evaluations[0].status==expected,(rect.bounds,box.bounds,expected,m.evaluations[0].status)
        assert m.count == (None if expected=='partial' else int(expected=='qualified'))
say('fin_integer_atom_oracle',result='PASS',random_cases=250,channel_decisions=500)
say('complete', result='PASS',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip())
