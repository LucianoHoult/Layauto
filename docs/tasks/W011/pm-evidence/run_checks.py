import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/workspace/Layauto')
OUT = Path('/workspace/work/w011-pm-check')
PYTHON = '/workspace/work/w005-pm-check-env/bin/python'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT))
commands = [
    ('targeted', [PYTHON, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
                 'tests/contracts/test_w011_geometry.py', '-k',
                 'actual_direct_composition_is_pure or normal_result_matches_all_independent or '
                 'existing_extraction_mismatch_is_actual or exact_fin_geometry_against_independent']),
    ('typing', [PYTHON, '-B', '-m', 'mypy', '--cache-dir', str(OUT / 'mypy-cache')]),
]
for name, argv in commands:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = time.monotonic()
    with (OUT / (name + '.stdout.txt')).open('wb') as stdout, (OUT / (name + '.stderr.txt')).open('wb') as stderr:
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
    receipt = dict(argv=argv, cwd=str(ROOT), started_utc=started,
                   finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   elapsed_seconds=time.monotonic()-before, returncode=result.returncode,
                   head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   environment_overrides={key: env[key] for key in ('PYTHONDONTWRITEBYTECODE', 'PYTHONPATH')},
                   interpreter=subprocess.check_output([PYTHON, '--version'], text=True).strip())
    for suffix in ('stdout.txt', 'stderr.txt'):
        path = OUT / (name + '.' + suffix)
        receipt[suffix] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (OUT / (name + '.json')).write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(name=name, returncode=result.returncode, elapsed_seconds=receipt['elapsed_seconds'])), flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
