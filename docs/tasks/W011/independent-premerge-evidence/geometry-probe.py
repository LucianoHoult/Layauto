"""Independent premerge geometry witnesses. No formal-test helper or golden generator.

Actual normal input is acquired once through W005, W008 and W009. Generated
records below are neutral mathematical witnesses, not claimed captured inputs.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import resource
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path

from layauto_v2.annotation.channel_identity import locate_channels, rational_cover
from layauto_v2.derive.fin_count import evaluate_fins
from layauto_v2.domain.channel_identity import ChannelRef, ChannelSeed, RationalRect
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.geometry import Rect, record_identity
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (build_effective_geometry, build_geometry,
    geometry_from_parse_result, normalize)

started = time.monotonic()
root = Path.cwd()
fixture = root / 'tests/fixtures/w003_m1'
receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'scope': 'W005/W008/W009 actual normal capture; neutral FIN and rational-union witnesses'}
parsed = read_inputs(fixture / 'site_config.yaml')
assert parsed.status == 'success'
inp = geometry_from_parse_result(parsed)
effective = build_effective_geometry(build_geometry(inp))
assert effective.status == 'success'
layout = effective.value.base.layout
channels = tuple(row.regions[0] for row in effective.value.records if row.operation == 'terminal')
binding = ChannelRef('binding', hashlib.sha256(b'independent mathematical witnesses').hexdigest())
measurements, relations, issues = evaluate_fins(channels, layout.records, 1, binding)
assert len(layout.records) == 40 and len([r for r in layout.records if r.layer == 'FIN']) == 18
assert not issues and not relations
expected = {(58, 20, 62, 70): ((24, 26), (34, 36), (44, 46), (54, 56), (64, 66)),
            (58, 110, 62, 180): tuple((y, y + 2) for y in (114, 124, 134, 144, 154, 164, 174))}
normal = []
for channel, m in zip(channels, measurements):
    q = [e for e in m.evaluations if e.status == 'qualified']
    answer = expected[channel.rectangles[0].bounds]
    assert {e.crossing.bounds for e in q} == {(58, lo, 62, hi) for lo, hi in answer}
    assert m.count == len(answer) and m.length_nm == 4
    assert len(m.evaluations) == 18 and {e.fin_id for e in m.evaluations} == {r.id for r in layout.records if r.layer == 'FIN'}
    assert all(e.source == layout.record(e.fin_id).source and e.width_nm == 2 for e in q)
    normal.append({'channel': channel.rectangles[0].bounds, 'count': m.count,
                   'crossings': sorted(e.crossing.bounds for e in q)})

semantic = normalize(inp.semantic_input)
assert semantic.status == 'success'
identities = {i.device_id: i for i in semantic.value.device_identities}
seeds = tuple(ChannelSeed(s.semantic_id, s.query_key, s.record, identities[s.semantic_id].provenance)
              for s in semantic.value.device_seeds)
selected = next(c for c in semantic.value.source.cells if c.id == semantic.value.source.selected_cell)
locations, associations, identity_issues = locate_channels(selected.devices, channels, seeds, 1, binding,
    tuple(layout.record(c.owner_id).source for c in channels))
assert not identity_issues and len(associations) == 2
assert all(a.coverage_fraction == 1 for a in associations)
assert all(len(loc.intersections) == 1 for loc in locations)

def exact(value):
    f = F(value)
    return FrozenMap({'numerator':str(f.numerator),'denominator':str(f.denominator)})

def seed_variant(seed, bounds, suffix=''):
    """Self-consistent neutral operand variant, deliberately not capture-authentic."""
    x0,y0,x1,y1 = map(F,bounds)
    vertices = ((x0,y0),(x0,y1),(x1,y1),(x1,y0))
    operands = seed.record['field_sources']['vertices_nm']['sources'][1:-1]
    updates = {(loc['path'],loc['line_1based'],loc['token_0based']):str(int(value*20))
               for loc,value in zip(operands,(y0,x0,y1,x0,y1,x1,y0,x1))}
    oldid = seed.record['record_id']
    def update(value):
        if type(value) is tuple: return tuple(update(v) for v in value)
        if type(value) is FrozenMap:
            row = {k:update(v) for k,v in value.items()}
            key = (row.get('path'),row.get('line_1based'),row.get('token_0based'))
            if key in updates: row['lexeme'] = updates[key]
            if row.get('lexeme') == oldid: row['lexeme'] = oldid+suffix
            return FrozenMap(row)
        return value
    row = dict(update(seed.record))
    row.update(record_id=oldid+suffix,
               bbox_nm=FrozenMap(dict(zip(('x_min','y_min','x_max','y_max'),map(exact,(x0,y0,x1,y1))))),
               vertices_nm=tuple(FrozenMap({'x':exact(x),'y':exact(y)}) for x,y in vertices))
    return replace(seed,record=FrozenMap(row))

nseed = next(s for s in seeds if s.device_id.name == 'MN0')
pseed = next(s for s in seeds if s.device_id.name == 'MP0')
sources = tuple(layout.record(c.owner_id).source for c in channels)
identity_cases = []
cases = [
    ('partial', (seed_variant(nseed,(58,20,62,40)),pseed), F(2,5), ()),
    ('fractional', (seed_variant(nseed,(58,20,F(121,2),70)),pseed), F(5,8), ()),
    ('overlap_union',(seed_variant(nseed,(58,20,62,50)),seed_variant(nseed,(58,40,62,70),'_second'),pseed),F(1),()),
    ('missing',(pseed,),None,('MissingDeviceSeed','UnassociatedChannel')),
    ('touch_only',(seed_variant(nseed,(58,70,62,80)),pseed),None,('MissingSeedChannel','UnassociatedChannel')),
    ('ambiguous',(seed_variant(nseed,(58,20,62,180)),pseed),None,('AmbiguousSeedChannel','UnassociatedChannel')),
    ('identity_conflict',(nseed,seed_variant(pseed,(58,20,62,70))),None,('ConflictingChannelIdentities','UnassociatedChannel')),
    ('split_identity',(nseed,seed_variant(nseed,(58,110,62,180),'_second'),pseed),None,('ConflictingDeviceSeeds','UnassociatedChannel')),
]
for name, variant, coverage, codes in cases:
    locs, assoc, probs = locate_channels(selected.devices,channels,variant,1,binding,sources)
    assert {p.code for p in probs} == set(codes), (name,probs)
    assert len(locs) == len(variant)
    if coverage is not None:
        a = next(a for a in assoc if a.device_id.name == 'MN0')
        assert a.coverage_fraction == coverage and a.full_coverage == (coverage==1)
    else:
        assert all(a.device_id.name != 'MN0' for a in assoc)
        assert all(p.source is not None for p in probs)
    if name == 'ambiguous': assert any(len(l.intersections)==2 for l in locs)
    identity_cases.append({'case':name,'source_devices':2,'channel_count':2,
        'seed_count':len(variant),'candidate_counts':sorted(len(l.intersections) for l in locs),
        'coverage':None if coverage is None else str(coverage),'issues':sorted(p.code for p in probs)})

template = next(r for r in layout.records if r.layer == 'FIN')
def record(box, index):
    source = SourceRef('independent://neutral-generated-fin', 'f' * 64, byte_offset=index * 100, record_index=index)
    x0, y0, x1, y1 = box
    xy = ((x0,y0), (x1,y0), (x1,y1), (x0,y1), (x0,y0))
    row = dict(template.preservation)
    row.update(xy=xy, bbox=box, byte_offset=source.byte_offset, record_index=index,
               xy_byte_offset=source.byte_offset + 20, xy_record_index=index, byte_length=60)
    return replace(template, id=record_identity(source, template.top), source=source,
                   raw_xy=xy, rect=Rect(*box), preservation=FrozenMap(row))

def open_cells(box):
    x0, y0, x1, y1 = box
    return {(x,y) for x in range(x0,x1) for y in range(y0,y1)}

# Finite integer unit cells independently determine positive area, complete
# channel-X coverage, and active-Y containment. This oracle does not call any
# product intersection/comparison operation.
channel = channels[0]
active = layout.record(channel.owner_id)
channel_cells = open_cells(channel.rectangles[0].bounds)
channel_x = {x for x,_ in channel_cells}
active_y = set(range(active.rect.y0,active.rect.y1))
fin_checks = 0
statuses = {s:0 for s in ('outside','touch','partial','qualified')}
rng = random.Random(20261110)
boxes = [(x0,y0,x1,y1) for x0,x1 in itertools.combinations((57,58,59,61,62,63),2)
         for y0,y1 in itertools.combinations((19,20,21,69,70,71),2)]
boxes += [(rng.randrange(45,65), rng.randrange(10,75), rng.randrange(66,80),rng.randrange(76,85)) for _ in range(100)]
for index, box in enumerate(boxes, 1):
    fin = record(box, index)
    got, _, _ = evaluate_fins((channel,), (active, fin), 1, binding)
    cells = open_cells(box)
    if cells & channel_cells:
        expected_status = ('qualified' if channel_x <= {x for x,_ in cells}
                           and {y for _,y in cells} <= active_y else 'partial')
    else:
        # Independent closed endpoint Cartesian witness distinguishes touch.
        closed_fin = {(x,y) for x in range(box[0],box[2]+1) for y in range(box[1],box[3]+1)}
        b = channel.rectangles[0].bounds
        closed_channel = {(x,y) for x in range(b[0],b[2]+1) for y in range(b[1],b[3]+1)}
        expected_status = 'touch' if closed_fin & closed_channel else 'outside'
    assert got[0].evaluations[0].status == expected_status, (box, got[0], expected_status)
    assert got[0].count == (None if expected_status == 'partial' else int(expected_status == 'qualified'))
    statuses[expected_status] += 1
    fin_checks += 1

# Long FIN at two distinct channel X ranges; same-Y disjoint-X remains outside.
second_active = replace(active, id=record_identity(replace(active.source, byte_offset=99900, record_index=999), active.top),
    source=replace(active.source, byte_offset=99900, record_index=999),
    preservation=FrozenMap(dict(active.preservation, byte_offset=99900, record_index=999)))
# The channel's region can independently use another owner with the same actual
# active rectangle: neutral qualification cares about active Y, not owner X.
second = replace(channel, owner_id=second_active.id, rectangles=(Rect(80,20,84,70),))
long_fin = record((58,24,84,26), 900)
rows, _, _ = evaluate_fins((channel,second),(active,second_active,long_fin),1,binding)
assert [r.count for r in rows] == [1,1]
rows, _, _ = evaluate_fins((channel,), (active,record((80,24,84,26),901)),1,binding)
assert rows[0].count == 0 and rows[0].evaluations[0].status == 'outside'

# Duplicate and overlap records are retained, never guessed to represent one/two
# physical FINs. Off-channel duplicates cannot poison otherwise known geometry.
relation_cases = []
for boxes2, expected_relation, unknown in [
    (((10,24,110,26),(10,24,110,26)), 'duplicate', True),
    (((10,24,110,26),(10,25,110,27)), 'overlap', True),
    (((10,194,110,196),(10,194,110,196)), 'duplicate', False),
]:
    rows, rels, probs = evaluate_fins((channel,), (active,record(boxes2[0],950),record(boxes2[1],951)),1,binding)
    assert len(rels) == 1 and rels[0].relation == expected_relation
    assert len(rows[0].evaluations) == 2 and (rows[0].count is None) == unknown
    assert bool(probs) == unknown
    relation_cases.append({'relation':expected_relation,'unknown':unknown,'evaluations':2})

union_cases = atom_checks = 0
for shift in (F(0),F(10**90),F(-10**90)):
    for _ in range(100):
        rectangles = []
        for _ in range(rng.randrange(1,8)):
            a,b = sorted(rng.sample(range(-12,13),2)); c,d = sorted(rng.sample(range(-12,13),2))
            rectangles.append(RationalRect(shift+F(a,7),shift+F(c,11),shift+F(b,7),shift+F(d,11)))
        rects = tuple(rectangles)
        out = rational_cover(rects)
        assert rational_cover(tuple(reversed(rects))) == out
        assert rational_cover(rects + rects) == out
        xs=sorted({x for r in rects+out for x in (r.x0,r.x1)})
        ys=sorted({y for r in rects+out for y in (r.y0,r.y1)})
        xprobe=xs+[F(a+b,2) for a,b in zip(xs,xs[1:])]
        yprobe=ys+[F(a+b,2) for a,b in zip(ys,ys[1:])]
        for x,y in itertools.product(xprobe,yprobe):
            before = any(r.x0 <= x < r.x1 and r.y0 <= y < r.y1 for r in rects)
            after_count = sum(r.x0 <= x < r.x1 and r.y0 <= y < r.y1 for r in out)
            assert after_count == int(before), (rects,out,x,y)
            atom_checks += 1
        union_cases += 1

receipt.update(normal_complete_crossings=normal, real_identity_associations=len(associations),
    neutral_identity_variants=identity_cases,
    generated_fin_verdicts=fin_checks, statuses=statuses, long_fin_two_channels=True,
    same_y_disjoint_x_outside=True, relation_cases=relation_cases,
    rational_union_cases=union_cases, rational_membership_checks=atom_checks,
    elapsed_seconds=time.monotonic()-started, ru_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    status='passed')
print(json.dumps(receipt, indent=2))
