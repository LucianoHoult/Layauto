"""Minimal W009 CR-01 residual: a valid nested base hides an algorithm fault.

Run at checkout root: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B <this-file>
This intentionally observes the defect and never changes product/fixture files.
"""
import json
from pathlib import Path
from unittest.mock import patch

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.effective_codec import decode_record, encode_record


result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))))
assert result.status == 'success'
observations = []
for enclosing, value in (('draft', result.value), ('result', result)):
    wire = encode_record(value)  # Valid wire, prepared before fault injection.
    failure = TypeError('unexpected internal occupancy reconstruction failure')

    def fail(*args, **kwargs):
        raise failure

    with patch('layauto_v2.state.occupancy._fragments', fail):
        try:
            decode_record(wire)
        except BaseException as observed:
            observations.append({'enclosing': enclosing, 'observed': type(observed).__name__,
                                 'message': str(observed), 'same_object': observed is failure,
                                 'cause_same_object': observed.__cause__ is failure})
        else:
            raise AssertionError('injected failure unexpectedly succeeded')
print(json.dumps(observations, indent=2))
