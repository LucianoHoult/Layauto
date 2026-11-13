"""Read-only final resource adoption, successful suffix and frozen Git audit."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = 'c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364'
COMMIT = '66f5b1e5369549ed8df361f89f099acfd2f39e17'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_bytes())


def identity(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def main():
    checks = []

    def check(ok, label):
        assert ok, label
        checks.append(label)

    frozen = load('docs/tasks/W014/development/frozen-source.json')
    resource = load('docs/tasks/W014/resource-adoption-r4/final-selection.json')
    prefix = load('docs/tasks/W014/review-evidence/candidate_r7_identity_audit.stdout.json')
    audited = load('docs/tasks/W014/review-evidence/resource_r4_audit.stdout.json')
    remaining = load('docs/tasks/W014/development/remaining-r7.command.json')
    check(frozen['source_id'] == identity(frozen['files']) == SOURCE, 'final source manifest self identity')
    check(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == COMMIT,
          'actual HEAD is requested freeze commit')
    check(frozen['git_head'] == COMMIT, 'manifest records exact freeze commit')
    for name, wanted in frozen['files'].items():
        check(sha((ROOT / name).read_bytes()) == wanted, 'frozen selected live byte ' + name)
    archive_bytes = subprocess.check_output(['git', 'archive', '--format=tar', COMMIT, '--', *frozen['files']], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:') as archive:
        committed = {member.name: sha(archive.extractfile(member).read())
                     for member in archive.getmembers() if member.isfile()}
    check(committed == frozen['files'], 'all 286 selected Git commit bytes equal frozen/live manifest')
    measured = load(resource['selected_samples']['normal-direct']['report']['path'])
    check(audited['source_id'] == resource['current_source_id'] == measured['source_id'] == prefix['resource_measured_source_id'],
          'resource remains its original measured source')
    delta = [name for name in sorted(set(measured['files']) | set(frozen['files']))
             if measured['files'].get(name) != frozen['files'].get(name)]
    check(delta == prefix['delta'] == ['tests/contracts/test_w014_contracts.py'],
          'resource-to-freeze delta remains exactly the independently reviewed test-only change')
    check(prefix['candidate_source_id'] == SOURCE and prefix['adopted_count'] == 85,
          'independently audited 85-prefix adoption binds final source')
    check(remaining['returncode'] == 0 and remaining['source_unchanged'] is True
          and remaining['source_id_before'] == remaining['source_id_after'] == SOURCE
          and remaining['files'] == frozen['files'], 'remaining command success on exact final source')
    for stream in ('stdout', 'stderr'):
        data = (ROOT / 'docs/tasks/W014/development' / ('remaining-r7.' + stream + '.txt')).read_bytes()
        check(sha(data) == remaining['logs'][stream]['sha256'], 'original remaining ' + stream + ' hash')
        if stream == 'stdout':
            check(b'80 passed in 644.58s' in data, 'actual remaining 80 pass summary')
    collection = [line for line in (ROOT / 'docs/tasks/W014/development/collection-r6.stdout.txt').read_text().splitlines()
                  if line.startswith('tests/') and '::' in line]
    selected = []
    for selector in (arg for arg in remaining['argv'] if arg.startswith('tests/')):
        selected.extend(node for node in collection
                        if node == selector or '::' not in selector and node.partition('::')[0] == selector)
    check(selected == prefix['remaining_nodeids'] and len(selected) == len(set(selected)) == 80,
          'actual remaining command covers exactly the audited 80-node suffix')
    check(set(selected).isdisjoint(prefix['adopted_nodeids'])
          and len(selected) + len(prefix['adopted_nodeids']) == 165, '85 adopted plus 80 actual close the targeted 165 scope')
    check(audited['parallel_matrices_safe_assessment'] is True, 'independent R4 resource scheduling assessment supports two workers')
    result = {'status': 'passed', 'scope': 'resource freeze/adoption/targeted evidence only',
        'source_id': SOURCE, 'freeze_commit': COMMIT, 'resource_measured_source_id': measured['source_id'],
        'resource_to_freeze_test_only_delta': delta, 'adopted_targeted_count': 85,
        'actual_remaining_count': 80, 'targeted_scope_count': 165,
        'check_count': len(checks), 'checks': checks,
        'limitations': ['Final full matrices/build/clean installation and product review remain pending.',
            'No product, tests, codec or capture were run by this audit.']}
    (OUT / 'resource_freeze_audit.stdout.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'source_id', 'freeze_commit',
        'check_count', 'adopted_targeted_count', 'actual_remaining_count')}, indent=2))


if __name__ == '__main__':
    main()
