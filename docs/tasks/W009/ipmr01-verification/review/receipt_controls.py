"""Independent malformed captured-receipt controls through full W009 wire."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain import publication_codec
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_effective_geometry, build_geometry, geometry_from_parse_result
from layauto_v2.normalization.contracts import NormalizationInput
from layauto_v2.normalization.effective_codec import encode_record, decode_record

def mutable(value):
    if type(value) is FrozenMap:
        return {k:mutable(v) for k,v in value.items()}
    if type(value) is tuple:
        return [mutable(v) for v in value]
    return value

def replace_parse(node, wire):
    if isinstance(node,dict):
        if set(node)=={'captured_record'}:
            captured=mutable(decode(node['captured_record']))
            if captured['value'].get('record')=='ParseResult':
                node['captured_record']=wire
                return True
        for key,value in node.items():
            if key in ('geometry_record','semantic_input') and isinstance(value,bytes):
                child=mutable(decode(value))
                if replace_parse(child,wire):
                    node[key]=canonical_bytes(child)
                    return True
            elif replace_parse(value,wire):
                return True
    elif isinstance(node,list):
        return any(replace_parse(item,wire) for item in node)
    return False

parsed=read_inputs(Path.cwd()/'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status=='success'
result=build_effective_geometry(build_geometry(geometry_from_parse_result(parsed)))
assert result.status=='success'
wire=encode_record(result)
controls=[
    ('missing model axes',('tech','physical','models','TOY_N','parameter_axes'),'delete'),
    ('wrong model parameters',('tech','physical','models','TOY_N','required_parameters'),[{}]),
    ('missing raw query declarations',('header','raw'),'delete'),
    ('wrong raw query uri',('header','raw',0,'uri'),{}),
    ('wrong capability raw refs',('query','device_regions','raw_refs'),1),
    ('missing query record identity',('query','device_regions','records',0,'record_id'),'delete'),
    ('wrong query precision',('query','device_regions','records',0,'precision'),{}),
    ('missing coordinate operand',('query','device_regions','records',0,'field_sources','vertices_nm','sources',1,'lexeme'),'delete'),
    ('wrong bounding region',('query','net_regions','records',0,'bbox_nm'),[]),
    ('missing xref metadata',('query','_format_metadata','instance_xref'),'delete'),
    ('wrong response source',('query','_format_metadata','responses',0,'source'),[]),
    ('missing response timestamp',('query','_format_metadata','responses',0,'timestamp'),'delete'),
    ('wrong closure reference',('header','closure','entries',0,'sha256'),[]),
    ('missing cdl source lexeme',('source_cdl','tops',0,'devices',0,'field_sources','D','lexeme'),'delete'),
    ('wrong cdl parameters',('source_cdl','tops',0,'devices',0,'parameters'),1),
    ('extra cdl top field',('source_cdl','tops',0,'unexpected'),True),
]
rows=[]
for name,path,change in controls:
    value=mutable(parsed.value)
    target=value
    for key in path[:-1]:
        target=target[key]
    if change=='delete':
        del target[path[-1]]
    else:
        target[path[-1]]=change
    completed=tuple(replace(record,payload=({'bundle':value['tech_bundle'],'owners':value['tech']} if record.kind=='tech' else value[record.kind])) for record in parsed.completed)
    bad=replace(parsed,value=value,completed=completed)
    for entry in ('constructor','w009-result-wire'):
        try:
            if entry=='constructor':
                NormalizationInput(bad)
            else:
                tree=mutable(decode(wire))
                assert replace_parse(tree,publication_codec.encode_record(bad))
                decode_record(canonical_bytes(tree))
        except ValueError as exc:
            rows.append(dict(control=name,entry=entry,exception=type(exc).__name__,message=str(exc)))
        else:
            raise AssertionError((name,entry,'unexpected success'))

# The late execution-side counterexample is independently exercised after its
# narrow explicit guard, using the full public W009 result decode.
value=mutable(parsed.value)
header=value['query']['_format_metadata']['responses'][0]['count_header']
header['lexeme']=' '
header.pop('token_0based',None)
header.pop('column',None)
completed=tuple(replace(record,payload=value['query']) if record.kind=='query' else record for record in parsed.completed)
bad=replace(parsed,value=value,completed=completed)
tree=mutable(decode(wire))
assert replace_parse(tree,publication_codec.encode_record(bad))
try:
    decode_record(canonical_bytes(tree))
except ValueError as exc:
    rows.append(dict(control='blank response count-header token',entry='w009-result-wire',exception=type(exc).__name__,message=str(exc)))
else:
    raise AssertionError('blank response count header accepted')
print(json.dumps(dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),case_count=len(rows),all_explicit_value_errors=True,observations=rows),indent=2))
