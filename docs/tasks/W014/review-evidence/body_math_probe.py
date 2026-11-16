"""Independent exact open-atom and boundary-segment checks of body primitives."""
from __future__ import annotations
from fractions import Fraction
import json
import random
from layauto_v2.domain.channel_identity import RationalRect
from layauto_v2.derive.body_relations import edge_length, positive_area, enclosure

rng=random.Random(14014)
count=0
for _ in range(800):
 boxes=[]
 for _ in range(2):
  xs=sorted(rng.sample(range(-10,11),2))
  ys=sorted(rng.sample(range(-10,11),2))
  boxes.append(tuple(Fraction(n,20) for n in (xs[0],ys[0],xs[1],ys[1])))
 a,b=boxes
 A,B=RationalRect(*a),RationalRect(*b)
 xs=sorted(set((a[0],a[2],b[0],b[2])))
 ys=sorted(set((a[1],a[3],b[1],b[3])))
 def inside(r,x,y):return r[0]<x<r[2] and r[1]<y<r[3]
 overlap=any(inside(a,(x0+x1)/2,(y0+y1)/2) and inside(b,(x0+x1)/2,(y0+y1)/2)
             for x0,x1 in zip(xs,xs[1:]) for y0,y1 in zip(ys,ys[1:]))
 assert positive_area(A,B)==overlap
 boundaries=[]
 for r in (a,b):
  boundaries.append(((r[0],r[1],r[0],r[3]),(r[2],r[1],r[2],r[3]),
                     (r[0],r[1],r[2],r[1]),(r[0],r[3],r[2],r[3])))
 lengths=[]
 for i,first in enumerate(boundaries[0]):
  for j,second in enumerate(boundaries[1]):
   # Only opposing boundary sides can make an abutment edge.
   if (i,j) not in ((0,1),(1,0),(2,3),(3,2)):continue
   if i<2 and first[0]==second[0]:
    lo,hi=max(first[1],second[1]),min(first[3],second[3])
   elif i>=2 and first[1]==second[1]:
    lo,hi=max(first[0],second[0]),min(first[2],second[2])
   else:continue
   lengths.append(max(Fraction(0),hi-lo))
 assert edge_length(A,B)==sum(lengths,Fraction(0))
 margins=enclosure(A,B)
 assert min(margins)>=0 if all(a[0]<=x<=a[2] and a[1]<=y<=a[3] for x,y in ((b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3]))) else min(margins)<0
 count+=1
assert Fraction(901,20)!=Fraction(45)
print(json.dumps({'cases':count,'fractional_denominator':20,'seed':14014,'status':'passed'}))
