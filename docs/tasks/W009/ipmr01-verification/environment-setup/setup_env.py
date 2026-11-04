"""Prepare dedicated W009 IPMR-01 check interpreters; no product commands."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/workspace/work/w009-ipmr01-env')
OUT = ROOT / 'setup'
UV = '/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/uv'
PY312 = '/workspace/.venvs/layauto/bin/python'
ENV = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(ROOT / 'interpreters'),
           UV_CACHE_DIR=str(ROOT / 'uv-cache'), UV_NATIVE_TLS='true',
           PIP_CACHE_DIR=str(ROOT / 'pip-cache'), PYTHONDONTWRITEBYTECODE='1',
           MPLCONFIGDIR=str(ROOT / 'mplconfig'))

def run(name, command):
    start = time.time()
    with (OUT / (name + '.stdout.txt')).open('wb') as stdout, (OUT / (name + '.stderr.txt')).open('wb') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr)
    receipt = {'command': command, 'cwd': str(ROOT), 'exit_code': result.returncode,
               'elapsed_seconds': round(time.time() - start, 3),
               'stdout': name + '.stdout.txt', 'stderr': name + '.stderr.txt',
               'stdout_sha256': hashlib.sha256((OUT / (name + '.stdout.txt')).read_bytes()).hexdigest(),
               'stderr_sha256': hashlib.sha256((OUT / (name + '.stderr.txt')).read_bytes()).hexdigest()}
    (OUT / (name + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
    if result.returncode:
        raise RuntimeError(name + ' failed')
    return receipt

def main():
    receipts = [run('existing-312', [PY312, '-c', 'import sys; print(sys.version); print(sys.executable); print(sys._base_executable)']),
                run('download-310', [UV, 'python', 'install', '3.10'])]
    py310 = next((ROOT / 'interpreters').glob('cpython-3.10*/bin/python3.10'))
    deps = ['numpy', 'matplotlib', 'pyyaml', 'pytest', 'mypy', 'types-PyYAML', 'build', 'setuptools', 'wheel']

    def prepare(tag, base):
        dest = ROOT / ('py' + tag)
        assert not dest.exists(), str(dest)
        rows = [run('create-' + tag, [str(base), '-m', 'venv', str(dest)])]
        py = str(dest / 'bin/python')
        rows.append(run('install-dependencies-' + tag, [py, '-m', 'pip', 'install', '--report', str(OUT / ('pip-report-' + tag + '.json')), *deps]))
        rows.append(run('pip-check-' + tag, [py, '-m', 'pip', 'check']))
        rows.append(run('identity-' + tag, [py, '-c', 'import sys,platform,importlib.metadata,json; print(json.dumps({"version":sys.version,"executable":sys.executable,"base_executable":sys._base_executable,"platform":platform.platform(),"distributions":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}},indent=2,sort_keys=True))']))
        rows.append(run('freeze-' + tag, [py, '-m', 'pip', 'freeze', '--all']))
        return rows

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(prepare, '310', py310), pool.submit(prepare, '312', PY312)]
        for job in jobs:
            receipts.extend(job.result())
    (OUT / 'receipt.json').write_text(json.dumps({'status': 'passed', 'commands': receipts,
        'interpreters': {tag: str(ROOT / ('py' + tag) / 'bin/python') for tag in ('310', '312')},
        'scope': 'Dedicated runtime and dev dependencies only; no product tests, build or product installation.'}, indent=2) + '\n')

if __name__ == '__main__':
    main()
