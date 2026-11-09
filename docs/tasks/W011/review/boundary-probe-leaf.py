from pathlib import Path
import sys,json
from dataclasses import replace
sys.path[:0]=['/workspace/work/w011-review-boundary']
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result,normalize
from layauto_v2.normalization.channel_identity_codec import encode_record,decode_record
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.domain.codec import FrozenMap
root=Path('/workspace/work/w011-review-boundary/tests/fixtures/w003_m1')
n=normalize(from_parse_result(read_inputs(root/'site_config.yaml')))
f=n.value;seed=f.device_seeds[0];identity=next(i for i in f.device_identities if i.device_id==seed.semantic_id)
base=ChannelSeed(seed.semantic_id,seed.query_key,seed.record,identity.provenance)
results=[]
changes=[('metadata_wrong_type',dict(base.record,metadata_opaque=7),base.identity_provenance),('record_source_fields_not_locations',dict(base.record,field_sources={k:0 for k in base.record['field_sources']}),base.identity_provenance),('xref_source_fields_not_locations',base.record,dict(base.identity_provenance,field_sources={k:0 for k in base.identity_provenance['field_sources']}))]
for name,record,provenance in changes:
    row={'case':name}
    try:
        obj=replace(base,record=FrozenMap(record),identity_provenance=FrozenMap(provenance))
        row['constructor_accepted']=True
        restored=decode_record(encode_record(obj));row['decode_accepted']=restored==obj
    except Exception as exc:
        row['exception']=type(exc).__name__;row['message']=str(exc)
    results.append(row)
print(json.dumps(results,indent=2))
