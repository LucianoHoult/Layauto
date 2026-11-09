from pathlib import Path
import hashlib, json, sys, time, resource
from dataclasses import replace

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry, build_effective_geometry, build_local_connectivity, build_channel_identity
from layauto_v2.domain.codec import FrozenMap, canonical_bytes
from layauto_v2.domain.geometry import evidence_value

started=time.monotonic()
def emit(**record): print(json.dumps(record,ensure_ascii=False,sort_keys=True),flush=True)
emit(stage='identity',head='3dbe270',python=sys.version,executable=sys.executable,
     source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'layauto_v2').rglob('*.py'))})
parsed=read_inputs(ROOT/'tests/fixtures/w003_m1/site_config.yaml')
assert parsed.status=='success'
local=build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(parsed))))
result=build_channel_identity(local)
assert result.status=='success'
emit(stage='normal',counts=sorted(item.count for item in result.value.measurements),seconds=time.monotonic()-started)
tech=next(item for item in result.completed if item.kind=='tech')
def change_at(value, path, replacement):
    if not path: return replacement
    return FrozenMap({key:change_at(item,path[1:],replacement) if key==path[0] else item for key,item in value.items()})
payload=change_at(tech.payload,('physical','fin_count_profile','finger_count_required'),True)
bad=replace(tech,payload=payload)
assert bad==tech
assert canonical_bytes(evidence_value(bad))!=canonical_bytes(evidence_value(tech))
changed=tuple(bad if item is tech else item for item in result.completed)
try:
    rebuilt=replace(result,completed=changed)
except ValueError as exc:
    emit(stage='completed_numeric_equivalence',constructor_accepted=False,error=str(exc),same_python_value=bad==tech)
else:
    emit(stage='completed_numeric_equivalence',constructor_accepted=True,same_python_value=bad==tech,
         retained_type=type(next(item for item in rebuilt.completed if item.kind=='tech').payload['physical']['fin_count_profile']['finger_count_required']).__name__)
emit(stage='done',seconds=time.monotonic()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
