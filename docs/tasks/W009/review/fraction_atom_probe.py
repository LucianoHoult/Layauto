from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from collections.abc import Mapping
import json,hashlib
from layauto_v2.domain.codec import freeze,canonical_bytes
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry,geometry_from_parse_result,build_effective_geometry

class MutableInt(int):
    def __new__(cls,value):
        result=super().__new__(cls,value);result.items=[];return result
    @property
    def numerator(self): return self
    @property
    def denominator(self): return 1
    def __mul__(self,other):
        return self if other==1 else MutableInt(int(self)*int(other))
    def __rmul__(self,other): return self.__mul__(other)
    def __floordiv__(self,other):
        return self if other==1 else MutableInt(int(self)//int(other))

def mutable(value):
    if isinstance(value,Mapping): return {k:mutable(v) for k,v in value.items()}
    if type(value) is tuple:return [mutable(v) for v in value]
    return value
root=Path('/workspace/Layauto')
g=build_geometry(geometry_from_parse_result(read_inputs(root/'tests/fixtures/w003_m1/site_config.yaml')))
b=g.value
encoded=mutable(b.layout.units.encoded)
normal=encoded['user_units_per_tick']['exact']
n=MutableInt(normal.numerator);d=MutableInt(normal.denominator)
foreign=Fraction(n,d)
assert type(foreign) is Fraction and foreign==normal
copied=freeze(foreign)
assert copied.numerator is n and copied.denominator is d
encoded['user_units_per_tick']['exact']=foreign
unit=replace(b.layout.units,encoded=encoded)
layout=replace(b.layout,units=unit)
partition=replace(b.partition,layout=layout)
base=replace(b,partition=partition)
borrowed=replace(g,value=base)
result={'standalone_exact_fraction_retains_mutable_integer_alias':True,'same_wire':canonical_bytes(foreign)==canonical_bytes(normal)}
try:
    new=build_effective_geometry(borrowed)
except ValueError as exc:
    result.update({'new_boundary':'rejected','reason':str(exc)})
else:
    n.items.append('caller mutation')
    actual=new.value.base.layout.units.encoded['user_units_per_tick']['exact']
    result.update({'new_boundary':new.status,'numerator_alias':actual.numerator is n,'numerator_items':actual.numerator.items})
result['source_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ('layauto_v2/domain/regions.py','layauto_v2/state/regions.py','layauto_v2/normalization/effective.py')}
print(json.dumps(result,indent=2))
