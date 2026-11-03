"""Independent review probe: an impossible first-acquisition GDS URI is accepted."""
from dataclasses import replace
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.normalization import from_parse_result
from layauto_v2.normalization.geometry_input import geometry_from_parse_result
from layauto_v2.normalization.geometry import build_geometry
from w005_cases import FIXTURE
from w007_cases import read, mutable

parsed = read(FIXTURE)
original = next(record for record in parsed.completed if record.kind == 'gds')
source = next(item for item in parsed.sources if item.uri == original.sources[0].uri)
sibling = SourceFile('another-role.gds', source.data)
value = mutable(parsed.value)
value['gds']['source']['uri'] = sibling.uri
completed = []
for record in parsed.completed:
    if record.kind == 'gds':
        record = replace(record, payload=value['gds'], sources=(sibling.ref(),))
    if record.kind == 'body':
        record = replace(record, sources=(record.sources[0], sibling.ref()))
    completed.append(record)
forged = replace(parsed, value=value, completed=tuple(completed),
                 sources=tuple(item for item in parsed.sources if item is not source) + (sibling,))
print('site selected:', forged.value['config']['inputs']['gds'])
print('captured GDS role:', sibling.uri)
print('original URI present:', source.uri in {item.uri for item in forged.sources})
print('semantic accepts:', type(from_parse_result(forged)).__name__)
result = build_geometry(geometry_from_parse_result(forged))
print('geometry result:', result.status, 'records:', len(result.layout.records))
assert result.status == 'success'
