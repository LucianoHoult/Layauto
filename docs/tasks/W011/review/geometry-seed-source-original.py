from pathlib import Path
import sys,traceback
sys.path[:0]=['/workspace/Layauto','/workspace/Layauto/tests/contracts']
from w005_cases import FIXTURE
from w007_cases import normal
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.annotation.channel_identity import seed_source
r=normal(FIXTURE)
facts=r.value
identities={i.device_id:i for i in facts.device_identities}
s=facts.device_seeds[0]
seed=ChannelSeed(s.semantic_id,s.query_key,s.record,identities[s.semantic_id].provenance)
print('device',seed.device_id,flush=True)
print('field_sources.record_id',seed.record['field_sources']['record_id'],flush=True)
try:
    print('seed_source',seed_source(seed),flush=True)
except BaseException:
    traceback.print_exc()
    raise
