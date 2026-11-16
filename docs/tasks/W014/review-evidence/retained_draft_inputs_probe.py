"""Independent actual-capture checks of retained draft inputs and malformed outputs."""
from __future__ import annotations
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'tests/contracts'),str(ROOT)]
from w014_cases import normal_capture
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.normalization import terminal_relations_codec as codec


def forge(obj,**changes):
 result=object.__new__(type(obj))
 for member in fields(obj):object.__setattr__(result,member.name,changes.get(member.name,getattr(obj,member.name)))
 return result


def main():
 begin=time.perf_counter()
 out={'codec_sha256':hashlib.sha256(Path(codec.__file__).read_bytes()).hexdigest(),'cases':[]}
 result=normal_capture()
 print('actual_normal_ready',flush=True)
 changed_source=forge(result.value.source,dialect='forged')
 changed_draft=forge(result.value,source=changed_source)
 changed_result=forge(result,value=changed_draft)
 row={'case':'result_retains_changed_draft_source_dialect','original':result.value.source.dialect,'changed':changed_result.value.source.dialect}
 try:wire=codec.encode_record(changed_result)
 except BaseException as exc:row.update(accepted=False,error_type=type(exc).__name__,message=str(exc))
 else:row.update(accepted=True,wire_bytes=len(wire),wire_sha256=hashlib.sha256(wire).hexdigest())
 out['cases'].append(row)
 print('forged_input_done',flush=True)
 bad=forge(result.value,channel_observations=FrozenMap({}))
 row={'case':'neutral_missing_channel_observations_coverage'}
 try:codec.encode_record(bad)
 except BaseException as exc:row.update(accepted=False,error_type=type(exc).__name__,message=str(exc))
 else:row.update(accepted=True)
 out['cases'].append(row)
 out['elapsed_seconds']=time.perf_counter()-begin
 print(json.dumps(out,indent=2),flush=True)


if __name__=='__main__':main()
