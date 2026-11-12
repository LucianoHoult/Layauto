"""Read-only independent audit of retained W013 resource04 receipts and input bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_id(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def main():
    root = Path.cwd()
    evidence = root / 'docs/tasks/W013/resource-attempt-04'
    suite = json.loads((evidence / 'suite.json').read_text())
    before = json.loads((root / 'docs/tasks/W013/review-evidence/code-static/postfix-source-identity.json').read_text())
    targeted = json.loads((root / 'docs/tasks/W013/development/targeted-attempt-01.command.json').read_text())
    baseline = json.loads((root / 'docs/tasks/W013/resource-attempt-01/w010-reference-normal-direct.json').read_text())
    old_sources = json.loads((root / 'docs/tasks/W012/A1/verification-r2/source-manifest.json').read_text())['files']
    fixed = json.loads((root / 'docs/tasks/W012/A1/preflight.json').read_text())['inputs']
    assert len(fixed) == 35
    assert all(sha(Path(row['target'])) == row['sha256'] for row in fixed)
    rows = []
    common_files = None
    expected_counts = {'W013_build': 1, 'W013_result_encode': 1, 'W013_result_decode': 2}
    for command in suite['commands']:
        assert command['returncode'] == 0
        args = command['argv']
        case = args[args.index('--case') + 1]
        report = json.loads((evidence / (case + '.json')).read_text())
        original = json.loads((root / 'docs/tasks/W013/resource-attempt-03' / (case + '.json')).read_text())
        assert report['source_id'] == suite['source_id'] == source_id(report['files'])
        assert report['files'] == before['files']
        assert common_files is None or report['files'] == common_files
        common_files = report['files']
        assert all(sha(root / name) == digest for name, digest in report['files'].items())
        assert report['probe_sha256'] == command['probe_sha256'] == sha(evidence / 'resource-probe.py')
        assert sha(evidence / (case + '.stdout.txt')) == command['stdout_sha256']
        assert sha(evidence / (case + '.stderr.txt')) == command['stderr_sha256']
        assert report['wire_sha256'] == original['wire_sha256']
        assert report['retained_W010_wire_sha256'] == original['retained_W010_wire_sha256']
        assert report['public_roundtrip_equal'] and report['W011_result_instances'] == 0
        assert report['wire_input_field_occurrences'] == 1
        assert report['gc_enabled'] and report['gc_threshold'] == [700, 10, 10]
        assert report['local_counts'] == {'nodes': 14, 'edges': 8, 'components': 6}
        if case == 'normal-direct':
            assert report['retained_W010_wire_sha256'] == baseline['wire_sha256']
        if case == 'normal-readback':
            assert report['readback_unsealed_checkpoint_unchanged_no_terminal']
        site = Path(report['input_site'])
        for source in report['capture_sources']:
            path = Path(source['uri'])
            if not path.is_absolute():
                path = site.parent / path
            assert sha(path) == source['sha256'] and path.stat().st_size == source['bytes']
        calls = report['observed_existing_calls']
        counts = {phase: sum(row['call'] == 'W010_public_decode' and row['phase'] == phase for row in calls)
                  for phase in expected_counts}
        assert counts == expected_counts
        buckets = {name: sum(row['inclusive_seconds'] for row in calls if row['call'] == name and row['phase'].startswith('W013'))
                   for name in ('W010_public_decode', 'W013_neutral_draft_build', 'W013_full_input_requirement',
                                'W013_capture_binding_digest', 'W007_source_normalization')}
        rows.append({'case': case, 'wire_bytes': report['wire_bytes'],
            'inner_W010_bytes': report['retained_W010_wire_bytes'],
            'added_wire_bytes': report['wire_bytes'] - report['retained_W010_wire_bytes'],
            'peak_kib': report['process_peak_rss_kib_before_postmeasurement_analysis'],
            'new_phase_seconds': sum(row['seconds'] for key, row in report['phases'].items() if key.startswith('W013')),
            'W010_public_decode_counts': counts, 'inclusive_call_buckets_do_not_add': buckets,
            'wire_sha_matches_original_resource03': True, 'actual_capture_bytes_verified': len(report['capture_sources'])})
    assert targeted['source_id_before'] == targeted['source_id_after'] == suite['source_id']
    assert targeted['returncode'] == 0 and targeted['source_unchanged']
    stdout = targeted['logs']['stdout']
    assert sha(Path(stdout['path'])) == stdout['sha256']
    assert '110 passed' in Path(stdout['path']).read_text()
    protected = [name for name in old_sources if name.startswith('tests/fixtures/w003_m1/')]
    assert all(sha(root / name) == old_sources[name] for name in protected)
    print(json.dumps({'classification': 'independent-resource-node-identity-audit-not-final-matrix',
        'python': sys.version, 'source_id': suite['source_id'], 'file_count': len(common_files),
        'source_and_tests_equal_postfix_review': True, 'targeted_110_passed_same_source': True,
        'all_accepted_fixture_hashes_unchanged': len(protected), 'fixed_mismatch_input_count': len(fixed),
        'cases': rows, 'evidence_files': {str(path.relative_to(evidence)): sha(path) for path in sorted(evidence.glob('*')) if path.is_file()},
        'not_run': ['product build/encode/decode', 'resource measurement', 'full regression'],
        'limits': 'Audit adopts retained actual measurements by exact identity. Inclusive nested timer buckets cannot be summed as independent costs; parallel test scheduling is not a performance improvement claim.'}, indent=2))


if __name__ == '__main__':
    main()
