"""Independent premerge reviewer: finite unit-square sets and graph closure.

Only fixture copy/rebinding and GDS byte editing helpers are reused. No formal
contact/region/enclosure oracle or historical reviewer probe is imported.
Product functions occur exclusively on the actual-result side of assertions.
"""
from __future__ import annotations
import gc
import itertools
import json
import random
import sys
import tempfile
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'tests/contracts')]
from w005_cases import FIXTURE, apply_case
from w007_cases import ready_copy, query_only_rename
from w008_geometry_cases import edit_geometry
from w009_cases import special_input, rewrite_geometry
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry, build_local_connectivity
from layauto_v2.domain.geometry import Rect
from layauto_v2.state.local_connectivity import same_layer_contact, encloses_connector

# Closed integer boxes are represented by their occupied unit squares; their
# closure is implicit. Equal cells prove area contact, 4-neighbor cells prove an
# edge interval, diagonals alone prove only corner contact. No min/max overlap
# formula, slab scan, or product region canonicalizer supplies expected values.
def squares(boxes):
    return frozenset((x,y) for a,b,c,d in boxes for x in range(a,c) for y in range(b,d))
def contact(a,b):
    return bool(a & b) or any((x+dx,y+dy) in b for x,y in a for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))
def enclosure(boxes,target,margin):
    q=margin.denominator
    cover=squares(tuple(tuple(v*q for v in b) for b in boxes))
    p=margin.numerator
    a,b,c,d=target
    wanted=squares(((a*q-p,b*q-p,c*q+p,d*q+p),))
    return wanted <= cover

def components(cells):
    pending=set(cells); answer=[]
    while pending:
        seed=pending.pop(); group={seed}; frontier=[seed]
        while frontier:
            x,y=frontier.pop()
            for nxt in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if nxt in pending:
                    pending.remove(nxt); group.add(nxt); frontier.append(nxt)
        answer.append(frozenset(group))
    return answer

PAIRS={'CONTACT':('OD','LI'),'VIA0':('LI','M1'),'GCONTACT':('POLY','M1')}
NORMAL={
 ('OD','S',(20,20,58,70)),('OD','D',(62,20,100,70)),
 ('OD','S',(20,110,58,180)),('OD','D',(62,110,100,180)),
 ('POLY','effective',(58,10,62,190)),('LI','effective',(28,30,34,55)),
 ('LI','effective',(28,130,34,155)),('LI','effective',(84,30,90,165)),
 ('M1','effective',(0,48,45,58)),('M1','effective',(0,148,45,158)),
 ('M1','effective',(50,90,75,98)),('M1','effective',(80,90,110,98)),
 ('BODY_N','effective',(0,0,120,90)),('BODY_P','effective',(0,100,120,200))}

