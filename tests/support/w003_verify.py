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


def units(path: Path) -> list[dict]:
    raw=next(payload for kind,_,payload in records(path) if kind==3)
    result=[]
    for offset,nominal in [(0,Fraction(1,1000)),(8,Fraction(1,1000000000))]:
        field=raw[offset:offset+8];decoded=decode_real8(field);exponent=(field[0]&127)-64
        nominal_exponent=0;normalized=nominal
        while normalized>=1:normalized/=16;nominal_exponent+=1
        while normalized<Fraction(1,16):normalized*=16;nominal_exponent-=1
        bound=Fraction(16)**exponent/Fraction(1<<57)
        assert exponent==nominal_exponent and abs(decoded-nominal)<=bound, 'UnitScaleMismatch'
        result.append({'raw_hex':field.hex(),'decoded':rational(decoded),'nominal':rational(nominal),'delta':rational(decoded-nominal),'allowed_half_ulp':rational(bound)})
    return result


def parse_raw(path: Path, cap: str) -> list[dict]:
    data=path.read_bytes();assert data.endswith(b'\n'),'MissingTerminator'
    lines=data.decode('ascii').splitlines()
    assert lines[-1]=='END W003_QUERY','MissingTerminator'
    assert lines[0].split()==['W003_QUERY','1',cap,'w003.synthetic.query.1','nm'],'UnitBindingMismatch'
    assert len(lines[1].split())==2 and lines[1].split()[0]=='COUNT','CountMismatch'
    assert int(lines[1].split()[1])==len(lines)-3,'CountMismatch'
    rows=[]
    for line in lines[2:-1]:
        f=line.split()
        if cap=='instance_xref':
            assert len(f)==4 and f[0]=='I' and f[3] in ('SWAP','NOSWAP'),'InvalidRecord'
            rows.append({'layout_instance':f[1],'schematic_instance':f[2],'sd_swap':f[3]=='SWAP'})
        elif cap=='net_xref':
            assert len(f)==4 and f[0]=='N' and re.fullmatch(r'[0-9]+',f[1]),'InvalidRecord'
            rows.append({'lvs_index':f[1],'lvs_name':f[2],'schematic_name':f[3]})
        else:
            assert len(f)==10 and f[0]==('D' if cap=='device_regions' else 'R'),'InvalidRecord'
            assert f[4]=='RECT','UnsupportedGeometryToken'
            assert f[5]=='exact','UnsupportedQuality'
            assert all(re.fullmatch(r'-?(0|[1-9][0-9]*)',v) for v in f[6:]),'InvalidCoordinate'
            box=list(map(int,f[6:])); assert box[0]<box[2] and box[1]<box[3],'InvalidRectangle'
            rows.append({'record_id':f[1],('layout_instance' if cap=='device_regions' else 'lvs_index'):f[2],'derived_layer':f[3],'geometry_kind':'rectangle','quality':f[5],'bbox_lexemes':f[6:],'unit':'nm'})
    return rows


