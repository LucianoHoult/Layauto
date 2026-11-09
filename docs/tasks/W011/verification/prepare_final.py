"""Frozen final engineering matrix for W011; no product or test implementation.

Example:
  python prepare_final.py --root /workspace/Layauto --out /absolute/evidence \
      --work /workspace/work/w011-final --smoke /absolute/installed_smoke.py \
      --python310 /workspace/.venvs/w011-py310/bin/python \
      --python312 /workspace/.venvs/w011-py312/bin/python --expected-tests 1234

Run after the product/tests/configuration and smoke are frozen. Network work
retains proxy/CA settings and requires the executor's network permission.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import platform
import resource
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('root', 'out', 'work', 'smoke', 'python310', 'python312'):
        parser.add_argument('--' + field, type=Path, required=True)
    parser.add_argument('--expected-tests', type=int, required=True)
    parser.add_argument('--baseline-collection', type=Path)
    parser.add_argument('--matrix-workers', type=int, choices=(1, 2), default=1,
                        help='Default 1 avoids overlapping full captured-wire decode peaks; packaging runs after both matrices.')
    parser.add_argument('--resource-gate', type=Path,
                        help='Required with two workers: archived pytest plugin holds the W011 lock until process exit.')
    args = parser.parse_args()
    if args.matrix_workers == 2 and args.resource_gate is None:
        parser.error('--matrix-workers 2 requires --resource-gate')
    root, out, work, smoke = (getattr(args, name).resolve() for name in ('root', 'out', 'work', 'smoke'))
    pythons = {'310': args.python310.absolute(), '312': args.python312.absolute()}
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Evidence output must be absent or empty; prior evidence is preserved')
    if work.exists():
        raise RuntimeError('Work directory must be absent; fresh environment/source identity required')
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True)
    source = work / 'source'
    source.mkdir()
    outside = work / 'installed-cwd'
    outside.mkdir()
    if outside.is_relative_to(root) or outside.is_relative_to(source):
        raise RuntimeError('Installed smoke must execute outside checkout and snapshot')

    def write(name: str, value: object) -> None:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def files_manifest(base: Path, names: list[str]) -> dict[str, str]:
        return {name: sha((base / name).read_bytes()) for name in names}

    def runtime_manifest(base: Path) -> dict[str, str]:
        return {str(path.relative_to(base)): sha(path.read_bytes())
                for path in sorted(base.rglob('*'))
                if path.is_file() and (path.suffix == '.py' or path.name == 'py.typed')}

    def run(name: str, command: list[object], cwd: Path, *, extra: dict[str, str] | None = None) -> dict[str, object]:
        overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PIP_CACHE_DIR': str(work / 'pip-cache'),
                     'MYPY_CACHE_DIR': str(work / ('mypy-' + name)), 'MPLCONFIGDIR': str(work / 'mplconfig')}
        if extra:
            overrides.update(extra)
        env = dict(os.environ, **overrides)
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc).isoformat()
        with (out / (name + '.stdout.txt')).open('wb') as stdout, (out / (name + '.stderr.txt')).open('wb') as stderr:
            completed = subprocess.run([str(item) for item in command], cwd=cwd, env=env,
                                       stdout=stdout, stderr=stderr)
        finished_at = datetime.now(timezone.utc).isoformat()
        row = {'command': [str(item) for item in command], 'cwd': str(cwd), 'exit_code': completed.returncode,
               'environment_overrides': overrides,
               'started_at_utc': started_at, 'finished_at_utc': finished_at,
               'elapsed_seconds': round(time.perf_counter() - started, 3),
               'stdout': name + '.stdout.txt', 'stdout_sha256': sha((out / (name + '.stdout.txt')).read_bytes()),
               'stderr': name + '.stderr.txt', 'stderr_sha256': sha((out / (name + '.stderr.txt')).read_bytes())}
        write(name + '.json', row)
        print(json.dumps(row), flush=True)
        if completed.returncode:
            raise RuntimeError(name + ' failed; inspect stdout/stderr in ' + str(out))
        return row

    gate_source = args.resource_gate.resolve() if args.resource_gate is not None else None
    gate_identity: dict[str, object] | None = None
    gate_directory = work / 'pytest-plugins'
    gate_lock = work / 'pytest-w011.lock'
    if gate_source is not None:
        gate_directory.mkdir()
        gate_bytes = gate_source.read_bytes()
        (gate_directory / 'w011_resource_gate.py').write_bytes(gate_bytes)
        (out / 'w011_resource_gate.py').write_bytes(gate_bytes)
        gate_identity = {'source': str(gate_source), 'sha256': sha(gate_bytes),
                         'module': 'w011_resource_gate', 'module_directory': str(gate_directory),
                         'shared_lock': str(gate_lock), 'lock_release': 'OS at pytest process exit',
                         'start': 'tryfirst setup hookwrapper before fixtures for first test_w011_* file',
                         'effect': 'Only waiting and logging; no test selection, reordering, fixture or outcome changes.',
                         'memory_basis': 'Observed W011 process peak about 7 GiB and legacy phase about 1-1.7 GiB under a 16 GiB cgroup; finite observations, not a proven maximum.'}
        write('resource-gate.json', gate_identity)

    def gate_release_observation(tag: str) -> None:
        log = out / ('resource-gate-' + tag + '.jsonl')
        command_receipt = out / ('pytest-' + tag + '.json')
        if gate_identity is None or not log.exists() or not command_receipt.exists():
            return
        records = [json.loads(line) for line in log.read_text().splitlines()]
        acquired = [row for row in records if row['event'] == 'ACQUIRED']
        if not acquired:
            return
        assert len(acquired) == 1
        row = {**acquired[0], 'event': 'RELEASED',
               'observed_at_utc': datetime.now(timezone.utc).isoformat(),
               'meaning': 'Parent observed subprocess completion; OS already released the lock. This observation can follow the other process ACQUIRED timestamp.',
               'observer_pid': os.getpid(),
               'subprocess_exit_code': json.loads(command_receipt.read_text())['exit_code']}
        with log.open('a') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')

    # Existing W006 independently compares the accepted RunAttempt example.
    # This is a test-only sample and is never a runtime smoke input.
    selected = ['layauto_v2', 'tests', 'pyproject.toml', 'README.md', 'docs/tasks/W003/examples/records.json']
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', *selected], cwd=root).decode().split('\0')
    untracked = subprocess.check_output(['git', 'ls-files', '-z', '--others', '--exclude-standard', '--', *selected], cwd=root).decode().split('\0')
    names = sorted({name for name in tracked + untracked if name})
    if any(not (root / name).is_file() or (root / name).is_symlink() for name in names):
        raise RuntimeError('Source selection contains removed, non-file, or symlink path')
    original = files_manifest(root, names)
    resource_paths = ['/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/memory.swap.max']
    write('resource-limits.json', {'platform': platform.platform(),
          'cpu_count': os.cpu_count(),
          'cgroup': {name: Path(name).read_text().strip() if Path(name).exists() else None for name in resource_paths},
          'rlimits': {name: resource.getrlimit(getattr(resource, name)) for name in
                      ('RLIMIT_AS', 'RLIMIT_CPU', 'RLIMIT_DATA', 'RLIMIT_NOFILE', 'RLIMIT_STACK')},
          'matrix_workers': args.matrix_workers,
          'phase_order': ['interpreter matrices', 'build', '3.10 clean installation and smoke', '3.12 clean installation and smoke'],
          'heavy_package_smokes_overlap_matrices': False,
          'w011_exclusive_until_pytest_process_exit': gate_identity is not None,
          'resource_gate': gate_identity,
          'limits': ['Sample timings and process RSS are not maximal input or production resource guarantees.']})
    source_meta = {'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                   'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=root, text=True),
                   'files': original, 'runtime_files': runtime_manifest(root / 'layauto_v2')}
    write('source-manifest.json', source_meta)
    with tarfile.open(out / 'source-snapshot.tar.gz', 'w:gz') as archive:
        for name in names:
            data = (root / name).read_bytes()
            item = tarfile.TarInfo(name)
            item.size, item.mtime = len(data), 0
            archive.addfile(item, io.BytesIO(data))
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    if files_manifest(source, names) != original:
        raise RuntimeError('Frozen source bytes differ from captured selection')
    shutil.copyfile(smoke, out / 'installed_smoke.py')
    runner_path = Path(__file__).resolve()
    if runner_path != out / runner_path.name:
        shutil.copyfile(runner_path, out / runner_path.name)
    smoke_sha, runner_sha = sha((out / 'installed_smoke.py').read_bytes()), sha(runner_path.read_bytes())
    baseline_collection = (args.baseline_collection or root / 'docs/tasks/W011/preflight/baseline-collection312.txt').resolve()
    baseline_ids = {line for line in baseline_collection.read_text().splitlines() if line.startswith('tests/') and '::' in line}
    if len(baseline_ids) != 1465:
        raise RuntimeError('W011 requires the retained original 1465-test baseline collection')
    shutil.copyfile(baseline_collection, out / 'baseline-collection.txt')
    commands: list[dict[str, object]] = []
    expected_runtime = source_meta['runtime_files']
    counts: dict[str, int] = {}

    def matrix(tag: str) -> list[dict[str, object]]:
        py = pythons[tag]
        rows = [run('environment-' + tag, [py, '-c',
            'import sys,platform,importlib.metadata as m,json,layauto_v2; from pathlib import Path; p=Path(layauto_v2.__file__).resolve(); assert p.parent==Path.cwd()/"layauto_v2", p; print(json.dumps({"executable":sys.executable,"version":sys.version,"platform":platform.platform(),"source_package":str(p),"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))'], source),
            run('collection-' + tag, [py, '-m', 'pytest', '-p', 'no:cacheprovider', '--collect-only', 'tests/unit', 'tests/contracts', '-q'], source)]
        current_ids = {line for line in (out / ('collection-' + tag + '.stdout.txt')).read_text().splitlines()
                       if line.startswith('tests/') and '::' in line}
        missing = sorted(baseline_ids - current_ids)
        write('pytest-scope-' + tag + '.json', {'baseline_test_count': len(baseline_ids),
              'current_test_count': len(current_ids), 'added_test_count': len(current_ids - baseline_ids),
              'missing_baseline_ids': missing})
        if missing or len(current_ids) != args.expected_tests:
            raise RuntimeError('The final matrix must retain all original baseline tests')
        pytest_command: list[object] = [py, '-m', 'pytest', '-p', 'no:cacheprovider']
        pytest_environment: dict[str, str] = {}
        if gate_identity is not None:
            pytest_command.extend(['-p', 'w011_resource_gate', '--w011-resource-lock', gate_lock,
                                   '--w011-resource-log', out / ('resource-gate-' + tag + '.jsonl')])
            pytest_environment['PYTHONPATH'] = os.pathsep.join(filter(None, (str(gate_directory), os.environ.get('PYTHONPATH', ''))))
        pytest_command.extend(['tests/unit', 'tests/contracts', '-q'])
        try:
            rows.append(run('pytest-' + tag, pytest_command, source, extra=pytest_environment))
        finally:
            gate_release_observation(tag)
        count = re.findall(r'^(\d+) passed', (out / ('pytest-' + tag + '.stdout.txt')).read_text(), re.MULTILINE)
        if len(count) != 1 or int(count[0]) != args.expected_tests:
            raise RuntimeError('Unexpected full regression result/count for ' + tag)
        counts[tag] = int(count[0])
        rows.extend([run('typing-' + tag, [py, '-m', 'mypy'], source),
                     run('pip-check-' + tag, [py, '-m', 'pip', 'check'], source)])
        return rows

    def package() -> list[dict[str, object]]:
        rows = [run('build', [pythons['312'], '-m', 'build', '--outdir', out / 'dist'], source)]
        wheels, sdists = list((out / 'dist').glob('*.whl')), list((out / 'dist').glob('*.tar.gz'))
        if len(wheels) != 1 or len(sdists) != 1:
            raise RuntimeError('Build must produce exactly one new wheel and sdist')
        wheel, sdist = wheels[0], sdists[0]
        with zipfile.ZipFile(wheel) as archive:
            wheel_files = {name.removeprefix('layauto_v2/'): sha(archive.read(name)) for name in archive.namelist()
                           if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
        with tarfile.open(sdist, 'r:gz') as archive:
            sdist_files = {}
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if member.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise RuntimeError('Unreadable source distribution member')
                    sdist_files['/'.join(parts[2:])] = sha(stream.read())
        if not expected_runtime == wheel_files == sdist_files:
            raise RuntimeError('Wheel/sdist runtime bytes differ from frozen source')
        write('package-identity.json', {'wheel': {'path': str(wheel), 'sha256': sha(wheel.read_bytes()), 'runtime_files': wheel_files},
                                        'sdist': {'path': str(sdist), 'sha256': sha(sdist.read_bytes()), 'runtime_files': sdist_files}})
        identities = {}
        for tag, artifact in (('310', sdist), ('312', wheel)):
            clean = work / ('clean-' + tag)
            if clean.exists():
                raise RuntimeError('Installation environment must be fresh')
            rows.append(run('create-install-' + tag, [pythons[tag], '-m', 'venv', clean], outside))
            py = clean / 'bin/python'
            rows.append(run('install-' + tag, [py, '-m', 'pip', 'install', '--report', out / ('install-' + tag + '-report.json'), artifact], outside))
            rows.append(run('installed-pip-check-' + tag, [py, '-m', 'pip', 'check'], outside))
            rows.append(run('installed-identity-' + tag, [py, '-I', '-B', '-c',
                'import layauto_v2,sys,json; print(json.dumps({"package":layauto_v2.__file__,"executable":sys.executable,"version":sys.version,"isolated":sys.flags.isolated}))'], outside))
            identity = json.loads((out / ('installed-identity-' + tag + '.stdout.txt')).read_text())
            installed = Path(identity['package']).resolve().parent
            if not installed.is_relative_to(clean) or 'site-packages' not in installed.parts:
                raise RuntimeError('Installed smoke resolves package outside clean installation')
            installed_files = runtime_manifest(installed)
            if installed_files != expected_runtime:
                raise RuntimeError('Installed runtime bytes differ from frozen source')
            rows.append(run('installed-smoke-' + tag, [py, '-I', '-B', out / 'installed_smoke.py', source / 'tests/fixtures/w003_m1'], outside))
            identities[tag] = {**identity, 'artifact': str(artifact), 'artifact_sha256': sha(artifact.read_bytes()),
                               'runtime_files': installed_files, 'fresh_environment': True}
        write('installation-identity.json', identities)
        return rows

    try:
        # W011 complete nested receipts have materially larger memory peaks
        # than W010. Do not overlap package smoke with a full test matrix.
        # The 16 GiB session uses the default single matrix worker.
        if args.matrix_workers == 1:
            # Stop immediately on the first failed matrix; do not queue the next
            # interpreter while a known failed attempt is being preserved.
            for tag in pythons:
                commands.extend(matrix(tag))
        else:
            with ThreadPoolExecutor(max_workers=args.matrix_workers) as pool:
                jobs = [pool.submit(matrix, tag) for tag in pythons]
                for job in jobs:
                    commands.extend(job.result())
        if gate_identity is not None:
            assert gate_source is not None
            if sha(gate_source.read_bytes()) != gate_identity['sha256'] or sha((gate_directory / 'w011_resource_gate.py').read_bytes()) != gate_identity['sha256']:
                raise RuntimeError('Resource gate changed during verification')
            gate_rows = {}
            for tag in pythons:
                records = [json.loads(line) for line in (out / ('resource-gate-' + tag + '.jsonl')).read_text().splitlines()]
                if [row['event'] for row in records] != ['WAIT', 'ACQUIRED', 'SESSION_FINISH_LOCK_RETAINED', 'RELEASED']:
                    raise RuntimeError('Resource gate events do not prove complete guarded execution')
                collection = (out / ('collection-' + tag + '.stdout.txt')).read_text().splitlines()
                first = next(line for line in collection if line.startswith('tests/') and '/test_w011_' in line)
                if any(row['first_gated_node'] != first or row['plugin_sha256'] != gate_identity['sha256'] for row in records):
                    raise RuntimeError('Resource gate did not guard the first W011 item with the captured plugin')
                gate_rows[tag] = records
            identities = {(row['lock_path'], row['lock_device'], row['lock_inode']) for rows in gate_rows.values() for row in rows}
            if len(identities) != 1:
                raise RuntimeError('Interpreters did not share one resource lock inode')
            ordered = sorted(gate_rows.values(), key=lambda rows: rows[1]['observed_at_utc'])
            if ordered[0][2]['observed_at_utc'] > ordered[1][1]['observed_at_utc']:
                raise RuntimeError('W011 guarded phases overlapped before session finish')
            write('resource-gate-validation.json', {'status': 'passed', 'events': gate_rows,
                  'shared_lock_inode': list(identities)[0],
                  'release_time_meaning': 'Kernel unlock is at process exit. Parent RELEASED records are observations and may follow the next ACQUIRED; they are not exact kernel unlock timestamps.'})
        commands.extend(package())
        if files_manifest(root, names) != original or files_manifest(source, names) != original:
            raise RuntimeError('Original or snapshot source/tests/config changed during verification')
        final_tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', *selected], cwd=root).decode().split('\0')
        final_untracked = subprocess.check_output(['git', 'ls-files', '-z', '--others', '--exclude-standard', '--', *selected], cwd=root).decode().split('\0')
        if sorted({name for name in final_tracked + final_untracked if name}) != names:
            raise RuntimeError('Source/tests/config path selection changed during verification')
        if sha(smoke.read_bytes()) != smoke_sha:
            raise RuntimeError('Installed smoke source changed during verification')
        write('receipt.json', {'status': 'passed', 'matrix_workers': args.matrix_workers, 'resource_gate': gate_identity,
              'package_smokes_after_matrices': True, 'runner_command': [sys.executable, *sys.argv], 'runner_sha256': runner_sha,
              'smoke_sha256': smoke_sha, 'commands': commands, 'actual_test_counts': counts, 'expected_test_count': args.expected_tests,
              'retained_baseline_test_count': len(baseline_ids),
              'baseline_collection_sha256': sha((out / 'baseline-collection.txt').read_bytes()),
              'python_environments': {tag: str(py) for tag, py in pythons.items()},
              'source_manifest_sha256': sha((out / 'source-manifest.json').read_bytes()),
              'source_snapshot_sha256': sha((out / 'source-snapshot.tar.gz').read_bytes()),
              'source_identity_rechecked_after_all_commands': True,
              'source_file_count': len(names), 'runtime_file_count': len(expected_runtime),
              'limitations': ['Synthetic W003/W004 local geometry scope only; no EDA/production performance or admission claim.',
                             'Complete coordinate model, external body/full device/net annotation/rule/lifecycle/publication closure remain deferred.']})
    except BaseException as exc:
        write('failure.json', {'status': 'failed', 'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        write('evidence-manifest.json', {str(path.relative_to(out)): sha(path.read_bytes()) for path in sorted(out.rglob('*'))
                                        if path.is_file() and path.name != 'evidence-manifest.json'})


if __name__ == '__main__':
    main()
