"""Frozen IPMR-01 source, regression and package verification.

Prepared outside the repository. Running this file is a separate authorized step.
Example:
  py312/bin/python -B runner.py --expected-312-count N \
      --py310-path tests/contracts/test_w007_inputs.py
The default 3.10 scope always includes every test_w008*.py/test_w009*.py contract.
Network commands use the inherited proxy and CA trust.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
import zipfile

ROOT = Path('/workspace/work/w009-ipmr01')
ENV = Path('/workspace/work/w009-ipmr01-env')
DEFAULT_OUT = ROOT / 'docs/tasks/W009/ipmr01-verification'
PY = {tag: ENV / ('py' + tag) / 'bin/python' for tag in ('310', '312')}
BASE = 'cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa'
BUILD_NAMES = {'README.md', 'pyproject.toml', 'setup.py', 'setup.cfg', 'MANIFEST.in',
               'pytest.ini', 'mypy.ini', '.python-version', 'LICENSE', 'LICENSE.md',
               'LICENSE.txt', 'COPYING', 'Makefile', 'tox.ini', '.gitignore'}
IDENTITY_CODE = '''import importlib.metadata,json,platform,sys,sysconfig
print(json.dumps({"python":sys.version,"executable":sys.executable,"prefix":sys.prefix,
"base_prefix":sys.base_prefix,"base_executable":sys._base_executable,
"platform":platform.platform(),"purelib":sysconfig.get_path("purelib"),
"distributions":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}},sort_keys=True,indent=2))'''
INSTALLED_CODE = '''import hashlib,json,pathlib,sys,sysconfig,layauto_v2
p=pathlib.Path(layauto_v2.__file__).resolve()
roots={pathlib.Path(sysconfig.get_path(n)).resolve() for n in ("purelib","platlib")}
assert any(p.is_relative_to(r) for r in roots),p
assert "site-packages" in p.parts,p
print(json.dumps({"installed_package":str(p),"sys_path":sys.path,
"runtime_files":{str(f.relative_to(p.parent)):hashlib.sha256(f.read_bytes()).hexdigest()
for f in sorted(p.parent.rglob("*")) if f.is_file() and (f.suffix==".py" or f.name=="py.typed")}},sort_keys=True,indent=2))'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def runtime_manifest(root):
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}


def selected_paths():
    candidates = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT
    ).decode().split('\0')
    paths = set()
    for name in candidates:
        if not name:
            continue
        p = Path(name)
        if p.parts[0] in ('layauto_v2', 'tests') or (len(p.parts) == 1 and
                (name in BUILD_NAMES or p.suffix in ('.toml', '.cfg') or name.startswith('requirements'))):
            assert not p.is_absolute() and '..' not in p.parts, name
            actual = ROOT / p
            assert actual.is_file() and not actual.is_symlink(), name
            paths.add(name)
    assert 'pyproject.toml' in paths and 'README.md' in paths
    return sorted(paths)


def collapse_test_paths(paths):
    """A selected directory already covers explicitly listed descendants."""
    directories = [Path(name) for name in paths if '::' not in name and (ROOT / name).is_dir()]
    return sorted(name for name in set(paths)
                  if not any(directory != Path(name.split('::', 1)[0]) and
                             directory in Path(name.split('::', 1)[0]).parents
                             for directory in directories))


class Runner:
    def __init__(self, args):
        self.args = args
        self.out = args.out.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        for name in ('source-manifest.json', 'source-snapshot.tar.gz', 'receipt.json', 'dist'):
            assert not (self.out / name).exists(), 'Archive the earlier run before reusing this output: ' + name
        self.head = git('rev-parse', 'HEAD')
        assert subprocess.run(['git', 'merge-base', '--is-ancestor', args.base_sha, self.head], cwd=ROOT).returncode == 0
        self.started = datetime.now(timezone.utc).isoformat()
        self.commands = []
        self.identities = {}
        self.lock = threading.Lock()
        self.test_counts = {}
        self.test_scopes = {}
        self.typing_counts = {}
        self.run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        self.scratch = ENV / 'runs' / self.run_id
        assert not self.scratch.exists()
        self.scratch.mkdir(parents=True)
        self.smoke_cwd = self.scratch / 'installed-cwd'
        self.smoke_cwd.mkdir()
        assert not self.smoke_cwd.is_relative_to(ROOT)
        self.source = None
        self.source_sha = None
        self.snapshot_sha = None
        self.errors = []

    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')

    def run(self, name, command, cwd=ROOT, source_import=False):
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PIP_CACHE_DIR': str(ENV / 'pip-cache'),
                     'XDG_CACHE_HOME': str(self.scratch / 'cache'),
                     'MPLCONFIGDIR': str(self.scratch / 'mplconfig'), 'MPLBACKEND': 'Agg',
                     'MYPY_CACHE_DIR': str(self.scratch / ('mypy-' + name)),
                     'TMPDIR': str(self.scratch / 'tmp')}
        Path(overrides['TMPDIR']).mkdir(exist_ok=True)
        if source_import:
            overrides['PYTHONPATH'] = str(ROOT)
        env.update(overrides)
        command = [str(arg) for arg in command]
        begun = datetime.now(timezone.utc).isoformat()
        head = git('rev-parse', 'HEAD')
        start = time.monotonic()
        stdout = self.out / (name + '.stdout.txt')
        stderr = self.out / (name + '.stderr.txt')
        with stdout.open('wb') as out, stderr.open('wb') as err:
            result = subprocess.run(command, cwd=cwd, env=env, stdout=out, stderr=err)
        row = {'command': command, 'cwd': str(cwd), 'base_sha': self.args.base_sha,
               'head': head, 'finished_head': git('rev-parse', 'HEAD'),
               'started_utc': begun, 'elapsed_seconds': round(time.monotonic() - start, 3),
               'exit_code': result.returncode, 'python_executable': command[0],
               'python_identity': self.identities.get(command[0]),
               'source_manifest_sha256': self.source_sha, 'env_overrides': overrides,
               'outputs': {'stdout': {'path': stdout.name, 'sha256': sha(stdout.read_bytes())},
                           'stderr': {'path': stderr.name, 'sha256': sha(stderr.read_bytes())}}}
        self.write(name + '.json', row)
        with self.lock:
            self.commands.append(row)
        print(json.dumps({'check': name, 'exit_code': result.returncode,
                          'elapsed_seconds': row['elapsed_seconds']}), flush=True)
        if result.returncode:
            raise RuntimeError(name + ' failed; read ' + str(stdout) + ' and ' + str(stderr))
        return row

    def identity(self, name, py, cwd=ROOT):
        row = self.run(name, [py, '-I', '-B', '-c', IDENTITY_CODE], cwd=cwd)
        value = json.loads((self.out / (name + '.stdout.txt')).read_text())
        self.identities[str(py)] = value
        row['python_identity'] = value
        self.write(name + '.json', row)
        return value

    def freeze(self):
        paths = selected_paths()
        contents = {name: (ROOT / name).read_bytes() for name in paths}
        self.source = {'git_head': self.head, 'base_sha': self.args.base_sha,
                       'checkout_root': str(ROOT), 'started_utc': self.started,
                       'git_status': git('status', '--porcelain=v2', '--branch'),
                       'selection': 'All tracked and nonignored untracked runtime/tests plus root README/build/test configuration.',
                       'files': {name: sha(data) for name, data in contents.items()},
                       'runtime_files': {str(Path(name).relative_to('layauto_v2')): sha(data)
                                         for name, data in contents.items()
                                         if Path(name).parts[0] == 'layauto_v2' and
                                         (Path(name).suffix == '.py' or Path(name).name == 'py.typed')}}
        self.write('source-manifest.json', self.source)
        self.source_sha = sha((self.out / 'source-manifest.json').read_bytes())
        snapshot = self.out / 'source-snapshot.tar.gz'
        with snapshot.open('wb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode='w') as archive:
                    for name in paths:
                        data = contents[name]
                        entry = tarfile.TarInfo(name)
                        entry.size = len(data)
                        entry.mode = 0o644
                        archive.addfile(entry, io.BytesIO(data))
        self.snapshot_sha = sha(snapshot.read_bytes())
        with tarfile.open(snapshot, 'r:gz') as archive:
            members = archive.getmembers()
            assert all(member.isfile() for member in members)
            assert len(members) == len({member.name for member in members}) == len(paths)
            snapshot_files = {member.name: sha(archive.extractfile(member).read()) for member in members}
        assert snapshot_files == self.source['files'], 'Source snapshot differs from final source manifest'
        self.write('source-snapshot-audit.json', {'source_manifest_sha256': self.source_sha,
                   'snapshot_sha256': self.snapshot_sha, 'file_count': len(snapshot_files),
                   'all_members_regular_and_unique': True, 'files_match_manifest': True,
                   'files': snapshot_files})
        build_root = self.scratch / 'build-source'
        build_root.mkdir()
        for name in paths:
            destination = build_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(contents[name])
        assert {name: sha((build_root / name).read_bytes()) for name in paths} == self.source['files']
        self.build_root = build_root
        # Scripts are copied only by this later, explicitly invoked runner.
        for path in (Path(__file__).resolve(), Path(__file__).resolve().with_name('installed_smoke.py')):
            destination = self.out / path.name
            if path != destination:
                shutil.copy2(path, destination)
        self.smoke = self.out / 'installed_smoke.py'
        assert self.smoke.is_file()

    def matrix(self, tag):
        py = PY[tag]
        self.identity('environment-' + tag, py)
        if tag == '312':
            paths = ['tests/unit', 'tests/contracts']
        else:
            paths = sorted({str(p.relative_to(ROOT)) for pattern in ('test_w008*.py', 'test_w009*.py')
                            for p in (ROOT / 'tests/contracts').glob(pattern)} | set(self.args.py310_path))
            assert paths, 'Missing affected 3.10 test scope'
        paths = collapse_test_paths(paths)
        for name in paths:
            p = Path(name.split('::', 1)[0])
            assert not p.is_absolute() and '..' not in p.parts and (ROOT / p).exists(), name
        self.test_scopes[tag] = {'paths': paths, 'complete_v2': {'tests/unit', 'tests/contracts'} <= set(paths)}
        self.write('pytest-scope-' + tag + '.json', self.test_scopes[tag])
        self.run('pytest-' + tag, [py, '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
                                 '--basetemp', self.scratch / ('pytest-' + tag), *paths, '-q'], source_import=True)
        summary = (self.out / ('pytest-' + tag + '.stdout.txt')).read_text()
        matches = re.findall(r'(\d+) passed(?:,|\s+in)', summary)
        assert len(matches) == 1 and not re.search(r'\d+ (?:failed|errors?|skipped|xfailed|xpassed)', summary), summary[-2000:]
        self.test_counts[tag] = int(matches[0])
        expected = self.args.expected_312_count if tag == '312' else self.args.expected_310_count
        if expected is not None:
            assert self.test_counts[tag] == expected, ('Unexpected test count', tag, self.test_counts[tag], expected)
        self.run('typing-' + tag, [py, '-B', '-m', 'mypy', '--cache-dir', self.scratch / ('typing-' + tag)], source_import=True)
        text = (self.out / ('typing-' + tag + '.stdout.txt')).read_text()
        match = re.search(r'Success: no issues found in (\d+) source files?', text)
        assert match, text
        self.typing_counts[tag] = int(match[1])
        self.run('pip-check-' + tag, [py, '-B', '-m', 'pip', 'check'])

    def packages(self):
        self.identity('build-environment-312', PY['312'], cwd=self.build_root)
        self.run('build', [PY['312'], '-B', '-m', 'build', '--outdir', self.out / 'dist'], cwd=self.build_root)
        wheels = list((self.out / 'dist').glob('*.whl'))
        sdists = list((self.out / 'dist').glob('*.tar.gz'))
        assert len(wheels) == len(sdists) == 1
        wheel, sdist = wheels[0], sdists[0]
        with zipfile.ZipFile(wheel) as archive:
            wm = {name[len('layauto_v2/'):]: sha(archive.read(name)) for name in archive.namelist()
                  if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
        with tarfile.open(sdist, 'r:gz') as archive:
            sm = {}
            for entry in archive.getmembers():
                parts = Path(entry.name).parts
                if entry.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                    sm['/'.join(parts[2:])] = sha(archive.extractfile(entry).read())
        original = self.source['runtime_files']
        assert wm == sm == original, 'New package runtime differs from final source'
        self.write('package-identity.json', {'source_manifest_sha256': self.source_sha,
                   'runtime_count': len(original), 'wheel': {'path': str(wheel), 'sha256': sha(wheel.read_bytes()), 'runtime_files': wm},
                   'sdist': {'path': str(sdist), 'sha256': sha(sdist.read_bytes()), 'runtime_files': sm}})
        clean_dirs = {tag: self.scratch / ('clean-' + tag) for tag in PY}
        preflight = {tag: {'path': str(p), 'exists': p.exists()} for tag, p in clean_dirs.items()}
        self.write('clean-environment-preflight.json', preflight)
        assert all(not row['exists'] for row in preflight.values())

        def install(tag, artifact):
            clean = clean_dirs[tag]
            assert not clean.exists()
            self.run('create-install-' + tag, [PY[tag], '-B', '-m', 'venv', clean], cwd=self.smoke_cwd)
            py = clean / 'bin/python'
            self.identity('clean-environment-before-install-' + tag, py, cwd=self.smoke_cwd)
            report = self.out / ('install-' + tag + '-report.json')
            self.run('install-' + tag, [py, '-B', '-m', 'pip', 'install', '--report', report, artifact], cwd=self.smoke_cwd)
            self.identity('clean-environment-installed-' + tag, py, cwd=self.smoke_cwd)
            self.run('installed-pip-check-' + tag, [py, '-B', '-m', 'pip', 'check'], cwd=self.smoke_cwd)
            self.run('installed-identity-' + tag, [py, '-I', '-B', '-c', INSTALLED_CODE], cwd=self.smoke_cwd)
            identity = json.loads((self.out / ('installed-identity-' + tag + '.stdout.txt')).read_text())
            assert identity['runtime_files'] == original, 'Installed runtime differs from final source'
            assert not Path(identity['installed_package']).is_relative_to(ROOT)
            assert str(ROOT) not in identity['sys_path']
            data = json.loads(report.read_text())
            installs = [row for row in data['install'] if row['metadata']['name'].lower() == 'layauto']
            assert len(installs) == 1
            direct = installs[0]['download_info']
            assert direct['url'] == artifact.as_uri(), direct
            info = direct['archive_info']
            archive_sha = info.get('hashes', {}).get('sha256')
            if archive_sha is None:
                # pip 23 emits the same digest in its legacy hash field.
                match = re.fullmatch(r'sha256=([0-9a-f]{64})', info.get('hash', ''))
                assert match, direct
                archive_sha = match[1]
            assert archive_sha == sha(artifact.read_bytes()), direct
            self.run('installed-smoke-' + tag, [py, '-I', '-B', self.smoke,
                     ROOT / 'tests/fixtures/w003_m1', self.out / 'source-manifest.json'], cwd=self.smoke_cwd)
            return tag, {'python': str(py), 'python_identity': self.identities[str(py)],
                         'cwd': str(self.smoke_cwd), 'source_artifact': str(artifact),
                         'source_sha256': sha(artifact.read_bytes()),
                         'pip_report': report.name, 'pip_report_sha256': sha(report.read_bytes()),
                         'direct_url': direct, **identity}

        installations = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(install, tag, artifact) for tag, artifact in (('312', wheel), ('310', sdist))]
            for future in as_completed(jobs):
                tag, identity = future.result()
                installations[tag] = identity
        self.write('installation-identity.json', installations)

    def finish(self):
        try:
            unchanged = self.source is not None and selected_paths() == list(self.source['files']) and {
                name: sha((ROOT / name).read_bytes()) for name in self.source['files']} == self.source['files']
        except (OSError, AssertionError) as exc:
            unchanged = False
            self.errors.append('Final source identity check: ' + type(exc).__name__ + ': ' + str(exc))
        if not unchanged:
            self.errors.append('Source/tests/build configuration changed during verification')
        self.write('receipt.json', {'status': 'passed' if not self.errors else 'failed',
                   'run_id': self.run_id, 'started_utc': self.started,
                   'finished_utc': datetime.now(timezone.utc).isoformat(),
                   'base_sha': self.args.base_sha, 'head': self.head, 'finished_head': git('rev-parse', 'HEAD'),
                   'runner_command': [sys.executable, *sys.argv], 'runner_sha256': sha(Path(__file__).read_bytes()),
                   'smoke_script_sha256': sha(self.smoke.read_bytes()),
                   'source_manifest_sha256': self.source_sha, 'source_snapshot_sha256': self.snapshot_sha,
                   'source_file_count': len(self.source['files']), 'runtime_count': len(self.source['runtime_files']),
                   'source_identity_rechecked_after_all_commands': unchanged,
                   'python_environments': {tag: str(py) for tag, py in PY.items()},
                   'actual_test_counts': self.test_counts, 'typing_source_counts': self.typing_counts,
                   'test_scopes': self.test_scopes,
                   'python310_complete_v2_rerun': self.test_scopes.get('310', {}).get('complete_v2', False),
                   'commands': self.commands, 'errors': self.errors,
                   'limitations': ['Python3.10 defaults to affected W008/W009 plus explicitly added paths; actual paths and completeness are recorded in test_scopes.',
                                  'Synthetic W003/W004 captures; no EDA or production admission.',
                                  'No geometry/performance algorithm change or new production capability is established by these engineering checks.']})

    def main(self):
        self.freeze()
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(self.matrix, tag) for tag in PY] + [pool.submit(self.packages)]
            for future in as_completed(futures):
                try:
                    future.result()
                except BaseException as exc:
                    self.errors.append(type(exc).__name__ + ': ' + str(exc))
        self.finish()
        if self.errors:
            raise RuntimeError('Verification failed; read receipt.json: ' + '; '.join(self.errors))
        print('Frozen IPMR-01 verification completed.', flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--base-sha', default=BASE)
    parser.add_argument('--py310-path', action='append', default=[], help='Additional affected path/node; repeatable')
    parser.add_argument('--expected-312-count', type=int)
    parser.add_argument('--expected-310-count', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    Runner(parse_args()).main()