def parse_cdl(path: Path) -> dict:
    rows=[l.split() for l in path.read_text().splitlines() if l and not l.startswith('*')]
    assert rows[0][0]=='.SUBCKT' and rows[-1]==['.ENDS',rows[0][1]]
    result={'cell':rows[0][1],'pins':rows[0][2:],'globals':[],'devices':[]}
    for row in rows[1:-1]:
        assert len(row)==12 and row[5] in ('TOY_N','TOY_P'), 'UnsupportedCdl'
        pairs=[v.split('=') for v in row[6:]];assert all(len(v)==2 for v in pairs),'UnsupportedCdlExpression'
        params=dict(pairs);assert len(params)==len(pairs) and set(params)=={'NFIN','NF','M','L','W','VT'}
        assert all(re.fullmatch(r'[1-9][0-9]*',params[k]) for k in ['NFIN','NF','M']),'UnsupportedCdlExpression'
        assert all(re.fullmatch(r'[1-9][0-9]*n',params[k]) for k in ['L','W']) and params['VT']=='toy'
        result['devices'].append({'id':row[0],'model':row[5],'terminals':dict(zip('DGSB',row[1:5])),'parameters':{'fins_per_finger':int(params['NFIN']),'finger_count':int(params['NF']),'multiplicity':int(params['M']),'L_nm':int(params['L'][:-1]),'W_nm':int(params['W'][:-1]),'VT':params['VT']}})
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
    cut=box(shapes['CUTB'])
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
        for connector in by_layer[layer['name']]:
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
    if min(margins)<1:failures.append('T05.contact_enclosure')
    minimum={}
    for layer,threshold,rid in [('LI',2,'T06.li_spacing'),('M1',5,'T07.m1_spacing')]:
        regions=[v['bbox'] for v in effective.values() if v['layer']==layer]
        distances=[distance2(a,b) for i,a in enumerate(regions) for b in regions[i+1:]]
        minimum[layer]={'pairs':len(distances),'minimum_squared_distance_nm2':min(distances)}
        if min(distances)<threshold**2:failures.append(rid)
    if any(encl(shapes['FRAME'],s['bbox'])<0 for s in spec['shapes']):failures.append('T01.frame')
    fins=sorted(shapes[f] for f in by_layer['FIN']);ys=sorted(r[1] for r in fins)
    assert len(fins)==18 and all(r[0]==10 and r[2]==110 and r[3]-r[1]==2 for r in fins)
    assert ys==list(range(24,195,10))
    assert encl(shapes['BN'],shapes['ON'])>=10 and encl(shapes['BP'],shapes['OP'])>=10
    assert (box(shapes['BN'])&box(shapes['BP'])).is_empty()
    for terminal in oracle['terminals']:
        component=next(c for c in oracle['components'] if terminal['region'] in c['regions'])
        assert component['id']==terminal['component'] and component['net']==terminal['net']
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
    assert len(spec['shapes'])==oracle['drawn_shape_count']==44
    return {'crossings':crossing_results,'fragment_count_witnesses':6,'physical_component_count':len(components),'qualified_connector_edges':len(edges),'independent_exact_net_annotations':len(spec['net_regions']),'independent_device_joins':len(ix),'minimum_contact_enclosure_nm':min(margins),'spacing':minimum,'mandatory_rule_failures':sorted(set(failures))}


