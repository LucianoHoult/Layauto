"""FR2 residual: coherent geometry + metadata permutation cannot change captured requests."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
REPOSITORY = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPOSITORY))
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize

def mutable(value):
    if isinstance(value, FrozenMap):
        return {key: mutable(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [mutable(child) for child in value]
    return value

parsed = read_inputs(REPOSITORY / 'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status == 'success'
value = mutable(parsed.value)
query = value['query']
rows = query['device_regions']['records']
first, second = deepcopy(rows)
identity_fields = {'record_id', 'layout_instance', 'schematic_instance', 'field_sources'}
for destination, geometry in ((rows[0], second), (rows[1], first)):
    for name, item in geometry.items():
        if name not in identity_fields:
            destination[name] = item
    for name, item in geometry['field_sources'].items():
        if name not in identity_fields:
            destination['field_sources'][name] = item
responses = query['_format_metadata']['responses']
responses[0], responses[1] = responses[1], responses[0]
changed = replace(parsed, value=value, completed=tuple(
    replace(record, payload=query) if record.kind == 'query' else record
    for record in parsed.completed))
assert changed.sources == parsed.sources
print('captured_sources_unchanged', changed.sources == parsed.sources)
print('request_object_pointers_unchanged', [row['field_sources']['layout_instance']['sources'][0]['json_pointer'] for row in rows])
try:
    result = normalize(from_parse_result(changed))
except ValueError as error:
    print('REJECT', str(error))
else:
    print('ACCEPTED', result.status)
    for seed in result.completed.device_seeds:
        point = seed.record['vertices_nm'][0]
        print(seed.semantic_id.name, 'first_y', point['y']['numerator'] + '/' + point['y']['denominator'])
