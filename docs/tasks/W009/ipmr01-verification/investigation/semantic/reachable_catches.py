"""Read-only in-memory probes of legal W009 result wires at cdf3d2d."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from unittest.mock import patch

from layauto_v2.importers import read_inputs
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.normalization import (build_geometry, build_effective_geometry,
    from_inputs_ready, from_parse_result, geometry_from_normalization_input)
from layauto_v2.normalization.effective_codec import encode_record, decode_record
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

root = Path.cwd()
fixture = root / 'tests/fixtures/w003_m1/site_config.yaml'
parsed = read_inputs(fixture)
assert parsed.status == 'success'
repository = PublicationRepository()
ready = prepare_inputs(repository, RunRequest(proposed_run_id='ipmr01-audit', lineage_id='ipmr01-audit-lineage',
    idempotency_key='ipmr01-audit-create', site_path=str(fixture)))
assert isinstance(ready, InputsReady)
readback = from_inputs_ready(ready, repository.load_checkpoint(ready.run_id), repository.read(ready.parse_ref),
    repository.read(ready.tool_ref), tuple(repository.read(ref) for ref in ready.evidence_refs))
inputs = {'direct': from_parse_result(parsed), 'readback': readback}
wires = {}
for label, receipt in inputs.items():
    geometry = build_geometry(geometry_from_normalization_input(receipt))
    result = build_effective_geometry(geometry)
    assert result.status == 'success'
    wire = encode_record(result)
    assert decode_record(wire) == result
    wires[label] = wire

rows = []
for label, wire in wires.items():
    targets = ['layauto_v2.normalization.contracts.request_decoder_input',
        'layauto_v2.normalization._validation._validate_cdl',
        'layauto_v2.normalization._validation._validate_query',
        'layauto_v2.domain.evidence.hashlib.sha256']
    if label == 'readback':
        targets.append('layauto_v2.normalization.contracts.content_ref')
    for target in targets:
        for cls in (TypeError, KeyError, AttributeError, IndexError, UnicodeError):
            cause = RuntimeError('existing cause')
            context = LookupError('existing context')
            failure = cls('audit legal wire internal reconstruction failure')
            failure.__cause__ = cause
            failure.__context__ = context
            failure.__suppress_context__ = False
            def broken(*args, **kwargs):
                raise failure
            with patch(target, broken):
                try:
                    decode_record(wire)
                except BaseException as observed:
                    rows.append({'input': label, 'target': target, 'injected': cls.__name__,
                        'observed': type(observed).__name__, 'message': str(observed),
                        'same_object': observed is failure, 'wrapped_cause_is_failure': observed.__cause__ is failure,
                        'failure_cause_preserved': failure.__cause__ is cause,
                        'failure_context_preserved': failure.__context__ is context})
                else:
                    raise AssertionError('fault not reached')

paths = ['layauto_v2/normalization/contracts.py', 'layauto_v2/normalization/_validation.py',
    'layauto_v2/normalization/codec.py', 'layauto_v2/domain/publication_codec.py', 'layauto_v2/domain/evidence.py']
print(json.dumps({'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'cwd': str(root), 'python': sys.version, 'executable': sys.executable,
    'platform': platform.platform(), 'wire_sha256': {k: hashlib.sha256(v).hexdigest() for k,v in wires.items()},
    'sources': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
    'case_count': len(rows), 'same_object_count': sum(r['same_object'] for r in rows),
    'identity_failures': [r for r in rows if not r['same_object']], 'observations': rows}, indent=2, sort_keys=True))
