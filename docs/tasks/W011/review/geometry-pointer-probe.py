"""CR-05 remaining pointer check: real W007 seeds, neutral zero-candidate locator."""
from pathlib import Path
import hashlib,json,sys

repo=Path(sys.argv[1]); commit=sys.argv[2]
sys.path[:0]=[str(repo),str(repo/'tests/contracts')]
from w005_cases import FIXTURE
from w007_cases import normal
from layauto_v2.domain.channel_identity import ChannelSeed,ChannelRef
from layauto_v2.annotation.channel_identity import locate_channels,seed_source

print(json.dumps({'commit':commit,'source_root':str(repo),'python':sys.version,
    'product':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((repo/'layauto_v2').rglob('*.py'))}},sort_keys=True),flush=True)
facts=normal(FIXTURE).value
identities={i.device_id:i for i in facts.device_identities}
seeds=tuple(ChannelSeed(s.semantic_id,s.query_key,s.record,identities[s.semantic_id].provenance) for s in facts.device_seeds)
devices=next(c for c in facts.source.cells if c.id==facts.source.selected_cell).devices
locations,associations,issues=locate_channels(devices,(),seeds,1,ChannelRef('binding','1'*64),())
assert len(locations)==2 and not associations and len(issues)==2
assert all(i.code=='MissingSeedChannel' for i in issues)
expected=[seed_source(seed) for seed in seeds]
actual=[i.source for i in issues]
print(json.dumps({'expected_pointers':[x.field for x in expected],
    'actual_pointers':[x.field for x in actual],'messages':[i.message for i in issues]},sort_keys=True),flush=True)
assert actual==expected, 'diagnostic sources must preserve the exact request record pointer'
assert len(set(actual))==2, 'two seed errors need distinguishable source records'
for seed,issue in zip(seeds,issues):
    document=json.loads((FIXTURE/issue.source.uri).read_text())
    for token in issue.source.field[1:].split('/'):
        token=token.replace('~1','/').replace('~0','~')
        document=document[int(token)] if isinstance(document,list) else document[token]
    assert document==seed.record['record_id']
    assert seed.record['record_id'] in issue.message
print('CR05 exact record pointer resolution: PASS',flush=True)
