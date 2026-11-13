"""Independent actual Result encoding rejects every retained input family.

One immutable captured result is shared; no runtime/test source is modified.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
from retained_draft_inputs_probe import ROOT,normal_capture,forge,codec
from layauto_v2.domain.codec import FrozenMap


def main():
 begin=time.perf_counter()
 out={'codec_sha256':hashlib.sha256(Path(codec.__file__).read_bytes()).hexdigest(),'cases':[]}
 result=normal_capture()
 draft=result.value
 print('actual_normal_ready',flush=True)
 variants=(
  ('source_dialect',forge(draft,source=forge(draft.source,dialect='forged'))),
  ('local_schema',forge(draft,local=forge(draft.local,schema_version='forged-local/1'))),
  ('derived_owner',forge(draft,derived=forge(draft.derived,sources=(draft.body_evidence.sources[0],)))),
  ('body_provenance',forge(draft,body_evidence=forge(draft.body_evidence,payload=FrozenMap(dict(draft.body_evidence.payload.items(),author='changed retained context provenance'))))),
  ('net_evidence_omitted',forge(draft,net_evidence=draft.net_evidence[:-1])),
 )
 for label,value in variants:
  row={'case':label}
  changed=forge(result,value=value)
  try:codec.encode_record(changed)
  except ValueError as exc:row.update(rejected=True,error_type=type(exc).__name__,message=str(exc))
  except BaseException as exc:row.update(rejected=False,error_type=type(exc).__name__,message=str(exc))
  else:row.update(rejected=False,error_type=None)
  out['cases'].append(row)
  print('case_done='+label,flush=True)
 row={'case':'neutral_missing_coverage'}
 try:codec.encode_record(forge(draft,channel_observations=FrozenMap({})))
 except ValueError as exc:row.update(rejected=True,error_type=type(exc).__name__,message=str(exc))
 except BaseException as exc:row.update(rejected=False,error_type=type(exc).__name__,message=str(exc))
 else:row.update(rejected=False,error_type=None)
 out['cases'].append(row)
 out['elapsed_seconds']=time.perf_counter()-begin
 print(json.dumps(out,indent=2),flush=True)
 assert all(row['rejected'] for row in out['cases'])


if __name__=='__main__':main()
