"""Independent public neutral draft checks on a real W005/W008/W009/W010 chain."""
from dataclasses import fields, replace
from pathlib import Path
import copy,json,resource,subprocess,time
from fractions import Fraction
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import normalize,build_geometry,geometry_from_parse_result,build_effective_geometry,build_local_connectivity
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.channel_identity import ChannelSeed
from layauto_v2.domain.evidence import EvidenceRecord
from layauto_v2.derive.channel_identity import build_channel_identity_draft
started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat();start=time.monotonic();checks=[]
def unchecked(value,**changes):
    result=object.__new__(type(value))
    for f in fields(value):object.__setattr__(result,f.name,changes.get(f.name,getattr(value,f.name)))
    return result
def reject(name,fn):
    try:fn()
    except ValueError as e:checks.append({'name':name,'passed':True,'exception':type(e).__name__,'message':str(e)});return
    raise AssertionError(name+' accepted')
geometry_input=geometry_from_parse_result(read_inputs(Path('tests/fixtures/w003_m1/site_config.yaml')))
semantic=normalize(geometry_input.semantic_input);assert semantic.status=='success';facts=semantic.value
identities={i.device_id:i for i in facts.device_identities}
seeds=tuple(ChannelSeed(s.semantic_id,s.query_key,s.record,identities[s.semantic_id].provenance) for s in facts.device_seeds)
tech=next(record for record in geometry_input.parse.completed if record.kind=='tech')
derived=EvidenceRecord('derived',geometry_input.value['tech']['derived'],(tech.sources[2],))
local=build_local_connectivity(build_effective_geometry(build_geometry(geometry_input)))
assert local.status=='success';control=build_channel_identity_draft(local.value,facts.source,seeds,derived)
assert not control.issues and sorted(m.count for m in control.measurements)==[5,7]
checks.append({'name':'actual captured chain neutral control','passed':True,'counts':[m.count for m in control.measurements]})
for index,seed in enumerate(seeds):
    loc=seed.record['field_sources']['derived_layer']['sources'][1];changed=FrozenMap(dict(loc,lexeme=dict(loc['lexeme'],target_layer='METAL')));replacements=[]
    def mutate(v):
      if type(v) is FrozenMap:
        if v==loc:replacements.append(1);return changed
        return FrozenMap({k:mutate(x) for k,x in v.items()})
      if type(v) is tuple:return tuple(mutate(x) for x in v)
      return v
    altered=replace(seed,record=mutate(seed.record));newseeds=tuple(altered if i==index else s for i,s in enumerate(seeds))
    assert len(replacements)==3
    reject('CR06 registry operand same path/hash/pointer conflicting lexeme '+str(index),lambda:build_channel_identity_draft(local.value,facts.source,newseeds,derived))
    checks[-1].update(source_path=loc['path'],source_sha=loc['sha256'],source_pointer=loc['json_pointer'],copies_changed=len(replacements))
# Full source rebuild must include NF, which does not appear in measured comparisons.
selected=facts.source.cells[0];device=selected.devices[0];parameter=next(p for p in device.parameters if p.axis=='finger_count')
for label,line in [('different line',999),('equal Fraction line',Fraction(parameter.source.line))]:
    source=unchecked(parameter.source,line=line);p=unchecked(parameter,source=source)
    d=unchecked(device,parameters=tuple(p if x is parameter else x for x in device.parameters))
    cell=unchecked(selected,devices=tuple(d if x is device else x for x in selected.devices))
    circuit=unchecked(facts.source,cells=tuple(cell if x is selected else x for x in facts.source.cells))
    reject('CR04 unmeasured NF source '+label,lambda:build_channel_identity_draft(local.value,circuit,seeds,derived))
# Public aggregate cannot omit/alter decisions even when counts remain unchanged.
reject('draft omitted comparisons',lambda:replace(control,comparisons=control.comparisons[:-1]))
reject('draft omitted topology',lambda:replace(control,topology=control.topology[:-1]))
reject('draft omitted seed locations',lambda:replace(control,locations=control.locations[:-1]))
outside=next(fin for fin in control.measurements[0].evaluations if fin.status=='outside')
reject('draft omitted outside FIN verdict with unchanged count',lambda:replace(control,measurements=(replace(control.measurements[0],evaluations=tuple(fin for fin in control.measurements[0].evaluations if fin is not outside)),*control.measurements[1:])))
print(json.dumps({'started_utc':started_utc,'finished_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'python':__import__('sys').version,'checks':checks,'checks_count':len(checks),'elapsed_s':time.monotonic()-start,'ru_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'limits':'Real W005 through W010 plus public neutral draft only; no W011 captured Result/readback/complete wire benchmark.'},indent=2))
