"""Read-only W013 preflight; records existing accepted input limitations.

Run from the repository root with Python 3.10+. This is diagnostic evidence,
not a W013 implementation or a new accepted fixture/answer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from layauto_v2.domain.identifiers import QueryKey
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import from_parse_result, normalize


def main() -> None:
    root = Path.cwd()
    fixture = root / 'tests/fixtures/w003_m1'
    parsed = read_inputs(fixture / 'site_config.yaml')
    assert parsed.status == 'success', parsed.issues
    normalized = normalize(from_parse_result(parsed))
    assert normalized.status == 'success' and normalized.value is not None
    facts = normalized.value
    keys = []
    for index in ('1', '7', '007'):
        try:
            key = QueryKey('probe-header', 'probe-run', 'probe-db', 'net', 'probe-name', index)
        except ValueError as exc:
            keys.append({'index': index, 'outcome': type(exc).__name__, 'message': str(exc)})
        else:
            keys.append({'index': index, 'outcome': 'accepted', 'retained_index': key.index})
    assert keys[-1]['outcome'] == 'ValueError'
    paths = (
        'layauto_v2/domain/identifiers.py',
        'layauto_v2/importers/calibre.py',
        'layauto_v2/normalization/_validation.py',
        'layauto_v2/normalization/contracts.py',
        'tests/fixtures/w003_m1/query/dialect.json',
        'tests/fixtures/w003_m1/query/raw/net_names.txt',
        'tests/fixtures/w003_m1/query/raw/nXref.temp',
        'tests/fixtures/w003_m1/tech/derived.json',
        'tests/fixtures/w003_m1/oracle.json',
        'tests/fixtures/w003_m1/special/cut_islands/oracle.json',
    )
    old_manifest = json.loads((root / 'docs/tasks/W012/A1/verification-r2/source-manifest.json').read_text())
    # Keep the original manifest schema visible instead of assuming a count
    # establishes identity. The actual identity comparison is recorded separately.
    result = {
        'classification': 'existing-input-preflight-not-W013-product-validation',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'python': sys.version,
        'executable': sys.executable,
        'platform': platform.platform(),
        'fixture_uri': str(fixture),
        'query_key_probe': keys,
        'net_identities': [
            {'schematic_name': item.net_id.name, 'layout_name': item.query_key.identity,
             'lvs_index': item.query_key.index, 'header_id': item.query_key.header_id,
             'query_run_id': item.query_key.query_run_id, 'database_id': item.query_key.database_id,
             'index_provenance': dict(item.provenance['field_sources']['lvs_index'])}
            for item in facts.net_identities
        ],
        'net_seeds': [
            {'record_id': item.record['record_id'], 'schematic_name': item.semantic_id.name,
             'layout_name': item.query_key.identity, 'lvs_index': item.query_key.index,
             'quality': item.record['quality'], 'geometry_kind': item.record['geometry_kind'],
             'unit': item.record['unit'], 'derived_layer': item.record['derived_layer']}
            for item in facts.net_seeds
        ],
        'sources': {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths},
        'old_manifest_top_level': sorted(old_manifest) if isinstance(old_manifest, dict) else type(old_manifest).__name__,
    }
    # FrozenMap/tuple source operands are converted only for this diagnostic JSON.
    def plain(value: object) -> object:
        if hasattr(value, 'items'):
            return {key: plain(child) for key, child in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(child) for child in value]
        return value
    print(json.dumps(plain(result), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
