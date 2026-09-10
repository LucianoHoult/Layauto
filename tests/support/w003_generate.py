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
STATIC = ["spec.json", "oracle.json", "source.cdl", "target.cdl", "tech.json", "site_config.yaml", "export_policy.json", "validation_policy.json", "limitations.json", "README.md"]
CAPS = ("instance_xref", "net_xref", "device_regions", "net_regions")
HEADER_ID = "w003.synthetic.query.1"


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


def gds_bytes(spec: dict, tech: dict, *, unit_nm: Fraction = Fraction(1), extra: bytes = b"") -> bytes:
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


def raw_text(cap: str, rows: list[dict]) -> str:
    lines = [f"W003_QUERY 1 {cap} {HEADER_ID} nm", f"COUNT {len(rows)}"]
    for r in rows:
        if cap == "instance_xref":
            lines.append(f'I {r["layout_instance"]} {r["schematic_instance"]} ' + ("SWAP" if r["sd_swap"] else "NOSWAP"))
        elif cap == "net_xref":
            lines.append(f'N {r["lvs_index"]} {r["lvs_name"]} {r["schematic_name"]}')
        else:
            prefix = (f'D {r["record_id"]} {r["layout_instance"]}' if cap == "device_regions" else f'R {r["record_id"]} {r["lvs_index"]}')
            lines.append(prefix + f' {r["derived_layer"]} RECT {r["quality"]} ' + " ".join(r["bbox_lexemes"]))
    return "\n".join(lines + ["END W003_QUERY", ""])


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


