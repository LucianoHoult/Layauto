from pathlib import Path
import sys
REPOSITORY = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests/contracts"))

from dataclasses import replace
from pathlib import Path
from layauto_v2.importers import read_inputs
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.normalization import from_parse_result, normalize

def mutable(v):
    if isinstance(v, FrozenMap): return {k: mutable(x) for k,x in v.items()}
    if isinstance(v, tuple): return [mutable(x) for x in v]
    return v
p = read_inputs(REPOSITORY / 'tests/fixtures/w003_m1/site_config.yaml')
v=mutable(p.value)
mn,mp=v['source_cdl']['tops'][0]['devices']
mn['parameters']['NFIN'] = mp['parameters']['NFIN']
changed=replace(p,value=v,completed=tuple(replace(x,payload=v['source_cdl']) if x.kind=='source_cdl' else x for x in p.completed))
n=normalize(from_parse_result(changed))
print('same-capture cross-device parameter substitution:',n.status)
print([(d.id.name,[(p.axis,str(p.exact),p.source.line) for p in d.parameters if p.axis=='fins_per_finger']) for d in n.completed.source.cells[0].devices])
base=normalize(from_parse_result(p))
facts=base.completed
cell=facts.source.cells[0]
net=cell.nets[0]
other=next(x for x in cell.nets if x.id!=net.id)
wrong_net=replace(net,sources=other.sources)
changed_cell=replace(cell,nets=tuple(wrong_net if x.id==net.id else x for x in cell.nets))
wrong_source=replace(facts.source,cells=(changed_cell,))
wrong_facts=replace(facts,source=wrong_source)
wrong_result=replace(base,value=wrong_facts,completed=wrong_facts)
print('wrong-net provenance substitution:',wrong_result.status,net.id.name,wrong_net.sources)
v=mutable(p.value)
query=v['query']
for cap in ('instance_xref','device_regions'):
    for row in query[cap]['records']:
        row['schematic_instance']={'MN0':'MP0','MP0':'MN0'}[row['schematic_instance']]
changed=replace(p,value=v,completed=tuple(replace(x,payload=v['query']) if x.kind=='query' else x for x in p.completed))
n=normalize(from_parse_result(changed))
print('query value versus unchanged field source substitution:',n.status,[(x.query_key.identity,x.device_id.name) for x in n.completed.device_identities])
v=mutable(p.value)
q17,q93=v['query']['device_regions']['records']
q17['vertices_nm']=q93['vertices_nm']
q17['bbox_nm']=q93['bbox_nm']
changed=replace(p,value=v,completed=tuple(replace(x,payload=v['query']) if x.kind=='query' else x for x in p.completed))
n=normalize(from_parse_result(changed))
print('query geometry copied with unchanged field provenance:',n.status,[(x.query_key.identity,x.record['vertices_nm']) for x in n.completed.device_seeds])
revfacts=replace(base.completed,device_identities=tuple(reversed(base.completed.device_identities)))
rev=replace(base,value=revfacts,completed=revfacts)
from layauto_v2.normalization.codec import record_digest
print('unordered identity tuple permutation record digest:',record_digest(rev)==record_digest(base))
import tempfile
import sys
sys.path.insert(0, str(REPOSITORY / 'tests/contracts'))
from w005_cases import copy_input,apply_case,without_cache,rebind
from layauto_v2.normalization.contracts import NormalizationResult
with tempfile.TemporaryDirectory() as d:
    root=copy_input(Path(d))
    apply_case(root,'multifinger');without_cache(root);rebind(root)
    parsed=read_inputs(root/'site_config.yaml')
    error=normalize(from_parse_result(parsed))
    baseline=normalize(from_parse_result(read_inputs(root/'site_config.yaml')))
    forged=replace(error.completed,device_identities=base.completed.device_identities,net_identities=base.completed.net_identities,device_seeds=base.completed.device_seeds,net_seeds=base.completed.net_seeds)
    try:
        success=NormalizationResult('success',forged,(),forged,error.input)
        print('unsupported source error relabeled full success:',success.status)
    except Exception as e:
        print('unsupported source success rejected:',type(e).__name__,str(e))
