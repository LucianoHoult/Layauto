"""Independent tiny smoke-helper probe with margins read from actual raw GDS.

This creates only a tool-check stand-in, not an authenticated product result.
It does not run reader, normalization, codec or installation.
"""
from __future__ import annotations
from fractions import Fraction
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.local_connectivity import LocalRef

ROOT=Path(__file__).resolve().parents[4]
FIXTURE=ROOT/'tests/fixtures/w003_m1'


def rectangles(path):
 data=path.read_bytes(); offset=0;layer=None;out=[]
 while offset<len(data):
  size,kind,dtype=struct.unpack('>HBB',data[offset:offset+4]);payload=data[offset+4:offset+size]
  if kind==8:layer=None
  elif kind==13:layer=struct.unpack('>h',payload)[0]
  elif kind==16 and layer in (2,10,11):
   xy=struct.unpack('>'+str(len(payload)//4)+'i',payload)
   out.append((layer,tuple(Fraction(x) for x in (min(xy[::2]),min(xy[1::2]),max(xy[::2]),max(xy[1::2])))))
  offset+=size
 return out


def margins(outer,inner):return (inner[0]-outer[0],inner[1]-outer[1],outer[2]-inner[2],outer[3]-inner[3])


def input_facts(case):
 path=FIXTURE/('failures/extraction_mismatch/source.gds' if case=='extraction-mismatch' else 'source.gds')
 raw=rectangles(path)
 active=sorted((box for layer,box in raw if layer==2),key=lambda b:b[1])
 context=json.loads((FIXTURE/'body/context.json').read_text())
 ext={r['id']:tuple(Fraction(v) for v in r['bbox']) for r in context['shapes']}
 audits=[];paths=[];rows={};tap_audits=[]
 for n,(device,bodylayer,rail,expectededge) in enumerate((('MN0',10,'VSS',90),('MP0',11,'VDD',100))):
  body=next(box for layer,box in raw if layer==bodylayer)
  a=context['associations'][n];bm=margins(ext[a['external_body']],ext[a['tap']]);rm=margins(ext[a['external_rail']],ext[a['tap']])
  margin=margins(body,active[n])
  audits.append({'device_id':{'name':device},'margins_nm':margin,'status':'satisfied'})
  tap_audits.append({'body_margins_nm':bm,'rail_margins_nm':rm,'status':'satisfied'})
  node=LocalRef('node',str(n+1)*64);component=LocalRef('component',str(n+3)*64)
  p=FrozenMap({'device_id':{'name':device},'chain_status':'established','rule_status':'satisfied','claim_status':'equal',
       'body_edge_length_nm':Fraction(expectededge),'rail_edge_length_nm':Fraction(10),'active_enclosure_nm':min(margin),
       'tap_body_enclosure_nm':min(bm),'tap_rail_enclosure_nm':min(rm),'observed_net_ids':({'name':rail},),
       'evidence_refs':('probe-only',),'local_body_node_ref':node.to_value(),'local_body_component_ref':component.to_value()})
  paths.append(p);rows[(device,'B')]=SimpleNamespace(context_path=p,node_refs=(node,),component_refs=(component,))
 return FrozenMap({'production_matched_body_evidence':False,'lvs_status':'not_run','local_graph_union':False,
    'binding':{'active_threshold_nm':Fraction(10),'tap_threshold_nm':Fraction(1)},'active_audits':audits,
    'tap_audits':tap_audits,'body_pair_audits':[{'domain':d,'status':'satisfied','positive_area_overlap':False} for d in ('local','external')],
    'paths':paths}),rows


def main():
 tool=ROOT/'docs/tasks/W014/verification-tools/installed_smoke.py' if '--current' in sys.argv else Path(__file__).with_name('installed_smoke_before_mismatch_fix.py')
 spec=importlib.util.spec_from_file_location('w014_smoke_tool_review',tool)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 out={'classification':'tool helper only; no actual installed smoke run','tool_sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'current':'--current' in sys.argv,'cases':[]}
 for case in ('normal-direct','extraction-mismatch'):
  body,rows=input_facts(case)
  try:
   if len(inspect.signature(module.check_body).parameters)==3:module.check_body(body,rows,case)
   else:module.check_body(body,rows)
  except AssertionError:
   out['cases'].append({'case':case,'accepted':False,'error':'AssertionError'})
  else:out['cases'].append({'case':case,'accepted':True})
 print(json.dumps(out,indent=2))


if __name__=='__main__':main()
