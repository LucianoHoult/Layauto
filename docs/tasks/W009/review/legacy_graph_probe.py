from dataclasses import replace
from pathlib import Path
import hashlib, json
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry, geometry_from_parse_result, build_effective_geometry
from layauto_v2.state.regions import build_effective_draft

class Forward:
    def __init__(self, value):
        self.value=value
        self.items=[]
    def __getattr__(self, key): return getattr(self.value,key)
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def to_value(self): return self.value.to_value()
class Switch(list):
    def __init__(self, values):
        super().__init__(values); self.calls=0
    def __iter__(self):
        self.calls+=1
        values=list.__iter__(self)
        return values if self.calls==1 else iter([Forward(v) for v in values])

root=Path('/workspace/Layauto')
g=build_geometry(geometry_from_parse_result(read_inputs(root/'tests/fixtures/w003_m1/site_config.yaml')))
r=build_effective_geometry(g); b=g.value
observations=[]
for name in ('records','policies','layers','fragments'):
    if name in ('records','policies'):
        layout=replace(b.layout,**{name:Switch(getattr(b.layout,name))})
        part=replace(b.partition,layout=layout)
        foreign=replace(b,partition=part)
    elif name=='layers':
        part=replace(b.partition,layers=Switch(b.partition.layers))
        foreign=replace(b,partition=part)
    else:
        foreign=replace(b,fragments=Switch(b.fragments))
    vectors={'records':foreign.layout.records,'policies':foreign.layout.policies,'layers':foreign.partition.layers,'fragments':foreign.fragments}
    assert type(vectors[name][0]) is Forward, (name,type(vectors[name][0]))
    borrowed=replace(g,value=foreign)
    outcome={'case':name,'legacy_constructor_accepted':True}
    for entry,fn in [('state',lambda:build_effective_draft(foreign,r.value.physical)),
                     ('draft_constructor',lambda:replace(r.value,base=foreign)),
                     ('public_builder',lambda:build_effective_geometry(borrowed))]:
        try: fn()
        except ValueError: outcome[entry]='rejected'
        else: outcome[entry]='ACCEPTED'
    observations.append(outcome)
value={'source_sha256':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ('layauto_v2/domain/regions.py','layauto_v2/state/regions.py','layauto_v2/normalization/effective.py')},'observations':observations}
print(json.dumps(value,indent=2))
