"""Primary reviewer's independent minimal reproduction of IPMR-01.

Exit 0 means the reviewed defect was reproduced, not that the contract passed.
Run from the repository root with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective_codec import encode_record, decode_record
import layauto_v2.state.occupancy as occupancy

root = Path.cwd()
result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(root / "tests/fixtures/w003_m1/site_config.yaml"))))
assert result.status == "success"
wire = encode_record(result.value)
sentinel = TypeError("IPMR-01 primary reviewer nested base sentinel")
def fail(*args, **kwargs):
    raise sentinel
with patch.object(occupancy, "_fragments", fail):
    try:
        decode_record(wire)
    except BaseException as error:
        observation = dict(actual_type=type(error).__name__, actual_message=str(error),
                           same_object=error is sentinel, cause_same_object=error.__cause__ is sentinel)
    else:
        raise AssertionError("injected algorithm failure was not reached")
assert observation == dict(actual_type="ValueError", actual_message="invalid geometry wire fields",
                           same_object=False, cause_same_object=True)
paths = ["layauto_v2/normalization/effective_codec.py", "layauto_v2/normalization/geometry_codec.py",
         "layauto_v2/state/occupancy.py"]
receipt = dict(head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               executable=sys.executable, python=sys.version, cwd=str(root), wire_sha256=hashlib.sha256(wire).hexdigest(),
               expected="the exact injected TypeError object must escape effective decode",
               observation=observation, source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
               conclusion="IPMR-01 reproduced; contract failed")
print(json.dumps(receipt, indent=2))
