"""Independent CR-02 constructor alias check; run from the repository root."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry
from layauto_v2.domain.regions import RegionRef


class MutableLiteral:
    def __init__(self):
        self.items = []

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


paths = ('layauto_v2/domain/regions.py', 'layauto_v2/normalization/effective.py')
sources = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}
literal = MutableLiteral()
observations = {}
try:
    reference = RegionRef(literal, 'a' * 64)
except ValueError:
    observations['ref_kind'] = 'rejected'
else:
    observations['ref_kind'] = 'accepted mutable alias' if reference.kind is literal else 'accepted'
result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))))
draft = result.value
row = draft.records[0]
region = row.regions[0]
try:
    changed = replace(region, role=literal)
    changed_row = replace(row, regions=(changed,) + row.regions[1:])
    changed_draft = replace(draft, records=(changed_row,) + draft.records[1:])
    changed_result = replace(result, value=changed_draft)
except ValueError:
    observations['success_region_role'] = 'rejected'
else:
    literal.items.append('caller mutation')
    observations['success_region_role'] = ('success retains mutable caller alias'
        if changed_result.value.records[0].regions[0].role.items == ['caller mutation'] else 'accepted')
print(json.dumps({'source_sha256': sources, 'observations': observations}, indent=2))
