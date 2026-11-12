"""Lightweight W013 engineering-tool checks; never executes a product matrix."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Preserve prior evidence; --out must be absent or empty')
    out.mkdir(parents=True, exist_ok=True)
    tools = Path(__file__).resolve().parent
    scripts = sorted(tools.glob('*.py'))
    for script in scripts:
        ast.parse(script.read_text(), filename=str(script), feature_version=(3, 10))
    rows = []

    def run(name: str, command: list[str], expected: int = 0) -> str:
        started = datetime.now(timezone.utc).isoformat()
        clock = time.monotonic()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root))
        result = subprocess.run(command, cwd=root, env=env, capture_output=True)
        stdout, stderr = out / (name + '.stdout.txt'), out / (name + '.stderr.txt')
        stdout.write_bytes(result.stdout)
        stderr.write_bytes(result.stderr)
        row = {'command': command, 'cwd': str(root), 'started_at_utc': started,
               'seconds': time.monotonic() - clock, 'returncode': result.returncode,
               'expected_returncode': expected, 'environment_overrides': {
                   'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(root)},
               'stdout': stdout.name, 'stdout_sha256': sha(stdout),
               'stderr': stderr.name, 'stderr_sha256': sha(stderr)}
        rows.append(row)
        (out / (name + '.command.json')).write_text(json.dumps(row, indent=2) + '\n')
        assert result.returncode == expected, row
        return result.stdout.decode()

    for name in ('prepare_final', 'source_identity', 'installed_smoke'):
        run(name + '-help', [sys.executable, '-B', str(tools / (name + '.py')), '--help'])
    identity = json.loads(run('source-identity', [sys.executable, '-B', str(tools / 'source_identity.py'),
                                                 '--root', str(root)]))
    baseline = root / 'docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt'
    ids = {line for line in baseline.read_text().splitlines() if line.startswith('tests/') and '::' in line}
    assert ids
    # The current API scaffold must fail closed, rather than pass an old W011 smoke.
    smoke_guard = run('smoke-not-ready-guard', [sys.executable, '-B', str(tools / 'installed_smoke.py'),
                                               '/not-a-runtime-input'], expected=2)
    assert smoke_guard == ''
    assert 'API assertions are not integrated' in (out / 'smoke-not-ready-guard.stderr.txt').read_text()
    with tempfile.TemporaryDirectory(prefix='w013-tool-preflight-') as temp:
        scratch = Path(temp)
        clearance = scratch / 'clearance.json'
        clearance.write_text(json.dumps({'status': 'not-approved', 'source_id': identity['source_id'],
                                         'cases': ['normal-direct', 'normal-readback', 'extraction-mismatch']}))
        run('resource-clearance-rejection', [sys.executable, '-B', str(tools / 'prepare_final.py'),
            '--root', str(root), '--out', str(scratch / 'out'), '--work', str(scratch / 'work'),
            '--smoke', str(tools / 'installed_smoke.py'), '--python310', sys.executable,
            '--python312', sys.executable, '--expected-tests', str(len(ids)),
            '--baseline-collection', str(baseline), '--baseline-sha256', sha(baseline),
            '--expected-source-id', identity['source_id'], '--resource-clearance', str(clearance)], expected=2)
        assert not (scratch / 'out').exists() and not (scratch / 'work').exists()
    result = {'classification': 'engineering-preparation-not-W013-final-matrix', 'status': 'passed',
              'python': sys.version, 'executable': sys.executable,
              'tools': {script.name: sha(script) for script in scripts},
              'source_id': identity['source_id'], 'source_file_count': len(identity['files']),
              'runtime_file_count': len(identity['runtime_files']),
              'baseline_collection_sha256': sha(baseline), 'baseline_node_count': len(ids),
              'commands': rows,
              'checks': ['Python3.10 grammar for every tool', '--help for runner/identity/smoke',
                         'all tracked and untracked source/test/config paths enumerated',
                         'unfinalized smoke refuses success', 'resource rejection occurs before output/work creation'],
              'not_run': ['product tests', 'typing', 'build/install', 'product combination/resource probe', 'final matrix'],
              'remaining': ['Integrate actual W013 public API assertions into installed_smoke.py before its freeze.',
                            'Root must provide final source identity and passed resource clearance before the matrix.']}
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'manifest.json').write_text(json.dumps({str(path.relative_to(out)): sha(path)
                                                 for path in sorted(out.rglob('*')) if path.is_file()}, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('classification', 'status', 'baseline_node_count', 'remaining')}, indent=2))


if __name__ == '__main__':
    main()
