"""Fixture-specific independent review. Run from any directory with Python 3.10+."""
import hashlib
import json
import struct
from collections import Counter
from fractions import Fraction
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[4] / "tests/fixtures/w003_m1"


def document(name):
    return json.loads((FIXTURE / name).read_text())


def gds_rectangles(relative_name, names, scales):
    # Read original integer XY and the location of the BOUNDARY record. Only
    # these two complete known flat examples are within this review probe.
    data = (FIXTURE / relative_name).read_bytes()
    records = []
    cursor = 0
    saw_units = False
    while cursor < len(data):
        length, kind, _ = struct.unpack_from(">HBB", data, cursor)
        assert 4 <= length <= len(data) - cursor
        raw = data[cursor + 4:cursor + length]
        if kind == 3:  # GDS UNITS
            assert not saw_units and len(raw) == 16
            for field, nominal in zip((raw[:8], raw[8:]), scales):
                ulp = Fraction(16) ** (field[0] - 64) / 2**56
                mantissa = int.from_bytes(field[1:], "big")
                assert 0x10 <= field[1] and mantissa == round(nominal / ulp)
            saw_units = True
        elif kind == 8:
            offset = cursor
        elif kind == 13:
            layer, = struct.unpack(">h", raw)
        elif kind == 14:
            datatype, = struct.unpack(">h", raw)
        elif kind == 16:
            points = list(struct.iter_unpack(">ii", raw))
            assert len(points) == 5 and points[0] == points[-1]
            xs, ys = zip(*points)
            bounds = (min(xs), min(ys), max(xs), max(ys))
            assert set(points) == {(x, y) for x in bounds[::2] for y in bounds[1::2]}
            assert all((x == xx) != (y == yy) for (x, y), (xx, yy) in zip(points, points[1:]))
            records.append((names[layer, datatype], bounds, offset))
        cursor += length
    assert saw_units
    return records


def pixels(box):
    x0, y0, x1, y1 = box
    return {(x, y) for x in range(x0, x1) for y in range(y0, y1)}


def cell_at(edges, value):
    return next((i for i, (a, b) in enumerate(zip(edges, edges[1:])) if a <= value < b), None)


