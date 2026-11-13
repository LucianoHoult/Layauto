"""Independent bounded W013 provenance checks; never constructs a W010 graph."""
from collections.abc import Mapping
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from layauto_v2.domain.codec import freeze_map
from layauto_v2.domain.identifiers import QueryKey
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize

ROOT = Path.cwd()
FIXTURE = ROOT / 'tests/fixtures/w003_m1'

def plain(x):
    if isinstance(x, Mapping):
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, tuple):
        return [plain(v) for v in x]
    return x

def transform(x, name, value):
    if isinstance(x, Mapping):
        return {k: value if k == name else transform(v, name, value) for k, v in x.items()}
    if isinstance(x, tuple):
        return tuple(transform(v, name, value) for v in x)
    return x

def rejected(fn):
    try:
        fn()
    except ValueError as exc:
        return {'status': 'rejected', 'type': type(exc).__name__, 'message': str(exc)}
    raise AssertionError('forged evidence was admitted')

parsed = read_inputs(FIXTURE / 'site_config.yaml')
assert parsed.status == 'success'
input = from_parse_result(parsed)
normalized = normalize(input)
assert normalized.status == 'success'
facts = normalized.value
# Expected identity comes from the two raw text operands independently of the
# product parser's returned xref rows or W013 matcher.
names = (FIXTURE / 'query/raw/net_names.txt').read_text().splitlines()[3:-1]
xref = {}
for line in (FIXTURE / 'query/raw/nXref.temp').read_text().splitlines():
    words = line.split()
    if len(words) == 4 and words[0] == words[2] == '0':
        xref[words[1]] = words[3]
expected = {name: (xref[name], str(i + 1)) for i, name in enumerate(names)}
observed = {row.query_key.identity: (row.net_id.name, row.query_key.index) for row in facts.net_identities}
assert observed == expected == {'n_a': ('A', '1'), 'n_y': ('Y', '2'), 'n_lo': ('VSS', '3'), 'n_hi': ('VDD', '4')}
assert len(facts.net_seeds) == 8
ids = {row.query_key: row for row in facts.net_identities}
for seed in facts.net_seeds:
    assert ids[seed.query_key].net_id == seed.semantic_id
    assert seed.record['lvs_index'] == seed.query_key.index
    assert seed.semantic_id.cell == facts.source.selected_cell
checks = {}
for name, value in (('query_run_id', 'foreign.query.run'), ('query_database_id', 'foreign.database'),
                    ('top_identities', {'layout':'FOREIGN', 'source':'FOREIGN'}),
                    ('lvs_index', '007')):
    # Both normal value and completed normalized evidence are forged together.
    # Captured raw bytes and source hashes are deliberately left untouched.
    forged = replace(parsed, value=freeze_map(transform(parsed.value, name, value)),
        completed=tuple(replace(row, payload=freeze_map(transform(row.payload, name, value))) for row in parsed.completed))
    checks[name] = rejected(lambda: from_parse_result(forged))
checks['query_key_007'] = rejected(lambda: QueryKey('h', 'r', None, 'net', 'n_a', '007'))
key = facts.net_identities[0].query_key
assert replace(key, query_run_id='other').id != key.id
assert replace(key, database_id='other').id != key.id
# Independently read the CURRENT local oracle and special fixture: they are
# expected answers only, never passed into any product call above.
o = json.loads((FIXTURE/'oracle.json').read_text())
components = o['components']
assert len(components) == 6 and len(o['edges']) == 8
assert sum(len(row['regions']) for row in components) == 14
assert len([row for row in components if row['net'] is not None]) == 4
assert {tuple(row['regions']) for row in components if row['net'] is None} == {('BN',), ('BP',)}
special = json.loads((FIXTURE/'special/cut_islands/oracle.json').read_text())
assert special['component_count'] == 3 and special['shared_label'] == 'A' and special['edges'] == []
paths = ['layauto_v2/importers/calibre.py', 'layauto_v2/normalization/_validation.py',
         'layauto_v2/normalization/identity.py', 'layauto_v2/normalization/net_annotation.py',
         'tests/fixtures/w003_m1/query/raw/net_names.txt', 'tests/fixtures/w003_m1/query/raw/nXref.temp',
         'tests/fixtures/w003_m1/oracle.json', 'tests/fixtures/w003_m1/special/cut_islands/oracle.json']
print(json.dumps({'classification':'independent-premerge-binding-bounded-probe',
    'head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
    'identity_from_raw':observed,'seed_count':len(facts.net_seeds),'rejections':checks,
    'local_oracle':{'nodes':14,'edges':8,'components':6,'associated':4,'unknown_body':2},
    'cut_special':{'components':3,'shared_label':'A','edges':0},
    'hashes': {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
    'scope':'reader->W007 only; no W010/W013 execution or publication; product/fixture bytes unchanged'},
    indent=2,ensure_ascii=False))
