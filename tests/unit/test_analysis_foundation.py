"""W016 foundation probes; these do not claim the public analysis API exists."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from layauto_v2.domain.codec import FrozenMap
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.domain.results import InputError
from layauto_v2.importers.analysis_reader import acquire_analysis, _analysis_doc
from layauto_v2.importers.reader import read_inputs
from layauto_v2.normalization.analysis_input import LocalAnalysisReceipt

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / 'docs/tasks/W015/evidence/candidate-input'


def materialize(root):
    """Explicit synthetic migration; copy actual bytes, never compute answers."""
    m = json.loads((CANDIDATE / 'analysis.json').read_bytes())
    h = json.loads((CANDIDATE / 'local-header.json').read_bytes())
    uris = {x['uri'] for x in h['closure']['entries'] + h['raw']}
    names = {uri: f'{i:02d}-{Path(uri).name}' for i, uri in enumerate(sorted(uris))}
    names['analysis.json'] = 'analysis.json'
    for uri, name in names.items():
        (root / name).write_bytes((CANDIDATE / uri).read_bytes())
    def save(name, value):
        (root / name).write_text(json.dumps(value, sort_keys=True, separators=(',', ':')))
    m['inputs'] = {k: 'local-header.json' if k == 'query_header' else names[v] for k, v in m['inputs'].items()}
    m['tech_ref'] = names[m['tech_ref']]
    m['limitation_ref'] = names[m['limitation_ref']]
    save('analysis.json', m)
    tech = json.loads((root / m['tech_ref']).read_bytes())
    for owner in tech['owners'].values():
        owner['path'] = names[owner['path']]
    save(m['tech_ref'], tech)
    requests_uri = next(u for u in names if u.endswith('requests.json'))
    requests = json.loads((root / names[requests_uri]).read_bytes())
    for request in requests['requests']:
        request['path'] = names[request['path']]
    save(names[requests_uri], requests)
    h['header_id'] = h['query_run_id'] = 'w016.test.explicit-synthetic-migration'
    for key in ('layout', 'source_netlist'):
        h[key]['uri'] = names[h[key]['uri']]
    h['limitations_ref'] = m['limitation_ref']
    for row in h['raw']:
        row['uri'] = names[row['uri']]
    entries = sorted(({'uri': names[x['uri']], 'sha256': hashlib.sha256((root / names[x['uri']]).read_bytes()).hexdigest()} for x in h['closure']['entries']), key=lambda x:x['uri'])
    h['closure']['entries'] = entries
    h['closure']['sha256'] = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    save('local-header.json', h)
    return root / 'analysis.json'


def test_actual_local_capture_reparse_without_full_run_files(tmp_path, monkeypatch):
    manifest = materialize(tmp_path)
    evidence = acquire_analysis(manifest)
    assert evidence.issues == ()
    assert len(evidence.captures) == 23
    assert not {'target_cdl', 'body', 'policies'} & {x.kind for x in evidence.records}
    def forbidden(*args, **kwargs):
        raise AssertionError('authentication must not read or resolve the filesystem')
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    receipt = LocalAnalysisReceipt(evidence)
    assert len(receipt.ref) == 64


def test_disk_change_does_not_change_receipt(tmp_path):
    manifest = materialize(tmp_path)
    evidence = acquire_analysis(manifest)
    before = LocalAnalysisReceipt(evidence).ref
    manifest.write_text('{}')
    assert LocalAnalysisReceipt(evidence).ref == before
    assert acquire_analysis(manifest).issues


@pytest.mark.parametrize('mutation', ['payload', 'missing_raw', 'alias', 'mutable_leaf', 'extra_field'])
def test_forged_evidence_is_rejected(tmp_path, mutation):
    evidence = acquire_analysis(materialize(tmp_path))
    if mutation == 'payload':
        evidence = replace(evidence, value=FrozenMap({'fake': True}))
    elif mutation == 'missing_raw':
        # Replace the immutable shell without allowing its constructor to erase evidence.
        object.__setattr__(evidence, 'captures', evidence.captures[:-1])
    elif mutation == 'alias':
        object.__setattr__(evidence, 'aliases', FrozenMap({}))
    elif mutation == 'mutable_leaf':
        object.__setattr__(evidence.captures[0], 'data', bytearray(b'fake'))
    else:
        object.__setattr__(evidence.captures[0], 'undeclared', [])
    with pytest.raises(ValueError):
        LocalAnalysisReceipt(evidence)


def test_legacy_and_analysis_headers_are_not_interchangeable(tmp_path):
    source = SourceFile('header.json', (ROOT / 'tests/fixtures/w003_m1/query/header.json').read_bytes())
    with pytest.raises(InputError, match='explicit synthetic migration'):
        _analysis_doc(source, 'analysis_header')
    manifest = materialize(tmp_path)
    assert read_inputs(manifest).status == 'error'


@pytest.mark.parametrize('text', ['{"schema_version":"x","schema_version":"y"}', '{"bad":1.2}', '{"extra":true}'])
def test_bad_manifest_returns_located_issue(tmp_path, text):
    manifest = tmp_path / 'analysis.json'
    manifest.write_text(text)
    result = acquire_analysis(manifest)
    assert result.value is None and result.issues
    assert result.issues[0].source.sha256 == hashlib.sha256(text.encode()).hexdigest()
