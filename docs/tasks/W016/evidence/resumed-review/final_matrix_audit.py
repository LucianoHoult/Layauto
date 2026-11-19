"""Final independent evidence audit: read existing results, never rerun tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, required=True)
a = p.parse_args()
root = a.root.resolve()
here = Path(__file__).resolve().parent
base = root/'docs/tasks/W016/evidence/resumed/completed'
support = json.loads(subprocess.check_output([sys.executable, str(here/'engineering_evidence_audit.py'), '--root', str(root)], text=True))
support.pop('full_matrices')
manifest_sha = support['manifest_sha256']
rows = []
for version in ('312', '310'):
    parts = []
    for label, expected, scope in (('pytest-'+version, 1953, ['tests/unit', 'tests/contracts']),
                                   ('fixture-support-'+version, 3, ['tests/fixture_support'])):
        path = base/(label+'.json')
        meta = json.loads(path.read_text())
        assert meta['exit_code'] == 0 and meta['source_manifest_sha256'] == manifest_sha
        assert all(item in meta['command'] for item in scope)
        assert meta['command'][0] == json.loads((base/('environment-'+version+'.json')).read_text())['executable']
        stdout, stderr = base/meta['stdout'], base/meta['stderr']
        assert hashlib.sha256(stdout.read_bytes()).hexdigest() == meta['stdout_sha256']
        assert hashlib.sha256(stderr.read_bytes()).hexdigest() == meta['stderr_sha256']
        assert not stderr.read_bytes()
        last_line = stdout.read_text().strip().splitlines()[-1]
        match = re.fullmatch(r'(\d+) passed(?:, (\d+) subtests passed)? in ([0-9.]+)s(?: \([^\n]+\))?', last_line)
        assert match and int(match[1]) == expected, last_line
        parts.append({'label': label, 'command': meta['command'], 'exit_code': 0,
                      'passed': expected, 'subtests_passed': int(match[2]) if match[2] else None,
                      'pytest_seconds': float(match[3]),
                      'driver_seconds': meta['elapsed_seconds'], 'stdout_sha256': meta['stdout_sha256'],
                      'stderr_empty': True, 'report_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    assert sum(part['passed'] for part in parts) == support['collection']['full_nodes']
    rows.append({'interpreter': version, 'full_tests_passed': 1956, 'parts': parts,
                 'disjoint_collection_union_verified': True})
print(json.dumps({'status': 'passed', 'manifest_sha256': manifest_sha,
                  'reviewer_method': 'Read original completed command metadata/output hashes and full node coverage; independently rechecked all 298 source/test/config hashes, environments, build/install bytes and supporting evidence. No pytest or product/wire rerun.',
                  'matrices': rows, 'supporting_engineering_audit': support,
                  'conclusion': 'A8 engineering evidence complete on this frozen snapshot; no open must. This is independent engineering review, not PM acceptance or production/EDA assurance.'}, indent=2))
