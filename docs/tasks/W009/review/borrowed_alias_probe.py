"""Independent CR-02 retained-value checks through valid legacy constructors."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry
from layauto_v2.state.regions import build_effective_draft


class MutableText(str):
    pass


def text(value):
    result = MutableText(value)
    result.items = []
    return result


result = build_effective_geometry(build_geometry(geometry_from_parse_result(
    read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))))
observations = []


def reject(label, call):
    try:
        call()
    except ValueError:
        observations.append({'case': label, 'status': 'rejected'})
    else:
        observations.append({'case': label, 'status': 'accepted'})


for where in ('geometry_schema', 'geometry_status', 'base_schema', 'fragment_schema',
              'geometry_input_schema', 'semantic_input_schema'):
    geometry = result.input
    if where == 'geometry_schema':
        geometry = replace(geometry, schema_version=text(geometry.schema_version))
    elif where == 'geometry_status':
        geometry = replace(geometry, status=text(geometry.status))
    elif where == 'base_schema':
        geometry = replace(geometry, value=replace(geometry.value, schema_version=text(geometry.value.schema_version)))
    elif where == 'fragment_schema':
        base = geometry.value
        fragment = base.fragments[0]
        geometry = replace(geometry, value=replace(base, fragments=(
            replace(fragment, schema_version=text(fragment.schema_version)),) + base.fragments[1:]))
    elif where == 'geometry_input_schema':
        geometry = replace(geometry, input=replace(geometry.input, schema_version=text(geometry.input.schema_version)))
    else:
        semantic = geometry.input.semantic_input
        geometry = replace(geometry, input=replace(geometry.input, semantic_input=replace(
            semantic, schema_version=text(semantic.schema_version))))
    reject(where + '/builder', lambda: build_effective_geometry(geometry))
    reject(where + '/result', lambda: replace(result, input=geometry))
    if where in ('base_schema', 'fragment_schema'):
        reject(where + '/state_builder', lambda: build_effective_draft(geometry.value, result.value.physical))
        reject(where + '/draft_constructor', lambda: replace(result.value, base=geometry.value))
for field in ('kind', 'parser_version', 'schema_version', 'source_uri'):
    original = result.completed[0]
    if field == 'source_uri':
        changed = replace(original, sources=(replace(original.sources[0], uri=text(original.sources[0].uri)),)
                          + original.sources[1:])
    else:
        changed = replace(original, **{field: text(getattr(original, field))})
    reject('completed/' + field, lambda: replace(result, completed=(changed,) + result.completed[1:]))
    original = result.value.operators.physical
    if field == 'source_uri':
        changed = replace(original, sources=(replace(original.sources[0], uri=text(original.sources[0].uri)),))
    else:
        changed = replace(original, **{field: text(getattr(original, field))})
    reject('binding/' + field, lambda: replace(result.value.operators, physical=changed))
paths = ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
         'layauto_v2/normalization/effective.py')
print(json.dumps({'source_sha256': {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths},
                  'observations': observations,
                  'all_rejected': all(row['status'] == 'rejected' for row in observations)}, indent=2))
