"""Restore the omitted F1 sample from the identical commit, preserving run 1."""
import hashlib
import json
from pathlib import Path
import subprocess

base = Path(__file__).resolve().parent
manifest_path = base / 'source-manifest.json'
initial_bytes = manifest_path.read_bytes()
manifest = json.loads(initial_bytes)
name = 'docs/tasks/W003/examples/records.json'
assert name not in manifest['files']
data = subprocess.check_output(['git', 'show', manifest['product_commit'] + ':' + name],
                               cwd='/workspace/Layauto')
destination = Path(manifest['snapshot']) / name
assert not destination.exists()
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_bytes(data)
(base / 'source-manifest-initial.json').write_bytes(initial_bytes)
manifest['files'][name] = hashlib.sha256(data).hexdigest()
manifest['file_count'] = len(manifest['files'])
manifest['git_archive_paths'].append(name)
manifest['harness_correction'] = {
    'initial_manifest': 'source-manifest-initial.json',
    'initial_result': 'pytest310.result.json',
    'reason': 'The initial partial git archive omitted the F1 test-only sample dependency.',
    'restored_from_same_commit': name,
    'sha256': hashlib.sha256(data).hexdigest(),
    'product_tests_and_fixture_unchanged': True,
    'retest_scope': 'test_f1_request_independently_matches_accepted_sample only; other 120 cases already passed on identical product/test bytes.'
}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest['harness_correction'], indent=2))
print('Completed snapshot file count:', manifest['file_count'])
