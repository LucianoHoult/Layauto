"""Compare legitimate wire/digests with identical captured URI spelling."""
from pathlib import Path
import hashlib,json,platform,sys
import layauto_v2
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import build_geometry,geometry_from_parse_result,build_effective_geometry
from layauto_v2.normalization import effective_codec,geometry_codec
fixture=Path(sys.argv[1])
parsed=read_inputs(fixture/'site_config.yaml')
assert parsed.status=='success'
base=build_geometry(geometry_from_parse_result(parsed))
result=build_effective_geometry(base)
assert base.status==result.status=='success'
rows={}
for name,record,codec in [('base',base,geometry_codec),('draft',result.value,effective_codec),('result',result,effective_codec)]:
    wire=codec.encode_record(record)
    assert codec.decode_record(wire)==record
    rows[name]={'sha256':hashlib.sha256(wire).hexdigest(),'record_digest':codec.record_digest(record),'length':len(wire)}
root=Path(layauto_v2.__file__).parent
print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'cwd':str(Path.cwd()),'package':str(root),'fixture':str(fixture),'wire':rows,'semantic_digest':result.value.semantic_digest,'source_uris':[s.uri for s in parsed.sources],'runtime_files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and (p.suffix=='.py' or p.name=='py.typed')}},indent=2))
