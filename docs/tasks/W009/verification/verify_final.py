"""Frozen W009 validation: dual tests/type checks plus independent package flow.

Usage: python verify_final.py /absolute/verification-output [expected-test-count]
Network operations retain the configured proxy/CA and need tool network access.
Run after product/test/config freeze; all inputs are copied into a source snapshot.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path('/workspace/Layauto')
ENV = Path('/workspace/work/w009-env')
SMOKE = ENV / 'scripts/installed_smoke.py'
PY = {tag: ENV / f'py{tag}/bin/python' for tag in ('310', '312')}
EXPECTED_TEST_COUNT = int(sys.argv[2]) if len(sys.argv) == 3 else None
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SMOKE_CWD = ENV / 'installed-cwd'
SMOKE_CWD.mkdir(parents=True, exist_ok=True)
assert not SMOKE_CWD.is_relative_to(ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def run(name, args, cwd=ROOT, extra_env=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PIP_CACHE_DIR=str(ENV / 'pip-cache'),
               MYPY_CACHE_DIR=str(ENV / ('mypy-final-' + name)), MPLCONFIGDIR=str(ENV / 'mplconfig'))
    if extra_env:
        env.update(extra_env)
    start = time.time()
    with (OUT / (name + '.txt')).open('wb') as output:
        result = subprocess.run([str(a) for a in args], cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
    info = {'command': [str(a) for a in args], 'cwd': str(cwd), 'exit_code': result.returncode,
            'elapsed_seconds': round(time.time() - start, 3),
            'output': name + '.txt', 'output_sha256': sha((OUT / (name + '.txt')).read_bytes())}
    write(name + '.json', info)
    print(json.dumps(info), flush=True)
    if result.returncode:
        raise RuntimeError(name + ' failed; read ' + str(OUT / (name + '.txt')))
    return info


def runtime_manifest(root):
    return {str(p.relative_to(root)): sha(p.read_bytes())
            for p in sorted(root.rglob('*'))
            if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}


def main():
    runner_sha = sha(Path(__file__).read_bytes())
    original = runtime_manifest(ROOT / 'layauto_v2')
    tracked = subprocess.check_output(['git', 'ls-files', 'layauto_v2', 'tests', 'pyproject.toml', 'README.md'], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'layauto_v2', 'tests'], cwd=ROOT, text=True).splitlines()
    paths = sorted(set(tracked + untracked))
    source = {'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'files': {p: sha((ROOT / p).read_bytes()) for p in paths}, 'runtime_files': original}
    write('source-manifest.json', source)
    with tarfile.open(OUT / 'source-snapshot.tar.gz', 'w:gz') as archive:
        for name in paths:
            data = (ROOT / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mtime = 0
            archive.addfile(entry, io.BytesIO(data))
    shutil.copy2(SMOKE, OUT / SMOKE.name)
    run_source = Path(__file__).resolve()
    if run_source != OUT / run_source.name:
        shutil.copy2(run_source, OUT / run_source.name)
    source_token = sha((OUT / 'source-manifest.json').read_bytes())[:12]
    clean_dirs = {tag: ENV / ('clean-' + source_token + '-' + tag) for tag in PY}
    preflight = {tag: {'path': str(path), 'exists': path.exists()} for tag, path in clean_dirs.items()}
    write('clean-environment-preflight.json', preflight)
    assert all(not row['exists'] for row in preflight.values()), 'Clean installation directories must previously be absent'
    commands = []
    test_counts = {}

    def matrix(tag):
        rows = [run('pytest-' + tag, [PY[tag], '-m', 'pytest', '-p', 'no:cacheprovider', 'tests/unit', 'tests/contracts', '-q'])]
        summary = (OUT / ('pytest-' + tag + '.txt')).read_text()
        matches = re.findall(r'^(\d+) passed', summary, re.MULTILINE)
        assert len(matches) == 1, 'Missing or ambiguous complete pytest success summary'
        test_counts[tag] = int(matches[0])
        if EXPECTED_TEST_COUNT is not None:
            assert test_counts[tag] == EXPECTED_TEST_COUNT, 'Unexpected final test count'
        rows.extend([run('typing-' + tag, [PY[tag], '-m', 'mypy']),
                     run('pip-check-' + tag, [PY[tag], '-m', 'pip', 'check'])])
        return rows

    def package_flow():
        logs = [run('build', [PY['312'], '-m', 'build', '--outdir', OUT / 'dist'])]
        wheel = next((OUT / 'dist').glob('*.whl'))
        sdist = next((OUT / 'dist').glob('*.tar.gz'))
        with zipfile.ZipFile(wheel) as archive:
            wheel_manifest = {name[len('layauto_v2/'):]: sha(archive.read(name)) for name in archive.namelist()
                              if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
        with tarfile.open(sdist, 'r:gz') as archive:
            sdist_manifest = {}
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if member.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                    sdist_manifest['/'.join(parts[2:])] = sha(archive.extractfile(member).read())
        assert original == wheel_manifest == sdist_manifest, 'Package runtime bytes differ from frozen source'
        write('package-identity.json', {'wheel': {'path': str(wheel), 'sha256': sha(wheel.read_bytes()), 'runtime_files': wheel_manifest},
                                       'sdist': {'path': str(sdist), 'sha256': sha(sdist.read_bytes()), 'runtime_files': sdist_manifest}})

        def install(tag, artifact):
            clean = clean_dirs[tag]
            assert not clean.exists(), 'Cannot reuse a clean installation environment'
            rows = [run('create-install-' + tag, [PY[tag], '-m', 'venv', clean])]
            py = clean / 'bin/python'
            rows.append(run('install-' + tag, [py, '-m', 'pip', 'install', '--report', OUT / ('install-' + tag + '-report.json'), artifact], cwd=SMOKE_CWD))
            rows.append(run('installed-pip-check-' + tag, [py, '-m', 'pip', 'check'], cwd=SMOKE_CWD))
            rows.append(run('installed-smoke-' + tag, [py, '-I', '-B', OUT / SMOKE.name, ROOT / 'tests/fixtures/w003_m1'], cwd=SMOKE_CWD))
            check = subprocess.check_output([str(py), '-I', '-B', '-c', 'import layauto_v2; print(layauto_v2.__file__)'], cwd=SMOKE_CWD, text=True).strip()
            manifest = runtime_manifest(Path(check).parent)
            assert manifest == original, 'Installed package bytes differ from frozen source'
            return rows, {'python': str(py), 'installed_package': check, 'source_artifact': str(artifact),
                          'source_sha256': sha(artifact.read_bytes()), 'runtime_files': manifest}

        installs = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {tag: pool.submit(install, tag, artifact) for tag, artifact in (('312', wheel), ('310', sdist))}
            for tag, job in jobs.items():
                rows, identity = job.result()
                logs.extend(rows)
                installs[tag] = identity
        write('installation-identity.json', installs)
        return logs

    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(matrix, tag) for tag in PY] + [pool.submit(package_flow)]
        for job in jobs:
            commands.extend(job.result())
    assert runtime_manifest(ROOT / 'layauto_v2') == original, 'Runtime source changed during verification'
    assert {p: sha((ROOT / p).read_bytes()) for p in paths} == source['files'], 'Source/tests/config changed during verification'
    write('receipt.json', {'status': 'passed', 'commands': commands,
                          'runner_command': [sys.executable, *sys.argv], 'runner_sha256': runner_sha,
                          'runtime_count': len(original), 'source_file_count': len(paths),
                          'expected_test_count': EXPECTED_TEST_COUNT, 'actual_test_counts': test_counts,
                          'python_environments': {tag: str(py) for tag, py in PY.items()},
                          'source_manifest_sha256': sha((OUT / 'source-manifest.json').read_bytes()),
                          'source_snapshot_sha256': sha((OUT / 'source-snapshot.tar.gz').read_bytes()),
                          'source_identity_rechecked_after_all_commands': True,
                          'adopted_source_external_smoke': {tag: 'installed-smoke-' + tag + '.txt' for tag in PY},
                          'limitations': ['Synthetic W003/W004 scope only; no EDA or production admission.',
                                         'No complete coordinate model, physical edge graph, device/net join, body proof, baseline, no_change or terminal.']})
    print('Final frozen verification completed.', flush=True)


if __name__ == '__main__':
    main()
