"""Read-only closure of original fixed URI, restored files and resource04 captures."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
TASK = ROOT / 'docs/tasks/W013'
BASE = 'd6182fe6893c26490f9d58c6b808a5ce9910384b'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def main():
    checks, files, captures = [], [], []
    def check(name, passed, detail=None):
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
    original_path = ROOT / 'docs/tasks/W012/A1/preflight.json'
    original_bytes = subprocess.check_output(['git', 'show', BASE + ':docs/tasks/W012/A1/preflight.json'], cwd=ROOT)
    check('original_A1_preflight_immutable', original_path.read_bytes() == original_bytes, digest(original_bytes))
    original = {row['target']: row for row in json.loads(original_bytes)['inputs']}
    restoration = {row['uri']: row for row in load(TASK / 'fixed-mismatch-restoration.json')['inputs']}
    fixed_root = Path('/workspace/w012-inputs/extraction-mismatch')
    actual_paths = {str(path) for path in fixed_root.rglob('*') if path.is_file()}
    check('exact_35_fixed_input_paths', len(original) == len(restoration) == len(actual_paths) == 35 and
          set(original) == set(restoration) == actual_paths)
    old_frozen = load(ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json')['files']
    new_frozen = load(TASK / 'verification-r2/source-manifest.json')['files']
    fixture_entries = {name: h for name, h in old_frozen.items() if name.startswith('tests/fixtures/')}
    check('normal_fixture_A1_and_R2_all_bytes', len(fixture_entries) == 116 and
          all(new_frozen[name] == h == digest((ROOT / name).read_bytes()) ==
              digest((Path('/workspace/work/w013-final-r2/source') / name).read_bytes())
              for name, h in fixture_entries.items()), len(fixture_entries))
    for uri, origin in sorted(original.items()):
        path = Path(uri)
        data = path.read_bytes()
        relative_origin = str(Path(origin['origin']).relative_to(ROOT))
        row = {'uri': uri, 'origin': origin['origin'], 'actual_sha256': digest(data), 'bytes': len(data),
               'original_A1_sha256': origin['sha256'], 'restored_sha256': restoration[uri]['sha256'],
               'frozen_A1_origin_sha256': old_frozen[relative_origin], 'frozen_R2_origin_sha256': new_frozen[relative_origin]}
        files.append(row)
        check('fixed_file:' + str(path.relative_to(fixed_root)),
              not path.is_symlink() and digest(data) == origin['sha256'] == restoration[uri]['sha256'] ==
              old_frozen[relative_origin] == new_frozen[relative_origin] and
              len(data) == origin['bytes'] == restoration[uri]['bytes'], row)
    normal_root = ROOT / 'tests/fixtures/w003_m1'
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        resource_path = TASK / 'resource-attempt-04' / (case + '.json')
        resource = load(resource_path)
        root = fixed_root if case == 'extraction-mismatch' else normal_root
        rows = resource['capture_sources']
        check('capture_unique_count:' + case, len(rows) == len({row['uri'] for row in rows}) == 31)
        check('fixed_site_URI:' + case, resource['input_site'] == str(root / 'site_config.yaml'), resource['input_site'])
        for row in rows:
            path = root / row['uri']
            data = path.read_bytes()
            actual = {'case': case, 'uri': str(path), 'relative_acquisition_uri': row['uri'],
                      'actual_sha256': digest(data), 'captured_sha256': row['sha256'], 'actual_bytes': len(data),
                      'captured_bytes': row['bytes'], 'recorded_resource_sha256': digest(resource_path.read_bytes())}
            captures.append(actual)
            if case == 'extraction-mismatch':
                original_sha = original[str(path)]['sha256']
                restored_sha = restoration[str(path)]['sha256']
                frozen_sha = old_frozen[str(Path(original[str(path)]['origin']).relative_to(ROOT))]
            else:
                original_sha = restored_sha = frozen_sha = old_frozen[str(path.relative_to(ROOT))]
            check('capture_source:' + case + ':' + row['uri'], not path.is_symlink() and
                  digest(data) == row['sha256'] == original_sha == restored_sha == frozen_sha and len(data) == row['bytes'])
    result = {'auditor': '/root/input_contracts', 'utc': datetime.now(timezone.utc).isoformat(),
              'classification': 'fixed input identity audit only; no product or performance rerun',
              'source_id_R2': '2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278',
              'original_preflight_sha256': digest(original_bytes),
              'restoration_receipt_sha256': digest((TASK / 'fixed-mismatch-restoration.json').read_bytes()),
              'fixed_files': files, 'capture_sources': captures, 'checks': checks,
              'failures': [row for row in checks if not row['passed']],
              'status': 'passed' if all(row['passed'] for row in checks) else 'failed',
              'not_run': ['capture', 'performance measurement', 'pytest', 'typing', 'build', 'installation', 'smoke'],
              'limits': ['This verifies current fixed inputs and saved resource captures share bytes; final engineering matrix remains separately pending.']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result['failures'] else 0)


if __name__ == '__main__':
    main()
