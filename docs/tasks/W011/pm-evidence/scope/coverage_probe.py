from fractions import Fraction as F
from pathlib import Path
import hashlib,json,random,subprocess,time
from layauto_v2.annotation.channel_identity import rational_cover
from layauto_v2.domain.channel_identity import RationalRect
started=time.monotonic()
rng=random.Random(1109)
checks=0
for case in range(256):
    rectangles=[]
    for _ in range(rng.randrange(7)):
        x=sorted(rng.sample(range(-8,9),2)); y=sorted(rng.sample(range(-8,9),2))
        rectangles.append(RationalRect(F(x[0],3),F(y[0],2),F(x[1],3),F(y[1],2)))
    rectangles=tuple(rectangles)
    cover=rational_cover(rectangles)
    xs=sorted({x for r in (*rectangles,*cover) for x in (r.x0,r.x1)})
    ys=sorted({y for r in (*rectangles,*cover) for y in (r.y0,r.y1)})
    area=F(0)
    for xa,xb in zip(xs,xs[1:]):
        for ya,yb in zip(ys,ys[1:]):
            x,y=(xa+xb)/2,(ya+yb)/2
            before=any(r.x0<x<r.x1 and r.y0<y<r.y1 for r in rectangles)
            after=sum(r.x0<x<r.x1 and r.y0<y<r.y1 for r in cover)
            assert before == bool(after),(case,x,y)
            assert after<=1,(case,'overlapping cover')
            if before:area+=(xb-xa)*(yb-ya)
            checks+=1
    assert sum((r.area for r in cover),F(0))==area
    assert rational_cover(tuple(reversed(rectangles)))==cover
    assert rational_cover(cover)==cover
print(json.dumps({'status':'passed','cases':256,'open_atom_membership_checks':checks,'per_case':['membership-preserved','non-overlapping','exact-area','order-invariant','idempotent'],'elapsed_seconds':time.monotonic()-started,'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
