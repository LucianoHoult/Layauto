"""Freeze exact A1/candidate files, fixed inputs and environment before A2 screening."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tarfile

from common import BASE, FIXED_ROOT, OWNERS, baseline, dump_new, environment, identity, inputs, sha


def tools():
    here = Path(__file__).resolve().parent
    return {path.name: sha(path.read_bytes()) for path in sorted(here.glob('*.py'))}


def freeze(args):
    assert not args.out.exists(), 'freeze output already exists; preserve evidence'
    before = baseline(args.before_root.resolve())
    after_root = args.after_root.resolve()
    after = identity(after_root)
    differences = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    assert OWNERS <= set(differences), 'both candidate encoder owners must differ from actual A1'
    assert all(name in OWNERS or (name.startswith('tests/') and name.endswith('.py')) for name in differences)
    assert not set(before) - set(after), 'original files/tests must remain'
    frozen_inputs = inputs(rebuild=True)
    args.out.mkdir(parents=True)
    for side, root, manifest in (('before', args.before_root.resolve(), before), ('after', after_root, after)):
        with tarfile.open(args.out / (side + '-source-snapshot.tar.gz'), 'x:gz') as archive:
            for name in manifest:
                archive.add(root / name, arcname=name, recursive=False)
        dump_new(args.out / (side + '-source-manifest.json'),
                 {'files': manifest, 'root': str(root),
                  'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                  'git_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True),
                  'snapshot_sha256': sha((args.out / (side + '-source-snapshot.tar.gz')).read_bytes())})
    dump_new(args.out / 'freeze.json',
             {'schema': 'w012-a2-implementation-freeze/1', 'at_utc': datetime.now(timezone.utc).isoformat(),
              'base': BASE, 'roots': {'before': str(args.before_root.resolve()), 'after': str(after_root)},
              'sources': {'before': before, 'after': after}, 'differences': differences,
              'tools': tools(), 'environment': environment(), 'inputs': frozen_inputs,
              'fixed_input_root': str(FIXED_ROOT), 'mismatch': '/workspace/w012-inputs/extraction-mismatch',
              'request': {'proposed_run_id': 'w012-investigation-run',
                          'lineage_id': 'w012-investigation-lineage', 'idempotency_key': 'create-w012',
                          'site_path': '/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml',
                          'selection_tuples': 'all defaults empty'},
              'conditions': 'fresh process and repository, all A1 roots retained, one gc.collect before acquire, automatic GC thereafter'})
    print('Frozen local A1/candidate source/tests/config, original fixed 35 inputs and environment')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-root', type=Path, required=True)
    parser.add_argument('--after-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    freeze(parser.parse_args())
