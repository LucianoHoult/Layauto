from __future__ import annotations
import hashlib, json, random, time
from pathlib import Path
from collections import deque
from layauto_v2.domain.geometry import Rect
from layauto_v2.domain.regions import canonical_cover
from layauto_v2.state.regions import slab_difference, _groups

START=time.perf_counter()
rng=random.Random(9072026)
stats={'cases':0,'membership_checks':0,'group_cases':0,'canonical_split_cases':0}

def inside(r,x,y): return r.x0*2 <= x < r.x1*2 and r.y0*2 <= y < r.y1*2

def components(cells):
    cells=set(cells); out=[]
    while cells:
        seed=min(cells); cells.remove(seed); component={seed}; pending=[seed]
        while pending:
            x,y=pending.pop()
            for neighbor in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if neighbor in cells:
                    cells.remove(neighbor); component.add(neighbor); pending.append(neighbor)
        out.append(component)
    return sorted(out,key=lambda a:sorted(a))

def check(target,cuts,grid=True):
    out=slab_difference(target, cuts)
    assert out==slab_difference(target,list(reversed(cuts))+list(cuts)), ('permutation',target,cuts,out)
    assert out==canonical_cover(out),('noncanonical',target,cuts,out)
    assert all(a.intersection(b) is None for i,a in enumerate(out) for b in out[i+1:])
    xs={target.x0,target.x1}; ys={target.y0,target.y1}
    for r in cuts+list(out): xs.update((r.x0,r.x1));ys.update((r.y0,r.y1))
    xs=sorted(xs);ys=sorted(ys)
    # Double all integer boundaries/midpoints so arithmetic remains integer.
    probes_x=sorted({2*x for x in xs}|{a+b for a,b in zip(xs,xs[1:])})
    probes_y=sorted({2*y for y in ys}|{a+b for a,b in zip(ys,ys[1:])})
    for x in probes_x:
        for y in probes_y:
            expected=inside(target,x,y) and not any(inside(c,x,y) for c in cuts)
            actual=sum(inside(r,x,y) for r in out)
            assert actual==int(expected),('membership',target,cuts,out,x,y,expected,actual)
            stats['membership_checks']+=1
    if grid:
        cells={(x,y) for x in range(target.x0,target.x1) for y in range(target.y0,target.y1)
               if not any(inside(c,2*x+1,2*y+1) for c in cuts)}
        expected=components(cells)
        actual=[]
        for group in _groups(out):
            actual.append({(x,y) for x in range(target.x0,target.x1) for y in range(target.y0,target.y1)
                           if any(inside(r,2*x+1,2*y+1) for r in group)})
        assert sorted(actual,key=lambda a:sorted(a))==expected, ('groups',target,cuts,out,actual,expected)
        stats['group_cases']+=1
    split=[]
    for r in out:
        if r.x1-r.x0>1:
            x=(r.x0+r.x1)//2
            split.extend((Rect(r.x0,r.y0,x,r.y1),Rect(x,r.y0,r.x1,r.y1)))
        else:split.append(r)
    assert canonical_cover(tuple(split+split))==out, ('redundant decomposition',target,cuts,out,split)
    stats['canonical_split_cases']+=1;stats['cases']+=1

hand=[(Rect(0,0,2,2),[Rect(0,1,1,2),Rect(1,0,2,1)]),
      (Rect(-4,-3,8,9),[Rect(-2,-1,6,7)]),
      (Rect(0,0,10,10),[Rect(3,0,7,10),Rect(0,3,10,7)]),
      (Rect(-5,-5,5,5),[Rect(-10,-10,10,10)]),
      (Rect(0,0,10,10),[Rect(10,2,12,7),Rect(-2,-2,0,0)])]
for t,c in hand:check(t,c)
for n in range(1500):
    x0,y0=rng.randint(-6,0),rng.randint(-6,0)
    t=Rect(x0,y0,rng.randint(1,8),rng.randint(1,8))
    cuts=[]
    for _ in range(rng.randrange(12)):
        a,b=sorted(rng.sample(range(-9,12),2));c,d=sorted(rng.sample(range(-9,12),2))
        cuts.append(Rect(a,c,b,d))
    check(t,cuts)
for offset in (-2**80,2**80):
    for t,c in hand:
        move=lambda r:Rect(r.x0+offset,r.y0-offset,r.x1+offset,r.y1-offset)
        check(move(t),[move(r) for r in c],grid=False)

source_paths=['layauto_v2/domain/regions.py','layauto_v2/state/regions.py','layauto_v2/normalization/effective.py']
manifest={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_paths}
print(json.dumps({'status':'passed','seed':9072026,**stats,'seconds':round(time.perf_counter()-START,3),'source_sha256':manifest},sort_keys=True,indent=2))
