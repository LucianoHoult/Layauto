"""Review probe: distinguish standalone neutral unit consistency from capture auth."""
import json
import sys
from dataclasses import replace
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.geometry_codec import decode_record, encode_record

parsed = read_inputs(root / "tests/fixtures/w003_m1/site_config.yaml")
accepted = build_geometry(geometry_from_parse_result(parsed))
unit = accepted.value.layout.units
encoded = dict(unit.encoded)
item = dict(encoded["metres_per_tick"])
item["raw"] = b"\0" * 8
encoded["metres_per_tick"] = item
neutral = replace(unit, encoded=encoded)
clone = decode_record(encode_record(neutral))
assert clone == neutral
assert neutral.encoded["metres_per_tick"]["exact"] > 0
assert neutral.encoded["metres_per_tick"]["raw"] == b"\0" * 8
aggregate_rejected = False
try:
    replace(accepted.value.layout, units=neutral)
except ValueError:
    aggregate_rejected = True
assert aggregate_rejected
print(json.dumps({"standalone_neutral_accepts_zero_real8_with_positive_exact": True,
                  "standalone_codec_roundtrip": True,
                  "bound_layout_rejects_unit_substitution": aggregate_rejected,
                  "exact_claim": str(neutral.encoded["metres_per_tick"]["exact"]),
                  "scope": "neutral DTO only; does not demonstrate false successful aggregate"}, indent=2))
