"""Regenerate only the fixed W003 teaching fixture, never a product importer.

The handwritten spec/oracle are inputs to fixture construction, never runtime
truth. Source GDS uses only exact integers/Fraction; expected GDS uses a separate
KLayout writer. Both are checked against handwritten geometry and graph tables.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import struct

HERE = Path(__file__).resolve().parents[1] / "fixtures" / "w003_m1"
STATIC = ["spec.json", "oracle.json", "source.cdl", "target.cdl", "tech.json", "site_config.yaml", "export_policy.json", "validation_policy.json", "limitations.json", "README.md", "sources.json", "independent-design-answer.json", "query/dialect.json", "body/context-template.json", "special/cut_islands/spec.json", "special/cut_islands/oracle.json"]
from w004_support import load_tech, bind_header, read, canonical
from w004_query import CAPS, normalize, DIALECT
HEADER_ID = "w004.synthetic.query.2"


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def real8(value: Fraction) -> bytes:
    """GDSII REAL8 nearest/ties-even; exact arithmetic, no int(float)."""
    if not value:
        return bytes(8)
    sign = 128 if value < 0 else 0
    v = abs(value)
    exponent = 0
    while v >= 1:
        v /= 16
        exponent += 1
    while v < Fraction(1, 16):
        v *= 16
        exponent -= 1
    scaled = v * (1 << 56)
    q, r = divmod(scaled.numerator, scaled.denominator)
    if 2 * r > scaled.denominator or (2 * r == scaled.denominator and q % 2):
        q += 1
    if q == (1 << 56):
        q //= 16
        exponent += 1
    if not -64 <= exponent <= 63:
        raise ValueError("REAL8 exponent out of range")
    return bytes([sign | (exponent + 64)]) + q.to_bytes(7, "big")


def record(kind: int, dtype: int = 0, payload: bytes = b"") -> bytes:
    if len(payload) % 2:
        payload += b"\0"
    return struct.pack(">HBB", 4 + len(payload), kind, dtype) + payload


def gds_bytes(spec: dict, tech: dict, *, unit_nm: Fraction | None = None, extra: bytes = b"") -> bytes:
    if unit_nm is None:
        u=tech["unit_scale_contract"]["nominal_tick_m"];unit_nm=Fraction(int(u["numerator"]),int(u["denominator"]))*1000000000
    layers = {r["name"]: r["stream_key"]["layer"] for r in tech["layers"]}
    date = struct.pack(">12h", *([2026, 9, 9, 0, 0, 0] * 2))
    data = record(0, 2, struct.pack(">h", 600)) + record(1, 2, date)
    data += record(2, 6, b"W003_SYNTH")
    data += record(3, 5, real8(unit_nm / 1000) + real8(unit_nm / 1000000000))
    data += record(5, 2, date) + record(6, 6, spec["cell"].encode("ascii"))
    for shape in spec["shapes"]:
        x0, y0, x1, y1 = shape["bbox"]
        xy = [x0, y0, x1, y0, x1, y1, x0, y1, x0, y0]
        if any(type(v) is not int or not -(1 << 31) <= v < (1 << 31) for v in xy):
            raise ValueError("GDS XY requires exact signed 32-bit integers")
        data += record(8) + record(13, 2, struct.pack(">h", layers[shape["layer"]]))
        data += record(14, 2, b"\0\0") + record(16, 3, struct.pack(">10i", *xy)) + record(17)
    return data + extra + record(7) + record(4)


def independent_gds(path: Path, spec: dict, tech: dict) -> None:
    import klayout.db as kdb
    layout = kdb.Layout()
    # Required KLayout API type; geometry stays integer. verify.py separately
    # decodes the resulting REAL8 bytes and checks the nominal binding.
    layout.dbu = 0.001
    cell = layout.create_cell(spec["cell"])
    layers = {x["name"]: layout.layer(x["stream_key"]["layer"], 0) for x in tech["layers"]}
    for s in reversed(spec["shapes"]):
        cell.shapes(layers[s["layer"]]).insert(kdb.Box(*s["bbox"]))
    options = kdb.SaveLayoutOptions()
    options.gds2_write_timestamps = False
    options.gds2_libname = "W003_INDEPENDENT"
    layout.write(str(path), options)
    original = path.read_bytes()
    normalized = bytearray(original)
    offset = 0
    while offset < len(original):
        length, kind, dtype = struct.unpack('>HBB',original[offset:offset+4])
        if kind == 3:
            assert length == 20 and dtype == 5
            units_before = original[offset+4:offset+20]
            units_after = real8(Fraction(1,1000)) + real8(Fraction(1,1000000000))
            normalized[offset+4:offset+20] = units_after
            write_json(path.parent/'unit-provenance.json', {
                'schema_version':'w003-independent-writer-provenance/1',
                'writer':'KLayout','version':kdb.__version__,
                'original_units_hex':units_before.hex(),'normalized_units_hex':units_after.hex(),
                'modified_byte_range':[offset+4,offset+20],
                'original_gds_sha256':hashlib.sha256(original).hexdigest(),
                'normalized_gds_sha256':hashlib.sha256(normalized).hexdigest(),
                'reason':'KLayout binary64 DBU conversion exceeds declared nearest56 half-ULP; normalize UNITS payload only to existing contract, never XY',
                'independent_scope':'geometry serialization and readback; unit writer intentionally shared, independently exact-decoded by verifier'
            })
            break
        offset += length
    else:
        raise AssertionError('KLayout output missing UNITS')
    path.write_bytes(normalized)


def write_raw(out, spec):
    raw=out/'query/raw';raw.mkdir(parents=True,exist_ok=True)
    for kind,cap,fn,tag in [('Instance','instance_xref','iXref.temp','ixf'),('Net','net_xref','nXref.temp','nxf')]:
        ls=[f'# SVDB: {kind} Cross Reference ({tag}) (File format 1)',f'# SVDB: Layout Primary {spec["cell"]}',f'# SVDB: Source Primary {spec["cell"]}','# SVDB: Layout system: GDSII','# SVDB: Source system: SPICE','# SVDB: Generated by Calibre LVS (synthetic fixture; not executed)','# SVDB: End of header.',('' if cap=='instance_xref' else '% ')+f'{spec["cell"]} 4 {spec["cell"]} 4']
        for r in spec[cap]:
            ls.append(f'0 {r["layout_instance"]} 0 {r["schematic_instance"]}'+(' X' if r['sd_swap'] else '') if cap=='instance_xref' else f'0 {r["lvs_name"]} 0 {r["schematic_name"]}')
        (raw/fn).write_text('\n'.join(ls)+'\n')
    (raw/'net_names.txt').write_text('Net_Names 20000\nNets:\n0 0 4 May 07 03:00:00 2026\n'+'\n'.join(x['lvs_name'] for x in spec['net_xref'])+'\nEND OF RESPONSE\n')
    requests=[]
    for cap,items in [('device_regions',[(x['layout_instance'],[r for r in spec['device_regions'] if r['layout_instance']==x['layout_instance']]) for x in spec['instance_xref']]),('net_regions',[(x['lvs_name'],[r for r in spec['net_regions'] if r['lvs_index']==x['lvs_index']]) for x in spec['net_xref']])]:
        for identity,rows in items:
            if not rows:continue
            fn=('device_info_' if cap=='device_regions' else 'net_shapes_')+identity+'.txt';path='query/raw/'+fn
            ls=[('Device_Info' if cap=='device_regions' else 'Net_Shapes')+' 20000','Info:',('0 0 2' if cap=='device_regions' else '0 0 1')+' May 07 03:00:00 2026']
            if cap=='device_regions':ls.append('0' if identity=='Q17' else '1')
            for r in rows:
                ls += [r['derived_layer'],'1 1 0 May 07 03:00:00 2026','p 1 4']
                x0,y0,x1,y1=[Fraction(x) for x in r['bbox_lexemes']]
                for y,x in [(y0,x0),(y1,x0),(y1,x1),(y0,x1)]:
                    assert (y*20).denominator==(x*20).denominator==1
                    ls.append(f'{int(y*20)} {int(x*20)}')
            (out/path).write_text('\n'.join(ls+['END OF RESPONSE','']))
            requests.append({'capability':cap,'path':path,'object':identity,'command_intent':'DEVICE INFO' if cap=='device_regions' else 'NET SHAPES','record_ids':[x['record_id'] for x in rows]})
    write_json(out/'query/requests.json',{'schema_version':'w004-query-requests/2','source':'synthetic query selection manifest; object identity is explicit, never inferred from filename','requests':requests})

def generate(out):
    out.mkdir(parents=True,exist_ok=True)
    if out.resolve()!=HERE.resolve():
        for n in STATIC+[str(p.relative_to(HERE)) for p in (HERE/'tech').glob('*.json')]:
            (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/n,out/n)
    for n in ['query/raw','query/normalized','failures']:
        if (out/n).exists():shutil.rmtree(out/n)
    spec,oracle=[read(out/n) for n in ['spec.json','oracle.json']];tech=load_tech(out)
    (out/'source.gds').write_bytes(gds_bytes(spec,tech))
    context=read(out/'body/context-template.json');context['source_gds']={'uri':'source.gds','sha256':digest(out/'source.gds')};write_json(out/'body/context.json',context)
    write_raw(out,spec)
    for cap in CAPS:write_json(out/f'query/normalized/{cap}.yaml',normalize(out,cap))
    raw=[{'capability':cap,'uri':'query/raw/'+name} for cap,name in [('instance_xref','iXref.temp'),('net_xref','nXref.temp'),('net_xref','net_names.txt')]]+[{'capability':q['capability'],'uri':q['path']} for q in read(out/'query/requests.json')['requests']]
    header={'schema_version':'w004-query-header/2','header_id':HEADER_ID,'query_run_id':HEADER_ID,'query_database_id':None,'query_database_absence_reason':'synthetic construction; no database','mode':'dummy_fixture','classification':'synthetic','assurance':'synthetic','lvs_completion_status':'not_run','lvs_match_status':'not_run','top_identities':{'layout':spec['cell'],'source':spec['cell']},'hierarchy_mode':'flat','layout':{'uri':'source.gds'},'source_netlist':{'uri':'source.cdl','include_library_preprocess_closure':[],'empty_closure_sha256':hashlib.sha256(b'[]').hexdigest(),'preprocess':'none'},'target':{'uri':'target.cdl'},'closure':{'entries':[],'canonical_encoding':'UTF-8 sorted-key compact JSON, array sorted by uri, no LF'},'tool':{'name':None,'version':None,'executed':False},'query_dialect_version':DIALECT,'parser_contract_version':'w004-query-normalized/2','product_parser_version':None,'query_unit':{'name':'micrometres/precision','metres_per_unit':{'numerator':'1','denominator':'1000000'},'geometry_precision':20000,'axis_order':['y','x']},'geometry_unit_contract':'toy_gds_real8_nm/1','raw':raw,'limitations_ref':'limitations.json'}
    header=bind_header(out,header);write_json(out/'query/header.json',header)
    (out/'expected').mkdir(exist_ok=True);independent_gds(out/'expected/output.gds',spec,tech)
    (out/'expected/output.cdl').write_text('* Expected semantic output, no product run.\n'+'\n'.join((out/'source.cdl').read_text().splitlines()[1:])+'\n')
    write_json(out/'expected/layout.json',{'schema_version':'w004-layout-export-sample/2','classification':'synthetic_expected_sample','source_truth':False,'cell':spec['cell'],'canonical_tick_nm':1,'current_semantic':oracle['semantic'],'geometry':spec['shapes'],'occupancy_fragment_witnesses':oracle['fragments'],'annotation':{'validity':'synthetic_source_evidence','records_ref':'../query/normalized','unannotated_nonconducting':['MARK'],'same_label_separate_components':[]},'connectivity':{'scope':'local_physical_graph','components':oracle['components'],'edges':oracle['edges'],'terminals':oracle['terminals']},'body_associations':oracle['body_associations'],'body_context':{'input_ref':'../body/context.json','sha256':digest(out/'body/context.json'),'exported':False,'production_matched_body_evidence':False},'lifecycle':{'profile_ref':'../tech.json','preserve_and_frame_equality':True,'prepublication_derived_layers':[]},'baseline_version':0,'ordered_commit_ids':[],'linkage':{'oracle_ref':'../oracle.json','spec_ref':'../spec.json','evidence_header_id':HEADER_ID},'is_complete_runtime_snapshot':False})
    special=read(out/'special/cut_islands/spec.json');(out/'special/cut_islands/source.gds').write_bytes(gds_bytes(special,tech))
    failures(out,spec,tech,header)

def failures(out,spec,tech,header):
    import tempfile,copy
    cases=[]; base=out/'failures';base.mkdir()
    src=(out/'source.cdl').read_text()
    def add(name,files,issue,phase='pre_context',malformed=(),intentional=False,remove=()):
        folder=base/name;folder.mkdir()
        with tempfile.TemporaryDirectory(prefix='w004-build-overlay-') as td:
            world=Path(td)
            for p in out.rglob('*'):
                if p.is_file() and 'failures' not in p.relative_to(out).parts:
                    n=p.relative_to(out);(world/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,world/n)
            for n,v in files.items():
                p=world/n;p.parent.mkdir(parents=True,exist_ok=True)
                if isinstance(v,bytes):p.write_bytes(v)
                elif isinstance(v,str):p.write_text(v)
                else:write_json(p,v)
            for n in remove:(world/n).unlink()
            removals=list(remove)
            if not intentional:
                if 'source.gds' in files:
                    c=read(world/'body/context.json');c['source_gds']['sha256']=digest(world/'source.gds');write_json(world/'body/context.json',c)
                for cap in CAPS:
                    n=f'query/normalized/{cap}.yaml'
                    if cap in malformed:(world/n).unlink();removals.append(n)
                    else:write_json(world/n,normalize(world,cap))
                write_json(world/'query/header.json',bind_header(world,header))
            for p in world.rglob('*'):
                if p.is_file() and (not (out/p.relative_to(world)).exists() or p.read_bytes()!=(out/p.relative_to(world)).read_bytes()):
                    dst=folder/p.relative_to(world);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
        number=len(cases)+1
        cases.append({'original_id':f'C{number:02}' if number<=22 else None,'id':name,'replacement_files':{str(p.relative_to(folder)):str(p.relative_to(base)) for p in sorted(folder.rglob('*')) if p.is_file()},'remove_files':removals,'expected_issue':issue,'phase':phase,'input_base':'../site_config.yaml','binding_instruction':'intentional single declared binding/cache defect' if intentional else 'fully rebound except declared missing required support; apply real replacements/removals','future_runtime_assertions':{'terminal':'reject','eco_commit_count':0,'normal_export_manifest':False},'executed_as_product_run':False})
    add('unit_mismatch',{'source.gds':gds_bytes(spec,tech,unit_nm=Fraction(2))},'UnitScaleMismatch')
    add('missing_terminator',{'query/raw/device_info_Q17.txt':(out/'query/raw/device_info_Q17.txt').read_text().replace('END OF RESPONSE\n','')},'MissingTerminator',malformed=['device_regions'])
    add('wrong_count',{'query/raw/net_names.txt':(out/'query/raw/net_names.txt').read_text().replace('0 0 4 May','0 0 5 May')},'CountMismatch',malformed=['net_xref','net_regions'])
    add('dialect_drift',{'query/raw/device_info_Q17.txt':(out/'query/raw/device_info_Q17.txt').read_text().replace('p 1 4','q 1 4')},'UnsupportedGeometryToken',malformed=['device_regions'])
    add('unknown_unit',{'query/raw/net_shapes_n_a.txt':(out/'query/raw/net_shapes_n_a.txt').read_text().replace('Net_Shapes 20000','Net_Shapes 0')},'UnitBindingMismatch',malformed=['net_regions'])
    add('raw_byte_drift',{'query/raw/nXref.temp':(out/'query/raw/nXref.temp').read_text().replace('n_y','n_z')},'RawHashMismatch',intentional=True)
    h=copy.deepcopy(header);h['top_identities']['source']='WRONG_TOP';add('header_top_mismatch',{'query/header.json':h},'TopBindingMismatch',intentional=True)
    add('mapping_many_to_one',{'query/raw/iXref.temp':(out/'query/raw/iXref.temp').read_text().replace('0 MP0','0 MN0')},'UnsupportedDeviceCardinality')
    add('multifinger',{'source.cdl':src.replace('NF=1','NF=2',1)},'UnsupportedFingerCount')
    add('device_reduction',{'query/raw/iXref.temp':(out/'query/raw/iXref.temp').read_text()+'0 Q18 0 MN0\n'},'UnsupportedDeviceReduction')
    add('cdl_expression',{'source.cdl':src.replace('NFIN=5','NFIN={2+3}')},'UnsupportedCdlExpression')
    add('cdl_include',{'source.cdl':'.INCLUDE private_model.cdl\n'+src},'UnsupportedDependencyDirective')
    add('unsupported_target',{'target.cdl':src.replace('L=4n','L=5n',1)},'UnsupportedTargetAxis','sealed_no_publication')
    for name,sid,bbox,issue in [('count_correct_rule_wrong','MY',[79,90,110,98],'MandatoryRuleViolation:T07.m1_spacing'),('via_enclosure','VN',[33,50,37,54],'MandatoryRuleViolation:T05.contact_enclosure'),('extraction_mismatch','ON',[20,20,100,64],'ExtractionCountMismatch')]:
        changed=copy.deepcopy(spec);next(x for x in changed['shapes'] if x['id']==sid)['bbox']=bbox
        files={'source.gds':gds_bytes(changed,tech),'geometry_change.json':{'shape':sid,'bbox':bbox,'note':'new geometry; companion raw rebound'}}
        if name=='count_correct_rule_wrong':files['query/raw/net_shapes_n_y.txt']=(out/'query/raw/net_shapes_n_y.txt').read_text().replace(' 1600\n',' 1580\n')
        if name=='extraction_mismatch':files['query/raw/device_info_Q17.txt']=(out/'query/raw/device_info_Q17.txt').read_text().replace('1400 ','1280 ')
        add(name,files,issue,'sealed_no_publication')
    text=record(12)+record(13,2,struct.pack('>h',101))+record(22,2,b'\0\0')+record(16,3,struct.pack('>2i',1,1))+record(25,6,b'UNSUPPORTED')+record(17)
    add('gds_text',{'source.gds':gds_bytes(spec,tech,extra=text)},'UnsupportedGdsElement:TEXT')
    poly=record(8)+record(13,2,struct.pack('>h',4))+record(14,2,b'\0\0')+record(16,3,struct.pack('>14i',130,60,140,60,140,62,135,62,135,70,130,70,130,60))+record(17)
    add('gds_nonrectangle',{'source.gds':gds_bytes(spec,tech,extra=poly)},'UnsupportedNonrectangle')
    for name,tick,issue in [('output_nonrepresentable',{'numerator':'2','denominator':'1'},'OutputCoordinateNotRepresentable'),('output_overflow',{'numerator':'1','denominator':'1000000000'},'OutputCoordinateOverflow')]:
        p=read(out/'export_policy.json');p['gds_tick_nm']=tick;add(name,{'export_policy.json':p},issue,'export')
    cache=read(out/'query/normalized/net_xref.yaml');cache['records'][0]['schematic_name']='Y';add('normalized_cache_drift',{'query/normalized/net_xref.yaml':cache},'NormalizedCacheMismatch',intentional=True)
    p=read(out/'tech/physical.json');p['operators'].pop('body_context/2');add('missing_body_operator',{'tech/physical.json':p},'RequiredBodyOperatorUnavailable')
    add('missing_body_context',{},'RequiredBodyContextUnavailable',remove=['body/context.json'])
    for name,issue in [('body_wrong_binding','BodySourceBindingMismatch'),('body_wrong_type','BodyTypeMismatch'),('body_disconnected','BodyContinuationMismatch'),('body_ambiguous','BodyUniqueMatchFailure'),('body_enclosure','BodyTapEnclosureFailure'),('body_wrong_rail','BodyTargetRailMismatch')]:
        c=read(out/'body/context.json');ss={x['id']:x for x in c['shapes']}
        if name=='body_wrong_binding':c['source_gds']['sha256']='0'*64
        if name=='body_wrong_type':ss['TN.ext']['layer']='BTAP_P'
        if name=='body_disconnected':ss['BN.ext']['bbox'][2]=-1
        if name=='body_ambiguous':c['shapes'].append({**ss['BN.ext'],'id':'BN.ext.duplicate'})
        if name=='body_enclosure':ss['TN.ext']['bbox']=[-12,48,-8,52]
        if name=='body_wrong_rail':
            c['associations'][0]['expected_semantic_rail']='VDD'
        add(name,{'body/context.json':c},issue,'pre_context' if name=='body_wrong_binding' else 'sealed_no_publication')
    write_json(base/'cases.json',{'schema_version':'w004-failure-cases/2','classification':'synthetic_negative_inputs','cases':cases})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);generate(p.parse_args().output)
