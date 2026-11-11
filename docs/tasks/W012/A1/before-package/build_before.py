"""Rebuild accessible before-source packages for W012 A1 identity evidence only.

No product tests/smokes/benchmarks. No measured source checkout is written.
"""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path('/workspace/Layauto')
DEST = Path('/workspace/w012-a1-before-package')
SOURCE = DEST/'source'
DIST = DEST/'dist'
REVISION = '7f7c1304bdafd941791421cef64864fb1616303c'
PYTHON = '/workspace/w012-a1-env/dev312/bin/python'
PERFORMANCE = ROOT/'docs/tasks/W012/A1/performance/frozen-identity.json'
W011 = ROOT/'docs/tasks/W011/verification/source-manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    (DEST/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def run(label, argv, cwd, stdout_name=None):
    stdout_name = stdout_name or label+'.stdout.txt'
    started = datetime.now(timezone.utc).isoformat()
    clock = time.perf_counter()
    overrides = {'PYTHONDONTWRITEBYTECODE':'1'}
    with (DEST/stdout_name).open('wb') as out, (DEST/(label+'.stderr.txt')).open('wb') as err:
        proc = subprocess.run(argv, cwd=cwd, env=dict(os.environ, **overrides), stdout=out, stderr=err)
    row = {'argv':argv,'cwd':str(cwd),'environment_overrides':overrides,
           'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
           'elapsed_seconds':time.perf_counter()-clock,'exit_code':proc.returncode,
           'stdout':stdout_name,'stdout_sha256':sha((DEST/stdout_name).read_bytes()),
           'stderr':label+'.stderr.txt','stderr_sha256':sha((DEST/(label+'.stderr.txt')).read_bytes())}
    write(label+'.command.json',row)
    if proc.returncode:
        raise RuntimeError(label+' failed; original command/stdout/stderr preserved')
    return row


def main():
    assert not SOURCE.exists() and not DIST.exists(), 'preserve previous attempts'
    SOURCE.mkdir()
    DIST.mkdir()
    commands = []
    commands.append(run('git-archive',['git','archive','--format=tar',REVISION,'layauto_v2','pyproject.toml','README.md'],ROOT,'before-source.tar'))
    with tarfile.open(DEST/'before-source.tar') as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            assert member.isfile() and not member.issym() and not member.islnk()
            relative = Path(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            target = SOURCE/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    performance = json.loads(PERFORMANCE.read_text())['sources']['before']
    prior = json.loads(W011.read_text())
    selected = {str(p.relative_to(SOURCE)):sha(p.read_bytes()) for p in sorted(SOURCE.rglob('*')) if p.is_file()}
    assert len(selected)==102
    assert all(performance[name]==digest for name,digest in selected.items())
    runtime = {name.removeprefix('layauto_v2/'):digest for name,digest in selected.items() if name.startswith('layauto_v2/')}
    assert len(runtime)==100 and runtime==prior['runtime_files']
    write('before-source-identity.json',{'source_git_revision':REVISION,'selected_files':selected,
          'runtime_files':runtime,'runtime_file_count':len(runtime),
          'performance_frozen_identity_sha256':sha(PERFORMANCE.read_bytes()),
          'performance_identity_owner':'sources.before','W011_source_manifest_sha256':sha(W011.read_bytes()),
          'matches_performance_before_and_W011_runtime':True})
    commands.append(run('build-environment',[PYTHON,'-B','-c',
        'import sys,platform,json,importlib.metadata as m;print(json.dumps({"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"packages":{d.metadata["Name"]:d.version for d in m.distributions()}},indent=2,sort_keys=True))'],SOURCE))
    commands.append(run('build',[PYTHON,'-B','-m','build','--no-isolation','--outdir',str(DIST)],SOURCE))
    wheels=list(DIST.glob('*.whl'));sdists=list(DIST.glob('*.tar.gz'))
    assert len(wheels)==len(sdists)==1
    wheel,sdist=wheels[0],sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        wheel_runtime={name.removeprefix('layauto_v2/'):sha(archive.read(name)) for name in archive.namelist()
                       if name.startswith('layauto_v2/') and (name.endswith('.py') or name.endswith('/py.typed'))}
    with tarfile.open(sdist) as archive:
        sdist_runtime={}
        for member in archive.getmembers():
            parts=Path(member.name).parts
            if member.isfile() and len(parts)>2 and parts[1]=='layauto_v2' and (parts[-1].endswith('.py') or parts[-1]=='py.typed'):
                sdist_runtime['/'.join(parts[2:])]=sha(archive.extractfile(member).read())
    assert runtime==wheel_runtime==sdist_runtime and len(wheel_runtime)==100
    assert all(sha((SOURCE/name).read_bytes())==digest for name,digest in selected.items())
    identity={'status':'passed','source_git_revision':REVISION,
       'classification':'New packages rebuilt in this A1 session from measured before source; not original W011 distribution blobs or performance samples.',
       'scope':'Package construction and member identity only. No installation, product smoke, matrix or performance sample executed.',
       'build_isolation':False,'build_isolation_reason':'Reuse the already recorded dev312 build/setuptools environment; no network or new dependency installation was needed.',
       'runtime_file_count':len(runtime),'commands':commands,
       'wheel':{'path':str(wheel.relative_to(DEST)),'sha256':sha(wheel.read_bytes()),'bytes':wheel.stat().st_size,'runtime_files':wheel_runtime},
       'sdist':{'path':str(sdist.relative_to(DEST)),'sha256':sha(sdist.read_bytes()),'bytes':sdist.stat().st_size,'runtime_files':sdist_runtime},
       'before_source_unchanged':True,'matches_performance_before_and_W011_runtime':True,
       'tool_sha256':sha(Path(__file__).read_bytes())}
    write('package-identity.json',identity)
    paths=[p for p in sorted(DEST.rglob('*')) if p.is_file() and not p.is_relative_to(SOURCE) and p.name!='evidence-manifest.json']
    write('evidence-manifest.json',{str(p.relative_to(DEST)):sha(p.read_bytes()) for p in paths})
    print(json.dumps({'status':'passed','source_revision':REVISION,'runtime_files':len(runtime),
          'wheel_sha256':identity['wheel']['sha256'],'sdist_sha256':identity['sdist']['sha256']},indent=2))


if __name__=='__main__':
    main()
