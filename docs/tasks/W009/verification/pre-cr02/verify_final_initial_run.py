"""Run only after W009 product/test/config freeze. Store raw logs and identities.

Usage: python verify_final.py /absolute/verification-output
Execute with the normal inherited proxy/CA and network tool permission.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
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
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)


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
    original = runtime_manifest(ROOT / 'layauto_v2')
    tracked = subprocess.check_output(['git', 'ls-files', 'layauto_v2', 'tests', 'pyproject.toml', 'README.md'], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'layauto_v2', 'tests'], cwd=ROOT, text=True).splitlines()
    paths = sorted(set(tracked + untracked))
    write('source-manifest.json', {'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
          'files': {p: sha((ROOT / p).read_bytes()) for p in paths}, 'runtime_files': original})
    shutil.copy2(SMOKE, OUT / SMOKE.name)
    commands = []
    def matrix(tag):
        return [run('pytest-' + tag, [PY[tag], '-m', 'pytest', '-p', 'no:cacheprovider', 'tests/unit', 'tests/contracts', '-q']),
                run('typing-' + tag, [PY[tag], '-m', 'mypy']),
                run('pip-check-' + tag, [PY[tag], '-m', 'pip', 'check'])]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(matrix, tag) for tag in PY]
        for future in futures:
            commands.extend(future.result())
    commands.append(run('build', [PY['312'], '-m', 'build', '--outdir', OUT / 'dist']))
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
    assert original == wheel_manifest == sdist_manifest, 'package runtime bytes differ from tested source'
    write('package-identity.json', {'wheel': {'path': str(wheel), 'sha256': sha(wheel.read_bytes()), 'runtime_files': wheel_manifest},
                                   'sdist': {'path': str(sdist), 'sha256': sha(sdist.read_bytes()), 'runtime_files': sdist_manifest}})
    def install(tag, artifact):
        clean = ENV / ('clean-final-' + tag)
        log = []
        log.append(run('create-install-' + tag, [PY[tag], '-m', 'venv', clean]))
        py = clean / 'bin/python'
        log.append(run('install-' + tag, [py, '-m', 'pip', 'install', '--report', OUT / ('install-' + tag + '-report.json'), artifact], cwd=OUT))
        log.append(run('installed-pip-check-' + tag, [py, '-m', 'pip', 'check'], cwd=OUT))
        log.append(run('installed-smoke-' + tag, [py, '-I', '-B', OUT / SMOKE.name, ROOT / 'tests/fixtures/w003_m1'], cwd=OUT))
        check = subprocess.check_output([str(py), '-I', '-B', '-c',
            'import layauto_v2; print(layauto_v2.__file__)'], cwd=OUT, text=True).strip()
        manifest = runtime_manifest(Path(check).parent)
        assert manifest == original, 'installed package bytes differ from tested source'
        return log, {'python': str(py), 'installed_package': check, 'source_artifact': str(artifact),
                     'source_sha256': sha(artifact.read_bytes()), 'runtime_files': manifest}
    installs = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {tag: pool.submit(install, tag, artifact) for tag, artifact in (('312', wheel), ('310', sdist))}
        for tag, future in futures.items():
            logs, identity = future.result()
            commands.extend(logs)
            installs[tag] = identity
    write('installation-identity.json', installs)
    assert runtime_manifest(ROOT / 'layauto_v2') == original, 'source changed during verification'
    current = {p: sha((ROOT / p).read_bytes()) for p in paths}
    stored = json.loads((OUT / 'source-manifest.json').read_text())['files']
    assert current == stored, 'tested sources/tests/config changed during verification'
    write('receipt.json', {'status': 'passed', 'commands': commands,
                          'runtime_count': len(original), 'python_environments': {tag: str(py) for tag, py in PY.items()},
                          'source_manifest_sha256': sha((OUT / 'source-manifest.json').read_bytes()),
                          'limitations': ['Synthetic W003/W004 scope only; no EDA or production admission.',
                                         'No complete coordinate model, physical edge graph, device/net join, body proof, baseline, no_change or terminal.']})
    print('Final verification completed.', flush=True)


if __name__ == '__main__':
    main()
