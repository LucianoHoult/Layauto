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

REPO = Path('/workspace/work/w011-review-geometry/fixed975')
sys.path[:0] = [str(REPO), str(REPO / 'tests/contracts')]
from w005_cases import FIXTURE, apply_case, copy_input, without_cache
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

from types import SimpleNamespace
from w007_cases import normal as semantic_normal
from w010_cases import build_effective
from w011_cases import change_seeds
from layauto_v2.domain.channel_identity import ChannelRef
say('fixed_identity',commit='975852d3b9ea946aca24f727071cf26a7dce8bc7',python=sys.version,
    product={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REPO/'layauto_v2').rglob('*.py'))})
effective=build_effective(FIXTURE).value
layout=effective.base.layout
channels=tuple(row.regions[0] for row in effective.records if row.operation=='terminal')
binding=ChannelRef('binding','1'*64)
d=SimpleNamespace(binding_ref=binding)
source_locations=tuple(layout.record(c.owner_id).source for c in channels)
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

seed_cases=[('partial',[(58,20,F(121,2),70)],F(5,8),None),
            ('union',[(58,20,62,50),(58,40,62,70)],F(1),None),
            ('ambiguous',[(58,20,62,180)],None,'AmbiguousSeedChannel'),
            ('edge',[(58,70,62,80)],None,'MissingSeedChannel'),
            ('conflict',[(58,20,62,70),(58,110,62,180)],None,'ConflictingDeviceSeeds'),
            ('missing',[],None,'MissingDeviceSeed')]
for name,boxes,want,issue in seed_cases:
    with tempfile.TemporaryDirectory(prefix='fixed-seed-'+name+'-',dir='/workspace/work/w011-review-geometry') as tmp:
        root=ready_copy(Path(tmp))
        change_seeds(root,'Q17',boxes)
        semantic=semantic_normal(root).value
        identities={i.device_id:i for i in semantic.device_identities}
        seeds=tuple(ChannelSeed(s.semantic_id,s.query_key,s.record,identities[s.semantic_id].provenance) for s in semantic.device_seeds)
        selected=next(c for c in semantic.source.cells if c.id==semantic.source.selected_cell)
        locations,associations,issues=locate_channels(selected.devices,channels,seeds,1,binding,source_locations)
        n=tuple(a for a in associations if a.device_id.name=='MN0')
        if issue:
            assert not n and issue in {x.code for x in issues}
            relevant=next(x for x in issues if x.code==issue)
            assert relevant.source.sha256 and relevant.source.uri
            if name in ('edge','ambiguous','conflict'):
                assert relevant.source.uri=='query/requests.json'
        else:
            assert len(n)==1 and n[0].coverage_fraction==want and not issues
        assert len(locations)==len(seeds)
        say('fixed_seed_'+name,result='PASS',coverage=str(want),issues=[x.code for x in issues],
            sources=[{'uri':x.source.uri,'field':x.source.field,'sha256':x.source.sha256} for x in issues])
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
say('complete',result='PASS',commit='975852d3b9ea946aca24f727071cf26a7dce8bc7')
