"""Reproducible read-only source/environment audit for the W013 implementation gate."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


def main() -> None:
    root = Path.cwd()
    out = root / 'docs/tasks/W013'
    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def command(argv: list[str]) -> dict[str, object]:
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic()
        result = subprocess.run(argv, text=True, capture_output=True, check=False)
        return {'argv': argv, 'cwd': str(root), 'utc_start': started,
                'seconds': time.monotonic() - tick, 'returncode': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
    manifest_path = root / 'docs/tasks/W012/A1/verification-r2/source-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    checked = {name: {'expected': expected, 'actual': sha(root / name) if (root / name).is_file() else None}
               for name, expected in manifest['files'].items()}
    differences = {name: item for name, item in checked.items() if item['actual'] != item['expected']}
    dependencies = {}
    for name in ('numpy', 'matplotlib', 'PyYAML', 'pytest', 'mypy', 'build', 'types-PyYAML'):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    evidence = command([sys.executable, '-B', str(out / 'input-boundary-probe.py')])
    # Original stdout is retained; exit success only establishes the diagnostics ran.
    (out / 'input-boundary-probe.stdout.json').write_text(str(evidence.pop('stdout')))
    (out / 'input-boundary-probe.stderr.txt').write_text(str(evidence.pop('stderr')))
    evidence['stdout_path'] = 'input-boundary-probe.stdout.json'
    evidence['stderr_path'] = 'input-boundary-probe.stderr.txt'
    evidence['stdout_sha256'] = sha(out / 'input-boundary-probe.stdout.json')
    evidence['probe_sha256'] = sha(out / 'input-boundary-probe.py')
    result = {
        'classification': 'pre-implementation-read-only-evidence-not-W013-final-matrix',
        'utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'dependencies': dependencies,
        'python310_on_path': shutil.which('python3.10'),
        'historical_paths_exist': {name: Path(name).exists() for name in (
            '/workspace/w012-a1-env/dev310/bin/python', '/workspace/w012-a1-env/dev312/bin/python',
            '/workspace/w012-inputs/extraction-mismatch')},
        'cgroup': {name: Path('/sys/fs/cgroup', name).read_text().strip()
                   for name in ('memory.max', 'cpu.max')},
        'old_manifest_path': str(manifest_path.relative_to(root)),
        'old_manifest_sha256': sha(manifest_path), 'files_checked': len(checked),
        'old_identity_differences': differences,
        'probe': evidence,
        'commands': [command(argv) for argv in (
            ['git', 'rev-parse', 'HEAD'], ['git', 'status', '--short', '--branch'],
            ['git', 'ls-remote', 'origin', 'refs/heads/main', 'refs/heads/codex/w013-net-annotation-coverage'],
            ['git', 'merge-base', '--is-ancestor', '2489b4609ae97d8211bf450d55cac9392492ac71', 'HEAD'],
            ['git', 'diff', '--name-only', '2489b4609ae97d8211bf450d55cac9392492ac71', '--',
             'layauto_v2', 'tests', 'pyproject.toml'],
            ['git', 'diff', '--name-only', '--', 'layauto_v2', 'tests', 'pyproject.toml',
             'docs/architecture.md', 'docs/current-work.md', 'docs/collaboration/rules.md'],
        )],
        'initial_recovery_failures': [
            'git switch --track failed because the managed checkout did not configure this remote branch as a tracked branch',
            'Fetched the exact branch ref explicitly, then created the original-named local branch without tracking; no content was lost',
        ],
        'verification_reuse': {
            'actually_run': 'source hashes, environment inventory, real reader/W007 and QueryKey diagnostics',
            'adopted_by_identity': 'unchanged A1 upstream historical evidence only; no new timing claim',
            'not_run': 'W013 product, full three-path resource combination, new full matrix/typing/build/install/code review',
            'rerun_trigger': 'P01 and design gate closure, actual source changes, source/input/dependency identity gaps or newly found risk',
        },
    }
    (out / 'preflight-audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    assert not differences, differences
    assert evidence['returncode'] == 0, evidence
    assert all(item['returncode'] == 0 for item in result['commands']), result['commands']
    print(json.dumps({'files_checked': len(checked), 'differences': len(differences),
                      'probe_returncode': evidence['returncode'], 'receipt': 'docs/tasks/W013/preflight-audit.json'}))


if __name__ == '__main__':
    main()
