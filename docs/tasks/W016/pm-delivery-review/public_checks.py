"""PM check of normal no-body analysis and independent input diagnostics."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "tests/support")]
from analysis_inputs import load, materialize, rebind, write
from layauto_v2.analysis import AnalysisRequest, analyze_cell


def observe(root, name, *, pin_error=False, geometry_error=False):
    manifest = materialize(root)
    if pin_error:
        cdl = root / "source.cdl"
        original = cdl.read_text()
        pins = ".SUBCKT INV_M1_SYNTH A Y VSS VDD"
        assert original.count(pins) == 1
        cdl.write_text(original.replace(pins, ".SUBCKT INV_M1_SYNTH A Y VSS"))
    if geometry_error:
        formats = root / "tech/formats.json"
        data = load(formats)
        data["geometry_capability"]["comparator"] = "hypothetical_topology_comparator/9"
        write(formats, data)
    rebind(root)
    result = analyze_cell(AnalysisRequest(manifest))
    facts = {"case": name, "request_status": result.request_status,
             "findings": [{"code": f.code, "uri": f.source.uri, "field": f.source.field} for f in result.findings]}
    if name == "normal":
        local = result.local
        assert local is not None
        terms = local.facets.terminals.value
        facts["fin"] = [m.count for m in local.facets.channel_fin.value.measurements]
        facts["equal_dgs"] = sum(t.expected.role != "B" and t.comparison == "equal" for t in terms)
        facts["indeterminate_body"] = sum(t.expected.role == "B" and t.comparison == "indeterminate" for t in terms)
        facts["parent"] = result.parent_global
        assert (result.request_status, sorted(facts["fin"]), facts["equal_dgs"],
                facts["indeterminate_body"], facts["parent"]) == ("completed", [5, 7], 6, 2, "unknown")
    return facts


if __name__ == "__main__":
    with TemporaryDirectory() as temp:
        root = Path(temp)
        cases = [
            observe(root/"normal", "normal"),
            observe(root/"pin", "pin_only", pin_error=True),
            observe(root/"geometry", "geometry_only", geometry_error=True),
            observe(root/"both", "both", pin_error=True, geometry_error=True),
        ]
    print(json.dumps(cases, indent=2))
    assert cases[1]["request_status"] == "rejected"
    assert cases[2]["request_status"] == "unsupported"
    expected_codes = {"SourceTopIdentityMismatch", "UnsupportedGeometryComparator"}
    assert cases[3]["request_status"] == "rejected" and expected_codes <= {f["code"] for f in cases[3]["findings"]}, "combined request must retain both independent findings and be rejected"
