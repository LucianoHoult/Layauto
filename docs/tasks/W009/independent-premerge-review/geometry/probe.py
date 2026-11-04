"""Independent premerge geometry witnesses; no product function supplies answers.

The finite oracle is a unit-pixel set and four-neighbour flood fill. Product
slabs/groups are solely subjects under test. Fixture helpers only rewrite bytes
and rebind temporary input captures; no helper geometry oracle is imported.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'tests/contracts'))
from layauto_v2.domain.geometry import Rect
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry, build_effective_geometry
from layauto_v2.state.regions import slab_difference, _groups
from w005_cases import FIXTURE
from w007_cases import ready_copy
from w009_cases import rewrite_geometry, special_input


def member(box, x2, y2):
    return 2 * box[0] <= x2 < 2 * box[2] and 2 * box[1] <= y2 < 2 * box[3]


def flood(pixels):
    pending = set(pixels)
    groups = []
    while pending:
        seed = min(pending)
        pending.remove(seed)
        group, todo = {seed}, [seed]
        while todo:
            x, y = todo.pop()
            for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if p in pending:
                    pending.remove(p)
                    group.add(p)
                    todo.append(p)
        groups.append(frozenset(group))
    return set(groups)


def pixels(boxes, target):
    return {(x, y) for x in range(target[0], target[2])
            for y in range(target[1], target[3])
            if any(member(b, 2 * x + 1, 2 * y + 1) for b in boxes)}


def finite_case(target, cuts):
    output = slab_difference(Rect(*target), tuple(Rect(*c) for c in cuts))
    boxes = tuple(r.bounds for r in output)
    expected = pixels((target,), target) - pixels(cuts, target)
    assert pixels(boxes, target) == expected
    samples = 0
    # All half-unit points include interior, edges and vertices. Integer input
    # bounds imply piecewise-constant membership between these sample lines.
    for x2 in range(2 * target[0] - 1, 2 * target[2] + 2):
        for y2 in range(2 * target[1] - 1, 2 * target[3] + 2):
            want = member(target, x2, y2) and not any(member(c, x2, y2) for c in cuts)
            got = sum(member(b, x2, y2) for b in boxes)
            assert got == int(want), (target, cuts, boxes, x2, y2)
            samples += 1
    # No area-only criterion: enumerate each region's exact pixels and compare
    # component partitions, not merely their counts.
    actual_groups = {frozenset(pixels(tuple(r.bounds for r in group), target))
                     for group in _groups(output)}
    assert actual_groups == flood(expected), (target, cuts, boxes, actual_groups, flood(expected))
    assert sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes) == len(expected)
    assert output == slab_difference(Rect(*target), tuple(Rect(*c) for c in reversed(cuts)) + tuple(Rect(*c) for c in cuts))
    return samples, len(output), len(actual_groups)


def capture(root):
    parsed = read_inputs(root / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    geometry = build_geometry(geometry_from_parse_result(parsed))
    assert geometry.status == 'success', geometry.issues
    return geometry, build_effective_geometry(geometry)


def boxes(record):
    return tuple(r.bounds for region in record.regions for r in region.rectangles)


def capture_cases():
    g, e = capture(FIXTURE)
    assert e.status == 'success', e.issues
    roles = [(region.role, tuple(r.bounds for r in region.rectangles))
             for rec in e.value.records for region in rec.regions if rec.operation == 'terminal']
    assert sorted(roles) == sorted([
        ('channel', ((58, 20, 62, 70),)), ('S', ((20, 20, 58, 70),)), ('D', ((62, 20, 100, 70),)),
        ('channel', ((58, 110, 62, 180),)), ('S', ((20, 110, 58, 180),)), ('D', ((62, 110, 100, 180),))])
    assert e.value.base is g.value
    details = [{'case': 'normal', 'channels': 2, 'terminals': 4}]
    with tempfile.TemporaryDirectory(prefix='w009-geometric-', dir='/workspace/work') as temp:
        work = Path(temp)
        special = ready_copy(work / 'special')
        special_input(special)
        g, e = capture(special)
        assert e.status == 'success', e.issues
        rows = {raw.rect.bounds: boxes(e.value.for_record(raw.id))
                for raw in g.value.layout.records if raw.layer == 'LI'}
        assert rows == {(130, 20, 150, 24): ((130, 20, 139, 24), (141, 20, 150, 24)),
                        (50, 20, 60, 24): ((50, 20, 60, 24),)}
        assert sum((r[2] - r[0]) * (r[3] - r[1]) for r in rows[(130, 20, 150, 24)]) == 72
        details.append({'case': 'special-cut-islands', 'exact_rows': str(rows)})
        # All OD cases use one new active with no normal OD/POLY. Output success
        # is inferred from the declared full-height interior-stripe rule only.
        active = (210, 220, 230, 240)
        cases = [
            ('no_gate', (), 'AmbiguousGateStripe'),
            ('edge_contact', ((230, 215, 234, 245),), 'AmbiguousGateStripe'),
            ('corner_contact', ((230, 240, 234, 245),), 'AmbiguousGateStripe'),
            ('partial_height', ((216, 225, 220, 245),), 'UnsupportedTerminalSplit'),
            ('two_stripes', ((215, 215, 218, 245), (222, 215, 225, 245)), 'AmbiguousGateStripe'),
            ('overlapping_distinct_stripes', ((215, 215, 221, 245), (218, 215, 224, 245)), 'AmbiguousGateStripe'),
            ('same_intersection_distinct_drawn', ((216, 215, 220, 245), (216, 210, 220, 250)), 'AmbiguousGateStripe'),
            ('covers_active', ((200, 210, 240, 250),), 'UnsupportedTerminalSplit'),
            ('touches_left', ((210, 215, 220, 245),), 'UnsupportedTerminalSplit'),
            ('horizontal', ((205, 225, 235, 230),), 'UnsupportedTerminalSplit'),
            ('valid', ((216, 215, 220, 245),), None),
            ('duplicate_poly', ((216, 215, 220, 245), (216, 215, 220, 245)), None),
        ]
        for name, gates, code in cases:
            root = ready_copy(work / name)
            rewrite_geometry(root, replace_layers={'OD': (active,), 'POLY': gates})
            g, e = capture(root)
            if code:
                assert e.status == 'error' and [i.code for i in e.issues] == [code], (name, e)
                assert e.issues[0].source is not None
            else:
                assert e.status == 'success', (name, e.issues)
                rec = next(r for r in e.value.records if r.operation == 'terminal')
                assert {r.role: boxes(type('RegionSet', (), {'regions': (r,)})()) for r in rec.regions} == {
                    'channel': ((216, 220, 220, 240),), 'S': ((210, 220, 216, 240),), 'D': ((220, 220, 230, 240),)}
                assert len(rec.contributors) == len(gates)
            details.append({'case': name, 'status': e.status, 'expected_issue': code})
        # Duplicate targets and duplicate/overlapping cutters preserve every
        # original record while all cutters act by union; an off-target CUT has
        # no contributor role. Reverse GDS order changes provenance, not geometry.
        outputs = []
        for reverse in (False, True):
            root = ready_copy(work / ('reverse' if reverse else 'forward'))
            rewrite_geometry(root, replace_layers={'LI': ((200, 200, 210, 210),) * 2,
                'CUT': ((203, 203, 207, 207), (203, 203, 207, 207), (205, 205, 209, 209), (210, 200, 215, 210))}, reverse=reverse)
            g, e = capture(root)
            assert e.status == 'success', e.issues
            targets = [r for r in g.value.layout.records if r.layer == 'LI']
            assert len(targets) == 2 and targets[0].id != targets[1].id
            rows = [e.value.for_record(r.id) for r in targets]
            assert all(len(r.contributors) == 3 for r in rows)
            assert rows[0].record_id != rows[1].record_id and boxes(rows[0]) == boxes(rows[1])
            finite_case((200, 200, 210, 210), ((203, 203, 207, 207), (203, 203, 207, 207), (205, 205, 209, 209)))
            assert pixels(boxes(rows[0]), (200, 200, 210, 210)) == pixels(((200, 200, 210, 210),), (200, 200, 210, 210)) - pixels(((203, 203, 207, 207), (205, 205, 209, 209)), (200, 200, 210, 210))
            # Internal LI raw axes are x=[200,210], y=[200,210]; hole edges
            # are absent, so retaining the full one raw occupancy cell matters.
            assert all(len(g.value.for_record(r.id)) == 1 for r in targets)
            assert all(g.value.for_record(r.id)[0].rect.bounds == r.rect.bounds for r in targets)
            outputs.append(e.value.semantic_digest)
        assert outputs[0] == outputs[1]
        details.append({'case': 'duplicate-target-overlap-cuts-and-reversed-GDS', 'stable_semantic_digest': outputs[0]})
    return details


def main():
    start = time.monotonic()
    count = samples = max_pieces = max_groups = 0
    cells = tuple(itertools.product(range(4), range(3)))
    for mask in range(1 << len(cells)):
        cuts = tuple((x, y, x + 1, y + 1) for i, (x, y) in enumerate(cells) if mask >> i & 1)
        points, pieces, groups = finite_case((0, 0, 4, 3), cuts)
        count += 1; samples += points; max_pieces = max(max_pieces, pieces); max_groups = max(max_groups, groups)
    rng = random.Random(11032026)
    for _ in range(320):
        cuts = []
        for _ in range(rng.randrange(13)):
            x0, x1 = sorted(rng.sample(range(-6, 7), 2))
            y0, y1 = sorted(rng.sample(range(-6, 7), 2))
            cuts.append((x0, y0, x1, y1))
        points, pieces, groups = finite_case((-4, -4, 4, 4), tuple(cuts))
        count += 1; samples += points; max_pieces = max(max_pieces, pieces); max_groups = max(max_groups, groups)
    # Huge affine transforms exercise integer arithmetic without rasterizing a
    # huge bounding box. Membership uses preimage half-unit coordinates.
    t, cs = (0, 0, 4, 3), ((1, 1, 3, 2), (3, 0, 5, 1))
    for scale, dx, dy in ((2**80 + 1, -2**121, 2**127), (1, 2**512, -2**512)):
        transform = lambda b: (b[0]*scale+dx, b[1]*scale+dy, b[2]*scale+dx, b[3]*scale+dy)
        output = slab_difference(Rect(*transform(t)), tuple(Rect(*transform(c)) for c in cs))
        for x2 in range(-1, 10):
            for y2 in range(-1, 8):
                want = member(t, x2, y2) and not any(member(c, x2, y2) for c in cs)
                got = sum(member(r.bounds, x2*scale+2*dx, y2*scale+2*dy) for r in output)
                assert got == int(want)
                samples += 1
        count += 1
    result = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.version, 'cwd': str(Path.cwd()), 'imported_root': str(ROOT),
        'finite_cases': count, 'point_checks': samples, 'max_output_pieces_seen': max_pieces,
        'max_local_groups_seen': max_groups, 'capture_cases': capture_cases(),
        'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py', 'layauto_v2/normalization/effective.py')},
        'elapsed_seconds': round(time.monotonic()-start, 3), 'status': 'passed'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
