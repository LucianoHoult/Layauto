"""Independent lattice witnesses for W013 exact arithmetic and fragment kernel.

The kernel challenge uses authored targets and minimal seed handles. It is not
a captured receipt, public admission check, or benchmark; it does not load the
formal tests, fixture generator, or historical probes for its expected values.
"""
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace as NS

from layauto_v2.annotation.net_regions import fragment_targets, _boundary
from layauto_v2.domain.channel_identity import RationalRect as RR
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import GeometryRecordId, GeometryRef, Rect
from layauto_v2.domain.identifiers import CellId, NetId
from layauto_v2.domain.local_connectivity import ContactNode, LocalRef
from layauto_v2.domain.net_annotation import (
    AnnotationRef, AnnotationTargetId, TargetEvidence, TargetIntersection,
    area, canonical_cover, difference, intersections,
)
from layauto_v2.domain.regions import ExactRegion, RegionRef


def h(value):
    return sha256(str(value).encode()).hexdigest()


def lattice(boxes, offset=F(0), scale=F(1)):
    """Enumerate integer unit tiles using original exact bounds only."""
    result = set()
    for box in boxes:
        points = tuple((v - offset if axis in (0, 2) else v) / scale
                       for axis, v in enumerate(box.bounds))
        assert all(v.denominator == 1 for v in points)
        x0, y0, x1, y1 = map(int, points)
        result.update((x, y) for x in range(x0, x1) for y in range(y0, y1))
    return result


def main():
    rng = random.Random(13112026)
    checks = 0
    for case in range(256):
        offset, scale = F(rng.choice((-10**40, 0, 10**40))), F(1, rng.choice((3, 7, 20)))
        groups = []
        for _ in range(2):
            boxes = []
            for _ in range(rng.randrange(7)):
                x0, x1 = sorted(rng.sample(range(-4, 6), 2))
                y0, y1 = sorted(rng.sample(range(-4, 6), 2))
                boxes.append(RR(offset + x0*scale, y0*scale, offset + x1*scale, y1*scale))
            groups.append(tuple(boxes))
        a, b = groups
        ca, cb = lattice(a, offset, scale), lattice(b, offset, scale)
        for name, output, expected in (
            ('union', canonical_cover(a+b), ca | cb),
            ('intersection', intersections(a,b), ca & cb),
            ('difference', difference(a,b), ca - cb),
        ):
            assert lattice(output, offset, scale) == expected, (case, name)
            assert area(output) == len(expected)*scale*scale, (case, name)
            assert sum(len(lattice((box,),offset,scale)) for box in output) == len(expected), (case,name)
            assert canonical_cover(tuple(reversed(output))) == output
            checks += 1

    binding_ref = AnnotationRef('binding', h('binding'))
    contact_ref = LocalRef('operators',h('contact'))
    region_ref = RegionRef('operators',h('region'))
    unit_ref = GeometryRef('unit', h('unit'))
    component_ref = LocalRef('component',h('component'))
    source = SourceRef('review:authored-lattice-target',h('source'))
    # Connected ring with a hole. Two distinct record identities cover the same
    # physical coordinates, exposing target multiplicity without geometry union.
    pieces = (Rect(0,0,2,4), Rect(2,0,4,1), Rect(2,3,4,4), Rect(4,0,6,4))
    targets = []
    for index in range(2):
        record = GeometryRecordId(h(index))
        region = ExactRegion(record,'effective',(),unit_ref,region_ref,pieces)
        node = ContactNode('LI',region,contact_ref)
        targets.append(TargetEvidence(AnnotationTargetId(binding_ref,'LI',record,region.ref),node,
                                      component_ref,RR(F(0),F(0),F(6),F(4)),source,1))
    seeds = []
    matches = []
    cell = CellId('REVIEW')
    authored = [('A',(0,0,3,4)),('A',(1,0,4,4)),('B',(3,2,6,4)),('A',(0,0,3,4))]
    for index,(name,box) in enumerate(authored):
        seed = NS(ref=AnnotationRef('evidence',h(('seed',index))),net_id=NetId(cell,name))
        seeds.append(seed)
        rectangle = RR(*(F(v) for v in box))
        hits = tuple(TargetIntersection(t.ref,intersections((rectangle,),t.rectangles)) for t in targets
                     if intersections((rectangle,),t.rectangles))
        matches.append(NS(evidence_ref=seed.ref,intersections=hits))
    fragments = fragment_targets(tuple(seeds),tuple(targets),tuple(matches))
    target_cells = lattice(targets[0].rectangles)
    for target in targets:
        rows = tuple(row for row in fragments if row.target_ref == target.ref)
        assert sum(row.area_nm2 for row in rows) == len(target_cells) == 20
        for point in target_cells:
            expected_refs = {seeds[i].ref for i,(_,box) in enumerate(authored)
                             if box[0] <= point[0] < box[2] and box[1] <= point[1] < box[3]}
            expected_nets = {seeds[i].net_id for i,(_,box) in enumerate(authored) if seeds[i].ref in expected_refs}
            actual = [row for row in rows if point in lattice(row.rectangles)]
            assert len(actual)==1 and set(actual[0].evidence_refs)==expected_refs
            assert set(actual[0].net_ids)==expected_nets
            assert actual[0].status==('unknown' if not expected_nets else 'annotated' if len(expected_nets)==1 else 'conflict')
        assert sum(row.area_nm2 for row in rows if row.status=='conflict')==2
        assert sum(row.area_nm2 for row in rows if row.status=='unknown')==4
    assert sum(row.area_nm2 for row in fragments)==40
    assert _boundary(RR(F(0),F(0),F(1),F(1)),RR(F(1),F(0),F(2),F(1)))
    assert _boundary(RR(F(0),F(0),F(1),F(1)),RR(F(1),F(1),F(2),F(2)))
    assert intersections((RR(F(0),F(0),F(1),F(1)),),(RR(F(1),F(1),F(2),F(2)),))==()
    print(json.dumps({'status':'passed','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'python':sys.version,'seed':13112026,'lattice_operation_checks':checks,
        'fragment_target_cells_checked':2*len(target_cells),'fragment_multiset_area':40,
        'scope':['Fraction and huge offset exact sets','ring hole','overlapping same-net duplicates',
                 'different-net conflict','unknown gap','duplicate occupant identities','edge/point zero area'],
        'not_run':['captured authentication','full regression','performance measurement'],
        'module_hashes':{p:sha256(Path(p).read_bytes()).hexdigest() for p in
            ['layauto_v2/domain/net_annotation.py','layauto_v2/annotation/net_regions.py']}},indent=2))


if __name__=='__main__':
    main()