def verify(root: Path, regenerated: Path|None) -> dict:
    spec,oracle,tech=[read(root/n) for n in ['spec.json','oracle.json','tech.json']]
    evidence={p:units(root/p) for p in ['source.gds','expected/output.gds']}
    prov=read(root/'expected/unit-provenance.json')
    reconstructed=bytearray((root/'expected/output.gds').read_bytes())
    start,end=prov['modified_byte_range'];reconstructed[start:end]=bytes.fromhex(prov['original_units_hex'])
    assert hashlib.sha256(reconstructed).hexdigest()==prov['original_gds_sha256']
    assert sha(root/'expected/output.gds')==prov['normalized_gds_sha256']
    original=bytes.fromhex(prov['original_units_hex'])
    evidence['klayout_original_units']=[{'raw_hex':original[i:i+8].hex(),'decoded':rational(decode_real8(original[i:i+8])),'delta_from_nominal':rational(decode_real8(original[i:i+8])-n)} for i,n in [(0,Fraction(1,1000)),(8,Fraction(1,1000000000))]]
    for p in ['source.gds','expected/output.gds']:layout_shapes(root/p,spec,tech)
    assert sha(root/'source.gds')!=sha(root/'expected/output.gds'),'independent writer should yield differing bytes'
    for p in ['source.cdl','target.cdl','expected/output.cdl']:assert parse_cdl(root/p)==oracle['semantic']
    header=read(root/'query/header.json')
    assert header['mode']=='dummy_fixture' and not header['tool']['executed'] and header['product_parser_version'] is None
    assert header['top_identities']=={'layout':spec['cell'],'source':spec['cell']}
    for obj in [header['layout'],header['source_netlist'],header['target'],*header['closure']['entries'],*header['raw']]:assert sha(root/obj['uri'])==obj['sha256']
    closure=json.dumps(header['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    assert hashlib.sha256(closure).hexdigest()==header['closure']['sha256']
    assert header['source_netlist']['include_library_preprocess_closure']==[]
    raw_counts={}
    for entry in header['raw']:
        cap=entry['capability'];normalized=read(root/f'query/normalized/{cap}.yaml')
        actual=parse_raw(root/entry['uri'],cap)
        assert actual==normalized['records']==spec[cap]
        assert normalized['header_id']==header['header_id'] and normalized['raw_sha256']==entry['sha256']
        raw_counts[cap]=len(actual)
    result=physics(spec,oracle,tech);assert result['mandatory_rule_failures']==[]
    failures={}
    for case,cap,error in [('missing_terminator','instance_xref','MissingTerminator'),('wrong_count','net_xref','CountMismatch'),('dialect_drift','device_regions','UnsupportedGeometryToken'),('unknown_unit','net_regions','UnitBindingMismatch')]:
        try:parse_raw(root/f'failures/{case}/query/raw/{cap}.txt',cap)
        except AssertionError as exc:assert str(exc)==error;failures[case]=error
        else:raise AssertionError(f'{case} not detected')
    try:units(root/'failures/unit_mismatch/source.gds')
    except AssertionError as exc:assert str(exc)=='UnitScaleMismatch';failures['unit_mismatch']='UnitScaleMismatch'
    else:raise AssertionError('unit mismatch not detected')
    assert sha(root/'failures/raw_byte_drift/query/raw/net_xref.txt')!=next(x['sha256'] for x in header['raw'] if x['capability']=='net_xref');failures['raw_byte_drift']='RawHashMismatch'
    assert read(root/'failures/normalized_cache_drift/query/normalized/net_xref.yaml')['records']!=spec['net_xref'];failures['normalized_cache_drift']='NormalizedCacheMismatch'
    for case,rule in [('count_correct_rule_wrong','T07.m1_spacing'),('via_enclosure','T05.contact_enclosure')]:
        mutation=read(root/f'failures/{case}/geometry_change.json');changed=json.loads(json.dumps(spec));next(s for s in changed['shapes'] if s['id']==mutation['shape'])['bbox']=mutation['bbox']
        if case=='count_correct_rule_wrong':next(r for r in changed['net_regions'] if r['record_id']=='R03')['bbox_lexemes'][0]='79'
        layout_shapes(root/f'failures/{case}/source.gds',changed,tech)
        checked=physics(changed,oracle,tech)
        assert rule in checked['mandatory_rule_failures'] and [x['count'] for x in checked['crossings']]==[5,7]
        failures[case]=rule
    for case in ['output_nonrepresentable','output_overflow']:
        p=read(root/f'failures/{case}/export_policy.json')['gds_tick_nm'];tick=Fraction(int(p['numerator']),int(p['denominator']))
        values=[Fraction(v)/tick for s in spec['shapes'] for v in s['bbox']]
        if case=='output_nonrepresentable':assert any(v.denominator!=1 for v in values)
        else:assert all(v.denominator==1 for v in values) and any(v<-(1<<31) or v>=(1<<31) for v in values)
        failures[case]='exact arithmetic detects rejection condition'
    for case,kind in [('gds_text',12),('gds_nonrectangle',8)]:
        rec=records(root/f'failures/{case}/source.gds')
        assert any(k==kind for k,_,_ in rec)
        if case=='gds_nonrectangle':assert any(k==16 and len(p)==56 for k,_,p in rec)
        failures[case]='unsupported stream witness present'
    assert read(root/'failures/header_top_mismatch/query/header.json')['top_identities']['source']!=spec['cell'];failures['header_top_mismatch']='TopBindingMismatch'
    for case in ['mapping_many_to_one','device_reduction']:
        rows=parse_raw(root/f'failures/{case}/query/raw/instance_xref.txt','instance_xref')
        assert len(set(r['schematic_instance'] for r in rows))<len(rows)
        failures[case]='non-one-to-one mapping witness'
    assert parse_cdl(root/'failures/multifinger/source.cdl')['devices'][0]['parameters']['finger_count']==2;failures['multifinger']='UnsupportedFingerCount'
    for case in ['cdl_expression','cdl_include']:
        try:parse_cdl(root/f'failures/{case}/source.cdl')
        except AssertionError:failures[case]='unsupported CDL grammar witness'
        else:raise AssertionError(f'{case} not detected')
    changed_target=parse_cdl(root/'failures/unsupported_target/target.cdl')
    assert changed_target['devices'][0]['parameters']['L_nm']==5 and changed_target!=oracle['semantic'];failures['unsupported_target']='UnsupportedTargetAxis:L'
    changed=read(root/'failures/extraction_mismatch/geometry_change.json');changed_spec=json.loads(json.dumps(spec));next(s for s in changed_spec['shapes'] if s['id']==changed['shape'])['bbox']=changed['bbox']
    layout_shapes(root/'failures/extraction_mismatch/source.gds',changed_spec,tech)
    negative_channel=box(changed['bbox'])&box(next(s['bbox'] for s in spec['shapes'] if s['id']=='G'))
    count=sum(not (box(s['bbox'])&negative_channel).is_empty() for s in spec['shapes'] if s['layer']=='FIN')
    assert count==4 and oracle['crossings'][0]['count']==5;failures['extraction_mismatch']='4 physical crossings versus 5 declared'
    badtech=read(root/'failures/missing_body_operator/tech.json')
    assert badtech['device_extraction_contract']['body_operator_ref'] not in badtech['operators'];failures['missing_body_operator']='RequiredBodyOperatorUnavailable'
    overlay_count=0
    for case in read(root/'failures/cases.json')['cases']:
        if case['id'] in ['raw_byte_drift','normalized_cache_drift','header_top_mismatch']:continue
        folder=root/'failures'/case['id']
        def current(n: str) -> Path:
            assert n not in case['remove_files']
            return folder/n if (folder/n).exists() else root/n
        h=read(folder/'query/header.json')
        for obj in [h['layout'],h['source_netlist'],h['target'],*h['closure']['entries'],*h['raw']]:assert sha(current(obj['uri']))==obj['sha256']
        assert hashlib.sha256(json.dumps(h['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==h['closure']['sha256']
        for raw in h['raw']:
            cap=raw['capability'];n=f'query/normalized/{cap}.yaml'
            if n in case['remove_files']:continue
            cache=read(current(n));assert cache['raw_sha256']==raw['sha256'] and cache['records']==parse_raw(current(raw['uri']),cap)
        overlay_count+=1
    regen=None
    if regenerated:
        left={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
        right={str(p.relative_to(regenerated)):sha(p) for p in regenerated.rglob('*') if p.is_file()}
        assert left==right, f'regeneration mismatch: {sorted(k for k in left.keys()|right.keys() if left.get(k)!=right.get(k))}'
        regen={'byte_clean':True,'file_count':len(left)}
    return {'kind':'fixture_support_verification_not_product_run','python':sys.version.split()[0],'klayout':kdb.__version__,'profile':tech['profile_id'],'units':evidence,'geometry_records':len(spec['shapes']),'independent_gds_bytes_different':True,'raw_record_counts':raw_counts,'physics':result,'checked_negative_witnesses':failures,'negative_case_count':len(read(root/'failures/cases.json')['cases']),'coherently_rebound_negative_overlays':overlay_count,'regeneration':regen,'unexecuted':['product parser/runtime','Stage 1-6','repository publication','full negative runtime outcomes','production EDA/model/PDK','real signoff','strict typing/build/other interpreter versions']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--regenerated',type=Path)
    args=parser.parse_args();print(json.dumps(verify(args.fixture,args.regenerated),indent=2))
