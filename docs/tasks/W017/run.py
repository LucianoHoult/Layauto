"""From repository root: python -B docs/tasks/W017/run.py [--resources]."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter_ns
import tracemalloc

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/contracts")]
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.geometry import Rect
from layauto_v2.importers import read_inputs
from layauto_v2.importers.config import load_document
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.state.coordinate import LayerPartition
from model import Edges, Issue, axes_for, bind, cover
from w005_cases import FIXTURE, copy_input, without_cache
from w009_cases import special_input


def capture(root):
    parsed = read_inputs(root / "site_config.yaml")
    assert parsed.status == "success", parsed.issues
    geometry = build_geometry(geometry_from_parse_result(parsed))
    assert geometry.status == "success", geometry.issues
    return parsed, geometry


def source(name):
    return SourceFile(name, (HERE / name).read_bytes())


def origin(record):
    return {"record_id": record.id.sha256, "layer": record.layer, "record_index": record.source.record_index,
            "byte_offset": record.source.byte_offset, "rect_dbu": record.rect.bounds}


def attempt(call):
    try:
        return call()
    except Issue as exc:
        return exc.detail


def strip_location(rect, tracks, units, width_nm):
    width = units.canonical_to_nm(rect.y1 - rect.y0)
    if rect.x1 - rect.x0 <= rect.y1 - rect.y0 or width != width_nm:
        return dict(status="unsupported_strip", rect_dbu=rect.bounds)
    centre = units.canonical_to_nm(rect.y0 + rect.y1) / 2
    return dict(tracks.locate(centre), rect_dbu=rect.bounds)


def fin_sample(layout, model, profile):
    tracks, = axes_for(model, "FIN", ("track",))
    rows = []
    for record in layout.records:
        if record.layer == "FIN":
            low, high = (layout.units.canonical_to_nm(t) for t in (record.rect.y0, record.rect.y1))
            query = strip_location(record.rect, tracks, layout.units, profile["fin_width_nm"])
            back = tracks.centre(query["index"]) if query["status"] == "on_track" else None
            rows.append(dict(origin(record), lower_nm=str(low), upper_nm=str(high), **query,
                             reverse_nm=str(back)))
    return {"source": "source.gds", "axis": "fin_y", "rows": rows,
            "queries": [tracks.locate(y) for y in (25, 35, 30, Fraction(2499, 100), 195, 196)]}


def math_sample():
    src = source("math-input.json")
    inputs = json.loads(src.data)
    grid = LayerPartition("S2", inputs["x_edges"], inputs["y_edges"])
    fragments = []
    for n, bounds in enumerate(inputs["rectangles"]):
        for i, j, part in grid.project(Rect(*bounds)):
            fragments.append(dict(source_field=f"/rectangles/{n}", cell=[i, j], rect_dbu=part.bounds,
                                  area_dbu2=part.area))
    points = []
    for point in inputs["points"]:
        try:
            cell = grid.point_to_index(*map(Fraction, point))
        except ValueError:
            points.append(dict(point=point, status="outside_range"))
        else:
            points.append(dict(point=point, status="inside", cell=cell))
    return dict(source=src.uri, sha256=src.sha256, pieces=fragments, points=points)


def cut_sample():
    # W009's adapter constructs a temporary reader-compatible geometry capture.
    with TemporaryDirectory() as directory:
        root = copy_input(Path(directory))
        without_cache(root)
        special_input(root)
        parsed, geometry = capture(root)
        result = build_effective_geometry(geometry)
        assert result.status == "success", result.issues
    layout = geometry.layout
    bucket_source = SourceFile("special/cut_islands/spec.json",
                               (FIXTURE / "special/cut_islands/spec.json").read_bytes())
    bucket = json.loads(bucket_source.data)["index_witness"]
    units = layout.units
    frame, = [r.rect for r in layout.records if r.layer == "BOUNDARY"]
    axes = []
    for dim, end, name in zip((0, 1), (frame.x1, frame.y1), ("width", "height")):
        first = units.nm_to_canonical(bucket["origin_nm"][dim])
        pitch = units.nm_to_canonical(bucket[f"index_cell_{name}_nm"])
        axes.append(Edges(first, pitch, -((first - end) // pitch)))
    cut_rows = []
    drawn_in_bucket = []
    effective = []
    for record in layout.records:
        if record.layer != "LI":
            continue
        for i, j, rect in cover(*axes, record.rect, 10000):
            drawn_in_bucket.append(dict(record_id=record.id.sha256, cell=[i, j], rect_dbu=rect.bounds))
        derived = result.value.for_record(record.id)
        for cid in derived.contributors:
            cutter = layout.record(cid)
            overlap = record.rect.intersection(cutter.rect)
            cut_rows.append(dict(drawn=origin(record), cut=origin(cutter), removed_dbu=overlap.bounds,
                                 area_nm2=overlap.area * units.canonical_tick_nm ** 2))
        for region in derived.regions:
            for piece in region.pieces:
                for i, j, rect in cover(*axes, piece.rect, 10000):
                    effective.append(dict(record_id=record.id.sha256, region=region.ref.sha256,
                                          piece=piece.ref.sha256, cut_ids=[c.sha256 for c in derived.contributors],
                                          cell=[i,j], rect_dbu=rect.bounds, area_nm2=rect.area * units.canonical_tick_nm ** 2))
    return dict(source="special/cut_islands/source.gds", top=layout.top, unit_ref=units.ref.sha256,
                captured={s.uri: s.sha256 for s in parsed.sources if s.uri in
                          ("source.gds", "tech/drawn.json", "tech/physical.json", "tech/formats.json",
                           "query/header.json", "body/context.json")},
                bucket_source=[bucket_source.uri, bucket_source.sha256, "/index_witness"],
                axes=[[a.first,a.pitch,a.cells] for a in axes], records=[origin(r) for r in layout.records],
                drawn_li=drawn_in_bucket, removed=cut_rows, effective=effective)


def drawn_li(layout, model, budget=10000):
    axes = axes_for(model, "LI", ("x", "y"))
    fragments = []
    for record in layout.records:
        if record.layer == "LI":
            for i, j, rect in cover(*axes, record.rect, budget - len(fragments)):
                fragments.append(dict(record_id=record.id.sha256, cell=[i,j], rect_dbu=rect.bounds))
    return fragments


def encoded(name, doc):
    return SourceFile(name, (json.dumps(doc, indent=2) + "\n").encode())


def variant(selection, candidate, edits, reselect=True):
    doc = json.loads(candidate.data)
    for path, value in edits:
        section, name, key = path.split("/")
        if value is None:
            del doc[section][name][key]
        else:
            doc[section][name][key] = value
    modified = encoded("candidate.json", doc)
    chosen = json.loads(selection.data)
    if reselect:
        chosen["sha256"] = modified.sha256
    return encoded("selection.json", chosen), modified


def legacy_status(layout, old_coordinate):
    projection = old_coordinate["coordinate_projection"]
    assert projection["example_only"] and not projection["is_complete_runtime_model"]
    rows = {}
    for p in layout.policies:
        if not p.projected:
            rows[p.name] = {"status": "projection_none"}
        else:
            rows[p.name] = {"status": "missing_axis", "layer_field": p.source.field,
                            "coverage_missing": ["x_edge", "y_edge"]}
            if p.declaration["tier"] == "A":
                rows[p.name]["track_missing"] = True
    return rows


def error_cases(sel, candidate, geometry, model):
    parsed = geometry.input.parse
    layout = geometry.layout
    cases = [
        ("missing_y", [("layers/LI/y", None)]),
        ("unknown_ref", [("layers/LI/y", "unknown")]),
        ("wrong_direction_ref", [("layers/LI/y", "li_x")]),
        ("zero_pitch", [("axes/li_x/pitch", 0)]),
        ("stale_selection", [("axes/li_y/offset", 1)]),
        ("shift_y_edge", [("axes/li_y/offset", 1)]),
        ("exchange_pitch_directions", [("axes/li_x/pitch", 10), ("axes/li_x/cells", 16),
                                       ("axes/li_y/pitch", 20), ("axes/li_y/cells", 10)]),
    ]
    rows = {}
    for name, edits in cases:
        chosen, current = variant(sel, candidate, edits, name != "stale_selection")
        def compute():
            rebound = bind(chosen, current, geometry)
            return drawn_li(layout, rebound)
        rows[name] = dict(edits=edits, candidate_sha256=current.sha256, selection_sha256=chosen.sha256,
                          selected_sha256=json.loads(chosen.data)["sha256"], result=attempt(compute))
    tracks, = axes_for(model, "FIN", ("track",))
    fin = next(r for r in layout.records if r.layer == "FIN")
    rect = fin.rect
    queries = []
    width_nm = parsed.value["tech"]["physical"]["fin_count_profile"]["fin_width_nm"]
    for dy in (0, 5, -1):
        moved = Rect(rect.x0, rect.y0 + dy, rect.x1, rect.y1 + dy)
        queries.append(dict(parent=origin(fin), synthetic_translation_dbu=[0, dy],
                            result=strip_location(moved, tracks, layout.units, width_nm)))
    return dict(shape_queries=queries, legacy={"coordinate": "tech/coordinate.json#/coordinate_projection",
                        "complete_model": "missing_axis", "drawn": len(layout.records),
                        "layers": legacy_status(layout, parsed.value["tech"]["coordinate"])}, candidate_layers=sorted(model),
                li_records=[origin(r) for r in layout.records if r.layer=="LI"],
                li_fragments=drawn_li(layout, model), variants=rows)


def resources(geometry, sel, candidate):
    parsed = geometry.input.parse
    layout = geometry.layout
    rows = []
    for label, edits in [
        ("selected", []),
        ("fine", [("axes/li_x/pitch", 1), ("axes/li_x/cells", 160), ("axes/li_y/pitch", 1),
                  ("axes/li_y/cells", 200)]),
        ("large_empty_extent", [("axes/li_x/cells", 10**9), ("axes/li_y/cells", 10**9)])]:
        chosen, current = variant(sel, candidate, edits)
        model = bind(chosen, current, geometry)
        x, y = axes_for(model, "LI", ("x", "y"))
        tracemalloc.start()
        start = perf_counter_ns()
        fragments = drawn_li(layout, model)
        occupied = len({tuple(f["cell"]) for f in fragments})
        elapsed = perf_counter_ns() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append(dict(case=label, edits=edits, sha256=current.sha256, possible_cells=x.cells*y.cells,
                         occupied=occupied, fragments=len(fragments), elapsed_ns=elapsed, python_peak_bytes=peak))
    fine = Edges(0,1,10**9)
    rejected = attempt(lambda: list(cover(fine, fine, Rect(0, 0, 10**9, 10**9), 10000)))
    return dict(python=sys.version, phase="drawn_li + distinct cell count; excludes acquisition/bind/IO",
                source_gds_bytes=len(next(s.data for s in parsed.sources if s.uri=="source.gds")),
                drawn_records=len(layout.records), li_records=sum(r.layer=="LI" for r in layout.records),
                rows=rows, stress_full_rectangle=rejected)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--resources", action="store_true")
    args = cli.parse_args()
    parsed, geometry = capture(FIXTURE)
    layout = geometry.layout
    sel = source("selection.json")
    target = load_document(sel)["uri"]
    if not isinstance(target, str) or Path(target).name != target or target in ("", ".", ".."):
        raise Issue("invalid_declaration", "/uri", target)
    candidate = source(target)
    model = bind(sel, candidate, geometry)
    if args.resources:
        report = resources(geometry, sel, candidate)
    else:
        counts = Counter(r.layer for r in layout.records)
        report = dict(selection_sha256=sel.sha256, candidate_sha256=candidate.sha256,
                      unit_ref=layout.units.ref.sha256, canonical_tick_nm=layout.units.canonical_tick_nm,
                      main_top=layout.top, layers={p.name: counts[p.name] for p in layout.policies},
                      w008=dict(algorithm=geometry.partition.algorithm, fragments=len(geometry.value.fragments),
                                occupied=len({f.cell for f in geometry.value.fragments})),
                      S1=fin_sample(layout, model, parsed.value["tech"]["physical"]["fin_count_profile"]), S2=math_sample(), S3=cut_sample(),
                      S4=error_cases(sel, candidate, geometry, model))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