def check_complete(effective, actual, name):
    records=effective.value.base.layout.records
    cuts=squares(tuple(r.rect.bounds for r in records if r.layer=='CUT'))
    poly=squares(tuple(r.rect.bounds for r in records if r.layer=='POLY'))
    # Per source record, never merge two independently captured conductors.
    expected=[]
    for r in records:
        cells=squares((r.rect.bounds,))
        if r.layer=='OD':
            channel=cells & poly
            assert channel
            lo=min(x for x,y in channel); hi=max(x for x,y in channel)
            expected += [(r.id,r.layer,'S',frozenset((x,y) for x,y in cells if x<lo)),
                         (r.id,r.layer,'D',frozenset((x,y) for x,y in cells if x>hi))]
        elif r.layer=='LI':
            expected.extend((r.id,r.layer,'effective',part) for part in components(cells-cuts))
        elif r.layer in ('POLY','M1','BODY_N','BODY_P'):
            expected.append((r.id,r.layer,'effective',cells))
    expected_edges=[]; expected_audits=[]; ambiguity=[]
    for i,a in enumerate(expected):
        for j,b in enumerate(expected[:i]):
            if a[1]==b[1] and contact(a[3],b[3]): expected_edges.append(('same_layer',None,frozenset((i,j))))
    for r in records:
        if r.layer not in PAIRS: continue
        ends=[]
        for side,layer in enumerate(PAIRS[r.layer]):
            hit=[i for i,n in enumerate(expected) if n[1]==layer and bool(n[3]&squares((r.rect.bounds,)))]
            if len(hit)!=1: ambiguity.append((r.id,side,len(hit))); continue
            i=hit[0]; ends.append(i)
            # Exact Minkowski square expansion at integer margin 1 for these
            # captures; all wanted unit cells must belong to the full region.
            assert effective.value.base.layout.units.canonical_tick_nm == 1
            a,b,c,d=r.rect.bounds
            status='pass' if squares(((a-1,b-1,c+1,d+1),)) <= expected[i][3] else 'violation'
            expected_audits.append((r.id,i,layer,Fraction(1),status))
        if len(ends)==2: expected_edges.append(('connector',r.id,frozenset(ends)))
    if ambiguity:
        assert actual.status=='error' and actual.value is None
        assert len(actual.issues)==1 and actual.issues[0].code=='AmbiguousConnectorEndpoint'
        assert actual.issues[0].source.uri=='source.gds'
        assert actual.input is effective and actual.completed==effective.completed
        return {'case':name,'expected_ambiguous_sides':len(ambiguity),'observed_code':actual.issues[0].code}
    assert actual.status=='success',actual.issues
    draft=actual.value
    actual_signatures=[(n.region.owner_id,n.layer,n.region.role,squares(tuple(r.bounds for r in n.region.rectangles))) for n in draft.nodes]
    assert Counter(actual_signatures)==Counter(expected),(name,'complete node geometry mismatch')
    refs={n.ref:expected.index(sig) for n,sig in zip(draft.nodes,actual_signatures)}
    assert Counter((e.kind,e.connector_id,frozenset(refs[r] for r in e.endpoints)) for e in draft.edges)==Counter(expected_edges)
    assert Counter((a.connector_id,refs[a.node_ref],a.layer,a.margin_ticks,a.status) for a in draft.audits)==Counter(expected_audits)
    # Independent transitive-closure graph oracle (product uses BFS).
    reach={(i,i) for i in range(len(expected))}
    for _,_,ends in expected_edges:
        a,b=ends; reach.update(((a,b),(b,a)))
    for k in range(len(expected)):
        reach |= {(i,j) for i in range(len(expected)) for j in range(len(expected)) if (i,k) in reach and (k,j) in reach}
    groups={frozenset(j for j in range(len(expected)) if (i,j) in reach) for i in range(len(expected))}
    assert {frozenset(refs[r] for r in c.members) for c in draft.components}==groups
    if name=='normal':
        assert {(n.layer,n.region.role,n.region.rectangles[0].bounds) for n in draft.nodes}==NORMAL
        assert all(len(n.region.rectangles)==1 for n in draft.nodes)
        assert (len(draft.nodes),len(draft.edges),len(draft.components),len(draft.audits))==(14,8,6,16)
        assert all(a.status=='pass' for a in draft.audits)
    if name=='cut_islands':
        assert (len(draft.nodes),len(draft.edges),len(draft.components))==(3,0,3)
        assert {frozenset(n[3]) for n in expected}=={squares((b,)) for b in ((50,20,60,24),(130,20,139,24),(141,20,150,24))}
    if name=='via_enclosure':
        via=next(r for r in records if r.layer=='VIA0' and r.rect.bounds==(33,50,37,54))
        assert sum(e.connector_id==via.id for e in draft.edges)==1
        assert {(a.layer,a.status) for a in draft.audits if a.connector_id==via.id}=={('LI','violation'),('M1','pass')}
    if name=='cut_boundary':
        axes=next(a for a in draft.effective.base.partition.layers if a.layer=='LI')
        assert 207 not in axes.xs and 213 not in axes.xs and 205 not in axes.ys
    return {'case':name,'nodes':len(draft.nodes),'edges':len(draft.edges),'components':len(draft.components),'audits':len(draft.audits),'enclosure':draft.local_enclosure_status,'semantic_digest':draft.semantic_digest}

