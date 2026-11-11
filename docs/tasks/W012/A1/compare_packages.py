"""Read-only comparison of the actual before/after distribution payloads."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile


BASE = Path(__file__).resolve().parent


def payload(path):
    if path.suffix == '.whl':
        with zipfile.ZipFile(path) as archive:
            return {name.removeprefix('layauto_v2/'): hashlib.sha256(archive.read(name)).hexdigest()
                    for name in archive.namelist() if name.startswith('layauto_v2/') and
                    (name.endswith('.py') or name.endswith('/py.typed'))}
    with tarfile.open(path) as archive:
        result = {}
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if member.isfile() and len(parts) > 2 and parts[1] == 'layauto_v2' and (
                    parts[-1].endswith('.py') or parts[-1] == 'py.typed'):
                result['/'.join(parts[2:])] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        return result


def main():
    target = BASE / 'package-comparison.json'
    if target.exists():
        raise RuntimeError('Preserve prior package comparison; do not overwrite')
    identities = {'before': json.loads((BASE / 'before-package/package-identity.json').read_text()),
                  'after': json.loads((BASE / 'verification-r2/package-identity.json').read_text())}
    result = {'status': 'passed', 'classification': 'Actual rebuilt-before versus final-after artifacts; not historical W011 blobs',
              'artifacts': {}, 'runtime_payload_differences': {}}
    maps = {}
    for side, identity in identities.items():
        result['artifacts'][side] = {}
        for kind in ('wheel', 'sdist'):
            directory = 'before-package/dist' if side == 'before' else 'verification-r2/dist'
            path = BASE / directory / Path(identity[kind]['path']).name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == identity[kind]['sha256'], (side, kind, 'artifact hash')
            members = payload(path)
            assert len(members) == 100 and members == identity[kind]['runtime_files'], (side, kind, 'actual members')
            maps[side, kind] = members
            result['artifacts'][side][kind] = {'path': str(path.relative_to(BASE)), 'sha256': digest,
                                              'bytes': path.stat().st_size, 'actual_runtime_members': len(members)}
        assert maps[side, 'wheel'] == maps[side, 'sdist'], (side, 'wheel/sdist payload equality')
    for kind in ('wheel', 'sdist'):
        before, after = maps['before', kind], maps['after', kind]
        assert before.keys() == after.keys(), (kind, 'runtime path equality')
        different = [name for name in before if before[name] != after[name]]
        assert different == ['domain/codec.py'], (kind, different)
        result['runtime_payload_differences'][kind] = different
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
