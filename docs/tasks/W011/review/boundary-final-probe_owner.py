from pathlib import Path
from dataclasses import replace
import sys,json,time,resource
sys.path.insert(0,'/workspace/work/w011-review-boundary-final')
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import normalize,build_geometry,geometry_from_parse_result,build_effective_geometry,build_local_connectivity
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.derive.channel_identity import build_channel_identity_draft
start=time.monotonic()
root=Path('/workspace/work/w011-review-boundary-final/tests/fixtures/w003_m1')
geometry_input=geometry_from_parse_result(read_inputs(root/'site_config.yaml'))
semantic=normalize(geometry_input.semantic_input);assert semantic.status=='success'
facts=semantic.value;identities={i.device_id:i for i in facts.device_identities}
seeds=tuple(ChannelSeed(s.semantic_id,s.query_key,s.record,identities[s.semantic_id].provenance) for s in facts.device_seeds)
tech=next(record for record in geometry_input.parse.completed if record.kind=='tech')
derived=EvidenceRecord('derived',geometry_input.value['tech']['derived'],(tech.sources[2],))
seed=seeds[0]; location=seed.record['field_sources']['derived_layer']['sources'][1]
changed_location=FrozenMap(dict(location,lexeme=dict(location['lexeme'],target_layer='METAL')))
replacements=0
def mutate(value):
    global replacements
    if type(value) is FrozenMap:
        if value==location:
            replacements+=1;return changed_location
        return FrozenMap({k:mutate(v) for k,v in value.items()})
    if type(value) is tuple:return tuple(mutate(v) for v in value)
    return value
changed_seed=replace(seed,record=mutate(seed.record))
row={'head':'8917d38d916c914bfa785cb116982f3f299b38de','seed_constructor_accepted':True,'source_copies_replaced':replacements,'source_path':location['path'],'source_sha256':location['sha256'],'source_json_pointer':location['json_pointer'],'derived_uri':derived.sources[0].uri,'derived_sha256':derived.sources[0].sha256,'original_seed_target_layer':location['lexeme']['target_layer'],'mutated_seed_target_layer':changed_location['lexeme']['target_layer'],'derived_target_layer':next(item['target_layer'] for item in derived.payload['derived_registry'] if item['id']==seed.record['derived_layer'])}
print(json.dumps({'phase':'leaf','result':row}),flush=True)
local=build_local_connectivity(build_effective_geometry(build_geometry(geometry_input)))
assert local.status=='success'
control=build_channel_identity_draft(local.value,facts.source,seeds,derived)
assert not control.issues
changed=tuple(changed_seed if item is seed else item for item in seeds)
try:
    result=build_channel_identity_draft(local.value,facts.source,changed,derived)
    row.update(public_draft_constructor_accepted=True,issues=[i.code for i in result.issues],counts=[m.count for m in result.measurements],control_counts=[m.count for m in control.measurements])
except BaseException as exc:
    row.update(public_draft_constructor_accepted=False,exception=type(exc).__name__,message=str(exc))
row.update(elapsed_seconds=time.monotonic()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
print(json.dumps({'phase':'aggregate','result':row},indent=2),flush=True)
