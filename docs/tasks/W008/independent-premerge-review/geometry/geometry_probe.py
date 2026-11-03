"""Independent W008 review oracle: binary records, set coverage, exact arithmetic.

Uses no expected/spec/oracle or project test helper. Derived files live only in
a temporary copy. The retained body/query facts are not a physical assertion.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import shutil
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import decode_record, encode_record
from layauto_v2.state.coordinate import LayerPartition, build_partition
from layauto_v2.state.occupancy import build_occupancy
from layauto_v2.domain.geometry import Rect


def must_reject(f):
    try:
        f()
    except ValueError:
        return
    raise AssertionError("invalid constructor accepted")


def stream_records(raw):
    out, pos = [], 0
    while pos < len(raw):
        length, kind, data_type = struct.unpack(">HBB", raw[pos:pos + 4])
        assert length >= 4 and length % 2 == 0
        assert pos + length <= len(raw)
        out.append((pos, kind, data_type, raw[pos + 4:pos + length], raw[pos:pos + length]))
        pos += length
    assert pos == len(raw)
    return out


def binary_shapes(raw):
    records = stream_records(raw)
    shapes = []
    for ordinal, (offset, kind, _, _, _) in enumerate(records):
        if kind != 8:
            continue
        a, b, c, d, e = records[ordinal:ordinal + 5]
        assert [v[1] for v in (a, b, c, d, e)] == [8, 13, 14, 16, 17]
        xy = struct.unpack(">10i", d[3])
        points = tuple(zip(xy[::2], xy[1::2]))
        shapes.append((ordinal, offset, struct.unpack(">h", b[3])[0],
                       struct.unpack(">h", c[3])[0], points,
                       (min(xy[::2]), min(xy[1::2]), max(xy[::2]), max(xy[1::2]))))
    return shapes


def contains(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def verify_coverage(occupancy):
    """Containment + pairwise disjoint interiors + area proves exact coverage."""
    for record in occupancy.layout.records:
        fragments = occupancy.for_record(record.id)
        if not occupancy.layout.policy(record.layer).projected:
            assert not fragments
            continue
        assert fragments
        boxes = [f.rect.bounds for f in fragments]
        assert all(contains(record.rect.bounds, box) for box in boxes)
        assert sum(map(area, boxes)) == area(record.rect.bounds)
        assert all(overlap(a, b) == 0 for a, b in itertools.combinations(boxes, 2))
        for fragment in fragments:
            assert fragment.record_id == record.id
            assert fragment.cell.layer == record.layer
            assert fragment in occupancy.in_cell(fragment.cell)
            layer = occupancy.partition.layer(record.layer)
            assert contains(layer.cell_bounds(fragment.cell.x, fragment.cell.y).bounds, fragment.rect.bounds)
            assert fragment.unit_ref == occupancy.layout.units.ref


def build(fixture):
    parsed = read_inputs(fixture / "site_config.yaml")
    assert parsed.status == "success", parsed.issues
    result = build_geometry(geometry_from_parse_result(parsed))
    assert result.status == "success", result.issues
    assert result.value is not None
    return parsed, result


def check_actual(fixture):
    parsed, result = build(fixture)
    occupancy = result.value
    raw = (fixture / "source.gds").read_bytes()
    expected = binary_shapes(raw)
    actual = occupancy.layout.records
    assert len(actual) == len(expected)
    for record, row in zip(actual, expected):
        ordinal, offset, layer, datatype, points, bbox = row
        assert (record.source.record_index, record.source.byte_offset) == (ordinal, offset)
        assert (record.stream_key.layer, record.stream_key.datatype) == (layer, datatype)
        assert record.raw_xy == points and record.rect.bounds == bbox
        assert record.id not in {r.id for r in actual if r is not record}
    verify_coverage(occupancy)
    units = occupancy.layout.units
    for name in ("user_units_per_tick", "metres_per_tick"):
        encoded = units.encoded[name]
        unit_raw = encoded["raw"]
        sign = -1 if unit_raw[0] & 128 else 1
        power = (unit_raw[0] & 127) - 64
        exact = sign * Fraction(int.from_bytes(unit_raw[1:], "big"), 2 ** 56) * Fraction(16) ** power
        assert exact == encoded["exact"]
        assert exact - encoded["nominal"] == encoded["encoding_delta"]
    for tick in (-2**100, -2147483648, -1, 0, 1, 2147483647, 2**100):
        assert units.source_to_canonical(tick) == tick
        assert units.canonical_to_source(tick) == tick
        assert units.source_to_nm(tick) == Fraction(tick)
    must_reject(lambda: units.source_to_canonical(True))
    must_reject(lambda: units.nm_to_canonical(Fraction(1, 2)))
    assert decode_record(encode_record(result)) == result
    assert build_occupancy(build_partition(occupancy.layout)) == occupancy
    if occupancy.fragments:
        must_reject(lambda: replace(occupancy, fragments=occupancy.fragments[:-1]))
        must_reject(lambda: replace(occupancy, fragments=occupancy.fragments + occupancy.fragments[:1]))
    if actual:
        must_reject(lambda: replace(occupancy.layout, records=actual[:-1]))
        must_reject(lambda: replace(occupancy.layout, records=actual + actual[:1]))
    return parsed, result


def mathematical_probe():
    rng = random.Random(72008113)
    cases, points_checked = 0, 0
    # Independent oracle enumerates every cell and compares interior membership;
    # it never uses the implementation's bisection/project range construction.
    for _ in range(600):
        xs = tuple(sorted(rng.sample(range(-12, 13), rng.randrange(2, 9))))
        ys = tuple(sorted(rng.sample(range(-12, 13), rng.randrange(2, 9))))
        partition = LayerPartition("independent-math", xs, ys)
        x0, x1 = sorted(rng.sample(range(xs[0], xs[-1] + 1), 2))
        y0, y1 = sorted(rng.sample(range(ys[0], ys[-1] + 1), 2))
        rectangle = Rect(x0, y0, x1, y1)
        expected = set()
        for i in range(len(xs) - 1):
            for j in range(len(ys) - 1):
                lo_x, hi_x = max(x0, xs[i]), min(x1, xs[i + 1])
                lo_y, hi_y = max(y0, ys[j]), min(y1, ys[j + 1])
                if lo_x < hi_x and lo_y < hi_y:
                    expected.add((i, j, (lo_x, lo_y, hi_x, hi_y)))
        actual = partition.project(rectangle)
        assert {(i, j, r.bounds) for i, j, r in actual} == expected
        boxes = [r.bounds for _, _, r in actual]
        assert sum(map(area, boxes)) == area(rectangle.bounds)
        assert all(overlap(a, b) == 0 for a, b in itertools.combinations(boxes, 2))
        for x in (Fraction(v, 2) for v in range(2 * xs[0] - 1, 2 * xs[-1] + 2)):
            y = Fraction(ys[rng.randrange(len(ys))])
            found = [(i, j) for i in range(len(xs)-1) for j in range(len(ys)-1)
                     if xs[i] <= x < xs[i+1] and ys[j] <= y < ys[j+1]]
            if found:
                assert partition.point_to_index(x, y) == found[0]
            else:
                must_reject(lambda: partition.point_to_index(x, y))
            points_checked += 1
        cases += 1
    huge = LayerPartition("huge", (-2**100, -1, 0, 2**100), (-2**90, 0, 2**90))
    assert huge.point_to_index(Fraction(-1, 2), Fraction(1, 3)) == (1, 1)
    assert sum(r.area for _, _, r in huge.project(Rect(-2**100, -2**90, 2**100, 2**90))) == 2**192
    empty = LayerPartition("empty", (), ())
    must_reject(lambda: empty.point_to_index(0, 0))
    must_reject(lambda: empty.project(Rect(0, 0, 1, 1)))
    for xs, ys in (((0,), (0,)), ((1, 0), (0, 1)), ((0, 0), (0, 1)), ((0, 1), ())):
        must_reject(lambda: LayerPartition("bad", xs, ys))
    return cases, points_checked


def gds_record(kind, datatype, body=b""):
    return struct.pack(">HBB", len(body) + 4, kind, datatype) + body


def rectangle_stream(layer, bounds, rotate=0, reverse=False):
    x0, y0, x1, y1 = bounds
    points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if reverse:
        points.reverse()
    points = points[rotate:] + points[:rotate]
    points.append(points[0])
    return b"".join((gds_record(8, 0), gds_record(13, 2, struct.pack(">h", layer)),
                     gds_record(14, 2, struct.pack(">h", 0)),
                     gds_record(16, 3, struct.pack(">10i", *(c for p in points for c in p))),
                     gds_record(17, 0)))


def rebind(fixture):
    gds_hash = hashlib.sha256((fixture / "source.gds").read_bytes()).hexdigest()
    body_path = fixture / "body/context.json"
    body = json.loads(body_path.read_text())
    body["source_gds"]["sha256"] = gds_hash
    body_path.write_text(json.dumps(body, indent=2) + "\n")
    header_path = fixture / "query/header.json"
    header = json.loads(header_path.read_text())
    header["layout"]["sha256"] = gds_hash
    for row in header["closure"]["entries"]:
        row["sha256"] = hashlib.sha256((fixture / row["uri"]).read_bytes()).hexdigest()
    wire = json.dumps(header["closure"]["entries"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    header["closure"]["sha256"] = hashlib.sha256(wire).hexdigest()
    header_path.write_text(json.dumps(header, indent=2) + "\n")


def derived_cases(fixture):
    # New input has three independent LI records: A, overlapping B and duplicate
    # A. Exact hand areas 35, 30, 35; intersection area 8; no physical claims.
    shapes = [(4, (-5, -3, 2, 2)), (4, (-1, 0, 5, 5)), (4, (-5, -3, 2, 2)),
              (5, (-2, -2, 1, 1)), (7, (-1, -1, 1, 1)), (6, (-3, -1, 3, 1)),
              (100, (-8, -8, 8, 8)), (101, (6, 6, 7, 7))]
    raw_records = stream_records((fixture / "source.gds").read_bytes())
    prefix = b"".join(r[4] for r in raw_records[:6])
    suffix = b"".join(r[4] for r in raw_records[-2:])
    with tempfile.TemporaryDirectory(prefix="w008-independent-math-") as temp:
        derived = Path(temp) / "fixture"
        shutil.copytree(fixture, derived)
        def write(order, vertices=False):
            data = prefix + b"".join(rectangle_stream(*shapes[i], rotate=(i % 4 if vertices else 0), reverse=vertices) for i in order) + suffix
            (derived / "source.gds").write_bytes(data)
            rebind(derived)
            return check_actual(derived)[1]
        original = write(range(len(shapes)))
        o = original.value
        assert len(o.layout.records) == 8
        li = [r for r in o.layout.records if r.layer == "LI"]
        assert sorted(sum(f.rect.area for f in o.for_record(r.id)) for r in li) == [30, 35, 35]
        shared = o.partition.physical_to_index("LI", 0, 1)
        occupants = [f for f in o.fragments if f.cell.layer == "LI" and (f.cell.x, f.cell.y) == shared]
        assert len(occupants) == 3 and len({f.record_id for f in occupants}) == 3
        assert all(f.cell.layer not in ("BOUNDARY", "MARKER") for f in o.fragments)
        for record in o.layout.records:
            if record.layer in ("VIA0", "CONTACT", "CUT"):
                assert all(f.cell.layer == record.layer for f in o.for_record(record.id))
        reordered = write(reversed(range(len(shapes))), vertices=True)
        assert reordered.value.layout.semantic_digest == o.layout.semantic_digest
        assert reordered.value.layout.ref != o.layout.ref
        assert reordered.value.partition.layers == o.partition.layers
        removed_duplicate = write([i for i in range(len(shapes)) if i != 2])
        assert removed_duplicate.value.layout.semantic_digest != o.layout.semantic_digest
        empty = write([])
        assert empty.value.layout.records == () and empty.value.fragments == ()
        assert all(layer.xs == layer.ys == () for layer in empty.value.partition.layers)
    return 4


if __name__ == "__main__":
    fixture = ROOT / "tests/fixtures/w003_m1"
    cases, points = mathematical_probe()
    parsed, result = check_actual(fixture)
    assert len(result.value.layout.records) == 40
    assert len(parsed.value["body"]["shapes"]) == 6
    derived = derived_cases(fixture)
    print(json.dumps({"status": "pass", "python": sys.version, "checkout": str(ROOT),
                      "math_partitions": cases, "point_membership_checks": points,
                      "actual_binary_records": len(result.value.layout.records),
                      "actual_projected_records": sum(bool(result.value.for_record(r.id)) for r in result.value.layout.records),
                      "actual_fragments": len(result.value.fragments), "derived_builds": derived,
                      "oracle": "independent binary record unpack + containment/disjointness/area + exhaustive cell membership"}, indent=2))
