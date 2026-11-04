import json
from dataclasses import replace
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry, build_effective_geometry
from layauto_v2.state.regions import build_effective_draft
from layauto_v2.domain.codec import freeze_map, canonical_bytes

class TextMeta(type):
    def __eq__(cls, other): return True
    def __ne__(cls, other): return False
    __hash__ = type.__hash__
class Text(str, metaclass=TextMeta): pass

def mutable(value):
    from collections.abc import Mapping
    if isinstance(value, Mapping): return {k:mutable(v) for k,v in value.items()}
    if isinstance(value, tuple): return [mutable(v) for v in value]
    return value

r=build_effective_geometry(build_geometry(geometry_from_parse_result(read_inputs(Path('/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml')))))
p=r.value.physical
v=mutable(p.payload)
s=Text(v['device_extraction_contract']['body_operator']); s.items=[]
v['device_extraction_contract']['body_operator']=s
bad=replace(p,payload=v)
assert bad.payload['device_extraction_contract']['body_operator'] is s
b=build_effective_draft(r.value.base,bad)
out=replace(r,value=b)
s.items.append('caller mutation')
kept=out.value.physical.payload['device_extraction_contract']['body_operator']
print(json.dumps({'status':out.status,'is_alias':kept is s,'items':kept.items,'canonical_equal':canonical_bytes(p.payload)==canonical_bytes(bad.payload)}))
