from pathlib import Path
import sys,json,time,hashlib
from unittest.mock import patch
sys.path[:0]=['/workspace/work/w011-review-boundary','/workspace/work/w011-review-boundary/tests/contracts']
from w007_cases import ready_copy,edit,read
from w005_cases import rebind
from layauto_v2.normalization import build_geometry,geometry_from_parse_result,build_effective_geometry,build_local_connectivity,build_channel_identity
from layauto_v2.normalization import component
work=Path('/workspace/work/w011-review-boundary')
results=[]
for case, path, old,new,hook in [('admission','source.cdl','NF=1','NF=2','NormalizationResult'),('identity','query/raw/iXref.temp','0 Q17 0 MN0','0 Q17 0 UNKNOWN','replace')]:
    base=work/case;base.mkdir(exist_ok=True)
    root=ready_copy(base);edit(root,path,old,new);rebind(root)
    local=build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(read(root)))))
    assert local.status=='success'
    control=build_channel_identity(local)
    assert control.status=='error'
    row={'case':case,'expected_issue':control.issues[0].code,'status':control.status}
    failure=TypeError('unexpected '+hook+' during actual W007 error completion')
    cause=RuntimeError('original cause');context=LookupError('original context')
    failure.__cause__=cause;failure.__context__=context;failure.__suppress_context__=False
    def broken(*args,**kwargs):raise failure
    with patch.object(component,hook,broken):
        try:build_channel_identity(local)
        except BaseException as exc:
            row.update(exception_type=type(exc).__name__,same_object=exc is failure,same_cause=exc.__cause__ is cause,same_context=exc.__context__ is context,suppression=exc.__suppress_context__,actual_context_type=type(exc.__context__).__name__,actual_context_text=str(exc.__context__))
        else:row['not_raised']=True
    results.append(row)
    print(json.dumps(row),flush=True)
(work/'expected-results.json').write_text(json.dumps({'review_head':'f49323311bd817f066cb3e2411cad45219764f04','results':results},indent=2)+'\n')
