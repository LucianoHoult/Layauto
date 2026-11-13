"""Follow the newly observed W007/W008 boundary through actual W013 admission."""
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'binding'))
from mutate_receipt import alter_retained_header
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_effective_geometry, build_geometry, build_local_connectivity,
    build_net_annotation, geometry_from_parse_result,
)

start = time.monotonic()
manifest = json.loads((ROOT/'docs/tasks/W013/verification-r2/source-manifest.json').read_text())
def check_source():
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == value
               for path, value in manifest['files'].items())
check_source()
parsed = read_inputs(ROOT/'tests/fixtures/w003_m1/site_config.yaml')
local = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_parse_result(parsed))))
assert local.status == 'success'
rows = []
for field, value in (
    ('query_run_id', 'foreign.query.run'),
    ('query_database_id', 'foreign.database'),
    ('top_identities', FrozenMap({'layout': 'FOREIGN', 'source': 'FOREIGN'})),
):
    forged = alter_retained_header(local, field, value)
    original_sources = local.input.input.input.semantic_input.parse.sources
    forged_sources = forged.input.input.input.semantic_input.parse.sources
    assert original_sources == forged_sources
    try:
        build_net_annotation(forged)
    except ValueError as error:
        assert '/header evidence' in str(error), str(error)
        rows.append({'field': field, 'rejected': True, 'type': type(error).__name__, 'message': str(error)})
    else:
        raise AssertionError('W013 admitted original-byte header tamper: ' + field)
check_source()
print(json.dumps({'head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    'python':sys.version,'source_id':manifest['source_id'], 'checks':rows,'status':'passed',
    'source_stable':True,'elapsed_seconds':time.monotonic()-start,
    'scope':'one real W010 build and three actual W013 public admission attacks; no full roundtrip/matrix'},indent=2))
