"""Frozen W014 dual-interpreter matrix; run only after its resource checkpoint.

Use source_identity.py to record the final current source_id first. Required
--resource-clearance is an explicit review receipt containing status="passed",
source_id equal to --expected-source-id, and all three fixed case names. This
receipt records the checkpoint decision; actual performance evidence stays at
its original linked owner. Network commands preserve inherited proxy/CA trust.
"""
from __future__ import annotations

import argparse
import ast
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

from source_identity import source_names, source_id


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('root', 'out', 'work', 'smoke', 'python310', 'python312'):
        parser.add_argument('--' + field, type=Path, required=True)
    parser.add_argument('--expected-tests', type=int, required=True)
    parser.add_argument('--baseline-collection', type=Path, required=True)
    parser.add_argument('--baseline-sha256', required=True)
    parser.add_argument('--expected-source-id', required=True)
    parser.add_argument('--resource-clearance', type=Path, required=True)
    parser.add_argument('--matrix-workers', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    clearance_path = args.resource_clearance.resolve()
    clearance_bytes = clearance_path.read_bytes()
    clearance = json.loads(clearance_bytes)
    required_cases = {'normal-direct', 'normal-readback', 'extraction-mismatch'}
    if (clearance.get('status') != 'passed' or
            clearance.get('source_id') != args.expected_source_id or
            set(clearance.get('cases', ())) != required_cases):
        parser.error('Resource clearance must bind this source_id and all three fixed cases')
    if args.matrix_workers == 2 and clearance.get('parallel_matrices_safe') is not True:
        parser.error('Two matrices require explicit parallel_matrices_safe resource clearance')
    root, out, work, smoke = (getattr(args, name).resolve() for name in ('root', 'out', 'work', 'smoke'))
    pythons = {'310': args.python310.absolute(), '312': args.python312.absolute()}
    smoke_tree = ast.parse(smoke.read_text())
    readiness = [node.value.value for node in smoke_tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                 and any(isinstance(target, ast.Name) and target.id == 'W014_SMOKE_READY'
                         for target in node.targets)]
    if readiness != [True]:
        parser.error('W014 installed smoke API assertions must be integrated before final matrix')
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
        overrides = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(cwd), 'PIP_CACHE_DIR': str(work / 'pip-cache'),
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

    write('resource-clearance.json', {'source': str(clearance_path), 'sha256': sha(clearance_bytes),
                                      'decision': clearance})
    tool_paths = {'runner': Path(__file__).resolve(),
                  'source_identity': Path(__file__).with_name('source_identity.py').resolve(),
                  'smoke': smoke}
    tool_hashes = {name: sha(path.read_bytes()) for name, path in tool_paths.items()}
    write('tool-identity.json', {name: {'source': str(tool_paths[name]), 'sha256': digest}
                                 for name, digest in tool_hashes.items()})
    (out / 'source_identity.py').write_bytes(tool_paths['source_identity'].read_bytes())
    # Existing W006 independently compares the accepted RunAttempt example.
    # This is a test-only sample and is never a runtime smoke input.
    names = source_names(root)
    original = files_manifest(root, names)
    if source_id(original) != args.expected_source_id:
        raise RuntimeError('Current complete source identity differs from the requested final freeze')
    resource_paths = ['/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/cpu.max', '/sys/fs/cgroup/memory.swap.max']
    write('resource-limits.json', {'platform': platform.platform(),
          'cpu_count': os.cpu_count(),
          'cgroup': {name: Path(name).read_text().strip() if Path(name).exists() else None for name in resource_paths},
          'rlimits': {name: resource.getrlimit(getattr(resource, name)) for name in
                      ('RLIMIT_AS', 'RLIMIT_CPU', 'RLIMIT_DATA', 'RLIMIT_NOFILE', 'RLIMIT_STACK')},
          'matrix_workers': args.matrix_workers,
          'phase_order': ['interpreter matrices', 'build', '3.10 clean installation and smoke', '3.12 clean installation and smoke'],
          'heavy_package_smokes_overlap_matrices': False,
          'resource_clearance_sha256': sha(clearance_bytes),
          'limits': ['Sample timings and process RSS are not maximal input or production resource guarantees.']})
    source_meta = {'source_id': source_id(original), 'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
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
    baseline_collection = args.baseline_collection.resolve()
    baseline_bytes = baseline_collection.read_bytes()
    if sha(baseline_bytes) != args.baseline_sha256:
        raise RuntimeError('Baseline collection identity mismatch')
    baseline_ids = {line for line in baseline_bytes.decode().splitlines() if line.startswith('tests/') and '::' in line}
    if not baseline_ids:
        raise RuntimeError('Baseline collection must contain the accepted test IDs')
    (out / 'baseline-collection.txt').write_bytes(baseline_bytes)
    commands: list[dict[str, object]] = []
    expected_runtime = source_meta['runtime_files']
    if not expected_runtime:
        raise RuntimeError('Frozen runtime manifest is empty')
    counts: dict[str, int] = {}

    def matrix(tag: str) -> list[dict[str, object]]:
        py = pythons[tag]
        minor = 10 if tag == '310' else 12
        rows = [run('environment-' + tag, [py, '-c',
            'import sys,platform,importlib.metadata as m,json,layauto_v2; from pathlib import Path; '
            f'assert sys.version_info[:2] == (3, {minor}), sys.version; '
            'p=Path(layauto_v2.__file__).resolve(); assert p.parent==Path.cwd()/"layauto_v2", p; '
            'print(json.dumps({"executable":sys.executable,"version":sys.version,"platform":platform.platform(),"source_package":str(p),"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2))'], source),
            run('collection-' + tag, [py, '-m', 'pytest', '-p', 'no:cacheprovider', '--collect-only', 'tests/unit', 'tests/contracts', '-q'], source)]
        current_ids = {line for line in (out / ('collection-' + tag + '.stdout.txt')).read_text().splitlines()
                       if line.startswith('tests/') and '::' in line}
        missing = sorted(baseline_ids - current_ids)
        write('pytest-scope-' + tag + '.json', {'baseline_test_count': len(baseline_ids),
              'current_test_count': len(current_ids), 'added_test_count': len(current_ids - baseline_ids),
              'missing_baseline_ids': missing})
        if missing or len(current_ids) != args.expected_tests:
            raise RuntimeError('The final matrix must retain all original baseline tests')
        pytest_command: list[object] = [py, '-m', 'pytest', '-p', 'no:cacheprovider', 'tests/unit', 'tests/contracts', '-q']
        rows.append(run('pytest-' + tag, pytest_command, source))
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
        # Packaging smokes run after both full matrices; resource clearance is
        # a scheduling gate, never evidence of a single-call cost improvement.
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
        if clearance_path.read_bytes() != clearance_bytes:
            raise RuntimeError('Resource clearance changed during verification')
        commands.extend(package())
        if files_manifest(root, names) != original or files_manifest(source, names) != original:
            raise RuntimeError('Original or snapshot source/tests/config changed during verification')
        if source_names(root) != names:
            raise RuntimeError('Source/tests/config path selection changed during verification')
        if sha(smoke.read_bytes()) != smoke_sha:
            raise RuntimeError('Installed smoke source changed during verification')
        if {name: sha(path.read_bytes()) for name, path in tool_paths.items()} != tool_hashes:
            raise RuntimeError('Frozen engineering tools changed during verification')
        if clearance_path.read_bytes() != clearance_bytes or baseline_collection.read_bytes() != baseline_bytes:
            raise RuntimeError('Clearance or baseline collection changed during verification')
        write('receipt.json', {'status': 'passed', 'matrix_workers': args.matrix_workers, 'resource_clearance_sha256': sha(clearance_bytes),
              'package_smokes_after_matrices': True, 'runner_command': [sys.executable, *sys.argv], 'runner_sha256': runner_sha,
              'smoke_sha256': smoke_sha, 'tool_hashes': tool_hashes,
              'commands': commands, 'actual_test_counts': counts, 'expected_test_count': args.expected_tests,
              'retained_baseline_test_count': len(baseline_ids),
              'baseline_collection_sha256': sha((out / 'baseline-collection.txt').read_bytes()),
              'python_environments': {tag: str(py) for tag, py in pythons.items()},
              'source_id': source_id(original),
              'source_manifest_sha256': sha((out / 'source-manifest.json').read_bytes()),
              'source_snapshot_sha256': sha((out / 'source-snapshot.tar.gz').read_bytes()),
              'source_identity_rechecked_after_all_commands': True,
              'source_file_count': len(names), 'runtime_file_count': len(expected_runtime),
              'limitations': ['Synthetic W003/W004 local geometry scope only; no EDA/production performance or admission claim.',
                             'Finite source D/G/S/B and synthetic external-body relations only; complete extraction, mandatory-rule, lifecycle and publication closure remain deferred.']})
    except BaseException as exc:
        write('failure.json', {'status': 'failed', 'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        write('evidence-manifest.json', {str(path.relative_to(out)): sha(path.read_bytes()) for path in sorted(out.rglob('*'))
                                        if path.is_file() and path.name != 'evidence-manifest.json'})


if __name__ == '__main__':
    main()
