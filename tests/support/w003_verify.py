"""Read-only independent checks for the fixed W003 fixture, not a product API."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import klayout.db as kdb
from w004_support import load_tech, bindings, canonical
from w004_query import CAPS, normalize, verify_backlinks
from w004_body import check_body


def read(path: Path) -> dict:
    def unique(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            assert key not in result, f"duplicate JSON key {key}"
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_float=lambda _: (_ for _ in ()).throw(ValueError("binary float forbidden")),
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite forbidden")))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rational(f: Fraction) -> dict:
    return {"numerator":str(f.numerator), "denominator":str(f.denominator)}


def records(path: Path) -> list[tuple[int, int, bytes]]:
    data=path.read_bytes(); offset=0; result=[]
    while offset < len(data):
        length, kind, dtype=struct.unpack('>HBB',data[offset:offset+4])
        assert length >=4 and length%2==0 and offset+length<=len(data)
        result.append((kind,dtype,data[offset+4:offset+length]));offset+=length
    assert offset==len(data) and result[-1][0]==4
    return result


def decode_real8(raw: bytes) -> Fraction:
    sign=-1 if raw[0]&128 else 1
    exponent=(raw[0]&127)-64
    return sign*Fraction(int.from_bytes(raw[1:],'big'),1<<56)*Fraction(16)**exponent


def units(path: Path, contract: dict) -> list[dict]:
    raw=next(payload for kind,_,payload in records(path) if kind==3)
    result=[]
    assert contract['id']=='toy_gds_real8_nm/1' and contract.get('nominal_source',{}).get('identity')=='w004-toy-unit-choice/2','UnitSourceMissing'
    def q(v):return Fraction(int(v['numerator']),int(v['denominator']))
    assert q(contract['nominal_tick_m'])==Fraction(1,1000000000),'UnitSourceConflict'
    assert q(contract['nominal_user_unit_m'])==Fraction(1,1000000) and q(contract['gds_units_first_nominal'])==q(contract['nominal_tick_m'])/q(contract['nominal_user_unit_m']) and Fraction(contract['canonical_tick_nm'])==q(contract['nominal_tick_m'])*1000000000,'UnitContractConflict'
    for offset,nominal in [(0,q(contract['gds_units_first_nominal'])),(8,q(contract['nominal_tick_m']))]:
        field=raw[offset:offset+8];decoded=decode_real8(field);exponent=(field[0]&127)-64
        nominal_exponent=0;normalized=nominal
        while normalized>=1:normalized/=16;nominal_exponent+=1
        while normalized<Fraction(1,16):normalized*=16;nominal_exponent-=1
        bound=Fraction(16)**exponent/Fraction(1<<57)
        assert exponent==nominal_exponent and abs(decoded-nominal)<=bound, 'UnitScaleMismatch'
        result.append({'raw_hex':field.hex(),'decoded':rational(decoded),'nominal':rational(nominal),'delta':rational(decoded-nominal),'allowed_half_ulp':rational(bound)})
    return result


def parse_cdl(path: Path, tech: dict) -> dict:
    assert tech['cdl_dialect']['numeric_suffixes']=={'n':{'numerator':'1','denominator':'1000000000'}},'CdlUnitContractConflict'
    assert not any(l.upper().startswith(('.INCLUDE','.LIB')) for l in path.read_text().splitlines()), 'UnsupportedDependencyDirective'
    rows=[l.split() for l in path.read_text().splitlines() if l and not l.startswith('*')]
    assert rows[0][0]=='.SUBCKT' and rows[-1]==['.ENDS',rows[0][1]]
    result={'cell':rows[0][1],'pins':rows[0][2:],'globals':[],'devices':[]}
    for row in rows[1:-1]:
        assert len(row)==12 and row[5] in tech['models'], 'UnsupportedCdl'
        model=tech['models'][row[5]]
        assert model['terminal_order']==list('DGSB') and not model['sd_symmetry']
        assert model['parameter_axes']=={'NFIN':'fins_per_finger','NF':'finger_count','M':'multiplicity','L':'channel_length','W':'fin_width','VT':'threshold_token'},'UnsupportedModelAxes'
        assert model['default_parameters']=={} and tech['cdl_dialect']['models_ref']=='physical.json#/models'
        pairs=[v.split('=') for v in row[6:]];assert all(len(v)==2 for v in pairs),'UnsupportedCdlExpression'
        params=dict(pairs);assert len(params)==len(pairs) and set(params)==set(model['required_parameters'])
        assert all(re.fullmatch(r'[1-9][0-9]*',params[k]) for k in ['NFIN','NF','M']),'UnsupportedCdlExpression'
        assert all(re.fullmatch(r'[1-9][0-9]*n',params[k]) for k in ['L','W']) and params['VT']=='toy'
        result['devices'].append({'id':row[0],'model':row[5],'terminals':dict(zip(model['terminal_order'],row[1:5])),'parameters':{'fins_per_finger':int(params['NFIN']),'finger_count':int(params['NF']),'multiplicity':int(params['M']),'L_nm':int(params['L'][:-1]),'W_nm':int(params['W'][:-1]),'VT':params['VT']}})
    return result


def layout_shapes(path: Path, spec: dict, tech: dict) -> dict[str,list[int]]:
    layout=kdb.Layout();layout.read(str(path));tops=list(layout.top_cells())
    assert len(tops)==1 and tops[0].name==spec['cell'] and layout.cells()==1
    actual=[]
    for index in layout.layer_indexes():
        info=layout.get_info(index)
        for shape in tops[0].shapes(index).each():
            assert shape.is_box() or (shape.is_polygon() and shape.polygon.is_box()), 'UnsupportedNonrectangle'
            box=shape.bbox();actual.append((info.layer,info.datatype,box.left,box.bottom,box.right,box.top))
    keys={v['name']:v['stream_key']['layer'] for v in tech['layers']}
    expected=[(keys[s['layer']],0,*s['bbox']) for s in spec['shapes']]
    assert Counter(actual)==Counter(expected),'GdsGeometryMismatch'
    # Id assignment is only the one-to-one equality join to handwritten table.
    return {s['id']:s['bbox'] for s in spec['shapes']}


def box(rect: list[int]) -> kdb.Region:
    return kdb.Region(kdb.Box(*rect))


def rectangles(region: kdb.Region) -> list[list[int]]:
    out=[]
    for poly in region.each_merged():
        assert poly.is_box(),'expected toy Boolean result must remain rectangle'
        b=poly.bbox();out.append([b.left,b.bottom,b.right,b.top])
    return sorted(out)


def encl(outer: list[int], inner: list[int]) -> int:
    return min(inner[0]-outer[0],inner[1]-outer[1],outer[2]-inner[2],outer[3]-inner[3])


def distance2(a: list[int], b: list[int]) -> int:
    dx=max(a[0]-b[2],b[0]-a[2],0);dy=max(a[1]-b[3],b[1]-a[3],0)
    return dx*dx+dy*dy


def physics(spec: dict, oracle: dict, tech: dict) -> dict:
    shapes={s['id']:s['bbox'] for s in spec['shapes']}
    by_layer={n:[s['id'] for s in spec['shapes'] if s['layer']==n] for n in {s['layer'] for s in spec['shapes']}}
    crossing_results=[];failures=[]
    for item in oracle['crossings']:
        channel=box(shapes[item['active']])&box(shapes['G'])
        assert rectangles(channel)==[item['channel_bbox']]
        selected=[]
        for fid in by_layer['FIN']:
            hit=box(shapes[fid])&channel
            if not hit.is_empty():
                selected.append(fid);assert hit.area()==8
        if selected!=item['fin_ids']:failures.append('T03.recognition')
        crossing_results.append({'device':item['device'],'fin_ids':selected,'count':len(selected),'total_channel_fin_area_nm2':len(selected)*8})
    effective={s['id']:{'bbox':s['bbox'],'layer':s['layer']} for s in spec['shapes'] if s['layer'] in ('BODY_N','BODY_P','POLY','M1')}
    for drawn,prefix in [('ON','ON'),('OP','OP')]:
        parts=rectangles(box(shapes[drawn])-box(shapes['G']))
        assert len(parts)==2
        for suffix,part in zip(['S','D'],parts):effective[prefix+'.'+suffix]={'bbox':part,'layer':'OD'}
    cut=kdb.Region()
    for sid in by_layer.get('CUT',[]):cut |= box(shapes[sid])
    for drawn in by_layer['LI']:
        parts=rectangles(box(shapes[drawn])-cut)
        for suffix,part in zip(['.left','.right'] if len(parts)==2 else [''],parts):effective[drawn+suffix]={'bbox':part,'layer':'LI'}
    for fragment in oracle['fragments']:assert effective[fragment['id']]['bbox']==fragment['bbox']
    parent={key:key for key in effective}
    def find(key: str) -> str:
        while parent[key]!=key:key=parent[key]
        return key
    def union(a: str,b: str) -> None:parent[find(a)]=find(b)
    direct=[];keys=list(effective)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            ra,rb=effective[a],effective[b]
            if ra['layer']!=rb['layer']:continue
            ax0,ay0,ax1,ay1=ra['bbox'];bx0,by0,bx1,by1=rb['bbox']
            ix=min(ax1,bx1)-max(ax0,bx0);iy=min(ay1,by1)-max(ay0,by0)
            if (ix>0 and iy>=0) or (iy>0 and ix>=0):union(a,b);direct.append([a,b])
    edges=[];margins=[]
    for layer in tech['layers']:
        if 'electrical_connects' not in layer:continue
        for connector in by_layer.get(layer['name'],[]):
            ends=[]
            for target in layer['electrical_connects']:
                touched=[rid for rid,r in effective.items() if r['layer']==target and not (box(r['bbox'])&box(shapes[connector])).is_empty()]
                if len(touched)!=1:failures.append('T05.contact_enclosure');continue
                ends.append(touched[0]);margins.append(encl(effective[touched[0]]['bbox'],shapes[connector]))
            if len(ends)==2:union(*ends);edges.append({'connector':connector,'ends':ends});direct.append(ends)
    assert sorted(edges,key=lambda x:x['connector'])==sorted(oracle['edges'],key=lambda x:x['connector'])
    components=sorted(sorted(k for k in effective if find(k)==root) for root in {find(k) for k in effective})
    assert components==sorted(sorted(c['regions']) for c in oracle['components'])
    for a,b in oracle['non_edges']:assert [a,b] not in direct and [b,a] not in direct
    rr={r['id']:r for r in tech['rules']}
    if min(margins)<rr['T05.contact_enclosure']['parameters']['enclosure_nm']:failures.append('T05.contact_enclosure')
    minimum={}
    for layer,threshold,rid in [('LI',rr['T06.li_spacing']['parameters']['min_distance_nm'],'T06.li_spacing'),('M1',rr['T07.m1_spacing']['parameters']['min_distance_nm'],'T07.m1_spacing')]:
        regions=[v['bbox'] for v in effective.values() if v['layer']==layer]
        distances=[distance2(a,b) for i,a in enumerate(regions) for b in regions[i+1:]]
        minimum[layer]={'pairs':len(distances),'minimum_squared_distance_nm2':min(distances)}
        if min(distances)<threshold**2:failures.append(rid)
    if any(encl(shapes['FRAME'],s['bbox'])<0 for s in spec['shapes']):failures.append('T01.frame')
    fins=sorted(shapes[f] for f in by_layer['FIN']);ys=sorted(r[1] for r in fins)
    assert len(fins)==18 and all(r[0]==10 and r[2]==110 and r[3]-r[1]==tech['fin_count_profile']['fin_width_nm'] for r in fins)
    assert ys==list(range(tech['fin_count_profile']['fin_lower_edge_offset_nm'],195,tech['fin_count_profile']['fin_pitch_nm']))
    assert encl(shapes['BN'],shapes['ON'])>=rr['T04.body']['parameters']['active_enclosure_nm'] and encl(shapes['BP'],shapes['OP'])>=rr['T04.body']['parameters']['active_enclosure_nm']
    assert (box(shapes['BN'])&box(shapes['BP'])).is_empty()
    for terminal in oracle['terminals']:
        component=next(c for c in oracle['components'] if terminal['region'] in c['regions'])
        assert component['id']==terminal['component']
        if terminal['role']!='B':assert component['net']==terminal['net']
        else:assert component['net'] is None
        dev=next(d for d in oracle['semantic']['devices'] if d['id']==terminal['device'])
        assert dev['terminals'][terminal['role']]==terminal['net']
    # Independently join actual synthetic query identities and exact regions.
    ix={r['layout_instance']:r['schematic_instance'] for r in spec['instance_xref']}
    nx={r['lvs_index']:r['schematic_name'] for r in spec['net_xref']}
    assert len(ix)==len(set(ix.values()))==2 and not any(r['sd_swap'] for r in spec['instance_xref'])
    registry={r['id']:r['target_layer'] for r in tech['derived_registry']}
    for r in spec['device_regions']:
        crossing=next(c for c in oracle['crossings'] if c['device']==ix[r['layout_instance']])
        assert registry[r['derived_layer']]=='POLY' and list(map(int,r['bbox_lexemes']))==crossing['channel_bbox']
    for r in spec['net_regions']:
        targets=[rid for rid,value in effective.items() if value['layer']==registry[r['derived_layer']] and value['bbox']==list(map(int,r['bbox_lexemes']))]
        assert len(targets)==1,'ambiguous exact synthetic annotation'
        component=next(c for c in oracle['components'] if targets[0] in c['regions'])
        assert component['net']==nx[r['lvs_index']]
    assert len(spec['shapes'])==oracle['drawn_shape_count']==40
    return {'crossings':crossing_results,'fragment_count_witnesses':len(oracle['fragments']),'physical_component_count':len(components),'qualified_connector_edges':len(edges),'independent_exact_net_annotations':len(spec['net_regions']),'independent_device_joins':len(ix),'minimum_contact_enclosure_nm':min(margins),'spacing':minimum,'mandatory_rule_failures':sorted(set(failures))}


def actual_shapes(path, spec, tech):
    """Read actual stream and join stable toy object ids by declared record order.
    Normal exact comparison uses KLayout separately; variants preserve order.
    """
    names={r['stream_key']['layer']:r['name'] for r in tech['layers']};result=[];layer=None
    for kind,dtype,payload in records(path):
        assert kind!=12,'UnsupportedGdsElement:TEXT'
        if kind==13:layer=names[struct.unpack('>h',payload)[0]]
        if kind==16:
            points=list(zip(*[iter(struct.unpack('>'+str(len(payload)//4)+'i',payload))]*2))
            assert len(points)==5 and points[0]==points[-1] and len(set(points[:-1]))==4,'UnsupportedNonrectangle'
            xs={x for x,y in points};ys={y for x,y in points}
            assert len(xs)==len(ys)==2 and all((points[i][0]==points[i+1][0]) != (points[i][1]==points[i+1][1]) for i in range(4)),'UnsupportedNonrectangle'
            result.append({'id':spec['shapes'][len(result)]['id'],'layer':layer,'bbox':[min(xs),min(ys),max(xs),max(ys)]})
    assert len(result)==len(spec['shapes'])
    return result

def raw_answers(root,spec):
    total=0;counts={}
    for cap in CAPS:
        cache=read(root/f'query/normalized/{cap}.yaml');parsed=normalize(root,cap)
        assert parsed==cache,'NormalizedCacheMismatch'
        total+=verify_backlinks(root,cache);counts[cap]=len(parsed['records'])
        stripped=[]
        for row in parsed['records']:
            if cap=='instance_xref':d={k:row[k] for k in ['layout_instance','schematic_instance','sd_swap']}
            elif cap=='net_xref':d={k:row[k] for k in ['lvs_index','lvs_name','schematic_name']}
            else:
                d={k:row[k] for k in ['record_id','derived_layer','geometry_kind','quality','unit']}
                key='layout_instance' if cap=='device_regions' else 'lvs_index';d[key]=row[key]
                vals=[Fraction(int(row['bbox_nm'][k]['numerator']),int(row['bbox_nm'][k]['denominator'])) for k in ['x_min','y_min','x_max','y_max']]
                assert all(v.denominator==1 for v in vals);d['bbox_lexemes']=[str(v.numerator) for v in vals]
            stripped.append(d)
        assert stripped==spec[cap],('IndependentHandTableMismatch',cap)
    return {'counts':counts,'backlinks_checked':total}

def witness(world,spec):
    """Detect the first actual fixture defect; no selection by case id."""
    h=bindings(world,allow_missing_context=not (world/'body/context.json').exists())
    t=load_tech(world)
    assert 'body_context/2' in t['operators'],'RequiredBodyOperatorUnavailable'
    assert (world/'body/context.json').exists(),'RequiredBodyContextUnavailable'
    units(world/'source.gds',t['unit_scale_contract']);ss=actual_shapes(world/'source.gds',spec,t)
    data={}
    for cap in CAPS:
        data[cap]=normalize(world,cap)
        p=world/f'query/normalized/{cap}.yaml'
        if p.exists():assert read(p)==data[cap],'NormalizedCacheMismatch'
    ix=data['instance_xref']['records'];assert len(ix)<=2,'UnsupportedDeviceReduction'
    assert len({r['schematic_instance'] for r in ix})==len(ix),'UnsupportedDeviceCardinality'
    source=parse_cdl(world/'source.cdl',t);target=parse_cdl(world/'target.cdl',t)
    assert all(d['parameters']['finger_count']==1 for d in source['devices']),'UnsupportedFingerCount'
    assert source==target,'UnsupportedTargetAxis'
    sm={x['id']:x for x in ss}
    check_body(world,sm,t,source)
    for active,count in [('ON',5),('OP',7)]:
        channel=box(sm[active]['bbox'])&box(sm['G']['bbox'])
        n=sum(not (box(x['bbox'])&channel).is_empty() for x in ss if x['layer']=='FIN')
        assert n==count,'ExtractionCountMismatch'
    rr={r['id']:r for r in t['rules']}
    # Exact independent witness checks on changed geometry, without oracle equality.
    for layer in t['layers']:
        if 'electrical_connects' not in layer:continue
        for s in ss:
            if s['layer']!=layer['name']:continue
            for target_layer in layer['electrical_connects']:
                hits=[x for x in ss if x['layer']==target_layer and not (box(s['bbox'])&box(x['bbox'])).is_empty()]
                assert len(hits)==1 and encl(hits[0]['bbox'],s['bbox'])>=rr['T05.contact_enclosure']['parameters']['enclosure_nm'],'MandatoryRuleViolation:T05.contact_enclosure'
    metals=[x['bbox'] for x in ss if x['layer']=='M1']
    assert all(distance2(a,b)>=rr['T07.m1_spacing']['parameters']['min_distance_nm']**2 for i,a in enumerate(metals) for b in metals[i+1:]),'MandatoryRuleViolation:T07.m1_spacing'
    tick=read(world/'export_policy.json')['gds_tick_nm'];tick=Fraction(int(tick['numerator']),int(tick['denominator']))
    values=[Fraction(v)/tick for x in ss for v in x['bbox']]
    assert all(v.denominator==1 for v in values),'OutputCoordinateNotRepresentable'
    assert all(-(1<<31)<=v<(1<<31) for v in values),'OutputCoordinateOverflow'
    return 'no_defect'

def overlays(root,spec,work):
    import shutil
    results=[]
    for case in read(root/'failures/cases.json')['cases']:
        world=work/case['id'];shutil.copytree(root,world,ignore=shutil.ignore_patterns('failures'))
        for dst,src in case['replacement_files'].items():
            assert (root/'failures'/src).is_file();(world/dst).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'failures'/src,world/dst)
        for path in case['remove_files']:assert (world/path).is_file();(world/path).unlink()
        bind_status='intentional top/raw defect' if case['id'] in ['raw_byte_drift','header_top_mismatch'] else 'all actual dependency bytes bound'
        if case['id'] not in ['raw_byte_drift','header_top_mismatch']:bindings(world,allow_missing_context=case['id']=='missing_body_context')
        try:got=witness(world,spec)
        except AssertionError as e:got=str(e)
        assert got==case['expected_issue'],(case['id'],got,case['expected_issue'])
        results.append({'original_id':case['original_id'],'id':case['id'],'replacements':case['replacement_files'],'removals':case['remove_files'],'expected_issue':case['expected_issue'],'observed_witness':got,'phase_expectation':case['phase'],'binding_check':bind_status,'materialized_directory':str(world),'product_run':False})
    return results

def special(root,tech):
    p=root/'special/cut_islands';s=read(p/'spec.json');o=read(p/'oracle.json');layout_shapes(p/'source.gds',s,tech)
    m={x['id']:x['bbox'] for x in s['shapes']};parts=rectangles(box(m['LB'])-box(m['CUTB']))
    assert parts==[x['bbox_nm'] for x in o['fragments'][:2]]
    assert distance2(*parts)==4 and sum(box(b).area() for b in parts)==72
    assert all(encl(o['common_bucket'],b)>=0 for b in parts)
    b=m['A_REMOTE'];dist=sorted([distance2(parts[0],parts[1]),distance2(parts[0],b),distance2(parts[1],b)])
    assert dist==sorted(o['all_pair_distance_squared_nm2']);assert o['component_count']==3 and o['edges']==[]
    return {'drawn':len(s['shapes']),'fragments':3,'physical_components':3,'connector_edges':0,'same_label':'A','same_cell_is_not_edge':True,'spacing_squared_nm2':dist}

def xy_provenance(path,spec,tech):
    """Actual byte positions and exact original XY-to-nominal source backlink."""
    data=path.read_bytes();offset=0;layer=None;items=[]
    mapping={x['name']:x['stream_key']['layer'] for x in tech['layers']}
    expected={(mapping[x['layer']],tuple(x['bbox'])):x['id'] for x in spec['shapes']}
    while offset<len(data):
        length,kind,dtype=struct.unpack('>HBB',data[offset:offset+4]);payload=data[offset+4:offset+length]
        if kind==13:layer=struct.unpack('>h',payload)[0]
        if kind==16:
            xy=list(struct.unpack('>'+str(len(payload)//4)+'i',payload));xs=xy[::2];ys=xy[1::2]
            sid=expected[(layer,(min(xs),min(ys),max(xs),max(ys)))]
            items.append({'shape_id':sid,'byte_range':[offset+4,offset+length],'raw_hex':payload.hex(),'original_xy_integer_ticks':xy,'nominal_tick_m':tech['unit_scale_contract']['nominal_tick_m'],'canonical_xy_nm':xy,'unit_owner':'tech/formats.json#/unit_scale_contract','source_dbu_backlink':{'file':path.name,'sha256':sha(path),'UNITS_kind':3},'coordinate_delta_nm':0})
        offset+=length
    assert len(items)==40
    return items


def contract_conflicts(root,spec,work):
    """Actual isolated selected-owner mutations with correct leaf/closure bytes."""
    import shutil
    from w004_support import bind_header,write
    trials=[('header_axis','query/header.json','QueryUnitDeclarationConflict'),
            ('dialect_precision','query/dialect.json','QueryUnitDeclarationConflict'),
            ('derived_quality','tech/derived.json','QueryQualityDeclarationConflict'),
            ('unit_source_missing','tech/formats.json','UnitSourceMissing'),
            ('unit_source_conflict','tech/formats.json','UnitSourceConflict'),
            ('duplicate_output_conflict','site_config.yaml','ConflictingDuplicatePolicy'),
            ('cdl_suffix_conflict','tech/formats.json','CdlUnitContractConflict'),
            ('user_unit_conflict','tech/formats.json','UnitContractConflict'),
            ('canonical_tick_conflict','tech/formats.json','UnitContractConflict')]
    results=[]
    for name,path,expected in trials:
        w=work/('contract-'+name);shutil.copytree(root,w,ignore=shutil.ignore_patterns('failures'))
        d=read(w/path)
        if name=='header_axis':d['query_unit']['axis_order']=['x','y']
        if name=='dialect_precision':d['geometry']['precision']=10000;d['geometry']['raw_tick_nm']={'numerator':'1','denominator':'10'}
        if name=='derived_quality':d['derived_registry'][0]['quality']='approximate_bbox'
        if name=='unit_source_missing':d['unit_scale_contract'].pop('nominal_source')
        if name=='unit_source_conflict':d['unit_scale_contract']['nominal_tick_m']={'numerator':'2','denominator':'1000000000'}
        if name=='duplicate_output_conflict':d['outputs']['directory']='different'
        if name=='cdl_suffix_conflict':d['cdl_dialect']['numeric_suffixes']['n']={'numerator':'2','denominator':'1000000000'}
        if name=='user_unit_conflict':d['unit_scale_contract']['nominal_user_unit_m']={'numerator':'2','denominator':'1000000'}
        if name=='canonical_tick_conflict':d['unit_scale_contract']['canonical_tick_nm']=2
        write(w/path,d)
        write(w/'query/header.json',bind_header(w,read(w/'query/header.json')))
        try:actual=witness(w,spec)
        except AssertionError as e:actual=str(e)
        assert actual==expected,(name,actual,expected)
        results.append({'id':name,'actual_issue':actual,'input':path,'actual_sha256':sha(w/path),'closure_rebound':True,'materialized_directory':str(w),'product_run':False})
    return results


def verify(root,regenerated,work):
    spec,oracle=[read(root/n) for n in ['spec.json','oracle.json']];tech=load_tech(root)
    evidence={p:units(root/p,tech['unit_scale_contract']) for p in ['source.gds','expected/output.gds']}
    prov=read(root/'expected/unit-provenance.json');reconstructed=bytearray((root/'expected/output.gds').read_bytes())
    start,end=prov['modified_byte_range'];reconstructed[start:end]=bytes.fromhex(prov['original_units_hex'])
    assert hashlib.sha256(reconstructed).hexdigest()==prov['original_gds_sha256'];assert sha(root/'expected/output.gds')==prov['normalized_gds_sha256']
    for p in ['source.gds','expected/output.gds']:layout_shapes(root/p,spec,tech)
    assert sha(root/'source.gds')!=sha(root/'expected/output.gds')
    for p in ['source.cdl','target.cdl','expected/output.cdl']:assert parse_cdl(root/p,tech)==oracle['semantic']
    header=bindings(root);raw=raw_answers(root,spec);result=physics(spec,oracle,tech);assert result['mandatory_rule_failures']==[]
    bodies=check_body(root,{s['id']:s for s in actual_shapes(root/'source.gds',spec,tech)},tech,oracle['semantic'])
    for actual,expected in zip(bodies,oracle['body_associations']):
        for k in ['device','local_body','semantic_rail','body_edge_length_nm','rail_edge_length_nm','tap_body_enclosure_nm','tap_rail_enclosure_nm']:assert actual[k]==expected[k]
    layout=read(root/'expected/layout.json');assert layout['geometry']==spec['shapes'];assert layout['connectivity']=={'scope':'local_physical_graph','components':oracle['components'],'edges':oracle['edges'],'terminals':oracle['terminals']};assert layout['current_semantic']==oracle['semantic'] and layout['body_associations']==oracle['body_associations']
    assert layout['body_context']['sha256']==sha(root/'body/context.json') and not layout['body_context']['exported']
    assert witness(root,spec)=='no_defect'
    failures=overlays(root,spec,work);regen=None
    if regenerated:
        left={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()};right={str(p.relative_to(regenerated)):sha(p) for p in regenerated.rglob('*') if p.is_file()}
        assert left==right,sorted(k for k in left.keys()|right.keys() if left.get(k)!=right.get(k))
        regen={'byte_clean':True,'file_count':len(left)}
    return {'kind':'fixture_support_verification_not_product_run','python':sys.version.split()[0],'klayout':kdb.__version__,'profile':tech['profile_id'],'units':evidence,'source_xy_provenance':xy_provenance(root/'source.gds',spec,tech),'geometry_records':len(spec['shapes']),'independent_gds_bytes_different':True,'raw':raw,'closure_entries':len(header['closure']['entries']),'physics':result,'body_context_associations':bodies,'cut_islands':special(root,tech),'contract_conflict_witnesses':contract_conflicts(root,spec,work),'negative_cases':failures,'negative_case_count':len(failures),'regeneration':regen,'unexecuted':['product parser/runtime/Stage1-6','repository publication or typed product failure pipeline','production EDA/model/PDK','real LVS/DRC','production independent downstream open/syntax','Virtuoso/SKILL dry-run','legacy virtuoso_readback unresolved scope','full grid/CSP/DTO/codec/CAS']}

if __name__=='__main__':
    import tempfile
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--regenerated',type=Path);p.add_argument('--work',type=Path)
    a=p.parse_args()
    if a.work:a.work.mkdir(parents=True,exist_ok=True);print(json.dumps(verify(a.fixture,a.regenerated,a.work),indent=2))
    else:
        with tempfile.TemporaryDirectory(prefix='w004-verify-overlays-') as td:print(json.dumps(verify(a.fixture,a.regenerated,Path(td)),indent=2))
