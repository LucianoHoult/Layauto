from pathlib import Path
import sys,json
from fractions import Fraction
from unittest.mock import patch
sys.path[:0]=['/workspace/work/w011-review-boundary']
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result,normalize
from layauto_v2.normalization.channel_identity_codec import encode_record,decode_record
from layauto_v2.domain.channel_identity import ParameterComparison,ChannelRef
from layauto_v2.domain.circuit import Parameter
from layauto_v2.domain.regions import RegionRef
root=Path('/workspace/work/w011-review-boundary/tests/fixtures/w003_m1')
f=normalize(from_parse_result(read_inputs(root/'site_config.yaml'))).value
d=f.source.cells[0].devices[0];p=next(p for p in d.parameters if p.axis=='channel_length')
comparison=ParameterComparison(d.id,RegionRef('region','a'*64),'channel_length',p.exact,p,None,ChannelRef('binding','b'*64))
wire=encode_record(comparison)
results=[]
for cls in (TypeError,KeyError,AttributeError,UnicodeError,ValueError,KeyboardInterrupt):
    failure=cls('unexpected semantic Parameter reconstruction');cause=RuntimeError('cause');context=LookupError('context')
    failure.__cause__=cause;failure.__context__=context;failure.__suppress_context__=False
    def broken(*args,**kwargs):raise failure
    with patch.object(Parameter,'__post_init__',broken):
        try:decode_record(wire)
        except BaseException as exc:
            results.append({'injected':cls.__name__,'raised':type(exc).__name__,'same_object':exc is failure,'same_cause':exc.__cause__ is cause,'same_context':exc.__context__ is context,'suppression':exc.__suppress_context__,'original_object_cause_kept':failure.__cause__ is cause,'original_context_kept':failure.__context__ is context})
        else:results.append({'not_raised':cls.__name__})
print(json.dumps(results,indent=2))
