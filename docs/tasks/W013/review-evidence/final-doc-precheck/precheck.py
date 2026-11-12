"""Independent read-only documentation/input identity precheck; no product imports."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
TASK = ROOT / 'docs/tasks/W013'
OUT = TASK / 'review-evidence/final-doc-precheck'
BASE = 'd6182fe6893c26490f9d58c6b808a5ce9910384b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    checks = []
    def check(name, condition, details=None):
        checks.append({'name': name, 'passed': bool(condition), 'details': details})
    reviewed_names = ['handoff-scope-audit.md', 'final-evidence-review.md',
        'review-evidence/final-audit/fixed_input_audit.py',
        'review-evidence/final-audit/fixed-input.stdout.json',
        'review-evidence/final-audit/fixed-input-manifest.json']
    reviewed_bytes = {name: (TASK / name).read_bytes() for name in reviewed_names}
    task_bytes = (ROOT / 'docs/tasks/W013-net-annotation-coverage.md').read_bytes()
    baseline_task = subprocess.check_output(['git', 'show', BASE + ':docs/tasks/W013-net-annotation-coverage.md'])
    def block(data, start, end=None):
        result = data.split(start.encode(), 1)[1]
        return result if end is None else result.split(end.encode(), 1)[0]
    check('PM_requirements_and_phase_unchanged', block(task_bytes, '## 任务要求（PM）', '## 方案与决定（执行）') ==
          block(baseline_task, '## 任务要求（PM）', '## 方案与决定（执行）'))
    check('PM_acceptance_segment_unchanged', block(task_bytes, '## PM 验收与交接（PM）') ==
          block(baseline_task, '## PM 验收与交接（PM）'))
    protected = ['tests/fixtures', 'docs/architecture.md', 'docs/roadmap.md', 'docs/current-work.md',
        'docs/collaboration/rules.md', 'layauto_v2/domain/codec.py', 'layauto_v2/domain/publication_codec.py',
        'layauto_v2/normalization/codec.py', 'layauto_v2/normalization/geometry_codec.py',
        'layauto_v2/normalization/effective_codec.py', 'layauto_v2/normalization/local_connectivity_codec.py',
        'layauto_v2/normalization/channel_identity_codec.py']
    diff = subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', *protected], text=True)
    check('protected_baseline_paths_unchanged', diff == '', diff)
    m = read(TASK / 'verification-r2/source-manifest.json')
    files = m['files']
    actual = {name: sha((ROOT / name).read_bytes()) for name in files}
    snapshot = {name: sha((Path('/workspace/work/w013-final-r2/source') / name).read_bytes()) for name in files}
    sid = sha(json.dumps(actual, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())
    check('R2_273_current_source_and_snapshot_identity', len(files) == 273 and actual == files == snapshot and
          sid == m['source_id'] == '2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278', sid)
    old = read(ROOT / 'docs/tasks/W012/A1/verification-r2/source-manifest.json')['files']
    fixed_stdout = read(TASK / 'review-evidence/final-audit/fixed-input.stdout.json')
    fixed_manifest = read(TASK / 'review-evidence/final-audit/fixed-input-manifest.json')
    check('fixed_audit_tool_output_manifest_matches', all(sha((TASK / 'review-evidence/final-audit' / name).read_bytes()) == value
          for name, value in fixed_manifest.items()) and len(fixed_manifest) == 3, fixed_manifest)
    categories = dict(Counter(row['name'].split(':')[0] for row in fixed_stdout['checks']))
    check('137_check_classes_and_failures', len(fixed_stdout['checks']) == 137 and
        all(row['passed'] is True for row in fixed_stdout['checks']) and not fixed_stdout['failures'] and
        fixed_stdout['status'] == 'passed' and categories == {'original_A1_preflight_immutable': 1,
        'exact_35_fixed_input_paths': 1, 'normal_fixture_A1_and_R2_all_bytes': 1, 'fixed_file': 35,
        'capture_unique_count': 3, 'fixed_site_URI': 3, 'capture_source': 93}, categories)
    preflight = ROOT / 'docs/tasks/W012/A1/preflight.json'
    baseline_preflight = subprocess.check_output(['git', 'show', BASE + ':docs/tasks/W012/A1/preflight.json'])
    check('A1_preflight_current_equals_base_git_bytes', preflight.read_bytes() == baseline_preflight)
    original = {row['target']: row for row in json.loads(baseline_preflight)['inputs']}
    restore = {row['uri']: row for row in read(TASK / 'fixed-mismatch-restoration.json')['inputs']}
    fixed = Path('/workspace/w012-inputs/extraction-mismatch')
    actual_paths = {str(path) for path in fixed.rglob('*') if path.is_file()}
    check('35_exact_fixed_URIs', len(original) == 35 and set(original) == set(restore) == actual_paths)
    recorded = {row['uri']: row for row in fixed_stdout['fixed_files']}
    fixed_results = {}
    for uri, entry in original.items():
        data = Path(uri).read_bytes()
        origin = str(Path(entry['origin']).relative_to(ROOT))
        fixed_results[uri] = (sha(data) == entry['sha256'] == restore[uri]['sha256'] == old[origin] == files[origin]
            == recorded[uri]['actual_sha256'] == recorded[uri]['original_A1_sha256'] == recorded[uri]['restored_sha256'] and
            len(data) == entry['bytes'] == restore[uri]['bytes'] == recorded[uri]['bytes'])
    check('35_fixed_bytes_and_origin_mapping', len(recorded) == 35 and all(fixed_results.values()), fixed_results)
    fixture = {name: value for name, value in old.items() if name.startswith('tests/fixtures/')}
    check('116_fixture_full_A1_R2_current_snapshot_equal', len(fixture) == 116 and
          all(value == files[name] == actual[name] == snapshot[name] for name, value in fixture.items()))
    saved_captures = {(row['case'], row['relative_acquisition_uri']): row for row in fixed_stdout['capture_sources']}
    capture_results = {}
    case_sites = {}
    for case in ('normal-direct', 'normal-readback', 'extraction-mismatch'):
        resource_path = TASK / 'resource-attempt-04' / (case + '.json')
        resource = read(resource_path)
        root = fixed if case == 'extraction-mismatch' else ROOT / 'tests/fixtures/w003_m1'
        case_sites[case] = resource['input_site']
        check('original_resource_site_and_source_id:' + case, resource['input_site'] == str(root / 'site_config.yaml') and
            resource['source_id'] == '6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9')
        rows = resource['capture_sources']
        check('31_unique_saved_capture_URIs:' + case, len(rows) == len({row['uri'] for row in rows}) == 31)
        for row in rows:
            path = root / row['uri']
            saved = saved_captures[case, row['uri']]
            if case == 'extraction-mismatch':
                origin_sha = original[str(path)]['sha256']
            else:
                origin_sha = old[str(path.relative_to(ROOT))]
            data = path.read_bytes()
            capture_results[case + ':' + row['uri']] = (
                path.is_relative_to(root) and sha(data) == row['sha256'] == origin_sha == saved['actual_sha256'] == saved['captured_sha256'] and
                len(data) == row['bytes'] == saved['actual_bytes'] == saved['captured_bytes'] and
                saved['recorded_resource_sha256'] == sha(resource_path.read_bytes()))
    check('93_saved_resource_capture_bytes_and_fixed_scope', len(saved_captures) == len(capture_results) == 93 and
          all(capture_results.values()), capture_results)
    check('stdout_R2_identity_tag_matches_real_manifest', fixed_stdout['source_id_R2'] == sid)
    stop = read(TASK / 'verification/controlled-stop.json')
    failure = read(TASK / 'verification/failure.json')
    check('first_failed_matrix_preserved_not_relabelled', failure['status'] == 'failed' and
          'test_normalization_and_new_domain_keep_pure_dependency_boundaries' in stop['nodeid'] and
          all((TASK / ('verification/pytest-' + tag + '.stdout.txt')).exists() and
              (TASK / ('verification/pytest-' + tag + '.stderr.txt')).exists() for tag in ('310', '312')))
    neutral = TASK / 'review-evidence/neutral-static'
    old_manifest = read(neutral / 'manifest.json')
    readme_name = 'docs/tasks/W013/review-evidence/neutral-static/README.md'
    initial_readme = (neutral / 'README.md').read_bytes().split('\n## 后续 target 与分类闭合探针'.encode())[0]
    check('initial_neutral_README_bytes_recovered_exactly', sha(initial_readme) == old_manifest['evidence_files'][readme_name])
    with (OUT / 'neutral-static-README.initial.md').open('xb') as stream:
        stream.write(initial_readme)
    probe_hashes = {name: {'recorded': value, 'actual': sha((ROOT / name).read_bytes())}
                    for name, value in old_manifest['evidence_files'].items() if name != readme_name}
    check('all_original_neutral_probe_and_output_hashes_unchanged', all(row['recorded'] == row['actual'] for row in probe_hashes.values()), probe_hashes)
    correction = {'classification': 'immutable historical README reference correction only',
        'original_manifest': str((neutral / 'manifest.json').relative_to(ROOT)),
        'original_manifest_sha256': sha((neutral / 'manifest.json').read_bytes()),
        'original_recorded_path': readme_name, 'original_recorded_sha256': old_manifest['evidence_files'][readme_name],
        'recovered_initial_copy': str((OUT / 'neutral-static-README.initial.md').relative_to(ROOT)),
        'recovered_initial_sha256': sha(initial_readme),
        'current_appended_README_sha256': sha((neutral / 'README.md').read_bytes()),
        'original_probe_and_output_hashes': probe_hashes,
        'scope': 'Original manifest covers only its listed old-batch probe/output bytes and initial README; later target-classification additions have their own identity.json and are not retroactively covered.',
        'unchanged': 'No old manifest, README, raw probe/output, product, test, config, or frozen engineering tool was modified.'}
    (OUT / 'neutral-readme-reference-correction.json').write_text(json.dumps(correction, indent=2) + '\n')
    check('reviewed_doc_bytes_stayed_same_during_precheck', all((TASK / name).read_bytes() == value for name, value in reviewed_bytes.items()))
    status = {'receipt_exists': (TASK / 'verification-r2/receipt.json').exists(),
              'failure_exists': (TASK / 'verification-r2/failure.json').exists(),
              'installed_smoke_command_receipt_present': {tag: (TASK / ('verification-r2/installed-smoke-' + tag + '.json')).exists() for tag in ('310', '312')}}
    result = {'auditor': '/root/independent_review/neutral_static_audit', 'utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'final documentation/input identity precheck; not full engineering acceptance',
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'reviewed_files': {name: sha(data) for name, data in reviewed_bytes.items()},
        'task_document_sha256': sha(task_bytes), 'R2_source_id': sid,
        'fixed_audit_check_count': 137, 'fixed_input_files': 35, 'saved_capture_rows': 93, 'fixture_files': 116,
        'fixed_case_sites': case_sites, 'checks': checks,
        'failures': [row for row in checks if not row['passed']],
        'status': 'passed' if all(row['passed'] for row in checks) else 'failed',
        'final_matrix_artifact_presence_only': status,
        'not_run': ['product import', 'capture', 'performance measurement', 'pytest', 'typing', 'build', 'installation', 'smoke'],
        'limits': ['Document precheck does not replace primary review or final receipt validation.',
                   'Any historical pending text is assessed at its recorded stage; no pending smoke is counted as passed.']}
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['failures'] else 0)


if __name__ == '__main__':
    main()
