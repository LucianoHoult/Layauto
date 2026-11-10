from pathlib import Path
from dataclasses import fields,is_dataclass
from collections import Counter
import sys,json,time,resource
sys.path.insert(0,'/workspace/work/w011-review-boundary-fixed')
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result,normalize
from layauto_v2.normalization import codec
from layauto_v2.domain.codec import FrozenMap,decode,canonical_bytes
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.normalization.channel_identity_codec import encode_record,decode_record
start=time.monotonic()
root=Path('/workspace/work/w011-review-boundary-fixed/tests/fixtures/w003_m1')
result=normalize(from_parse_result(read_inputs(root/'site_config.yaml')))
facts=result.value;seed=facts.device_seeds[0];identity=next(i for i in facts.device_identities if i.device_id==seed.semantic_id)
normal_seed=ChannelSeed(seed.semantic_id,seed.query_key,seed.record,identity.provenance)
assert decode_record(encode_record(normal_seed))==normal_seed
examples={}
def walk(value):
    if is_dataclass(value):
        name=type(value).__name__
        if name in codec._SPEC and name not in ('ReadbackBinding','NormalizationInput','NormalizationResult','NormalizationFacts'):
            examples.setdefault(name,value)
        for field in fields(value):walk(getattr(value,field.name))
    elif type(value) is tuple:
        for item in value:walk(item)
walk(facts)
mutations={'null':{'scalar':None},'integer':{'scalar':17},'bool':{'scalar':True},'text':{'scalar':'invalid-review-value'},'map':{'map':{}},'tuple':{'tuple':()}}
counts=Counter();unexpected=[];accepted=[]
for name,obj in examples.items():
    original=decode(codec.encode_record(obj))
    assert codec.decode_record(codec.encode_record(obj))==obj
    for field in codec._SPEC[name][1]:
        for label,replacement in mutations.items():
            record=original['record'];changed_fields=dict(record['fields']);changed_fields[field]=replacement
            altered=canonical_bytes(dict(original,record=dict(record,fields=changed_fields)))
            try:codec.decode_record(altered)
            except ValueError:counts['ValueError']+=1
            except BaseException as exc:
                counts[type(exc).__name__]+=1;unexpected.append({'record':name,'field':field,'mutation':label,'exception':type(exc).__name__,'message':str(exc)})
            else:
                counts['accepted']+=1;accepted.append({'record':name,'field':field,'mutation':label})
print(json.dumps({'review_head':'975852d3b9ea946aca24f727071cf26a7dce8bc7','normal_seed_roundtrip':True,'normal_neutral_roundtrips':sorted(examples),'field_mutations_count':sum(counts.values()),'results':dict(counts),'unexpected_non_value_errors':unexpected,'accepted_mutations_not_claimed_invalid':accepted,'elapsed_seconds':time.monotonic()-start,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2))
