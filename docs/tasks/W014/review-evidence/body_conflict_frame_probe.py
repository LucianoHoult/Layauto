"""Independent authentic capture probes against preserved pre-fix evaluator.

Use --current for repaired evaluator. No complete result/wire is constructed.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import time

REPO=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(REPO/'tests/contracts'),str(REPO)]
import layauto_v2.derive.terminal_relations as aggregate
import layauto_v2.derive.body_relations as current_body
from w007_cases import ready_copy
from w010_cases import build_local
from w013_cases import rewrite_net_response
from w014_cases import neutral_inputs,change_body
from w008_geometry_cases import blocks,rectangle_bytes
from w005_cases import rebind


def report(draft):
 result={'issues':[issue.code for issue in draft.issues], 'paths':[]}
 for p in draft.body['paths']:
  result['paths'].append({'device':p['device_id']['name'],'chain':p['chain_status'],'rule':p['rule_status'],
      'observed':[net['name'] for net in p['observed_net_ids']],
      'body_edge':str(p['body_edge_length_nm']),'rail_edge':str(p['rail_edge_length_nm'])})
 result['terminals']=[{'device':r.target.device_id.name,'role':r.target.role,'status':r.status,
                      'observed':[net.name for net in r.observed_net_ids]} for r in draft.relations if r.target.role=='B']
 return result


def move_seam(root):
 path=root/'source.gds'
 prefix,elements,suffix=blocks(path.read_bytes())
 out=[]
 for element in elements:
  pos=0;layer=None;coords=None
  while pos<len(element):
   size,kind,dtype=struct.unpack('>HBB',element[pos:pos+4])
   payload=element[pos+4:pos+size]
   if kind==13:layer=struct.unpack('>h',payload)[0]
   elif kind==16:coords=struct.unpack('>10i',payload)
   pos+=size
  box=(min(coords[::2]),min(coords[1::2]),max(coords[::2]),max(coords[1::2]))
  if (layer,box)==(10,(0,0,120,90)):element=rectangle_bytes(10,(-10,0,120,90))
  elif (layer,box)==(9,(0,48,45,58)):element=rectangle_bytes(9,(-10,48,45,58))
  out.append(element)
 path.write_bytes(prefix+b''.join(out)+suffix)
 def context(doc):
  for row in doc['local_bindings']:
   if row['id'] in ('BN','MN'):row['bbox'][0]=-10
  for row in doc['shapes']:
   if row['id'] in ('BN.ext','MN.ext'):row['bbox'][2]=-10
   elif row['id']=='TN.ext':row['bbox'][0],row['bbox'][2]=-18,-14
 change_body(root,context)
 rewrite_net_response(root,'n_lo',[('toy_li',(28,30,34,55)),('toy_m1',(-10,48,45,58))])
 rebind(root)


def main():
 begin=time.perf_counter()
 before=Path(__file__).with_name('body_before_scope_fixes.py')
 if '--current' in sys.argv:
  evaluator=current_body
  identity=REPO/'layauto_v2/derive/body_relations.py'
 else:
  spec=importlib.util.spec_from_file_location('layauto_v2.derive._w014_before_scope',before)
  evaluator=importlib.util.module_from_spec(spec)
  spec.loader.exec_module(evaluator)
  identity=before
 aggregate.evaluate_body=evaluator.evaluate_body
 output={'evaluator_sha256':hashlib.sha256(identity.read_bytes()).hexdigest(),'current':'--current' in sys.argv,'cases':[]}
 print('begin_evaluator='+output['evaluator_sha256'],flush=True)
 base=Path(tempfile.mkdtemp(prefix='w014-independent-frame-',dir=REPO/'work'))
 conflict=ready_copy(base/'conflict')
 local=build_local(conflict).value
 rewrite_net_response(conflict,'n_hi',[('toy_li',(28,130,34,155)),('toy_m1',(0,148,45,158)),('toy_m1',(0,48,20,58))])
 draft=aggregate.build_terminal_relations_draft(*neutral_inputs(conflict,local))
 output['cases'].append({'case':'full_VSS_with_partial_VDD',**report(draft)})
 print('conflict_done',flush=True)
 frame=ready_copy(base/'frame')
 move_seam(frame)
 local=build_local(frame).value
 draft=aggregate.build_terminal_relations_draft(*neutral_inputs(frame,local))
 output['cases'].append({'case':'continuation_at_minus10_frame_at_zero',**report(draft)})
 print('frame_done',flush=True)
 output['elapsed_seconds']=time.perf_counter()-begin
 print(json.dumps(output,indent=2),flush=True)


if __name__=='__main__':main()
