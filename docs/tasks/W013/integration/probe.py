"""Actual merge-tree composition; reuses frozen smoke assertions, not an install test."""
from pathlib import Path
import gc
import hashlib
import json
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
import layauto_v2
from layauto_v2.domain.publication import InputsReady, RunRequest
from layauto_v2.importers import read_inputs
from layauto_v2.normalization import (
    build_geometry, build_effective_geometry, build_local_connectivity,
    geometry_from_inputs_ready,
)
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

assert Path(layauto_v2.__file__).resolve() == ROOT / 'layauto_v2/__init__.py'
MERGE = '088ed3c718eb5a0703511ff6b214274f30052ff1'
REVIEW = 'da90a793cc1d1e45ae7f2de26d9e98766191428d'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == MERGE
assert not subprocess.check_output(['git', 'diff', '--name-only', MERGE, REVIEW], cwd=ROOT)
manifest = json.loads((ROOT / 'docs/tasks/W013/verification-r2/source-manifest.json').read_text())
for name, expected in manifest['files'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
print(json.dumps({'merge': MERGE, 'review': REVIEW, 'identical_tree': True,
                  'source_files': len(manifest['files']), 'source_id': manifest['source_id'],
                  'python': sys.version, 'import_path': layauto_v2.__file__}), flush=True)

smoke = runpy.run_path(str(ROOT / 'docs/tasks/W013/verification-r2/installed_smoke.py'))
fixture = ROOT / 'tests/fixtures/w003_m1'

def check(local, case):
    smoke['check_upstream'](local)
    result = smoke['annotation_checks'](local, case)
    print(json.dumps({'case': case, **result}), flush=True)

local = smoke['local_from_parse'](read_inputs(fixture / 'site_config.yaml'))
check(local, 'normal-direct')
del local
gc.collect()

repository = PublicationRepository()
ready = prepare_inputs(repository, RunRequest(
    proposed_run_id='w013-pm-integration', lineage_id='w013-pm-integration',
    idempotency_key='w013-pm-integration', site_path=str(fixture / 'site_config.yaml')))
assert isinstance(ready, InputsReady)
checkpoint = repository.load_checkpoint(ready.run_id)
attempt = repository.load_attempt(ready.run_id)
local = build_local_connectivity(build_effective_geometry(build_geometry(geometry_from_inputs_ready(
    ready, checkpoint, repository.read(ready.parse_ref), repository.read(ready.tool_ref),
    tuple(repository.read(ref) for ref in ready.evidence_refs)))))
check(local, 'normal-readback')
assert repository.load_attempt(ready.run_id) == attempt and attempt.phase == 'unsealed'
assert repository.load_checkpoint(ready.run_id) == checkpoint
assert repository.read_terminal(ready.run_id) is None
del local
gc.collect()

with tempfile.TemporaryDirectory(prefix='w013-pm-mismatch-') as tmp:
    site = smoke['make_mismatch_input'](fixture, Path(tmp) / 'input')
    local = smoke['local_from_parse'](read_inputs(site))
    check(local, 'extraction-mismatch')
print(json.dumps({'status': 'passed', 'attempt_unchanged': True, 'checkpoint_unchanged': True,
                  'terminal_absent': True, 'limits': [
                      'Synthetic local/source-evidence only; no full M1 or production/EDA assurance.',
                      'Source-tree integration check, not a fresh clean-install or performance matrix.',
                      'Paths differ from historical runs; wire hashes are not benchmark comparisons.']}), flush=True)
