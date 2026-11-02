"""CR-01-FR2: seed geometry must remain bound to its own request object."""
from pathlib import Path
import sys
from dataclasses import replace
from copy import deepcopy
REPOSITORY = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPOSITORY))
from layauto_v2.importers import read_inputs
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.normalization import from_parse_result, normalize

def mutable(value):
    if isinstance(value, FrozenMap):
        return {key: mutable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable(item) for item in value]
    return value

parsed = read_inputs(REPOSITORY / 'tests/fixtures/w003_m1/site_config.yaml')
value = mutable(parsed.value)
first, second = value['query']['device_regions']['records']
original_first, original_second = deepcopy(first), deepcopy(second)
geometry_fields = set(first) - {'record_id', 'layout_instance', 'schematic_instance', 'field_sources'}
for destination, donor in ((first, original_second), (second, original_first)):
    for field in geometry_fields:
        destination[field] = donor[field]
        destination['field_sources'][field] = donor['field_sources'][field]
changed = replace(parsed, value=value, completed=tuple(
    replace(record, payload=value['query']) if record.kind == 'query' else record
    for record in parsed.completed))
try:
    result = normalize(from_parse_result(changed))
    print('complete geometry/provenance groups swapped between device request objects:', result.status)
    print([(seed.query_key.identity, seed.record['bbox_nm']['y_min']) for seed in result.completed.device_seeds])
except Exception as exc:
    print(type(exc).__name__, str(exc))
