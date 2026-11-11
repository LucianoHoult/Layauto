"""Independent exact pre-screen identity/snapshot review; standard library only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path('/workspace/Layauto')
OUT = Path(__file__).resolve().parent
PREFIX = ROOT / 'docs/tasks/W012/A2-implementation'
BASE = '2489b4609ae97d8211bf450d55cac9392492ac71'
CANDIDATE = 'c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    destination = OUT / 'freeze-check-attempt02.json'
    assert not destination.exists()
    frozen = read(PREFIX / 'freeze-screen-attempt02/freeze.json')
    accepted = read(ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json')['files']
    counts = {}
    for side in ('before', 'after'):
        manifest = read(PREFIX / f'freeze-screen-attempt02/{side}-source-manifest.json')
        files = manifest['files']
        assert files == frozen['sources'][side]
        expected_commit = BASE if side == 'before' else CANDIDATE
        assert manifest['git_head'] == expected_commit
        for name, expected in files.items():
            assert sha((Path(frozen['roots'][side]) / name).read_bytes()) == expected
            assert sha(subprocess.check_output(['git', 'show', f'{expected_commit}:{name}'], cwd=ROOT)) == expected
        snapshot = PREFIX / f'freeze-screen-attempt02/{side}-source-snapshot.tar.gz'
        assert sha(snapshot.read_bytes()) == manifest['snapshot_sha256']
        with tarfile.open(snapshot) as archive:
            assert sorted(member.name for member in archive.getmembers()) == sorted(files)
            assert all(sha(archive.extractfile(name).read()) == expected for name, expected in files.items())
        counts[side] = len(files)
    assert frozen['sources']['before'] == accepted and counts == {'before': 263, 'after': 264}
    differences = sorted(name for name in frozen['sources']['before'].keys() | frozen['sources']['after'].keys()
                         if frozen['sources']['before'].get(name) != frozen['sources']['after'].get(name))
    assert differences == frozen['differences'] == [
        'layauto_v2/normalization/channel_identity_codec.py',
        'layauto_v2/normalization/local_connectivity_codec.py',
        'tests/contracts/test_w012_typed_pack.py']
    old_inputs = read(ROOT / 'docs/tasks/W012/A1/preflight.json')['inputs']
    assert len(frozen['inputs']) == len(old_inputs) == 35
    overlays = []
    for old, current in zip(old_inputs, frozen['inputs']):
        assert all(current[key] == value for key, value in old.items())
        origin, target, normal = map(Path, (current['origin'], current['target'], current['normal']))
        data = origin.read_bytes()
        assert data == target.read_bytes() and len(data) == current['bytes'] and sha(data) == current['sha256']
        assert sha(normal.read_bytes()) == current['normal_sha256']
        for name, expected in ((origin, current['sha256']), (normal, current['normal_sha256'])):
            relative = name.relative_to(ROOT)
            assert sha(subprocess.check_output(['git', 'show', f'{BASE}:{relative}'], cwd=ROOT)) == expected
        if current['overlay']:
            overlays.append(str(target.relative_to('/workspace/w012-inputs/extraction-mismatch')))
    assert sorted(overlays) == ['body/context.json', 'query/header.json',
        'query/normalized/device_regions.yaml', 'query/raw/device_info_Q17.txt', 'source.gds']
    current_tools = {path.name: sha(path.read_bytes()) for path in (PREFIX / 'measurement').glob('*.py')}
    assert current_tools == frozen['tools']
    selfcheck = read(PREFIX / 'tool-failure-I-R02/selfcheck-final-result.json')
    assert selfcheck['status'] == 'passed' and selfcheck['tools'] == current_tools
    old = read(PREFIX / 'freeze-screen/freeze.json')
    assert frozen['sources'] == old['sources'] and frozen['inputs'] == old['inputs']
    assert frozen['environment'] == old['environment'] and frozen['request'] == old['request']
    assert {name for name in current_tools if current_tools[name] != old['tools'][name]} == {'probe.py', 'selfcheck.py', 'analyze.py'}
    own_selfcheck = read(OUT / 'I-R02-selfcheck-result.json')
    assert own_selfcheck['status'] == 'passed' and own_selfcheck['tools'] == current_tools
    assert own_selfcheck['preservation_witnesses'] == selfcheck['preservation_witnesses']
    assert selfcheck['inputs'] == frozen['inputs'] and selfcheck['environment'] == frozen['environment']
    assert frozen['request'] == {'proposed_run_id': 'w012-investigation-run',
        'lineage_id': 'w012-investigation-lineage', 'idempotency_key': 'create-w012',
        'site_path': '/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml',
        'selection_tuples': 'all defaults empty'}
    result = {'status': 'passed', 'at_utc': datetime.now(timezone.utc).isoformat(),
        'base': BASE, 'candidate': CANDIDATE, 'source_counts': counts,
        'differences': differences, 'tar_members_and_complete_bytes_checked': True,
        'input_count': 35, 'five_overlays': overlays,
        'all_input_bytes_match_original_A1_git': True, 'tools': current_tools,
        'freeze_sha256': sha((PREFIX / 'freeze-screen-attempt02/freeze.json').read_bytes()),
        'scope': 'Independent pre-screen scope/input/source/test/config/tool checks; no complete product benchmark run.'}
    with destination.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: before/after 263/264 complete snapshots and Git, 35/five input bytes, fixed request, frozen tools/selfcheck')


if __name__ == '__main__':
    main()
