"""Additional neutral localization/CR05 source-pointer witnesses.

Reuse this review's independent setup and geometry probe, not formal tests.
The variants reconstruct neutral ChannelSeed DTOs and their operand shapes;
they intentionally do not claim modified bytes or capture authentication.
"""
import contextlib
import hashlib
import io
import json
import runpy
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

started = time.monotonic()
base = Path(__file__).with_name('geometry-probe.py')
with contextlib.redirect_stdout(io.StringIO()):
    ctx = runpy.run_path(str(base))
locate = ctx['locate_channels']
selected, channels, seeds = ctx['selected'], ctx['channels'], ctx['seeds']
sources, binding, variant = ctx['sources'], ctx['binding'], ctx['seed_variant']
nseed,pseed = ctx['nseed'],ctx['pseed']

# Both originally legal seed records now have zero-area contact only. Each
# diagnostic must retain the *actual original* request JSON pointer and ID.
bad = (variant(nseed,(58,70,62,80)), variant(pseed,(58,180,62,190)))
locs,associations,issues = locate(selected.devices,channels,bad,1,binding,sources)
assert not associations and all(not l.intersections for l in locs)
pointer_checks = []
for seed in bad:
    issue = next(i for i in issues if i.code=='MissingSeedChannel' and seed.record['record_id'] in i.message)
    source = issue.source
    path = ctx['fixture'] / source.uri
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source.sha256
    value = json.loads(path.read_text())
    for token in source.field.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        value=value[int(token)] if isinstance(value,list) else value[token]
    assert value==seed.record['record_id']
    pointer_checks.append({'record_id':value,'uri':source.uri,'field':source.field,
                           'sha256':source.sha256,'message':issue.message})
assert {x['record_id'] for x in pointer_checks}=={'D0','D1'}
assert len({(x['uri'],x['field']) for x in pointer_checks})==2

# A real source device with no seed is never dropped; an additional recognized
# region without any seed must also be reported while existing joins survive.
_,assoc_missing,problems_missing = locate(selected.devices,channels,(pseed,),1,binding,sources)
assert len(assoc_missing)==1 and assoc_missing[0].device_id.name=='MP0'
assert {p.code for p in problems_missing}=={'MissingDeviceSeed','UnassociatedChannel'}
extra=replace(channels[0],rectangles=(ctx['Rect'](238,20,242,70),))
_,assoc_extra,problems_extra = locate(selected.devices,channels+(extra,),seeds,1,binding,sources+(sources[0],))
assert len(assoc_extra)==2 and {p.code for p in problems_extra}=={'UnassociatedChannel'}
assert len(problems_extra)==1 and problems_extra[0].source is not None

print(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,
    'head':ctx['receipt']['head'],'scope':'neutral self-consistent seed variants; actual original pointer resolution',
    'base_probe_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),
    'base_probe_checks':{'fin_verdicts':ctx['fin_checks'],'union_cases':ctx['union_cases'],
                        'union_membership_checks':ctx['atom_checks'],'identity_variants':len(ctx['identity_cases'])},
    'cr05_pointer_checks':pointer_checks,'missing_device_checked':True,
    'extra_unassociated_channel_checked':True,'elapsed_seconds':time.monotonic()-started,'status':'passed'},indent=2))
