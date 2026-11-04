"""Independent CR-02 two-pass container and borrowed-base element probes."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import layauto_v2
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry
from layauto_v2.normalization.effective_codec import encode_record


class Foreign:
    def __init__(self, original):
        self.original = original
        self.items = []

    def __getattr__(self, name):
        return getattr(self.original, name)

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash(self.original)


class ChangingList(list):
    def __init__(self, original, changed):
        super().__init__(original)
        self.changed = changed
        self.calls = 0

    def __iter__(self):
        self.calls += 1
        return list.__iter__(self) if self.calls == 1 else iter(self.changed)


result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))))
draft = result.value
row = next(row for row in draft.records if row.operation == 'terminal')
row_index = draft.records.index(row)
region = row.regions[0]
base = draft.base
observations = []
for where in ('draft_records', 'row_regions', 'region_rectangles', 'region_contributors',
              'base_records', 'base_policies', 'base_layers', 'base_fragments'):
    try:
        if where == 'draft_records':
            foreign = Foreign(draft.records[0])
            changed_draft = replace(draft, records=ChangingList(draft.records, (foreign,) + draft.records[1:]))
            selected = changed_draft.records[0]
        elif where == 'row_regions':
            foreign = Foreign(region)
            changed_row = replace(row, regions=ChangingList(row.regions, (foreign,) + row.regions[1:]))
            changed_draft = replace(draft, records=draft.records[:row_index] + (changed_row,) + draft.records[row_index + 1:])
            selected = changed_draft.records[row_index].regions[0]
        elif where in ('region_rectangles', 'region_contributors'):
            name = where.removeprefix('region_')
            values = getattr(region, name)
            foreign = Foreign(values[0])
            changed_region = replace(region, **{name: ChangingList(values, (foreign,) + values[1:])})
            changed_row = replace(row, regions=(changed_region,) + row.regions[1:])
            changed_draft = replace(draft, records=draft.records[:row_index] + (changed_row,) + draft.records[row_index + 1:])
            selected = getattr(changed_draft.records[row_index].regions[0], name)[0]
        else:
            if where == 'base_records':
                values = base.layout.records
                foreign = Foreign(values[0])
                layout = replace(base.layout, records=ChangingList(values, (foreign,) + values[1:]))
                changed_base = replace(base, partition=replace(base.partition, layout=layout))
                selected = changed_base.layout.records[0]
            elif where == 'base_policies':
                values = base.layout.policies
                foreign = Foreign(values[0])
                layout = replace(base.layout, policies=ChangingList(values, (foreign,) + values[1:]))
                changed_base = replace(base, partition=replace(base.partition, layout=layout))
                selected = changed_base.layout.policies[0]
            elif where == 'base_layers':
                values = base.partition.layers
                foreign = Foreign(values[0])
                partition = replace(base.partition, layers=ChangingList(values, (foreign,) + values[1:]))
                changed_base = replace(base, partition=partition)
                selected = changed_base.partition.layers[0]
            else:
                values = base.fragments
                foreign = Foreign(values[0])
                changed_base = replace(base, fragments=ChangingList(values, (foreign,) + values[1:]))
                selected = changed_base.fragments[0]
            changed_draft = replace(draft, base=changed_base)
        changed_result = replace(result, value=changed_draft)
    except ValueError:
        status = 'rejected'
    else:
        foreign.items.append('caller mutation')
        if selected is foreign:
            status = 'success retains mutable foreign DTO'
        else:
            encode_record(changed_result)
            status = 'safe immutable snapshot'
    observations.append({'case': where, 'status': status})
paths = ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
         'layauto_v2/normalization/effective.py')
print(json.dumps({'package': layauto_v2.__file__,
                  'source_sha256': {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths},
                  'observations': observations,
                  'closed': all(row['status'] in ('rejected', 'safe immutable snapshot') for row in observations)}, indent=2))
