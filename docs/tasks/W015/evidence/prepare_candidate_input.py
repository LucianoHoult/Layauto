"""Materialize candidate synthetic manifest/header only; no new API is invoked."""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[4]
FIX = ROOT / 'tests/fixtures/w003_m1'
DEST = Path(__file__).resolve().parent / 'candidate-input'

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def uri(path):
    return os.path.relpath(path, DEST)

DEST.mkdir(exist_ok=True)
manifest = {
    'schema_version': 'layauto-cell-analysis-request/1', 'purpose': 'local_readonly',
    'mode': 'dummy_fixture',
    'inputs': {'gds': uri(FIX / 'source.gds'), 'source_cdl': uri(FIX / 'source.cdl'),
               'query_header': 'local-header.json'},
    'tech_ref': 'tech.json', 'limitation_ref': uri(FIX / 'limitations.json'),
    'external_body': {'kind': 'not_selected'},
}
write(DEST / 'analysis.json', manifest)
bundle = json.loads((FIX / 'tech.json').read_text())
for declaration in bundle['owners'].values():
    declaration['path'] = uri(FIX / declaration['path'])
write(DEST / 'tech.json', bundle)
requests = json.loads((FIX / 'query/requests.json').read_text())
for row in requests['requests']:
    row['path'] = uri(FIX / row['path'])
write(DEST / 'requests.json', requests)
header = json.loads((FIX / 'query/header.json').read_text())
header['schema_version'] = 'layauto-analysis-query-header/1'
header['header_id'] = 'w015.candidate.synthetic.local.1'
header['query_run_id'] = 'w015.candidate.synthetic.local.1'
del header['target']
for name in ('layout', 'source_netlist'):
    header[name]['uri'] = uri(FIX / header[name]['uri'])
header['limitations_ref'] = uri(FIX / 'limitations.json')
for row in header['raw']:
    row['uri'] = uri(FIX / row['uri'])
paths = [DEST / 'analysis.json', FIX / 'source.gds', FIX / 'source.cdl', DEST / 'tech.json',
         FIX / 'limitations.json', DEST / 'requests.json', FIX / 'query/dialect.json']
paths += [FIX / 'tech' / (name + '.json') for name in
          ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules')]
entries = sorted([{'uri': uri(p), 'sha256': sha(p)} for p in paths], key=lambda x: x['uri'])
header['closure']['entries'] = entries
header['closure']['sha256'] = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
write(DEST / 'local-header.json', header)
write(DEST / 'provenance.json', {
    'classification': 'candidate synthetic input only; not accepted by current runtime',
    'source_header': {'uri': uri(FIX / 'query/header.json'), 'sha256': sha(FIX / 'query/header.json')},
    'generator': 'docs/tasks/W015/evidence/prepare_candidate_input.py',
    'changes': ['new explicit local header/run identity', 'local dependency closure only',
                'original raw bytes and source hashes retained',
                'candidate tech owner paths and requests raw paths explicitly relocated', 'target excluded; no body or policy selection'],
    'observed_results_generated': False,
})
print(json.dumps({'candidate_only': True, 'local_dependencies': len(entries),
                  'raw_entries': len(header['raw']), 'manifest_sha256': sha(DEST / 'analysis.json'),
                  'header_sha256': sha(DEST / 'local-header.json')}))
