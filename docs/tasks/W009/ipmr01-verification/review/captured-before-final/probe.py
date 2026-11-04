"""Independent bounded malformed-field audit of newly unwrapped capture DTOs."""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from layauto_v2.domain import publication_codec as codec
from layauto_v2.domain.codec import canonical_bytes, decode
from layauto_v2.domain.publication import RunRequest, InputsReady, Selection
from layauto_v2.domain.results import EvidenceIssue
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository
from layauto_v2.domain import evidence

OUT = Path(__file__).resolve().parent

def mutable(value):
    if hasattr(value, 'items'):
        return {k: mutable(v) for k,v in value.items()}
    if isinstance(value, tuple):
        return tuple(mutable(v) for v in value)
    return value

def main():
    started=time.monotonic()
    repo=PublicationRepository()
    request=RunRequest('review-captured-input','review-captured-lineage','review-captured-key',str(ROOT/'tests/fixtures/w003_m1/site_config.yaml'))
    ready=prepare_inputs(repo,request)
    assert isinstance(ready,InputsReady)
    checkpoint=repo.load_checkpoint(ready.run_id)
    parse=repo.read(ready.parse_ref)
    tool=repo.read(ready.tool_ref)
    audit=repo.read(ready.evidence_refs[0])
    source=parse.result.sources[0]
    records=(Selection('source.gds'),ready.checkpoint_ref,tool.events[0],source.ref(),source,
             EvidenceIssue('binding','ReviewMalformed','review-only issue',source.ref()),
             parse.result.completed[0],parse.result,request,ready.attempt,tool,parse,audit,checkpoint,ready)
    assert {type(r).__name__ for r in records} == codec._CAPTURED_INPUT_RECORDS
    replacements=[('none',{'scalar':None}),('integer',{'scalar':7}),('boolean',{'scalar':True}),
                  ('string',{'scalar':'wrong'}),('bytes',{'scalar':b'wrong'}),
                  ('rational',{'scalar':Fraction(1,2)}),('empty_tuple',{'tuple':()}),
                  ('nonempty_tuple',{'tuple':({'scalar':7},)}),('empty_map',{'value':{}}),
                  ('nonempty_map',{'value':{'wrong':7}}),('foreign_record',mutable(codec._pack(Selection('foreign'))))]
    rows=[]
    for record in records:
        wire=codec.encode_record(record)
        assert codec.decode_record(wire)==record
        assert codec.record_digest(record)==hashlib.sha256(wire).hexdigest()
        tree=mutable(decode(wire)); fields=tree['value']['fields']
        cases=[]
        for field in fields:
            missing=mutable(tree);del missing['value']['fields'][field]
            cases.append((field,'missing',missing,False))
            for label,replacement in replacements:
                if fields[field]==replacement:continue
                changed=mutable(tree);changed['value']['fields'][field]=replacement
                cases.append((field,label,changed,None))
        extra=mutable(tree);extra['value']['fields']['review_extra']={'scalar':None}
        cases.append(('review_extra','extra',extra,False))
        for field,label,changed,valid in cases:
            changed_wire=canonical_bytes(changed)
            try:
                rebuilt=codec.decode_record(changed_wire)
            except ValueError as exc:
                rows.append({'record':type(record).__name__,'field':field,'mutation':label,'outcome':'rejected','exception':type(exc).__name__})
            except BaseException as exc:
                rows.append({'record':type(record).__name__,'field':field,'mutation':label,'outcome':'unexpected_exception','exception':type(exc).__name__,'message':str(exc)})
            else:
                assert valid is not False,(type(record).__name__,field,label)
                assert codec.encode_record(rebuilt)==changed_wire
                assert codec.decode_record(codec.encode_record(rebuilt))==rebuilt
                rows.append({'record':type(record).__name__,'field':field,'mutation':label,'outcome':'accepted_canonical_alternative'})
    cause=OSError('existing cause');context=LookupError('existing context')
    exception_rows=[]
    wire=codec.encode_record(source)
    original=evidence.hashlib
    try:
        for cls in (RuntimeError,ValueError,TypeError,KeyError,AttributeError,IndexError,UnicodeError,KeyboardInterrupt,SystemExit):
            failure=cls('independent SourceFile hash injection')
            failure.__cause__=cause;failure.__context__=context
            suppression=failure.__suppress_context__
            def broken(*args,**kwargs):raise failure
            evidence.hashlib=SimpleNamespace(sha256=broken)
            try:codec.decode_record(wire)
            except BaseException as observed:
                same=observed is failure and observed.__cause__ is cause and observed.__context__ is context and observed.__suppress_context__ is suppression
                exception_rows.append({'exception':cls.__name__,'same_object_and_chain':same})
            else:raise AssertionError('injected SourceFile reconstruction unexpectedly succeeded')
    finally:evidence.hashlib=original
    failures=[r for r in rows if r['outcome']=='unexpected_exception']
    result={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
            'records':len(records),'mutation_cases':len(rows),'rejected':sum(r['outcome']=='rejected' for r in rows),
            'canonical_alternatives':sum(r['outcome']=='accepted_canonical_alternative' for r in rows),
            'unexpected_exceptions':failures,'hash_exception_cases':exception_rows,'elapsed_s':time.monotonic()-started,'cases':rows}
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False,indent=2))
    assert not failures
    assert all(r['same_object_and_chain'] for r in exception_rows)
if __name__=='__main__':main()
