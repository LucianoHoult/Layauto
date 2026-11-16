"""Actual reader -> neutral graph tests of retained EvidenceRecord versions.

No captured W010 Result or complete Result wire is constructed.
"""
from __future__ import annotations
from dataclasses import fields,replace
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'tests/contracts'),str(ROOT)]
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry,geometry_from_parse_result,build_effective_geometry
from layauto_v2.state.local_connectivity import build_local_connectivity_draft
from layauto_v2.derive.terminal_relations import build_terminal_relations_draft
from layauto_v2.normalization import terminal_relations_codec as codec
from w005_cases import FIXTURE
from w014_cases import neutral_inputs


def forge(obj,**changes):
 result=object.__new__(type(obj))
 for f in fields(obj):object.__setattr__(result,f.name,changes.get(f.name,getattr(obj,f.name)))
 return result


def main():
 begin=time.perf_counter()
 parsed=read_inputs(FIXTURE/'site_config.yaml')
 assert parsed.status=='success'
 geometry=build_geometry(geometry_from_parse_result(parsed))
 effective=build_effective_geometry(geometry)
 assert effective.status=='success'
 tech=next(record for record in parsed.completed if record.kind=='tech')
 rules=EvidenceRecord('rules',geometry.input.value['tech']['rules'],(tech.sources[6],))
 local=build_local_connectivity_draft(effective.value,rules)
 draft=build_terminal_relations_draft(*neutral_inputs(FIXTURE,local))
 out={'domain_sha256':hashlib.sha256((ROOT/'layauto_v2/domain/terminal_relations.py').read_bytes()).hexdigest(),'codec_sha256':hashlib.sha256(Path(codec.__file__).read_bytes()).hexdigest(),'cases':[]}
 print('actual_neutral_ready',flush=True)
 for owner in ('body_evidence','derived'):
  for field in ('schema_version','parser_version'):
   changed=forge(getattr(draft,owner),**{field:'unknown/999'})
   row={'owner':owner,'field':field}
   try:bad=replace(draft,**{owner:changed})
   except BaseException as exc:row.update(constructor_accepted=False,constructor_error=type(exc).__name__,message=str(exc))
   else:
    row['constructor_accepted']=True
    try:wire=codec.encode_record(bad)
    except BaseException as exc:row.update(encode_accepted=False,encode_error=type(exc).__name__,message=str(exc))
    else:
     row.update(encode_accepted=True,wire_bytes=len(wire),wire_sha256=hashlib.sha256(wire).hexdigest())
     try:restored=codec.decode_record(wire)
     except BaseException as exc:row.update(decode_accepted=False,decode_error=type(exc).__name__,message=str(exc))
     else:row.update(decode_accepted=True,equal=restored==bad)
   out['cases'].append(row)
   print('case_done='+owner+'.'+field,flush=True)
 # Build a neutral local graph with a wrong wrapper on its actual rule owner.
 # Physical is already bound by effective; direct mutation without coherent
 # rebuild would test stale refs instead of this version invariant.
 for field in ('schema_version','parser_version'):
  wrong_rules=forge(rules,**{field:'unknown/999'})
  row={'owner':'local_rules','field':field}
  try:
   bad_local=build_local_connectivity_draft(effective.value,wrong_rules)
   bad=build_terminal_relations_draft(*neutral_inputs(FIXTURE,bad_local))
  except BaseException as exc:row.update(constructor_accepted=False,constructor_error=type(exc).__name__,message=str(exc))
  else:
   row['constructor_accepted']=True
   try:wire=codec.encode_record(bad)
   except BaseException as exc:row.update(encode_accepted=False,encode_error=type(exc).__name__,message=str(exc))
   else:
    row.update(encode_accepted=True,wire_bytes=len(wire))
    try:codec.decode_record(wire)
    except BaseException as exc:row.update(decode_accepted=False,decode_error=type(exc).__name__,message=str(exc))
    else:row.update(decode_accepted=True)
  out['cases'].append(row)
  print('case_done=local_rules.'+field,flush=True)
 out['elapsed_seconds']=time.perf_counter()-begin
 print(json.dumps(out,indent=2),flush=True)


if __name__=='__main__':main()
