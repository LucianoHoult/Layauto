"""Independent W009 byte transformations and finite-arrangement set checks.

Only temporary captured inputs are edited. No product geometry function, fixture
answer, or generator supplies expected coverage.
"""
from __future__ import annotations

import struct
from fractions import Fraction

from w005_cases import FIXTURE, read_json, rebind, write_json
from w008_geometry_cases import STREAM_LAYER, blocks, rectangle_bytes


def stream_layer(element):
    offset = 0
    while offset < len(element):
        size, kind, _ = struct.unpack('>HBB', element[offset:offset + 4])
        if kind == 13:
            return struct.unpack('>h', element[offset + 4:offset + size])[0]
        offset += size
    raise AssertionError('test BOUNDARY lacks layer')


def rewrite_geometry(root, *, replace_layers=None, append=(), reverse=False):
    """Edit actual GDS records without parsing through a product geometry API."""
    replace_layers = {} if replace_layers is None else replace_layers
    path = root / 'source.gds'
    prefix, elements, suffix = blocks(path.read_bytes())
    replaced = {STREAM_LAYER[name] for name in replace_layers}
    elements = [element for element in elements if stream_layer(element) not in replaced]
    additions = [(name, bounds) for name, rectangles in replace_layers.items() for bounds in rectangles]
    additions.extend(append)
    elements.extend(rectangle_bytes(STREAM_LAYER[name], bounds) for name, bounds in additions)
    if reverse:
        elements.reverse()
    path.write_bytes(prefix + b''.join(elements) + suffix)
    rebind(root)


def special_input(root):
    """Bind the existing special GDS to a temporary reader-compatible capture.

    Retained semantic/query/body associations isolate geometry only; this does
    not assert that they explain the special stream's electrical properties.
    """
    (root / 'source.gds').write_bytes((FIXTURE / 'special/cut_islands/source.gds').read_bytes())
    header = read_json(root / 'query/header.json')
    header['top_identities']['layout'] = 'CUT_ISLANDS_SYNTH'
    write_json(root / 'query/header.json', header)
    body = read_json(root / 'body/context.json')
    body['top'] = 'CUT_ISLANDS_SYNTH'
    write_json(root / 'body/context.json', body)
    for name in ('iXref.temp', 'nXref.temp'):
        path = root / 'query/raw' / name
        lines = path.read_text().splitlines()
        lines[1] = '# SVDB: Layout Primary CUT_ISLANDS_SYNTH'
        lines[7] = lines[7].replace('INV_M1_SYNTH', 'CUT_ISLANDS_SYNTH', 1)
        path.write_text('\n'.join(lines) + '\n')
    rebind(root)


def change_owner(root, owner, mutate):
    """Change one captured owner and rebind its actual bytes in the header."""
    path = root / 'tech' / (owner + '.json')
    document = read_json(path)
    mutate(document)
    write_json(path, document)
    rebind(root)


def contains(bounds, x, y):
    return bounds[0] <= x < bounds[2] and bounds[1] <= y < bounds[3]


def overlap_area(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def area(bounds):
    return (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])


def independent_difference(target, cuts, output):
    """Prove finite rectilinear coverage using independent exact point tests.

    Membership is constant inside every cell formed by all input/output bounds.
    All cells, boundary lines and vertices are tested using exact Fractions.
    Area is an additional check; it is never the only equivalence criterion.
    """
    cuts, output = tuple(cuts), tuple(output)
    for index, box in enumerate(output):
        assert area(box) > 0
        assert overlap_area(box, target) == area(box)
        assert all(overlap_area(box, other) == 0 for other in output[index + 1:])
    boxes = (target,) + cuts + output
    xs = sorted({value for box in boxes for value in (box[0], box[2])})
    ys = sorted({value for box in boxes for value in (box[1], box[3])})
    xs = [xs[0] - 1] + xs + [xs[-1] + 1]
    ys = [ys[0] - 1] + ys + [ys[-1] + 1]
    sample_x = xs + [Fraction(a + b, 2) for a, b in zip(xs, xs[1:])]
    sample_y = ys + [Fraction(a + b, 2) for a, b in zip(ys, ys[1:])]
    for x in sample_x:
        for y in sample_y:
            expected = contains(target, x, y) and not any(contains(cut, x, y) for cut in cuts)
            actual = sum(contains(box, x, y) for box in output)
            assert actual == int(expected), (target, cuts, output, x, y, expected, actual)
    expected_area = 0
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            x, y = Fraction(x0 + x1, 2), Fraction(y0 + y1, 2)
            if contains(target, x, y) and not any(contains(cut, x, y) for cut in cuts):
                expected_area += (x1 - x0) * (y1 - y0)
    assert sum(area(box) for box in output) == expected_area
    return expected_area


def region_boxes(record_result):
    return tuple(box.bounds for region in record_result.regions for box in region.rectangles)


def hand_channel_partition(record_result, active):
    roles = {region.role: region for region in record_result.regions}
    assert set(roles) == {'channel', 'S', 'D'}
    assert all(len(region.rectangles) == 1 for region in roles.values())
    channel, source, drain = (roles[role].rectangles[0].bounds for role in ('channel', 'S', 'D'))
    assert channel[1::2] == active[1::2]
    assert active[0] < channel[0] < channel[2] < active[2]
    assert source == (active[0], active[1], channel[0], active[3])
    assert drain == (channel[2], active[1], active[2], active[3])
    independent_difference(active, (), (channel, source, drain))
    return roles
