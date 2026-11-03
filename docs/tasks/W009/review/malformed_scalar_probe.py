"""Replay the reviewer's 132 closed-wire scalar replacement checks."""
from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

from layauto_v2.importers import read_inputs
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from layauto_v2.normalization.effective import build_effective_geometry
from layauto_v2.normalization.effective_codec import encode_record, decode_record
from layauto_v2.domain.codec import canonical_bytes, decode


def mutable(value):
    if isinstance(value, Mapping):
        return {key: mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable(item) for item in value]
    return value


result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))))
draft = result.value
row = draft.records[0]
region = row.regions[0]
values = [draft.operators, draft, row, region, region.pieces[0], region.ref, result]
rows = []
for value in values:
    original = mutable(decode(encode_record(value)))
    for field in original['record']['fields']:
        for scalar in (None, True, 17, 'foreign'):
            tree = mutable(decode(encode_record(value)))
            tree['record']['fields'][field] = {'scalar': scalar}
            try:
                decode_record(canonical_bytes(tree))
            except ValueError:
                status = 'rejected'
            except BaseException as exc:
                status = type(exc).__name__
            else:
                status = 'accepted'
            rows.append((type(value).__name__, field, repr(scalar), status))
print(json.dumps({'checks': len(rows), 'outcomes': rows}, indent=2))
