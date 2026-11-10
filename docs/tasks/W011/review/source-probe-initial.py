from pathlib import Path
import hashlib, json, sys, tempfile, shutil, time
from dataclasses import replace
from fractions import Fraction
from unittest.mock import patch
from contextlib import ExitStack
sys.path.insert(0, '/workspace/Layauto')
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (geometry_from_parse_result, geometry_from_inputs_ready, build_geometry,
    build_effective_geometry, build_local_connectivity, build_channel_identity)
from layauto_v2.normalization.channel_identity_codec import encode_record, decode_record
from layauto_v2.domain.publication import RunRequest, InputsReady
from layauto_v2.repository import PublicationRepository
from layauto_v2.pipeline import prepare_inputs

ROOT=Path('/workspace/Layauto'); FIX=ROOT/'tests/fixtures/w003_m1'
checks=[]
def check(name, condition):
    assert condition, name
    checks.append(name)
def local(site):
    parsed=read_inputs(site)
    check(str(site)+':read',parsed.status=='success')
    result=build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(parsed))))
    check(str(site)+':local',result.status=='success')
    return result
def reject(name, fn):
    try: fn()
    except ValueError: checks.append(name)
    else: raise AssertionError('accepted '+name)
def bind(root):
    header_path=root/'query/header.json'; header=json.loads(header_path.read_text())
    for item in [header['layout'],header['source_netlist'],header['target'],*header['raw'],*header['closure']['entries']]:
        p=root/item['uri']
        if p.exists(): item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    header['closure']['entries'].sort(key=lambda x:x['uri'])
    header['closure']['sha256']=hashlib.sha256(json.dumps(header['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    header_path.write_text(json.dumps(header,indent=2)+'\n')
def noio(*args, **kwargs):raise AssertionError('unexpected IO')
started=time.time()
b=local(FIX/'site_config.yaml')
r=build_channel_identity(b)
check('normal_complete',r.status=='success' and len(r.value.associations)==2)
d=r.value
ms={m.channel_ref:m for m in d.measurements}
check('normal_counts',{a.device_id.name:ms[a.channel_ref].count for a in d.associations}=={'MN0':5,'MP0':7})
check('normal_exact_width_length',all(m.length_nm==4 and all(x.width_nm==2 for x in m.crossings) for m in d.measurements))
check('source_comparison',len(d.comparisons)==16 and not d.differences and d.comparison_status=='equal')
check('raw_fin',sum(x.layer=='FIN' for x in b.value.effective.base.layout.records)==18)
check('original_topology_audit',d.local==b.value and d.local.audits==b.value.audits)
check('normal_body',r.body_evidence==b.body_evidence)
repo=PublicationRepository(); req=RunRequest('independent-w011-review','review-lineage','create-review',str((FIX/'site_config.yaml').resolve()))
ready=prepare_inputs(repo,req);check('ready',isinstance(ready,InputsReady))
checkpoint=repo.load_checkpoint(ready.run_id);pa=repo.read(ready.parse_ref);tool=repo.read(ready.tool_ref);evidence=tuple(repo.read(x) for x in ready.evidence_refs);attempt=repo.load_attempt(ready.run_id)
back=build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_inputs_ready(ready,checkpoint,pa,tool,evidence))))
with ExitStack() as stack:
    for name in ('read_bytes','read_text','open'):stack.enter_context(patch.object(Path,name,noio))
    stack.enter_context(patch.object(repo,'read',noio))
    rb=build_channel_identity(back)
    check('readback_semantic_and_draft',rb.value==d and rb.semantic.value==r.semantic.value)
    restored=decode_record(encode_record(rb))
    check('readback_wire',restored==rb)
check('attempt_unsealed_unchanged',repo.load_attempt(ready.run_id)==attempt and attempt.phase=='unsealed')
with tempfile.TemporaryDirectory(dir='/workspace/work/w011-review') as td:
    root=Path(td)/'target';shutil.copytree(FIX,root)
    p=root/'target.cdl';s=p.read_text();assert 'NFIN=5' in s;s=s.replace('NFIN=5','NFIN=6').replace('L=4n','L=5n').replace('VT=toy','VT=alternate');p.write_text(s);bind(root)
    tr=build_channel_identity(local(root/'site_config.yaml'))
    check('target_separate_status',tr.status=='success' and tr.value.comparison_status=='equal' and not tr.value.differences)
    check('target_deltas_complete',{x.axis for x in tr.semantic.value.differences}=={'fins_per_finger','channel_length','threshold_token'})
    check('target_measurements_unchanged',sorted(m.count for m in tr.value.measurements)==[5,7])
    reject('foreign_semantic_result',lambda:replace(r,semantic=tr.semantic))
    reject('foreign_draft',lambda:replace(r,value=tr.value))
    reject('foreign_completed',lambda:replace(r,completed=tr.completed))
    root2=Path(td)/'source';shutil.copytree(FIX,root2)
    p=root2/'source.cdl';s=p.read_text().replace('NFIN=5','NFIN=6').replace('L=4n','L=5n').replace('W=2n','W=3n');p.write_text(s);bind(root2)
    sr=build_channel_identity(local(root2/'site_config.yaml'))
    check('source_mismatch_success',sr.status=='success' and sr.value.comparison_status=='mismatch')
    diff=sr.value.differences
    check('all_decidable_mismatches',len(diff)==15 and sum(x.axis=='fin_width' for x in diff)==12 and sum(x.axis=='channel_length' for x in diff)==2 and sum(x.axis=='fins_per_finger' for x in diff)==1)
    check('measured_source_values',{x.measured for x in diff if x.axis=='channel_length'}=={Fraction(4,10**9)} and {x.measured for x in diff if x.axis=='fin_width'}=={Fraction(2,10**9)})
reject('drop_comparison',lambda:replace(d,comparisons=d.comparisons[1:]))
reject('drop_local_audit',lambda:replace(d.local,audits=d.local.audits[1:]))
reject('fake_error',lambda:replace(r,status='error'))
print(json.dumps({'checks':checks,'count':len(checks),'elapsed_seconds':time.time()-started,'candidate_head':'f493233','python':sys.version},indent=2))
