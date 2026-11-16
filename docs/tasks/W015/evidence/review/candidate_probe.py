"""Independent source/hash/query boundary audit; no new runtime API is assumed."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.config import load_document, validate_tech
from layauto_v2.importers.calibre import parse_query

BASE = '5a815f58584746986b344f7616786b6360986e42'
CANDIDATE = ROOT / 'docs/tasks/W015/evidence/candidate-input'

def git_bytes(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def audit_header(directory, header_bytes, manifest_bytes, byte_provider):
    h = json.loads(header_bytes)
    m = json.loads(manifest_bytes)
    entries = h['closure']['entries']
    bad_hashes = [row['uri'] for row in entries + h['raw'] if digest(byte_provider(row['uri'])) != row['sha256']]
    closure_digest = digest(json.dumps(entries, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    requests_row = next(row for row in entries if row['uri'].endswith('requests.json'))
    dialect_row = next(row for row in entries if row['uri'].endswith('dialect.json'))
    req = json.loads(byte_provider(requests_row['uri']))
    mismatched_requests = [row['path'] for row in req['requests'] if row['path'] not in {r['uri'] for r in h['raw']}]
    bundle = json.loads(byte_provider(m['tech_ref']))
    missing_owners = [name for name, row in bundle['owners'].items() if not (directory / row['path']).is_file()]
    # Original broken candidate: old W005 owners isolate the independent raw URI error.
    # Repaired candidate: use its actual declared owner sources without fallback.
    # This is a parser-only probe, not an authentication receipt or new API success.
    source_by_owner = {}
    owner_docs = {}
    for name in ('drawn', 'derived', 'physical', 'formats', 'coordinate', 'rules'):
        owner_uri = bundle['owners'][name]['path']
        if missing_owners:
            path = ROOT / 'tests/fixtures/w003_m1/tech' / (name + '.json')
            source = SourceFile(str(path.relative_to(ROOT)), path.read_bytes())
        else:
            source = SourceFile(owner_uri, byte_provider(owner_uri))
        source_by_owner[name] = source
        owner_docs[name] = load_document(source)
    tech = freeze_map(owner_docs)
    validate_tech(tech, source_by_owner)
    raw = tuple(SourceFile(row['uri'], byte_provider(row['uri'])) for row in h['raw'])
    try:
        value = parse_query(raw, freeze_map(h), SourceFile(requests_row['uri'], byte_provider(requests_row['uri'])),
                            SourceFile(dialect_row['uri'], byte_provider(dialect_row['uri'])), tech,
                            derived_source=source_by_owner['derived'])
    except InputError as exc:
        query = {'status': 'error', 'code': exc.issue.code, 'category': exc.issue.category,
                 'source': exc.issue.source.uri, 'field': exc.issue.source.field}
    else:
        query = {'status': 'success', 'record_counts': {key: len(value[key]['records']) for key in
                  ('instance_xref', 'net_xref', 'device_regions', 'net_regions')}}
    return {'hash_mismatches': bad_hashes, 'closure_digest_matches': closure_digest == h['closure']['sha256'],
            'request_uri_mismatches': mismatched_requests, 'owner_paths_missing_from_manifest_root': missing_owners,
            'query_parser_only': query,
            'input_identity': {'manifest_sha256': digest(manifest_bytes), 'header_sha256': digest(header_bytes)},
            'actual_candidate_owner_sources_used': not missing_owners}

mode = sys.argv[1] if len(sys.argv) > 1 else 'initial'
if mode == 'initial':
    header = git_bytes('docs/tasks/W015/evidence/candidate-input/local-header.json')
    manifest = git_bytes('docs/tasks/W015/evidence/candidate-input/analysis.json')
    # Original dependencies all refer to frozen files or the original manifest.
    def read(uri):
        path = (CANDIDATE / uri).resolve().relative_to(ROOT)
        return git_bytes(str(path))
else:
    header = (CANDIDATE / 'local-header.json').read_bytes()
    manifest = (CANDIDATE / 'analysis.json').read_bytes()
    def read(uri):
        return (CANDIDATE / uri).read_bytes()
result = audit_header(CANDIDATE, header, manifest, read)
result['mode'] = mode
result['reviewed_initial_commit'] = BASE
result['python'] = sys.version
print(json.dumps(result, indent=2))
if mode == 'initial':
    assert not result['hash_mismatches'] and result['closure_digest_matches']
    assert len(result['request_uri_mismatches']) == 6
    assert len(result['owner_paths_missing_from_manifest_root']) == 6
    assert result['query_parser_only']['code'] == 'RequestBindingMismatch'
else:
    assert not result['hash_mismatches'] and result['closure_digest_matches']
    assert not result['request_uri_mismatches'] and not result['owner_paths_missing_from_manifest_root']
    assert result['query_parser_only']['status'] == 'success'
