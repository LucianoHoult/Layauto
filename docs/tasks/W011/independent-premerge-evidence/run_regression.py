"""Independent premerge selection; retains original output and process facts."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
NODES = [
    'tests/contracts/test_w011_geometry.py::test_actual_direct_composition_is_pure_and_retains_original_inputs',
    'tests/contracts/test_w011_geometry.py::test_normal_result_matches_all_independent_crossings_and_retains_18_fin',
    'tests/contracts/test_w011_geometry.py::test_existing_extraction_mismatch_is_actual_four_against_source_five',
    'tests/contracts/test_w011_geometry.py::test_partial_crossing_preserves_unknown_count_and_all_decidable_l_w',
    'tests/contracts/test_w011_geometry.py::test_zero_crossing_does_not_claim_width_was_verified',
    'tests/contracts/test_w011_geometry.py::test_original_t05_violation_and_body_scope_remain_visible',
    'tests/contracts/test_w011_contracts.py::test_all_topology_refs_reach_actual_ordered_regions_and_shared_gate',
    'tests/contracts/test_w011_contracts.py::test_public_results_reject_cross_capture_semantic_or_graph_substitution',
    'tests/contracts/test_w011_contracts.py::test_cr04_full_result_rebuilds_unmeasured_source_provenance_beyond_projection',
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
argv = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', *NODES]
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
with (OUT / 'regression.stdout.txt').open('w') as stdout, (OUT / 'regression.stderr.txt').open('w') as stderr:
    result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
receipt = dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    argv=argv, cwd=str(ROOT), python=sys.version, start_utc=start,
    end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-tick,
    exit_code=result.returncode, child_ru_maxrss_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    environment_overrides={key:env[key] for key in ('PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD')},
    limits={'memory.max':Path('/sys/fs/cgroup/memory.max').read_text().strip(),
            'cpu.max':Path('/sys/fs/cgroup/cpu.max').read_text().strip()},
    outputs={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('regression.stdout.txt','regression.stderr.txt')})
(OUT / 'regression.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
sys.exit(result.returncode)
