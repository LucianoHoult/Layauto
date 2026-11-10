"""Independent premerge boundary probes. No formal tests or fixture files changed."""
from __future__ import annotations
import copy, hashlib, json, resource, shutil, subprocess, tempfile, time
from collections import Counter
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from layauto_v2.domain.channel_identity import ChannelSeed, ChannelRef, FinEvaluation, ChannelMeasurement, ParameterComparison
from layauto_v2.domain.circuit import Parameter
from layauto_v2.domain.codec import FrozenMap, canonical_bytes, decode
from layauto_v2.domain.geometry import GeometryRecordId, Rect
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.source_location import ref_from_location
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize
from layauto_v2.normalization import component, codec
from layauto_v2.normalization.channel_identity_codec import encode_record, decode_record

ROOT = Path.cwd()
FIXTURE = ROOT / 'tests/fixtures/w003_m1'
started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat();start=time.monotonic(); checks=[]
def ok(name, **detail): checks.append({'name':name,'passed':True,**detail})
def rejected(name, fn):
    try: fn()
    except ValueError as e: ok(name,error=str(e)); return
    raise AssertionError(name+' was accepted')
def mutable(v):
    if isinstance(v,FrozenMap): return {k:mutable(x) for k,x in v.items()}
    if type(v) is tuple:return tuple(mutable(x) for x in v)
    return v
parsed=read_inputs(FIXTURE/'site_config.yaml'); assert parsed.status=='success'
input=from_parse_result(parsed)
with patch.object(Path,'read_bytes',side_effect=AssertionError('unexpected IO')), patch.object(Path,'read_text',side_effect=AssertionError('unexpected IO')), patch.object(Path,'open',side_effect=AssertionError('unexpected IO')):
    normal=normalize(input)
assert normal.status=='success'; facts=normal.value
ok('W007 normalization after capture uses no Path IO')
seed=facts.device_seeds[0]; identity=next(i for i in facts.device_identities if i.device_id==seed.semantic_id)
seed=ChannelSeed(seed.semantic_id,seed.query_key,seed.record,identity.provenance)
assert decode_record(encode_record(seed))==seed
ok('actual W007 seed W011 roundtrip')
for name,row,prov in [
 ('metadata scalar',dict(seed.record,metadata_opaque=7),seed.identity_provenance),
 ('record source operands scalar',dict(seed.record,field_sources={k:0 for k in seed.record['field_sources']}),seed.identity_provenance),
 ('xref source operands scalar',seed.record,dict(seed.identity_provenance,field_sources={k:0 for k in seed.identity_provenance['field_sources']}))]:
    rejected('CR01 '+name,lambda row=row,prov=prov:replace(seed,record=FrozenMap(row),identity_provenance=FrozenMap(prov)))
# Every declared source field remains checked independently, not just record_id.
for key in seed.record['field_sources']:
    sources=dict(seed.record['field_sources']); sources[key]=0
    rejected('seed operand '+key,lambda sources=sources:replace(seed,record=FrozenMap(dict(seed.record,field_sources=sources))))
for key in seed.identity_provenance['field_sources']:
    sources=dict(seed.identity_provenance['field_sources']); sources[key]=0
    rejected('identity operand '+key,lambda sources=sources:replace(seed,identity_provenance=FrozenMap(dict(seed.identity_provenance,field_sources=sources))))

p=next(p for p in facts.source.cells[0].devices[0].parameters if p.axis=='channel_length')
comparison=ParameterComparison(facts.source.cells[0].devices[0].id,RegionRef('region','a'*64),'channel_length',p.exact,p,None,ChannelRef('binding','b'*64))
wire=encode_record(comparison)
for failure_type in (TypeError,KeyError,AttributeError,UnicodeError,ValueError,KeyboardInterrupt,SystemExit):
  for suppress in (False,True):
    failure=failure_type('semantic Parameter fault');cause=RuntimeError('prior cause');context=LookupError('prior context')
    failure.__cause__,failure.__context__,failure.__suppress_context__=cause,context,suppress
    def broken(*a,**kw):raise failure
    with patch.object(Parameter,'__post_init__',broken):
      try:decode_record(wire)
      except BaseException as e:
        assert e is failure and e.__cause__ is cause and e.__context__ is context and e.__suppress_context__ is suppress
      else:raise AssertionError('fault swallowed')
    ok('CR02 '+failure_type.__name__,suppression=suppress)

# Revisit the changed W007 constructor translation boundary with more scalar
# variants than the original six-value mutation matrix. Accepted edits are listed
# as type/admissibility observations, never claimed malformed rejections.
examples={}
def walk(v):
    if is_dataclass(v):
      name=type(v).__name__
      if name in codec._SPEC and name not in ('ReadbackBinding','NormalizationInput','NormalizationResult','NormalizationFacts'):
        examples.setdefault(name,v)
      for f in fields(v):walk(getattr(v,f.name))
    elif type(v) is tuple:
      for x in v:walk(x)