def generate(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if out.resolve() != HERE.resolve():
        for name in STATIC:
            shutil.copy2(HERE / name, out / name)
    spec, oracle, tech = [json.loads((out / n).read_text()) for n in ("spec.json", "oracle.json", "tech.json")]
    (out / "source.gds").write_bytes(gds_bytes(spec, tech))
    (out / "query/raw").mkdir(parents=True, exist_ok=True)
    for cap in CAPS:
        raw = out / f"query/raw/{cap}.txt"
        raw.write_text(raw_text(cap, spec[cap]))
        write_json(out / f"query/normalized/{cap}.yaml", {"schema_version":"w003-query-normalized/1", "header_id":HEADER_ID,"capability":cap,"raw_sha256":digest(raw),"records":spec[cap]})
    dependencies = []
    for name in ("source.cdl", "tech.json", "export_policy.json", "validation_policy.json"):
        dependencies.append({"uri":name,"sha256":digest(out/name)})
    closure_bytes = json.dumps(dependencies,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    header = {"schema_version":"w003-query-header/1","header_id":HEADER_ID,"query_run_id":"w003.synthetic.query.1","query_database_id":None,"mode":"dummy_fixture","classification":"synthetic","assurance":"synthetic_unmatched","lvs_completion_status":"not_run","lvs_match_status":"not_run","top_identities":{"layout":spec["cell"],"source":spec["cell"]},"hierarchy_mode":"flat","layout":{"uri":"source.gds","sha256":digest(out/"source.gds")},"source_netlist":{"uri":"source.cdl","sha256":digest(out/"source.cdl"),"include_library_preprocess_closure":[],"empty_closure_sha256":hashlib.sha256(b"[]").hexdigest(),"preprocess":"none"},"target":{"uri":"target.cdl","sha256":digest(out/"target.cdl")},"closure":{"entries":dependencies,"sha256":hashlib.sha256(closure_bytes).hexdigest(),"canonical_encoding":"UTF-8 JSON, sorted object keys, compact separators, no trailing newline; listed array order"},"tool":{"name":None,"version":None,"executed":False},"query_dialect_version":"synthetic_query_dialect/1","parser_contract_version":"w003-query-normalized/1","product_parser_version":None,"query_unit":{"name":"nm","metres_per_unit":{"numerator":"1","denominator":"1000000000"}},"geometry_unit_contract":"toy_gds_real8_nm/1","raw":[{"capability":cap,"uri":f"query/raw/{cap}.txt","sha256":digest(out/f"query/raw/{cap}.txt")} for cap in CAPS],"limitations_ref":"limitations.json"}
    header['assurance']='synthetic'
    header['query_database_absence_reason']='synthetic raw construction; no query database exists'
    write_json(out/"query/header.json",header)
    (out/"expected").mkdir(exist_ok=True)
    independent_gds(out/"expected/output.gds", spec, tech)
    (out/"expected/output.cdl").write_text("* Expected portable semantic output sample, not a product run.\n" + "\n".join((out/"source.cdl").read_text().splitlines()[1:]) + "\n")
    write_json(out/"expected/layout.json",{"schema_version":"w003-layout-export-sample/1","classification":"expected_sample_not_run","source_truth":False,"cell":spec["cell"],"canonical_tick_nm":1,"current_semantic":oracle["semantic"],"geometry":spec["shapes"],"occupancy_fragment_witnesses":oracle["fragments"],"annotation":{"validity":"synthetic_source_evidence","records_ref":"../query/normalized","unannotated_nonconducting":["MARK"],"same_label_separate_components":["C_A","C_A_island_left","C_A_island_right"]},"connectivity":{"components":oracle["components"],"edges":oracle["edges"],"terminals":oracle["terminals"]},"lifecycle":{"profile_ref":"../tech.json","preserve_and_frame_equality":True,"prepublication_derived_layers":[]},"baseline_version":0,"ordered_commit_ids":[],"linkage":{"oracle_ref":"../oracle.json","spec_ref":"../spec.json","evidence_header_id":HEADER_ID},"is_complete_runtime_snapshot":False})
    failures(out, spec, tech, header)


def failures(out: Path, spec: dict, tech: dict, header: dict) -> None:
    path = out / "failures"
    path.mkdir(exist_ok=True)
    cases=[]
    def add(name: str, files: dict, issue: str, phase: str="pre_context", rebind: bool=False) -> None:
        folder=path/name; folder.mkdir(exist_ok=True)
        for n,value in files.items():
            target=folder/n; target.parent.mkdir(parents=True,exist_ok=True)
            if isinstance(value,bytes): target.write_bytes(value)
            elif isinstance(value,str):target.write_text(value)
            else:write_json(target,value)
        cases.append({"id":name,"replacement_files":{n:f"{name}/{n}" for n in files},"input_base":"../site_config.yaml","expected_issue":issue,"phase":phase,"binding_instruction":"rebind affected source/raw/closure hashes first to isolate semantic condition" if rebind else "deliberately retain original header binding; binding error may precede deeper issue","future_runtime_assertions":{"terminal":"reject","eco_commit_count":0,"normal_export_manifest":False},"executed_as_product_run":False})
    add('unit_mismatch',{'source.gds':gds_bytes(spec,tech,unit_nm=Fraction(2))},'UnitScaleMismatch',rebind=True)
    add('missing_terminator',{'query/raw/instance_xref.txt':raw_text('instance_xref',spec['instance_xref']).replace('END W003_QUERY\n','')},'MissingTerminator',rebind=True)
    add('wrong_count',{'query/raw/net_xref.txt':raw_text('net_xref',spec['net_xref']).replace('COUNT 4','COUNT 5')},'CountMismatch',rebind=True)
    add('dialect_drift',{'query/raw/device_regions.txt':raw_text('device_regions',spec['device_regions']).replace('RECT','BBOX')},'UnsupportedGeometryToken',rebind=True)
    add('unknown_unit',{'query/raw/net_regions.txt':raw_text('net_regions',spec['net_regions']).replace(' nm\n',' mystery\n',1)},'UnitBindingMismatch',rebind=True)
    add('raw_byte_drift',{'query/raw/net_xref.txt':raw_text('net_xref',spec['net_xref']).replace('042','043')},'RawHashMismatch')
    wrong=json.loads(json.dumps(header));wrong['top_identities']['source']='WRONG_TOP'
    add('header_top_mismatch',{'query/header.json':wrong},'TopBindingMismatch')
    dup=json.loads(json.dumps(spec['instance_xref']));dup[1]['schematic_instance']='MN0'
    add('mapping_many_to_one',{'query/raw/instance_xref.txt':raw_text('instance_xref',dup)},'UnsupportedDeviceCardinality',rebind=True)
    src=(out/'source.cdl').read_text()
    add('multifinger',{'source.cdl':src.replace('NF=1','NF=2',1)},'UnsupportedFingerCount',rebind=True)
    add('device_reduction',{'query/raw/instance_xref.txt':raw_text('instance_xref',spec['instance_xref']+[{'layout_instance':'Q18','schematic_instance':'MN0','sd_swap':False}])},'UnsupportedDeviceReduction',rebind=True)
    add('cdl_expression',{'source.cdl':src.replace('NFIN=5','NFIN={2+3}')},'UnsupportedCdlExpression',rebind=True)
    add('cdl_include',{'source.cdl':'.INCLUDE private_model.cdl\n'+src},'UnsupportedDependencyDirective',rebind=True)
    add('unsupported_target',{'target.cdl':src.replace('L=4n','L=5n',1)},'UnsupportedTargetAxis','sealed_no_publication',True)
    for name,shape_id,bbox,issue in [('count_correct_rule_wrong','MY',[79,90,110,98],'MandatoryRuleViolation:T07.m1_spacing'),('via_enclosure','VN',[33,50,37,54],'MandatoryRuleViolation:T05.contact_enclosure'),('extraction_mismatch','ON',[20,20,100,64],'ExtractionCountMismatch')]:
        changed=json.loads(json.dumps(spec))
        next(s for s in changed['shapes'] if s['id']==shape_id)['bbox']=bbox
        add(name,{'source.gds':gds_bytes(changed,tech),'geometry_change.json':{'shape':shape_id,'bbox':bbox,'note':'companion raw/normalized/header updates are materialized in this overlay'}},issue,'sealed_no_publication',True)
    # Actual unsupported stream elements, not only prose descriptions.
    text_record=record(12)+record(13,2,struct.pack('>h',101))+record(22,2,b'\0\0')+record(16,3,struct.pack('>2i',1,1))+record(25,6,b'UNSUPPORTED')+record(17)
    add('gds_text',{'source.gds':gds_bytes(spec,tech,extra=text_record)},'UnsupportedGdsElement:TEXT',rebind=True)
    polygon=record(8)+record(13,2,struct.pack('>h',4))+record(14,2,b'\0\0')+record(16,3,struct.pack('>14i',130,60,140,60,140,62,135,62,135,70,130,70,130,60))+record(17)
    add('gds_nonrectangle',{'source.gds':gds_bytes(spec,tech,extra=polygon)},'UnsupportedNonrectangle',rebind=True)
    for name,unit,issue in [('output_nonrepresentable',{'numerator':'2','denominator':'1'},'OutputCoordinateNotRepresentable'),('output_overflow',{'numerator':'1','denominator':'1000000000'},'OutputCoordinateOverflow')]:
        policy=json.loads((out/'export_policy.json').read_text());policy['gds_tick_nm']=unit
        add(name,{'export_policy.json':policy},issue,'export',True)
    stale=json.loads((out/'query/normalized/net_xref.yaml').read_text());stale['records'][0]['schematic_name']='Y'
    add('normalized_cache_drift',{'query/normalized/net_xref.yaml':stale},'NormalizedCacheMismatch')
    badtech=json.loads(json.dumps(tech));badtech['operators'].pop('body/1')
    add('missing_body_operator',{'tech.json':badtech},'RequiredBodyOperatorUnavailable',rebind=True)
    # Produce self-contained overlays with current bindings. Applying each
    # replacement/removal list to the positive fixture reaches the named
    # condition directly, rather than failing first on an unrelated old hash.
    malformed={'missing_terminator':'instance_xref','wrong_count':'net_xref','dialect_drift':'device_regions','unknown_unit':'net_regions'}
    deliberately_unbound={'raw_byte_drift','normalized_cache_drift','header_top_mismatch'}
    for case in cases:
        name=case['id'];folder=path/name
        if name in deliberately_unbound:
            case['binding_instruction']='intentional single binding/cache defect; apply overlay unchanged'
            case['remove_files']=[]
            continue
        rows={cap:json.loads(json.dumps(spec[cap])) for cap in CAPS}
        if name=='mapping_many_to_one':rows['instance_xref'][1]['schematic_instance']='MN0'
        if name=='device_reduction':rows['instance_xref'].append({'layout_instance':'Q18','schematic_instance':'MN0','sd_swap':False})
        if name=='count_correct_rule_wrong':
            next(r for r in rows['net_regions'] if r['record_id']=='R03')['bbox_lexemes'][0]='79'
            (folder/'query/raw').mkdir(parents=True,exist_ok=True)
            (folder/'query/raw/net_regions.txt').write_text(raw_text('net_regions',rows['net_regions']))
        if name=='extraction_mismatch':
            rows['device_regions'][0]['bbox_lexemes'][3]='64'
            (folder/'query/raw').mkdir(parents=True,exist_ok=True)
            (folder/'query/raw/device_regions.txt').write_text(raw_text('device_regions',rows['device_regions']))
        def current(n: str) -> Path:
            candidate=folder/n
            return candidate if candidate.exists() else out/n
        rebound=json.loads(json.dumps(header))
        for obj in [rebound['layout'],rebound['source_netlist'],rebound['target'],*rebound['closure']['entries'],*rebound['raw']]:
            obj['sha256']=digest(current(obj['uri']))
        rebound['closure']['sha256']=hashlib.sha256(json.dumps(rebound['closure']['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        write_json(folder/'query/header.json',rebound)
        for cap in CAPS:
            raw=folder/f'query/raw/{cap}.txt'
            if raw.exists() and malformed.get(name)!=cap:
                write_json(folder/f'query/normalized/{cap}.yaml',{'schema_version':'w003-query-normalized/1','header_id':HEADER_ID,'capability':cap,'raw_sha256':digest(raw),'records':rows[cap]})
        case['remove_files']=[f'query/normalized/{malformed[name]}.yaml'] if name in malformed else []
        case['replacement_files']={str(f.relative_to(folder)):str(f.relative_to(path)) for f in sorted(folder.rglob('*')) if f.is_file()}
        case['binding_instruction']='copy positive fixture, apply all replacement_files, remove remove_files; header/source/raw/closure/cache bindings already consistent except intended failure'
    write_json(path/'cases.json',{'schema_version':'w003-failure-cases/1','classification':'concrete negative inputs and future runtime expectations; not executed StageFailure outputs','cases':cases})


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    generate(parser.parse_args().output)