def main():
    started=time.monotonic(); rng=random.Random(20261106); counts={'contact':0,'enclosure':0}
    for trial in range(1600):
        groups=[]
        for _ in range(2):
            boxes=[]
            for _ in range(rng.randrange(1,5)):
                x,y=rng.randrange(-4,4),rng.randrange(-4,4)
                boxes.append((x,y,x+rng.randrange(1,5),y+rng.randrange(1,5)))
            groups.append(tuple(boxes))
        want=contact(*(squares(g) for g in groups))
        # Huge offsets stress exact integer arithmetic without huge raster cost.
        offset=(2**103,-2**111) if trial%4==0 else (0,0)
        shifted=[tuple(Rect(a+offset[0],b+offset[1],c+offset[0],d+offset[1]) for a,b,c,d in g) for g in groups]
        assert same_layer_contact(*shifted)==want
        counts['contact']+=1
        target=groups[1][0]; margin=Fraction(rng.randrange(5),rng.choice((1,2,3)))
        want=enclosure(groups[0],target,margin)
        assert encloses_connector(shifted[0],shifted[1][0],margin)==want
        counts['enclosure']+=1
    print(json.dumps({'mathematical_unit_square_oracles':counts}),flush=True)
    cases=[
      ('normal',lambda p:None),
      ('cut_islands',special_input),
      ('via_enclosure',lambda p:apply_case(p,'via_enclosure')),
      ('duplicate_connector',lambda p:rewrite_geometry(p,append=[('VIA0',(29,50,33,54))])),
      ('duplicate_conductor',lambda p:rewrite_geometry(p,append=[('LI',(28,30,34,55))])),
      ('connected_candidates',lambda p:rewrite_geometry(p,append=[('LI',(30,35,36,60))])),
      ('enclosure_cannot_disambiguate',lambda p:rewrite_geometry(p,append=[('LI',(32,41,35,45))])),
      ('edge_only',lambda p:rewrite_geometry(p,replace_layers={'VIA0':((34,50,38,54),)})),
      ('corner_only',lambda p:rewrite_geometry(p,replace_layers={'VIA0':((34,55,38,59),)})),
      ('missing_side',lambda p:rewrite_geometry(p,replace_layers={'VIA0':((110,50,114,54),)})),
      ('cut_boundary',lambda p:rewrite_geometry(p,append=[('LI',(200,200,220,210)),('CUT',(207,199,213,205)),('LI',(220,203,225,207))])),
      ('hole_and_cross_piece',lambda p:rewrite_geometry(p,append=[('LI',(200,200,220,220)),('CUT',(207,207,213,213)),('M1',(198,198,222,222)),('VIA0',(202,204,218,206)),('VIA0',(203,203,207,207))])),
      ('negative_reordered',lambda p:edit_geometry(p,translate=(-1000,-2000),vertices=True,reorder=True)),
      ('reordered_renamed',lambda p:(rewrite_geometry(p,reverse=True),query_only_rename(p))),
    ]
    results=[]
    with tempfile.TemporaryDirectory(prefix='w010-independent-geometry-',dir='/tmp') as tmp:
        for name,edit in cases:
            path=ready_copy(Path(tmp)/name); edit(path)
            parsed=read_inputs(path/'site_config.yaml'); assert parsed.status=='success',parsed.issues
            geometry=build_geometry(geometry_from_parse_result(parsed)); assert geometry.status=='success',geometry.issues
            effective=build_effective_geometry(geometry); assert effective.status=='success',effective.issues
            actual=build_local_connectivity(effective)
            result=check_complete(effective,actual,name); results.append(result)
            print(json.dumps(result),flush=True)
            del actual,effective,geometry,parsed; gc.collect()
    assert results[0]['semantic_digest']==results[-1]['semantic_digest']
    summary={'status':'passed','head':'c4909ab679d0c0806200fcb132db8a5de1ad3e75','python':sys.version,'mathematical_comparisons':counts,'cases':results,'elapsed_seconds':time.monotonic()-started}
    (Path(__file__).parent/'geometry-result.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'status':'passed','elapsed_seconds':summary['elapsed_seconds']}),flush=True)

if __name__=='__main__':main()
