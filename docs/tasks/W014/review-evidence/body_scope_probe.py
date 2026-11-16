"""Independent actual-reader/neutral W014 status, binding and error-scope probe.

One temporary local graph is shared. No result wire or installed tree is built.
"""
from __future__ import annotations
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

REPO=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(REPO/'tests/contracts'))
sys.path.insert(0,str(REPO))
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.derive.terminal_relations import build_terminal_relations_draft
from w007_cases import ready_copy
from w010_cases import build_local
from w014_cases import neutral_inputs, change_body


def paths(draft):
 return [{'device':p['device_id']['name'],'chain':p['chain_status'],'rule':p['rule_status'],
          'observed':[n['name'] for n in p['observed_net_ids']]} for p in draft.body['paths']]


def main():
 begin=time.perf_counter()
 source=REPO/'layauto_v2/derive/body_relations.py'
 print('body_source_sha256='+hashlib.sha256(source.read_bytes()).hexdigest(),flush=True)
 temp=Path(tempfile.mkdtemp(prefix='w014-review-body-',dir=REPO/'work'))
 root=ready_copy(temp)
 original=(root/'body/context.json').read_bytes()
 local=build_local(root).value
 print('shared_local_ready',flush=True)
 args=neutral_inputs(root,local)
 output={'runtime_body_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':[]}
 for name,mutate in (
  ('normal',None),
  ('unknown_lvs',lambda doc:doc.__setitem__('lvs_status','unknown')),
  ('mn_wrong_body_only',lambda doc:doc['associations'][0].__setitem__('local_body','BP')),
 ):
  (root/'body/context.json').write_bytes(original)
  if mutate is not None:change_body(root,mutate)
  current=neutral_inputs(root,local)
  draft=build_terminal_relations_draft(*current)
  output['cases'].append({'case':name,'coverage_lvs':draft.coverage['lvs_status'],
       'body_lvs':draft.body['lvs_status'],'paths':paths(draft),'issues':[x.code for x in draft.issues]})
  print('case_done='+name,flush=True)
 for name,patch in (
  ('raw_uri_selects_source_cdl',{'source_gds':dict(args[5].payload['source_gds'].items(),uri='source.cdl')}),
  ('global_wrong_top',{'top':'ANOTHER_TOP'}),
 ):
  body=replace(args[5],payload=FrozenMap(dict(args[5].payload.items(),**patch)))
  current=(*args[:5],body,args[6])
  try:draft=build_terminal_relations_draft(*current)
  except ValueError as exc:
   output['cases'].append({'case':name,'rejected':True,'error':str(exc)})
  else:
   output['cases'].append({'case':name,'rejected':False,'paths':paths(draft),'issues':[x.code for x in draft.issues]})
  print('case_done='+name,flush=True)
 output['elapsed_seconds']=time.perf_counter()-begin
 print(json.dumps(output,indent=2),flush=True)


if __name__=='__main__':main()
