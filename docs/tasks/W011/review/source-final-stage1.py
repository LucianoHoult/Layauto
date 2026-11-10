from pathlib import Path
import hashlib, json, sys, tempfile, shutil, time, resource, copy
from dataclasses import replace
from fractions import Fraction
from unittest.mock import patch
from contextlib import ExitStack

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import geometry_from_parse_result, build_geometry, build_effective_geometry, build_local_connectivity, build_channel_identity
from layauto_v2.domain.codec import FrozenMap, canonical_bytes
from layauto_v2.domain.geometry import evidence_value

HEAD='8917d38d916c914bfa785cb116982f3f299b38de'
FIX=ROOT/'tests/fixtures/w003_m1'
started=time.monotonic()
def emit(**record): print(json.dumps(record,ensure_ascii=False,sort_keys=True),flush=True)
def check(name,condition):
    assert condition,name
    emit(check=name,result='PASS',seconds=time.monotonic()-started)
def reject(name,call):
    try: call()
    except ValueError as exc: emit(check=name,result='REJECTED',message=str(exc),seconds=time.monotonic()-started)
    else: raise AssertionError(name+' unexpectedly accepted')
def noio(*a,**k):raise AssertionError('unexpected IO')
def local(site):
    parsed=read_inputs(site)
    assert parsed.status=='success',parsed.issues
    value=build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(parsed))))
    assert value.status=='success'
    return value
def bind(root):
    p=root/'query/header.json'; h=json.loads(p.read_text())
    for item in [h['layout'],h['source_netlist'],h['target'],*h['raw'],*h['closure']['entries']]:
        q=root/item['uri']
        if q.exists():item['sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
    h['closure']['entries'].sort(key=lambda x:x['uri'])
    h['closure']['sha256']=hashlib.sha256(json.dumps(h['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    p.write_text(json.dumps(h,indent=2)+'\n')
def change_at(value,path,replacement):
    if not path:return replacement
    assert path[0] in value
    return FrozenMap({key:change_at(item,path[1:],replacement) if key==path[0] else item for key,item in value.items()})
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'layauto_v2').rglob('*.py'))}
(ROOT/'source-manifest.json').write_text(json.dumps({'head':HEAD,'sha256':manifest},indent=2)+'\n')
emit(stage='identity',head=HEAD,python=sys.version,executable=sys.executable,cwd=str(Path.cwd()),source_manifest='source-manifest.json')
base=local(FIX/'site_config.yaml')
with ExitStack() as stack:
    for name in ('read_bytes','read_text','open'):stack.enter_context(patch.object(Path,name,noio))
    result=build_channel_identity(base)
check('normal_pure_builder',result.status=='success')
draft=result.value
check('normal_counts_and_all_comparisons',sorted(row.count for row in draft.measurements)==[5,7] and len(draft.comparisons)==16 and not draft.differences)
check('original_topology_audits_body',draft.local==base.value and result.body_evidence==base.body_evidence)
for value,label in [(999,'changed_line'),(Fraction(3),'equal_fraction_line')]:
    forged=copy.deepcopy(draft)
    parameter=next(p for c in forged.source.cells for d in c.devices if d.id.name=='MN0' for p in d.parameters if p.axis=='finger_count')
    old=parameter.source
    bad=copy.deepcopy(old);object.__setattr__(bad,'line',value)
    object.__setattr__(parameter,'source',bad)
    check('projection_omits_'+label,canonical_bytes(forged.to_value())==canonical_bytes(draft.to_value()))
    reject('complete_public_result_'+label,lambda:replace(result,value=forged))
tech=next(item for item in result.completed if item.kind=='tech')
bad=replace(tech,payload=change_at(tech.payload,('owners','physical','fin_count_profile','finger_count_required'),True))
check('completed_python_equal_but_wire_diff',bad==tech and canonical_bytes(evidence_value(bad))!=canonical_bytes(evidence_value(tech)))
reject('completed_wrong_scalar_type',lambda:replace(result,completed=tuple(bad if item is tech else item for item in result.completed)))
with tempfile.TemporaryDirectory(dir=ROOT) as td:
    target=Path(td)/'target';shutil.copytree(FIX,target)
    p=target/'target.cdl';p.write_text(p.read_text().replace('NFIN=5','NFIN=6').replace('L=4n','L=5n').replace('W=2n','W=3n').replace('NF=1','NF=2').replace('M=1','M=2'));bind(target)
    tr=build_channel_identity(local(target/'site_config.yaml'))
    check('target_source_comparison_separate',tr.status=='success' and tr.value.comparison_status=='equal' and not tr.value.differences)
    check('target_five_axes_preserved',{x.axis for x in tr.semantic.value.differences}=={'fins_per_finger','channel_length','fin_width','finger_count','multiplicity'})
    check('target_measured_counts_unchanged',sorted(x.count for x in tr.value.measurements)==[5,7])
    reject('foreign_semantic_result',lambda:replace(result,semantic=tr.semantic))
    reject('foreign_draft',lambda:replace(result,value=tr.value))
    reject('foreign_completed',lambda:replace(result,completed=tr.completed))
    source=Path(td)/'source';shutil.copytree(FIX,source)
    p=source/'source.cdl';p.write_text(p.read_text().replace('NFIN=5','NFIN=6').replace('L=4n','L=5n').replace('W=2n','W=3n'));bind(source)
    sr=build_channel_identity(local(source/'site_config.yaml'))
    check('source_mismatch_success',sr.status=='success' and sr.value.comparison_status=='mismatch')
    diff=sr.value.differences
    check('all_15_source_differences',len(diff)==15 and sum(x.axis=='fin_width' for x in diff)==12 and sum(x.axis=='channel_length' for x in diff)==2 and sum(x.axis=='fins_per_finger' for x in diff)==1)
    check('exact_measured_source_values',{x.measured for x in diff if x.axis=='channel_length'}=={Fraction(4,10**9)} and {x.measured for x in diff if x.axis=='fin_width'}=={Fraction(2,10**9)})
reject('drop_comparison',lambda:replace(draft,comparisons=draft.comparisons[1:]))
reject('drop_local_audit',lambda:replace(draft.local,audits=draft.local.audits[1:]))
reject('fake_error_status',lambda:replace(result,status='error'))
emit(stage='done',seconds=time.monotonic()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
