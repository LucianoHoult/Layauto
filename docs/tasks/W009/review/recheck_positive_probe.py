"""Run a formerly positive alias probe and record its corrected rejection."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import traceback

try:
    runpy.run_path(sys.argv[1])
except ValueError as exc:
    frame = traceback.extract_tb(exc.__traceback__)[-1]
    print(json.dumps({'status': 'rejected', 'reason': str(exc),
                      'last_frame': {'filename': frame.filename, 'lineno': frame.lineno, 'name': frame.name},
                      'source_sha256': {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                        for path in ('layauto_v2/domain/regions.py', 'layauto_v2/state/regions.py',
                                                     'layauto_v2/normalization/effective.py')}}, indent=2))
else:
    raise AssertionError('former alias probe unexpectedly accepted')
