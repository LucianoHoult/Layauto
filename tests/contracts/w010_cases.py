"""W010 independent finite-arrangement geometry and real-capture test helpers.

These helpers never supply runtime answers. Temporary GDS edits use the declared
stream subset, then rebind its actual captured bytes through the existing tests.
"""
from __future__ import annotations

from fractions import Fraction

from w005_cases import FIXTURE, rebind
from w007_cases import read
from w008_geometry_cases import STREAM_LAYER, blocks, rectangle_bytes


def build_effective(root=FIXTURE):
    from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
    geometry = build_geometry(geometry_from_parse_result(read(root)))
    assert geometry.status == 'success', geometry.issues
    result = build_effective_geometry(geometry)
    assert result.status == 'success', result.issues
    return result


def build_local(root=FIXTURE):
    from layauto_v2.normalization import build_local_connectivity
    result = build_local_connectivity(build_effective(root))
    assert result.status == 'success', result.issues
    return result


def append_records(root, records):
    prefix, elements, suffix = blocks((root / 'source.gds').read_bytes())
    layers = dict(STREAM_LAYER, BTAP_N=12, BTAP_P=13)
    elements.extend(rectangle_bytes(layers[layer], bounds) for layer, bounds in records)
    (root / 'source.gds').write_bytes(prefix + b''.join(elements) + suffix)
    rebind(root)


def closed_contains(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def arrangement_contact(first, second):
    """Independent exhaustive open-cell and open-line witness search.

    Exact membership is constant on each arrangement atom. A common 2D atom or
    1D atom proves contact; 0D vertices are intentionally excluded.
    """
    first, second = tuple(first), tuple(second)
    boxes = first + second
    xs = sorted({v for box in boxes for v in (box[0], box[2])})
    ys = sorted({v for box in boxes for v in (box[1], box[3])})
    mx = [Fraction(a + b, 2) for a, b in zip(xs, xs[1:])]
    my = [Fraction(a + b, 2) for a, b in zip(ys, ys[1:])]
    witnesses = ((x, y) for x in mx for y in my)
    lines = ((x, y) for x in xs for y in my)
    horizontal = ((x, y) for x in mx for y in ys)
    for candidates in (witnesses, lines, horizontal):
        for x, y in candidates:
            if any(closed_contains(box, x, y) for box in first) and any(
                    closed_contains(box, x, y) for box in second):
                return True
    return False


def arrangement_enclosure(cover, target, margin):
    """Exhaust all 2D, 1D and 0D target atoms, including fractional expansion."""
    target = (Fraction(target[0]) - margin, Fraction(target[1]) - margin,
              Fraction(target[2]) + margin, Fraction(target[3]) + margin)
    xs = sorted({target[0], target[2]} | {v for box in cover for v in (box[0], box[2])
                                         if target[0] < v < target[2]})
    ys = sorted({target[1], target[3]} | {v for box in cover for v in (box[1], box[3])
                                         if target[1] < v < target[3]})
    sample_x = xs + [Fraction(a + b, 2) for a, b in zip(xs, xs[1:])]
    sample_y = ys + [Fraction(a + b, 2) for a, b in zip(ys, ys[1:])]
    return all(any(closed_contains(box, x, y) for box in cover)
               for x in sample_x for y in sample_y)


def normal_node_names(draft, spec, oracle):
    """Attach hand-authored display names only after product graph creation."""
    raw = {(row['layer'], tuple(row['bbox'])): row['id'] for row in spec['shapes']}
    expected = {row['id']: tuple(row['bbox']) for row in oracle['fragments']}
    names = {}
    for node in draft.nodes:
        owner = draft.effective.base.layout.record(node.region.owner_id)
        name = raw[node.layer, owner.rect.bounds]
        if node.layer == 'OD':
            name += '.' + node.region.role
            assert tuple(rect.bounds for rect in node.region.rectangles) == (expected[name],)
        else:
            assert tuple(rect.bounds for rect in node.region.rectangles) == (owner.rect.bounds,)
        names[node.ref] = name
    return names
