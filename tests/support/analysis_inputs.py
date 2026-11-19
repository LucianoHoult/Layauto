"""Explicit synthetic file migration for W016 tests and install smoke.

Only copies captured bytes and declaration files. No parser/geometry algorithm,
expected/spec/oracle, or observation-generating helper is consumed.
"""
from pathlib import Path
import hashlib
import json

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/w003_m1'


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')))


def rebind(root):
    header = load(root / 'query/local-header.json')
    for entry in header['raw'] + header['closure']['entries']:
        entry['sha256'] = hashlib.sha256((root / entry['uri']).read_bytes()).hexdigest()
    for name in ('layout', 'source_netlist'):
        header[name]['sha256'] = hashlib.sha256((root / header[name]['uri']).read_bytes()).hexdigest()
    header['closure']['sha256'] = hashlib.sha256(json.dumps(header['closure']['entries'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    write(root / 'query/local-header.json', header)


def materialize(root, *, case='normal', body=False, external=None, manual=None):
    root.mkdir(parents=True, exist_ok=True)
    cache = root / 'query/normalized'
    if cache.exists():
        # Old normalized captures bind the old synthetic header/run identity.
        # Keep the bytes as migration evidence, outside the new cache path.
        cache.rename(root / 'query/original-normalized')
    header_bytes = (FIXTURE / 'query/header.json').read_bytes()
    header = json.loads(header_bytes)
    replacements = {}
    removals = []
    if case != 'normal':
        declaration = next(x for x in load(FIXTURE / 'failures/cases.json')['cases'] if x['id'] == case)
        replacements = declaration['replacement_files']
        removals = declaration['remove_files']
        if 'query/header.json' in replacements:
            header_bytes = (FIXTURE / 'failures' / replacements['query/header.json']).read_bytes()
            header = json.loads(header_bytes)
    selected = {'source.gds', 'source.cdl', 'tech.json', 'limitations.json', 'query/requests.json', 'query/dialect.json'}
    selected.update(x['uri'] for x in header['raw'])
    selected.update(x['path'] for x in load(FIXTURE / 'tech.json')['owners'].values())
    if body:
        selected.add('body/context.json')
    for uri in selected:
        if uri in removals:
            continue
        source = FIXTURE / 'failures' / replacements[uri] if uri in replacements else FIXTURE / uri
        target = root / uri
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    manifest = {'schema_version': 'layauto-cell-analysis-request/1', 'purpose': 'local_readonly', 'mode': 'dummy_fixture',
        'inputs': {'gds':'source.gds', 'source_cdl':'source.cdl', 'query_header':'query/local-header.json'},
        'tech_ref':'tech.json', 'limitation_ref':'limitations.json',
        'external_body': external or ({'kind':'synthetic_context','uri':'body/context.json'} if body else {'kind':'not_selected'})}
    if manual is not None:
        manifest['manual_intent'] = {'kind':'declaration', 'uri':'manual.json'}
        write(root / 'manual.json', manual)
    write(root / 'analysis.json', manifest)
    (root / 'query/original-header.json').write_bytes(header_bytes)
    header['schema_version'] = 'layauto-analysis-query-header/1'
    header['header_id'] = header['query_run_id'] = 'w016.explicit.synthetic.local.1'
    header.pop('target')
    local_files = selected - {'body/context.json'}
    # closure excludes all raw/header and includes the newly selected manifest.
    local_files -= {x['uri'] for x in header['raw']}
    local_files.add('analysis.json')
    header['closure']['entries'] = [{'uri':u,'sha256':hashlib.sha256((root/u).read_bytes()).hexdigest()} for u in sorted(local_files)]
    write(root / 'query/local-header.json', header)
    rebind(root)
    write(root / 'migration.json', {'classification':'synthetic', 'source_header': {'uri':'query/original-header.json',
        'sha256':hashlib.sha256(header_bytes).hexdigest()}, 'changes':['explicit new synthetic header/run identity','local closure excludes full run inputs'],
        'raw_bytes_unchanged':True, 'observations_generated':False})
    return root / 'analysis.json'


def manual_for(root):
    return {'schema_version':'layauto-manual-supply-declaration/1','author':'synthetic-test', 'created_at':'2026-11-17T00:00:00Z',
        'source_layout':{'uri':'source.gds','sha256':hashlib.sha256((root/'source.gds').read_bytes()).hexdigest()},
        'source_netlist':{'uri':'source.cdl','sha256':hashlib.sha256((root/'source.cdl').read_bytes()).hexdigest()},
        'cell':'INV_M1_SYNTH','instance_hint':'TOP/U7',
        'assertions':[{'device':'MN0','role':'B','expected_supply_label':'GND1'}]}
