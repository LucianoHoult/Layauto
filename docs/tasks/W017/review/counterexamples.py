"""Rebind independent candidate copies in memory, then exercise the proposal."""
from fractions import Fraction
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from run import FIXTURE, capture, source
from model import Issue, axes_for, bind, cover
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.geometry import Rect


def expect_issue(call, status, field):
    try:
        call()
    except Issue as exc:
        assert (exc.detail["status"], exc.detail["field"]) == (status, field), exc.detail
        return
    raise AssertionError(("missing diagnostic", status, field))


def review():
    _, geometry = capture(FIXTURE)
    original, selection = source("candidate.json"), source("selection.json")
    grid = bind(selection, original, geometry)
    track, = axes_for(grid, "FIN", ("track",))
    for value in (30.1, True):
        expect_issue(lambda: track.locate(value), "invalid_query", "y_nm")
    assert track.locate(Fraction(301, 10))["adjacent"] == [
        {"index": 0, "delta_nm": "51/10"}, {"index": 1, "delta_nm": "-49/10"}]
    assert track.locate(Fraction(19501, 100))["status"] == "outside_range"
    expect_issue(lambda: track.centre(True), "invalid_query", "index")
    expect_issue(lambda: track.centre(18), "outside_range", "index")
    print("R1 float/bool, rational neighbours and track extent passed")

    for field, value, location in [
        ("axes", [], "/axes"),
        ("axes", {"broken": None}, "/axes/broken"),
        ("layers", [], "/layers"),
        ("layers", {"LI": {"y": "absent"}}, "/layers/LI/y"),
        ("layers", {"LI": {"x": "li_y"}}, "/layers/LI/x"),
        ("layers", {"BOUNDARY": {"x": "li_x"}}, "/layers/BOUNDARY"),
    ]:
        altered = json.loads(original.data)
        altered[field] = value
        supplied = SourceFile(original.uri, json.dumps(altered).encode())
        updated = json.loads(selection.data)
        updated["sha256"] = supplied.sha256
        chosen = SourceFile(selection.uri, json.dumps(updated).encode())
        expect_issue(lambda: bind(chosen, supplied, geometry), "invalid_declaration", location)
        expect_issue(lambda: bind(selection, supplied, geometry), "invalid_declaration", "/sha256")
    print("R2 malformed containers/refs and stale selection passed")

    x, y = axes_for(grid, "LI", ("x", "y"))
    # Cumulative budget, max-exclusive endpoint, and partly out of bounds.
    assert len(list(cover(x, y, Rect(140, 190, 160, 200), 1))) == 1
    expect_issue(lambda: list(cover(x, y, Rect(140, 190, 161, 200), 100)), "outside_range", "x")
    expect_issue(lambda: list(cover(x, y, Rect(139, 190, 160, 200), 1)), "resource_limit", "fragments")
    expect_issue(lambda: axes_for(grid, "VIA0", ("x", "y")), "missing_axis", "/layers/VIA0/x")
    print("Exact outer edge, partial overrun, fragment cap, absent via axis passed")


if __name__ == "__main__":
    review()
