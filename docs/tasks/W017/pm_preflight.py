"""Read the accepted fixture and exercise existing geometry math for W017 planning."""
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from layauto_v2.domain.geometry import Rect
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result
from layauto_v2.state.coordinate import LayerPartition


def main():
    site = ROOT / "tests/fixtures/w003_m1/site_config.yaml"
    parsed = read_inputs(site)
    assert parsed.status == "success", parsed.issues
    result = build_geometry(geometry_from_parse_result(parsed))
    assert result.status == "success", result.issues
    layout = result.layout
    tech = parsed.value["tech"]
    profile = tech["physical"]["fin_count_profile"]
    fin_records = [record for record in layout.records if record.layer == "FIN"]
    centres = []
    for record in fin_records:
        lower = layout.units.canonical_to_nm(record.rect.y0)
        upper = layout.units.canonical_to_nm(record.rect.y1)
        assert upper - lower == profile["fin_width_nm"]
        centres.append((lower + upper) / 2)
    phase = profile["fin_lower_edge_offset_nm"] + Fraction(profile["fin_width_nm"], 2)
    expected = [phase + k * profile["fin_pitch_nm"] for k in range(18)]
    assert sorted(centres) == expected
    assert (expected[0], expected[1], expected[-1]) == (25, 35, 195)
    poly_count = sum(record.layer == "POLY" for record in layout.records)
    assert poly_count == 1
    coordinate = tech["coordinate"]["coordinate_projection"]
    assert coordinate["example_only"] and not coordinate["is_complete_runtime_model"]

    # Explicit example in integer DBU. Axis entries here are cell boundaries.
    sample = LayerPartition("math-example", (-6, 4, 14), (-3, 1, 5))
    pieces = sample.project(Rect(-2, -1, 6, 3))
    bounds = sorted((i, j, part.bounds) for i, j, part in pieces)
    assert bounds == [(0, 0, (-2, -1, 4, 1)), (0, 1, (-2, 1, 4, 3)),
                      (1, 0, (4, -1, 6, 1)), (1, 1, (4, 1, 6, 3))]
    assert sample.point_to_index(4, 1) == (1, 1)
    assert sample.point_to_index(Fraction(7, 2), Fraction(1, 2)) == (0, 0)
    assert len(sample.project(Rect(-2, -1, 4, 1))) == 1

    print(json.dumps({
        "top": layout.top,
        "drawn_records": len(layout.records),
        "declared_layers": len(layout.policies),
        "fin_centres_nm": [str(c) for c in sorted(centres)],
        "poly_records": poly_count,
        "coordinate_id": coordinate["id"],
        "complete_runtime_model": coordinate["is_complete_runtime_model"],
        "w008_partition": result.partition.algorithm,
        "example_xy_intersections_dbu": bounds,
    }, indent=2))


if __name__ == "__main__":
    main()
