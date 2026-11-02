"""Regression checks for the W004 fixture helper, not product body extraction.

Run with: python -B -m unittest discover -s tests/fixture_support -v
The fixed spec/oracle identify unchanged local objects; these tests exercise
helper behavior and do not replace the independent geometric fixture audit.
"""

from fractions import Fraction
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests/fixtures/w003_m1"
# The fixture support scripts use sibling imports and are not a runtime package.
sys.path.insert(0, str(REPO / "tests/support"))
try:
    from w004_body import check_body
    from w004_query import normalize
    from w004_support import bind_header, bindings, load_tech, read, write
finally:
    sys.path.pop(0)


class W004BodyFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w004-body-regression-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.shapes = {s["id"]: s for s in read(FIXTURE / "spec.json")["shapes"]}
        self.oracle = read(FIXTURE / "oracle.json")

    def copy_fixture(self, name):
        root = self.work / name
        shutil.copytree(FIXTURE, root, ignore=shutil.ignore_patterns("failures"))
        return root

    def check(self, root):
        return check_body(root, self.shapes, load_tech(root), self.oracle["semantic"])

    def test_normal_body_associations(self):
        bindings(FIXTURE)
        result = self.check(FIXTURE)
        self.assertEqual(len(result), 2)
        for actual, expected in zip(result, self.oracle["body_associations"]):
            for key in (
                "device", "local_body", "semantic_rail", "body_edge_length_nm",
                "rail_edge_length_nm", "tap_body_enclosure_nm", "tap_rail_enclosure_nm",
            ):
                self.assertEqual(actual[key], expected[key], key)
            self.assertEqual(actual["local_rail"], expected["context_path"][-1])
            self.assertIs(actual["local_graph_union"], False)

    def test_existing_body_failures_keep_their_specific_cause(self):
        ids = {
            "missing_body_operator", "missing_body_context", "body_wrong_binding",
            "body_wrong_type", "body_disconnected", "body_ambiguous",
            "body_enclosure", "body_wrong_rail",
        }
        cases = [c for c in read(FIXTURE / "failures/cases.json")["cases"]
                 if c["id"] in ids]
        self.assertEqual({c["id"] for c in cases}, ids)
        for case in cases:
            with self.subTest(case=case["id"]):
                root = self.copy_fixture(case["id"])
                for dest, source in case["replacement_files"].items():
                    shutil.copyfile(FIXTURE / "failures" / source, root / dest)
                for removed in case["remove_files"]:
                    (root / removed).unlink()
                bindings(root, allow_missing_context=not (root / "body/context.json").exists())
                self.assertEqual((root / "source.gds").read_bytes(),
                                 (FIXTURE / "source.gds").read_bytes())
                with self.assertRaises(AssertionError) as failure:
                    self.check(root)
                self.assertEqual(str(failure.exception), case["expected_issue"])

    def test_fractional_raw_rail_does_not_match_integer_local_rail(self):
        root = self.copy_fixture("fractional-rail")
        raw = root / "query/raw/net_shapes_n_lo.txt"
        original = raw.read_text()
        old_vertices = "1160 900\n960 900"
        self.assertEqual(original.count(old_vertices), 1)
        raw.write_text(original.replace(old_vertices, "1160 901\n960 901"))
        write(root / "query/header.json", bind_header(root, read(root / "query/header.json")))
        normalized = normalize(root, "net_regions")
        write(root / "query/normalized/net_regions.yaml", normalized)

        # Prove that neither a stale hash/cache nor changed local geometry is
        # the rejection cause. Only the exact raw rail edge has moved 0.05 nm.
        bindings(root)
        self.assertEqual(read(root / "query/normalized/net_regions.yaml"),
                         normalize(root, "net_regions"))
        for unchanged in ("source.gds", "source.cdl", "body/context.json"):
            self.assertEqual((root / unchanged).read_bytes(),
                             (FIXTURE / unchanged).read_bytes())
        row = next(r for r in normalized["records"]
                   if r["derived_layer"] == "toy_m1" and r["schematic_name"] == "VSS")
        bbox = [Fraction(int(row["bbox_nm"][k]["numerator"]),
                         int(row["bbox_nm"][k]["denominator"]))
                for k in ("x_min", "y_min", "x_max", "y_max")]
        self.assertEqual(bbox, [0, 48, Fraction(901, 20), 58])
        self.assertEqual(self.shapes["MN"]["bbox"], [0, 48, 45, 58])
        with self.assertRaisesRegex(AssertionError, "^BodyTargetRailMismatch$"):
            self.check(root)


if __name__ == "__main__":
    unittest.main()
