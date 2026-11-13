"""Independent W014 exact map closure and exception-history controls."""
from __future__ import annotations
import json
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.terminal_relations import validate_terminal_graph

results=[]
for shape in ('extra','list_backing','duplicate_keys','missing_backing','cycle'):
    row=FrozenMap({'kept':1})
    if shape=='extra':object.__setattr__(row,'extra',[])
    elif shape=='list_backing':object.__setattr__(row,'_entries',[('kept',1)])
    elif shape=='duplicate_keys':object.__setattr__(row,'_entries',(('kept',1),('kept',2)))
    elif shape=='missing_backing':object.__delattr__(row,'_entries')
    else:object.__setattr__(row,'_entries',(('cycle',row),))
    try:validate_terminal_graph(row)
    except ValueError as exc:results.append({'shape':shape,'rejected':True,'error':str(exc)})
    else:results.append({'shape':shape,'rejected':False})
assert all(row['rejected'] for row in results)
print(json.dumps({'results':results},indent=2))