def review():
    table = document("tech/drawn.json")["layers"]
    names = {(row["stream_key"]["layer"], row["stream_key"]["datatype"]): row["name"] for row in table}
    coord = document("tech/coordinate.json")["coordinate_projection"]
    assert coord["frame_origin_nm"] == [0, 0]
    assert coord["example_only"] and not coord["is_complete_runtime_model"]
    assert "axes" not in coord and all("coordinate_axes" not in row for row in table)
    scale = document("tech/formats.json")["unit_scale_contract"]

    def nominal(field):
        ratio = scale[field]
        return Fraction(int(ratio["numerator"]), int(ratio["denominator"]))

    metres = nominal("nominal_tick_m")
    scales = (metres / nominal("nominal_user_unit_m"), metres)
    assert metres * 10**9 == scale["canonical_tick_nm"] == 1
    main = gds_rectangles("source.gds", names, scales)
    counts = Counter(name for name, _, _ in main)
    assert len(main) == 40 and len(table) == 15
    assert set(names.values()) - counts.keys() == {"CUT", "BTAP_N", "BTAP_P"}
    assert {row["name"] for row in table if row["projection_kind"] == "none"} == {"BOUNDARY", "MARKER"}
    fin = document("tech/physical.json")["fin_count_profile"]
    pitch, width = fin["fin_pitch_nm"], fin["fin_width_nm"]
    phase = fin["fin_lower_edge_offset_nm"] + Fraction(width, 2)
    observed = []
    for name, (x0, y0, x1, y1), offset in main:
        if name == "FIN":
            assert x1 - x0 > y1 - y0 == width
            centre = Fraction(y1 + y0, 2)
            k = (centre - phase) / pitch
            assert k.denominator == 1 and phase + pitch * k == centre
            observed.append((int(k), y0, y1, offset))
    assert [k for k, *_ in sorted(observed)] == list(range(18))
    assert counts["POLY"] == 1
    assert 30 - phase == 5 and 30 - (phase + pitch) == -5

    # Enumerate integer unit-square interiors, partitioning them by midpoint.
    xs, ys = [-6, 4, 14], [-3, 1, 5]
    groups = {}
    source = pixels((-2, -1, 6, 3))
    for x, y in source:
        key = cell_at(xs, x + Fraction(1, 2)), cell_at(ys, y + Fraction(1, 2))
        groups.setdefault(key, set()).add((x, y))
    expected = {(0, 0): (-2, -1, 4, 1), (0, 1): (-2, 1, 4, 3),
                (1, 0): (4, -1, 6, 1), (1, 1): (4, 1, 6, 3)}
    assert groups == {key: pixels(box) for key, box in expected.items()}
    assert set.union(*groups.values()) == source and sum(map(len, groups.values())) == 32
    assert [cell_at(xs, Fraction(4) + d) for d in (Fraction(-1, 100), 0, Fraction(1, 100))] == [0, 1, 1]
    assert [cell_at(ys, Fraction(1) + d) for d in (Fraction(-1, 100), 0, Fraction(1, 100))] == [0, 1, 1]
    assert cell_at(xs, 14) is None and cell_at(ys, 5) is None
    assert cell_at(xs, -6) == cell_at(ys, -3) == 0

    special = gds_rectangles("special/cut_islands/source.gds", names, scales)
    cut, = [box for name, box, _ in special if name == "CUT"]
    lb, = [box for name, box, _ in special if name == "LI" and pixels(cut) & pixels(box)]
    drawn, removed = pixels(lb), pixels(cut) & pixels(lb)
    effective = drawn - removed
    left, right = (130, 20, 139, 24), (141, 20, 150, 24)
    assert effective == pixels(left) | pixels(right)
    assert len(drawn) == 80 and len(removed) == 8 and removed == pixels((139, 20, 141, 24))
    assert len(pixels(left)) == len(pixels(right)) == 36 and right[0] - left[2] == 2
    bucket = document("special/cut_islands/spec.json")["index_witness"]
    ox, oy = bucket["origin_nm"]
    w, h = bucket["index_cell_width_nm"], bucket["index_cell_height_nm"]
    assert {((x - ox) // w, (y - oy) // h) for x, y in effective} == {(4, 1)}
    assert bucket["example_only"] and not bucket["is_runtime_coordinate_model"]
    # Compare the independent facts above to the persisted proposal report.
    report = json.loads((Path(__file__).resolve().parents[1] / "samples.json").read_bytes())
    s1, s2, s3, s4 = (report[f"S{i}"] for i in (1, 2, 3, 4))
    assert report["layers"] == {name: counts[name] for name in names.values()}
    assert sorted((r["index"], int(r["lower_nm"]), int(r["upper_nm"]), r["byte_offset"])
                  for r in s1["rows"]) == sorted(observed)
    middle, = [r for r in s1["queries"] if r["y_nm"] == "30"]
    assert [(r["index"], Fraction(r["delta_nm"])) for r in middle["adjacent"]] == [(0, 5), (1, -5)]
    for n, rect in enumerate(((-2, -1, 6, 3), (-2, -1, 4, 1))):
        rows = [r for r in s2["pieces"] if r["source_field"] == f"/rectangles/{n}"]
        footprint = Counter()
        for row in rows:
            unit_squares = pixels(row["rect_dbu"])
            footprint.update(unit_squares)
            assert len(unit_squares) == row["area_dbu2"]
            assert unit_squares <= groups[tuple(row["cell"])]
        assert footprint == Counter(pixels(rect))
    for row in s2["points"]:
        x, y = map(Fraction, row["point"])
        cell = [cell_at(xs, x), cell_at(ys, y)]
        if None in cell:
            assert row["status"] == "outside_range"
        else:
            assert row["cell"] == cell
    assert {(r["layer"], tuple(r["rect_dbu"]), r["byte_offset"]) for r in s3["records"]} == set(special)
    cut_id, = [r["record_id"] for r in s3["records"] if r["layer"] == "CUT"]
    lb_id, = [r["record_id"] for r in s3["records"] if tuple(r["rect_dbu"]) == lb]
    branches = [r for r in s3["effective"] if r["record_id"] == lb_id]
    assert len(branches) == 2 and len({r["region"] for r in branches}) == 2
    assert all(r["cut_ids"] == [cut_id] and r["cell"] == [4, 1] for r in branches)
    assert {tuple(r["rect_dbu"]) for r in branches} == {left, right}
    assert len(s3["removed"]) == 1 and pixels(s3["removed"][0]["removed_dbu"]) == removed

    li_by_offset = {offset: pixels(box) for name, box, offset in main if name == "LI"}
    for variant, result, dx, dy, y_origin in [
        ("selected", s4["li_fragments"], 20, 10, 0),
        ("shift_y_edge", s4["variants"]["shift_y_edge"]["result"], 20, 10, 1),
        ("exchange_pitch_directions", s4["variants"]["exchange_pitch_directions"]["result"], 10, 20, 0)
    ]:
        for rec in s4["li_records"]:
            expected_li = li_by_offset[rec["byte_offset"]]
            rows = [r for r in result if r["record_id"] == rec["record_id"]]
            assembled = Counter()
            for r in rows:
                squares = pixels(r["rect_dbu"])
                assembled.update(squares)
                assert {(x // dx, (y - y_origin) // dy) for x, y in squares} == {tuple(r["cell"])}
            assert assembled == Counter(expected_li)
        print("LI fragments", variant, len(result))
    print("GDS source hashes", *(hashlib.sha256((FIXTURE / path).read_bytes()).hexdigest()
                                for path in ("source.gds", "special/cut_islands/source.gds")))
    print("FIN (k, lower, upper, record byte offset)", sorted(observed)[0], sorted(observed)[-1])
    print("Layer counts", {row["name"]: counts[row["name"]] for row in table})
    print("Half-open cell areas", {key: len(groups[key]) for key in sorted(groups)})
    print("CUT sample (layer, bounds, record byte offset)", special)
    print("LB drawn/removed/effective", len(drawn), len(removed), len(effective), "shared bucket", (4, 1))


if __name__ == "__main__":
    review()
