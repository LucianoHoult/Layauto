"""Independent caller selections for run-aware actual-file tests (not runtime)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from layauto_v2.domain.publication import RunRequest, Selection


def byte_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def caller_request(root: Path, *, run_id: str = 'run-w006',
                   site_name: str = 'site_config.yaml', **overrides) -> RunRequest:
    """Caller discovers its selections independently before invoking the product.

    No product parser, sample-record answer, oracle or fixture support is used.
    Header closure is a caller input declaration, not proof of actual read bytes.
    """
    site = json.loads((root / site_name).read_text(encoding='utf-8'))
    header = json.loads((root / site['inputs']['query_header']).read_text(encoding='utf-8'))
    input_uris = set(site['inputs'].values())
    raw_uris = {entry['uri'] for entry in header['raw']}
    config_uris = {entry['uri'] for entry in header['closure']['entries']} - input_uris

    def selected(uris):
        return tuple(Selection(uri, byte_sha(root / uri)) for uri in sorted(uris))

    fields = dict(proposed_run_id=run_id, lineage_id='lineage-w006',
                  idempotency_key='create-w006', site_path=str(root / site_name),
                  raw_input_selections=selected(input_uris),
                  raw_capture_selections=selected(raw_uris),
                  config_policy_selections=selected(config_uris),
                  raw_descriptor={'caller': 'independent-test', 'selected_profile': 'synthetic'})
    fields.update(overrides)
    return RunRequest(**fields)


def rename_site(root: Path, name: str = 'chosen-entry.json') -> str:
    """Relocate the site filename and rebind only the real header closure."""
    (root / 'site_config.yaml').rename(root / name)
    header_path = root / 'query/header.json'
    header = json.loads(header_path.read_text(encoding='utf-8'))
    for entry in header['closure']['entries']:
        if entry['uri'] == 'site_config.yaml':
            entry['uri'] = name
            entry['sha256'] = byte_sha(root / name)
    header['closure']['entries'].sort(key=lambda item: item['uri'])
    raw = json.dumps(header['closure']['entries'], sort_keys=True,
                     separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    header['closure']['sha256'] = hashlib.sha256(raw).hexdigest()
    header_path.write_text(json.dumps(header, indent=2) + '\n', encoding='utf-8')
    return name
