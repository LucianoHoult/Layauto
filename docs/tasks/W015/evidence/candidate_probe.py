"""Probe candidate source closure/actual existing parsers; not the future API."""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.importers.config import load_document, validate_document, validate_tech
from layauto_v2.domain.codec import freeze_map
from layauto_v2.importers.calibre import parse_query
from layauto_v2.importers.gds import parse_gds
from layauto_v2.importers.cdl import parse_cdl

D = Path(__file__).resolve().parent / 'candidate-input'
def capture(uri):
    return SourceFile(uri, (D / uri).read_bytes())
def document(uri):
    return load_document(capture(uri))
m = json.loads((D / 'analysis.json').read_text())
h = json.loads((D / m['inputs']['query_header']).read_text())
for row in h['closure']['entries'] + h['raw']:
    assert hashlib.sha256((D / row['uri']).read_bytes()).hexdigest() == row['sha256']
assert h['closure']['sha256'] == hashlib.sha256(json.dumps(h['closure']['entries'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
bundle = document(m['tech_ref'])
validate_document(bundle, 'tech', capture(m['tech_ref']))
sources = {name: capture(decl['path']) for name, decl in bundle['owners'].items()}
tech = freeze_map({name: load_document(source) for name, source in sources.items()})
for name, source in sources.items():
    validate_document(tech[name], name, source)
validate_tech(tech, sources)
requests = next(r['uri'] for r in h['closure']['entries'] if r['uri'].endswith('requests.json'))
dialect = next(r['uri'] for r in h['closure']['entries'] if r['uri'].endswith('dialect.json'))
validate_document(document(requests), 'requests', capture(requests))
validate_document(document(dialect), 'dialect', capture(dialect))
query = parse_query(tuple(capture(r['uri']) for r in h['raw']), freeze_map(h),
                    capture(requests), capture(dialect), tech, derived_source=sources['derived'])
gds = parse_gds(capture(m['inputs']['gds']), tech)
cdl = parse_cdl(capture(m['inputs']['source_cdl']), tech)
print(json.dumps({'candidate_only': True, 'new_analysis_api_executed': False,
                  'closure_entries': len(h['closure']['entries']), 'raw_entries': len(h['raw']),
                  'query_capabilities': sorted(k for k in query if k != '_format_metadata'),
                  'gds_top': gds['top'], 'cdl_tops': [t['name'] for t in cdl['tops']],
                  'tool': h['tool'], 'body_selected': m['external_body']}))
