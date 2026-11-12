"""Run immutable original pure-neutral review probes with full runtime identity."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback

FILES = ('layauto_v2/domain/net_annotation.py', 'layauto_v2/state/annotation.py',
         'layauto_v2/annotation/net_regions.py', 'layauto_v2/derive/net_annotation.py',
         'layauto_v2/normalization/net_annotation.py', 'layauto_v2/normalization/net_annotation_codec.py',
         'layauto_v2/normalization/__init__.py', 'pyproject.toml')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('probes', nargs='+')
    args = parser.parse_args()
    root, out = Path.cwd(), args.out
    out.mkdir(parents=True, exist_ok=False)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    identities = {name: digest(root / name) for name in FILES}
    patch = subprocess.check_output(['git', 'diff', 'HEAD', '--', *FILES])
    (out / 'runtime.patch').write_bytes(patch)
    rows = []
    for name in args.probes:
        path = root / 'docs/tasks/W013/review-evidence/neutral-static' / name
        stdout, stderr = io.StringIO(), io.StringIO()
        clock = time.perf_counter()
        row = {'script': str(path.relative_to(root)), 'sha256': digest(path),
               'started_at_utc': datetime.now(timezone.utc).isoformat()}
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                runpy.run_path(str(path), run_name='__main__')
        except BaseException as exc:
            row.update(outcome='rejected', error_type=type(exc).__name__, message=str(exc))
            traceback.print_exception(exc, file=stderr)
        else:
            row['outcome'] = 'accepted'
        row['seconds'] = time.perf_counter() - clock
        (out / (name + '.stdout.txt')).write_text(stdout.getvalue())
        (out / (name + '.stderr.txt')).write_text(stderr.getvalue())
        row.update(stdout_sha256=hashlib.sha256(stdout.getvalue().encode()).hexdigest(),
                   stderr_sha256=hashlib.sha256(stderr.getvalue().encode()).hexdigest())
        rows.append(row)
    stable = identities == {name: digest(root / name) for name in FILES}
    stable = stable and patch == subprocess.check_output(['git', 'diff', 'HEAD', '--', *FILES])
    result = {'classification': 'independent-pure-neutral-review-recheck-not-product-matrix',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'source_files': identities, 'runtime_patch_sha256': hashlib.sha256(patch).hexdigest(),
        'source_stable_during_probes': stable, 'cwd': str(root), 'python': sys.version,
        'executable': sys.executable, 'argv': sys.argv,
        'probes': rows, 'scope': 'Original pure small-value probes only; no captured construction or resource claim.'}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    assert stable, 'Runtime changed during independent review probes; preserve this attempt and retry.'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
