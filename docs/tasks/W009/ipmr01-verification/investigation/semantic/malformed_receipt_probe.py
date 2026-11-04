from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from collections.abc import Mapping
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result

def mutable(value):
    if isinstance(value, Mapping): return {k:mutable(v) for k,v in value.items()}
    if isinstance(value, tuple): return [mutable(v) for v in value]
    return value
root=Path.cwd()
parsed=read_inputs(root/'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status=='success'
original=mutable(parsed.value)
paths=[]
def walk(value,path):
    if len(path)>5:return
    if isinstance(value,dict):
        for key,child in value.items():
            paths.append(path+[key]);walk(child,path+[key])
    elif isinstance(value,list) and value:
        walk(value[0],path+[0])
for key in ('tech','source_cdl','target_cdl','query','header'):
    walk(original[key],[key])
observations=[]
for path in paths:
    for mutation in ('missing','collection'):
        value=deepcopy(original)
        parent=value
        for key in path[:-1]:parent=parent[key]
        if mutation=='missing':del parent[path[-1]]
        else:parent[path[-1]]={}
        try:
            completed=tuple(replace(record,payload=({'bundle':value['tech_bundle'],'owners':value['tech']}
                if record.kind=='tech' else value[record.kind])) for record in parsed.completed)
            from_parse_result(replace(parsed,value=value,completed=completed))
        except BaseException as exc:
            status='explicit_rejection' if isinstance(exc,ValueError) else 'bare_exception'
            observations.append({'path':path,'mutation':mutation,'status':status,
                'exception':type(exc).__name__,'message':str(exc)})
        else:observations.append({'path':path,'mutation':mutation,'status':'accepted'})
print(json.dumps({'case_count':len(observations),'source':hashlib.sha256((root/'layauto_v2/normalization/_validation.py').read_bytes()).hexdigest(),
 'bare_exceptions':[x for x in observations if x['status']=='bare_exception'],
 'accepted':[x for x in observations if x['status']=='accepted'],
 'explicit_rejection_count':sum(x['status']=='explicit_rejection' for x in observations),
 'observations':observations},indent=2))
