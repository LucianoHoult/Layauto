"""A2 evidence utilities, never imported by runtime or formal product tests."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

BASE = '2489b4609ae97d8211bf450d55cac9392492ac71'
PREPARATION = '0213c346ac03b7b7282aae522c299155958ac8f6'
FIXED_ROOT = Path('/workspace/Layauto')
OVERLAY = Path('/workspace/w012-inputs/extraction-mismatch')
CASES = ('normal-direct', 'normal-readback', 'extraction-mismatch')
OWNERS = {'layauto_v2/normalization/local_connectivity_codec.py',
          'layauto_v2/normalization/channel_identity_codec.py'}
OVERLAYS = {'source.gds', 'query/header.json', 'query/raw/device_info_Q17.txt',
            'query/normalized/device_regions.yaml', 'body/context.json'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def dump_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')


def identity(root):
    historical = read_json(FIXED_ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json')
    names = set(historical['files'])
    names.update(str(p.relative_to(root)) for p in (root / 'tests').rglob('*.py'))
    names.update(str(p.relative_to(root)) for p in (root / 'layauto_v2').rglob('*.py'))
    return {name: sha((root / name).read_bytes()) for name in sorted(names)}


def environment():
    return {'python': sys.version, 'executable': sys.executable,
            'platform': platform.platform(),
            'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
            'cgroup': {name: Path('/sys/fs/cgroup', name).read_text().strip()
                       for name in ('memory.max', 'memory.swap.max', 'cpu.max')}}


def inputs(rebuild=False):
    """Exact original 35-item manifest, including the original five overlays."""
    old = read_json(FIXED_ROOT / 'docs/tasks/W012/A1/preflight.json')['inputs']
    assert len(old) == 35
    fixture = FIXED_ROOT / 'tests/fixtures/w003_m1'
    rows, overlaid = [], set()
    expected_targets = set()
    for item in old:
        target, origin = Path(item['target']), Path(item['origin'])
        relative = target.relative_to(OVERLAY)
        assert str(origin).startswith(str(fixture) + '/')
        is_overlay = origin.is_relative_to(fixture / 'failures/extraction_mismatch')
        assert is_overlay == (str(relative) in OVERLAYS)
        if is_overlay:
            overlaid.add(str(relative))
        data = origin.read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes']
        expected_targets.add(str(target))
        if rebuild and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
        assert target.read_bytes() == data, 'fixed input differs; preserve and investigate'
        # Also freeze normal-side counterpart bytes at their original URI.
        normal = fixture / relative
        rows.append({**item, 'normal': str(normal), 'normal_sha256': sha(normal.read_bytes()),
                     'overlay': is_overlay})
    assert overlaid == OVERLAYS
    assert {str(p) for p in OVERLAY.rglob('*') if p.is_file()} == expected_targets
    return rows


def baseline(root):
    """Rebuild only from the exact local A1 Git tree, never from old measurements."""
    if not root.exists():
        subprocess.run(['git', 'worktree', 'add', '--detach', str(root), BASE],
                       cwd=FIXED_ROOT, check=True)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == BASE
    files = identity(root)
    accepted = read_json(FIXED_ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json')['files']
    assert files == accepted, 'baseline source/tests/config differ from accepted A1'
    for name, expected in files.items():
        assert sha(subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=FIXED_ROOT)) == expected
    return files


def same_bytes(left, right):
    count = 0
    with left.open('rb') as a, right.open('rb') as b:
        while True:
            x, y = a.read(1024 * 1024), b.read(1024 * 1024)
            assert x == y, 'actual complete wire bytes differ'
            count += len(x)
            if not x:
                return count
