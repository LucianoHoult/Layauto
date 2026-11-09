import runpy,copy,json,time,resource
from dataclasses import replace
from pathlib import Path
start=time.monotonic()
ns=runpy.run_path('/workspace/work/w011-review-boundary-final/probe_owner.py')
from layauto_v2.domain.codec import canonical_bytes
control=ns['control'];forged=copy.deepcopy(control)
parameter=next(p for p in forged.source.cells[0].devices[0].parameters if p.axis=='finger_count')
old_line=parameter.source.line
object.__setattr__(parameter,'source',replace(parameter.source,line=999))
row={'head':'8917d38d916c914bfa785cb116982f3f299b38de','case':'unmeasured_source_parameter_provenance_projection','uses_object_setattr_bypass':True,'axis':parameter.axis,'original_line':old_line,'forged_line':parameter.source.line,'draft_equal':forged==control,'canonical_to_value_equal':canonical_bytes(forged.to_value())==canonical_bytes(control.to_value())}
try:replace(forged)
except BaseException as exc:row.update(public_draft_reconstruction_rejected=True,exception=type(exc).__name__,message=str(exc))
else:row['public_draft_reconstruction_rejected']=False
row.update(elapsed_seconds=time.monotonic()-start,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
print(json.dumps({'phase':'projection','result':row},indent=2),flush=True)
