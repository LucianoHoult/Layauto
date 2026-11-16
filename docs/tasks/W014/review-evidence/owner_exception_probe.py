"""Independent small owner semantics/native values and exception-history probes."""
from __future__ import annotations
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import EvidenceRecord,SourceRef
from layauto_v2.tech.schema import SchemaError
import layauto_v2.derive.body_relations as body

ROOT=Path(__file__).resolve().parents[4]
FIXTURE=ROOT/'tests/fixtures/w003_m1'


def load(name):
 p=FIXTURE/'tech'/f'{name}.json'
 data=p.read_bytes()
 return json.loads(data),SourceRef(f'tech/{name}.json',hashlib.sha256(data).hexdigest())


def owner_input(change=None):
 rows={}
 for name in ('physical','drawn','rules'):
  doc,ref=load(name)
  if change is not None:change(name,doc)
  rows[name]=EvidenceRecord(name,FrozenMap(doc),(ref,))
 return SimpleNamespace(local=SimpleNamespace(binding=SimpleNamespace(**rows)))


def main():
 out={'owner_checks':[],'history_checks':[]}
 assert body._owners(owner_input())==(Fraction(10),Fraction(1))
 mutations=(
  ('gate_operator','physical',lambda d:d['device_extraction_contract'].__setitem__('gate_operator','POLY is severed at each recognized channel')),
  ('tap_connects','drawn',lambda d:next(r for r in d['layers'] if r['name']=='BTAP_N').__setitem__('electrical_connects',['BODY_P','M1'])),
  ('tap_predicate','drawn',lambda d:next(r for r in d['layers'] if r['name']=='BTAP_N').__setitem__('contact_predicate','corner_touch_is_contact')),
  ('rule_evaluator','rules',lambda d:next(r for r in d['rules'] if r['id']=='T04.body').__setitem__('exact_evaluator_ref','unknown/2')),
 )
 for label,owner,mutate in mutations:
  target=owner_input(lambda n,d:mutate(d) if n==owner else None)
  try:body._owners(target)
  except body.BodyProblem as exc:
   assert exc.issue.category=='unsupported'
   out['owner_checks'].append({'case':label,'category':exc.issue.category,'source':exc.issue.source.uri,'field':exc.issue.source.field})
  else:raise AssertionError(label+' was ignored')
 native=owner_input(lambda n,d:d['rules'][3]['parameters'].__setitem__('active_enclosure_nm',11) if n=='rules' else None)
 assert body._owners(native)==(Fraction(11),Fraction(1))
 original_validate,original_unsupported=body.validate_payload,body._unsupported
 for failure_type in (RuntimeError,KeyboardInterrupt,SystemExit):
  for suppression in (False,True):
   cause,context=LookupError('cause'),IndexError('context')
   failure=failure_type('original diagnostic failure')
   failure.__cause__,failure.__context__,failure.__suppress_context__=cause,context,suppression
   def expected_schema(*args,**kwargs):raise SchemaError('/controlled','expected invalid owner')
   def fail_diagnostic(*args,**kwargs):raise failure
   body.validate_payload,body._unsupported=expected_schema,fail_diagnostic
   try:
    try:body._owners(owner_input())
    except BaseException as raised:
     assert raised is failure
     assert raised.__cause__ is cause and raised.__context__ is context and raised.__suppress_context__ is suppression
     out['history_checks'].append({'type':failure_type.__name__,'suppression':suppression,'preserved':True})
    else:raise AssertionError('diagnostic failure did not propagate')
   finally:body.validate_payload,body._unsupported=original_validate,original_unsupported
 out['body_source_sha256']=hashlib.sha256((ROOT/'layauto_v2/derive/body_relations.py').read_bytes()).hexdigest()
 print(json.dumps(out,indent=2))


if __name__=='__main__':main()
