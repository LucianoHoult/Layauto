from pathlib import Path
import hashlib
import json
import subprocess
from unittest.mock import patch
from types import SimpleNamespace
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective_codec import encode_record, decode_record
root = Path.cwd()
parsed = read_inputs(root / 'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'
result = build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
assert result.status == 'success'
wire = encode_record(result)
wire_sha = hashlib.sha256(wire).hexdigest()
failure = TypeError('captured SourceFile hash calculation failed internally')
def broken(*args, **kwargs):
    raise failure
with patch('layauto_v2.domain.evidence.hashlib', SimpleNamespace(sha256=broken)):
    try:
        decode_record(wire)
    except BaseException as observed:
        answer = {'observed':type(observed).__name__, 'message':str(observed), 'same_object':observed is failure,
                  'cause_is_failure':observed.__cause__ is failure}
    else:
        raise AssertionError('unexpected success')
print(json.dumps({'head':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                  'wire_sha256':wire_sha, **answer}, indent=2))
