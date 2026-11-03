"""Test-only independent stream edits and hand-derived geometry expectations.

No product parser/projection or fixture answer/generator supplies these answers.
Edits touch only pytest temporary copies, then use W005's existing test rebinder.
"""
from __future__ import annotations

import struct
from collections import Counter

from w005_cases import rebind

# Read directly from the specified synthetic input's integer BOUNDARY records.
# FIN is a hand-enumerated backdrop: eighteen strips, each 100 x 2 nm.
EXPECTED_RECTS = {
    'BOUNDARY': [(0, 0, 160, 200)],
    'BODY_N': [(0, 0, 120, 90)],
    'BODY_P': [(0, 100, 120, 200)],
    'OD': [(20, 20, 100, 70), (20, 110, 100, 180)],
    'POLY': [(58, 10, 62, 190)],
    'FIN': [(10, y, 110, y + 2) for y in (24, 34, 44, 54, 64, 74, 84, 94, 104,
                                                    114, 124, 134, 144, 154, 164, 174, 184, 194)],
    'LI': [(28, 30, 34, 55), (28, 130, 34, 155), (84, 30, 90, 165)],
    'CONTACT': [(29, 40, 33, 44), (85, 40, 89, 44), (29, 140, 33, 144), (85, 140, 89, 144)],
    'VIA0': [(29, 50, 33, 54), (29, 150, 33, 154), (85, 92, 89, 96)],
    'GCONTACT': [(59, 92, 61, 96)],
    'M1': [(0, 48, 45, 58), (0, 148, 45, 158), (50, 90, 75, 98), (80, 90, 110, 98)],
    'MARKER': [(145, 180, 150, 185)],
}
STREAM_LAYER = {'BOUNDARY': 100, 'BODY_N': 10, 'BODY_P': 11, 'OD': 2, 'POLY': 3,
                'FIN': 1, 'LI': 4, 'CONTACT': 7, 'VIA0': 5, 'GCONTACT': 8,
                'M1': 9, 'MARKER': 101, 'CUT': 6}


def hand_multiset(dx=0, dy=0):
    return Counter((layer, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))
                   for layer, rectangles in EXPECTED_RECTS.items() for x0, y0, x1, y1 in rectangles)


def record_bytes(kind, dtype, payload=b''):
    return struct.pack('>HBB', len(payload) + 4, kind, dtype) + payload


def rectangle_bytes(layer, bounds):
    x0, y0, x1, y1 = bounds
    coords = (x0, y0, x0, y1, x1, y1, x1, y0, x0, y0)
    return (record_bytes(8, 0) + record_bytes(13, 2, struct.pack('>h', layer))
            + record_bytes(14, 2, struct.pack('>h', 0))
            + record_bytes(16, 3, struct.pack('>10i', *coords)) + record_bytes(17, 0))


def blocks(raw):
    prefix, elements, suffix = [], [], []
    offset, current = 0, None
    while offset < len(raw):
        size, kind, _ = struct.unpack('>HBB', raw[offset:offset + 4])
        record = raw[offset:offset + size]
        offset += size
        if kind == 8:
            assert current is None
            current = [record]
        elif current is not None:
            current.append(record)
            if kind == 17:
                elements.append(b''.join(current))
                current = None
        elif elements:
            suffix.append(record)
        else:
            prefix.append(record)
    assert current is None
    return b''.join(prefix), elements, b''.join(suffix)


def edit_geometry(root, *, append=(), reorder=False, vertices=False, translate=(0, 0)):
    path = root / 'source.gds'
    prefix, elements, suffix = blocks(path.read_bytes())
    if reorder:
        elements.reverse()
    transformed = []
    dx, dy = translate
    for element in elements:
        offset, output = 0, []
        while offset < len(element):
            size, kind, dtype = struct.unpack('>HBB', element[offset:offset + 4])
            payload = element[offset + 4:offset + size]
            if kind == 16:
                coords = struct.unpack('>10i', payload)
                corners = [(coords[i] + dx, coords[i + 1] + dy) for i in range(0, 8, 2)]
                if vertices:
                    corners = corners[::-1]
                    corners = corners[2:] + corners[:2]
                points = corners + corners[:1]
                payload = struct.pack('>10i', *(v for pair in points for v in pair))
            output.append(record_bytes(kind, dtype, payload))
            offset += size
        transformed.append(b''.join(output))
    transformed.extend(rectangle_bytes(STREAM_LAYER[layer], box) for layer, box in append)
    path.write_bytes(prefix + b''.join(transformed) + suffix)
    rebind(root)


def overlap_area(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def independent_coverage(occupancy):
    """Containment + pairwise interior disjointness + area proves rectangle union."""
    records = {record.id: record for record in occupancy.layout.records}
    assert len(records) == len(occupancy.layout.records)
    assert len({fragment.id for fragment in occupancy.fragments}) == len(occupancy.fragments)
    for fragment in occupancy.fragments:
        assert fragment.record_id in records
        record = records[fragment.record_id]
        assert fragment.cell.layer == record.layer
        assert fragment.cell.partition_ref == occupancy.partition.ref
        assert fragment.unit_ref == occupancy.layout.units.ref
        actual = fragment.rect.bounds
        assert overlap_area(actual, record.rect.bounds) == area(actual)
        cell_bounds = occupancy.partition.layer(record.layer).cell_bounds(fragment.cell.x, fragment.cell.y).bounds
        assert overlap_area(actual, cell_bounds) == area(actual)
        assert fragment in occupancy.in_cell(fragment.cell)
    for record in records.values():
        fragments = occupancy.for_record(record.id)
        if not occupancy.layout.policy(record.layer).projected:
            assert fragments == ()
            continue
        boxes = [fragment.rect.bounds for fragment in fragments]
        assert boxes
        assert sum(area(box) for box in boxes) == area(record.rect.bounds)
        for i, box in enumerate(boxes):
            assert all(overlap_area(box, other) == 0 for other in boxes[i + 1:])
