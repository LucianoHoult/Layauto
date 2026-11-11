"""Freeze source/input/environment evidence; rebuild fixed mismatch input safely."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

ROOT = Path('/workspace/Layauto')
OUT = ROOT/'docs/tasks/W012'
FIXTURE = ROOT/'tests/fixtures/w003_m1'
OVERLAY = Path('/workspace/w012-inputs/extraction-mismatch')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT/'docs/tasks/W011/verification/source-manifest.json').read_text())
    refs = ('HEAD','origin/main',manifest['git_head'])
    for name, expected in manifest['files'].items():
        assert sha((ROOT/name).read_bytes()) == expected
        for ref in refs:
            assert sha(subprocess.check_output(['git','show',f'{ref}:{name}'],cwd=ROOT)) == expected
    with tarfile.open(ROOT/'docs/tasks/W011/verification/source-snapshot.tar.gz') as archive:
        for name, expected in manifest['files'].items():
            assert sha(archive.extractfile(name).read()) == expected
    overlay_names = ('source.gds','query/header.json','query/raw/device_info_Q17.txt',
                     'query/normalized/device_regions.yaml','body/context.json')
    OVERLAY.mkdir(parents=True,exist_ok=True)
    inputs = []
    for source in sorted(FIXTURE.rglob('*')):
        relative = source.relative_to(FIXTURE)
        if not source.is_file() or relative.parts[0] in ('expected','failures','outputs') or relative.name in ('oracle.json','spec.json','README.md'):
            continue
        original = FIXTURE/'failures/extraction_mismatch'/relative if str(relative) in overlay_names else source
        target = OVERLAY/relative
        data = original.read_bytes()
        if target.exists():
            assert target.read_bytes() == data, 'existing fixed overlay differs'
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        inputs.append({'target':str(target), 'origin':str(original), 'sha256':sha(data),'bytes':len(data)})
    # Preserve original command output, including package check and launch process state.
    commands = []
    for label, command in (
        ('git-status',['git','status','--short','--branch']),
        ('git-identity',['git','log','-3','--format=%H %an <%ae> %s']),
        ('pip-check',[sys.executable,'-m','pip','check']),
        ('processes',['ps','-eo','pid,comm,rss,etime','--sort=-rss']),
    ):
        proc = subprocess.run(command,cwd=ROOT,capture_output=True)
        (OUT/(label+'.stdout.txt')).write_bytes(proc.stdout)
        (OUT/(label+'.stderr.txt')).write_bytes(proc.stderr)
        commands.append({'argv':command,'cwd':str(ROOT),'exit_code':proc.returncode,
                         'stdout_sha256':sha(proc.stdout),'stderr_sha256':sha(proc.stderr)})
        assert proc.returncode == 0
    receipt = {'utc':datetime.now(timezone.utc).isoformat(), 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               'verified_refs':refs,'source_count':len(manifest['files']), 'runtime_count':len(manifest['runtime_files']),
               'source_manifest_sha256':sha((ROOT/'docs/tasks/W011/verification/source-manifest.json').read_bytes()),
               'snapshot_sha256':sha((ROOT/'docs/tasks/W011/verification/source-snapshot.tar.gz').read_bytes()),
               'files':manifest['files'], 'inputs':inputs, 'python':sys.version,'executable':sys.executable,
               'platform':platform.platform(), 'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},
               'cgroup':{n:Path('/sys/fs/cgroup',n).read_text().strip() for n in ('memory.max','memory.current','memory.swap.max','cpu.max')},
               'commands':commands,'tool_sha256':sha(Path(__file__).read_bytes()),
               'history_adoption':'W011 same 262-source/100-runtime: dual1605, typing54, build/dual install; not rerun for investigation'}
    (OUT/'preflight.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('262 source / 100 runtime / snapshot / fixed overlay / environment passed')


if __name__ == '__main__':
    main()
