"""Read-only resource-adoption and stopped-attempt evidence audit; no product imports."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
TASK = ROOT / 'docs/tasks/W013'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    checks = []
    def check(name, passed, detail=None):
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
    clearance = read(TASK / 'resource-clearance-r2.json')
    for label in ('delta_proof', 'delta_review'):
        check(label + '_hash', sha(ROOT / clearance[label]) == clearance[label + '_sha256'])
    proof = read(ROOT / clearance['delta_proof'])
    review = read(ROOT / clearance['delta_review'])
    old = read(TASK / 'verification/source-manifest.json')
    new = read(TASK / 'verification-r2/source-manifest.json')
    delta = {name: {'measured': old['files'].get(name), 'current': new['files'].get(name)}
             for name in set(old['files']) | set(new['files'])
             if old['files'].get(name) != new['files'].get(name)}
    check('actual_delta_exactly_reviewed', delta == proof['changed_files'] == review['delta'] and
          set(delta) == {'tests/contracts/test_w007_contracts.py'}, delta)
    check('measured_new_source_binding', old['source_id'] == proof['measured_source_id'] == clearance['measured_source_id'] == review['measured_source_id'] and
          new['source_id'] == proof['source_id'] == clearance['source_id'] == review['new_source_id'])
    check('all_runtime_bytes_unchanged', old['runtime_files'] == new['runtime_files'] and len(new['runtime_files']) == proof['runtime_file_count'] == 106)
    # Resource probe is a reviewed script, not part of the one changed test.
    probes = [path for path in (TASK / 'resource-attempt-04').glob('*.py') if sha(path) == proof['resource_probe_sha256']]
    check('measured_resource_probe_exists', len(probes) == 1 and proof['resource_probe_sha256'] == proof['measured_probe_sha256'], [str(p) for p in probes])
    baseline_guard = (Path('/workspace/work/w013-final/source') / 'tests/contracts/test_w007_contracts.py').read_text()
    new_guard = (Path('/workspace/work/w013-final-r2/source') / 'tests/contracts/test_w007_contracts.py').read_text()
    addition = """            # W013 composes its immutable proposed annotation draft only. This
            # does not permit any mutable state or publication dependency.
            allowed_net_annotation_state = (path.parent.name == 'normalization'
                                            and path.name in ('net_annotation.py', 'net_annotation_codec.py')
                                            and isinstance(node, ast.ImportFrom)
                                            and node.module == 'layauto_v2.state.annotation'
                                            and {alias.name for alias in node.names} == {'AnnotationDraft'})
"""
    restored = new_guard.replace(addition, '').replace('or allowed_effective_state or allowed_local_contact_state or allowed_net_annotation_state):',
                                                      'or allowed_effective_state or allowed_local_contact_state):')
    check('guard_exact_narrow_source_delta', restored == baseline_guard and addition in new_guard)
    stopped = TASK / 'verification'
    for tag in ('310', '312'):
        row = read(stopped / ('pytest-' + tag + '.json'))
        check('original_stopped_command:' + tag, row['exit_code'] == -15 and
              all(sha(stopped / row[stream]) == row[stream + '_sha256'] for stream in ('stdout', 'stderr')), row)
    old_evidence = read(stopped / 'evidence-manifest.json')
    check('all_stopped_evidence_preserved', all(sha(stopped / name) == digest for name, digest in old_evidence.items()), len(old_evidence))
    after = read(TASK / 'development/retained-boundary-after.command.json')
    check('three_boundary_checks_same_new_source', after['returncode'] == 0 and after['files'] == new['files'] and
          after['source_id_before'] == after['source_id_after'] == new['source_id'] and
          '3 passed' in (TASK / 'development/retained-boundary-after.stdout.txt').read_text())
    check('boundary_check_raw_logs', all(sha(Path(row['path'])) == row['sha256'] for row in after['logs'].values()))
    result = {'auditor': '/root/input_contracts', 'classification': 'R2 test-only resource adoption and failure evidence identity',
              'checks': checks, 'failures': [row for row in checks if not row['passed']],
              'status': 'passed' if all(row['passed'] for row in checks) else 'failed',
              'not_run': ['product captures', 'pytest', 'typing', 'build', 'installation', 'smoke'],
              'limits': ['Resource measurements remain bound to their original source; this check only validates adoption under a test-only delta.']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result['failures'] else 0)


if __name__ == '__main__':
    main()