walk(facts)
mutations={'null':{'scalar':None},'integer':{'scalar':17},'bool':{'scalar':True},'text':{'scalar':'review-value'},'bytes':{'scalar':b'review'},'fraction':{'scalar':Fraction(17)},'empty_text':{'scalar':''},'map':{'map':{}},'tuple':{'tuple':()}}
counts=Counter(); accepted=[]
for name,v in examples.items():
    original=decode(codec.encode_record(v)); assert codec.decode_record(codec.encode_record(v))==v
    for field in codec._SPEC[name][1]:
      for label,change in mutations.items():
        row=dict(original['record']);fs=dict(row['fields']);fs[field]=change;row['fields']=fs
        raw=canonical_bytes(dict(original,record=row))
        try:codec.decode_record(raw)
        except ValueError:counts['ValueError']+=1
        except BaseException as e:raise AssertionError((name,field,label,type(e).__name__)) from e
        else:counts['accepted']+=1;accepted.append([name,field,label])
ok('upstream W007 malformed/type matrix',records=sorted(examples),cases=sum(counts.values()),counts=dict(counts),accepted_not_claimed_invalid=accepted)

# Exact-value equality does not excuse wrong nested scalar types or aliases.
region=RegionRef('region','a'*64);binding=ChannelRef('binding','b'*64)
fin=FinEvaluation(GeometryRecordId('c'*64),region,'qualified',Rect(0,0,4,2),Fraction(2),p.source,binding)
measurement=ChannelMeasurement(region,GeometryRecordId('d'*64),Fraction(4),[fin],1,[],binding)
for field,wrong in [('width_nm',2),('width_nm',True)]:
    forged=copy.copy(fin);object.__setattr__(forged,field,wrong)
    rejected('CR04 nested '+repr(wrong),lambda forged=forged:replace(measurement,evaluations=[forged]))
source=copy.copy(p.source); object.__setattr__(source,'line',Fraction(p.source.line))
forged=copy.copy(fin); object.__setattr__(forged,'source',source)
rejected('CR04 nested equal Fraction source line',lambda:replace(measurement,evaluations=[forged]))
items=[fin];aliased=replace(measurement,evaluations=items);before=encode_record(aliased);items.clear()
assert encode_record(aliased)==before and type(aliased.evaluations) is tuple
ok('collection defensive snapshot remains stable after caller list mutation')
for name,loc in [('plain map',{'path':'x','sha256':'a'*64}),('missing hash',FrozenMap({'path':'x'})),('UTF8 surrogate',FrozenMap({'path':'\ud800','sha256':'a'*64})),('bool line',FrozenMap({'path':'x','sha256':'a'*64,'line':True})),('fraction line',FrozenMap({'path':'x','sha256':'a'*64,'line':Fraction(1)})),('wrong field',FrozenMap({'path':'x','sha256':'a'*64,'field':7}))]:
    rejected('source_location '+name,lambda loc=loc:ref_from_location(loc))

# Real capture edits, independently rehashed according to existing header schema.
def rebind(root):
    hp=root/'query/header.json'; header=json.loads(hp.read_text())
    for item in [header['layout'],header['source_netlist'],header['target'],*header['raw'],*header['closure']['entries']]:
      item['sha256']=hashlib.sha256((root/item['uri']).read_bytes()).hexdigest()
    header['closure']['entries'].sort(key=lambda v:v['uri'])
    header['closure']['sha256']=hashlib.sha256(json.dumps(header['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    hp.write_text(json.dumps(header,indent=2)+'\n')
for case,hook in [('admission','NormalizationResult'),('identity','replace')]:
  with tempfile.TemporaryDirectory(prefix='w011-premerge-boundary-') as tmp:
    root=Path(tmp)/'input';shutil.copytree(FIXTURE,root);shutil.rmtree(root/'query/normalized')
    path=root/('source.cdl' if case=='admission' else 'query/raw/iXref.temp')
    text=path.read_text(); old,new=('NF=1','NF=2') if case=='admission' else ('MN0','UNDECLARED')
    assert old in text; path.write_text(text.replace(old,new));rebind(root)
    parse=read_inputs(root/'site_config.yaml');assert parse.status=='success',parse.issues
    inp=from_parse_result(parse);control=normalize(inp);assert control.status=='error'
    expected='UnsupportedFingerCount' if case=='admission' else 'UnknownDeviceIdentity'
    assert control.issues[0].code==expected,(case,control.issues)
    for failure_type in (TypeError,KeyboardInterrupt,SystemExit):
      for suppress in (False,True):
        failure=failure_type('W007 completion fault');cause=RuntimeError('prior cause');context=LookupError('prior context')
        failure.__cause__,failure.__context__,failure.__suppress_context__=cause,context,suppress
        def broken(*a,**kw):raise failure
        with patch.object(component,hook,broken):
          try:normalize(inp)
          except BaseException as e:
            assert e is failure and e.__cause__ is cause and e.__context__ is context and e.__suppress_context__ is suppress
          else:raise AssertionError('fault swallowed')
        ok('CR03 '+case+' '+failure_type.__name__,expected_issue=expected,suppression=suppress)

print(json.dumps({'started_utc':started_utc,'finished_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'python':__import__('sys').version,'checks':checks,'checks_count':len(checks),'elapsed_s':time.monotonic()-start,'ru_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':'No full W011 captured Result/readback codec; no formal pytest, installs or peak benchmark.'},indent=2))
