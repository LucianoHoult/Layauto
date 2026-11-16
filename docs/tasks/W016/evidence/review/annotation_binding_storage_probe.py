"""Independent new-binding reconstruction probe, using actual-file local setup.

The execution probe supplies only a real constructed draft; it supplies no
expected answer for these deliberate invalid scope/version/storage assertions.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
values = runpy.run_path(str(ROOT / 'docs/tasks/W016/evidence/local_probe.py'))
draft = values['annotation']
rows = []
for field, forged in (('scope', 'production_verified'), ('validity', 'trusted'),
                      ('schema_version', 'layauto-net-annotation/1')):
    altered = replace(draft.binding)
    object.__setattr__(altered, field, forged)
    try:
        replace(draft, binding=altered)
    except ValueError as exc:
        rows.append({'field': field, 'rejected': True, 'error': str(exc)})
    else:
        raise AssertionError('Draft accepted forged analysis binding ' + field)
original = draft.binding.scope
try:
    object.__setattr__(draft.binding, 'scope', 'production_verified')
    try:
        draft.to_value()
    except ValueError as exc:
        rows.append({'operation': 'to_value', 'rejected': True, 'error': str(exc)})
    else:
        raise AssertionError('Report value accepted mutated binding scope')
finally:
    object.__setattr__(draft.binding, 'scope', original)
print(json.dumps({'probe': 'analysis-binding-reconstruction', 'results': rows,
    'source_hashes': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted((ROOT / 'layauto_v2').rglob('*.py'))}}, indent=2))
