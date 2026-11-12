"""Independent final engineering closure audit; no product or test execution."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path.cwd()
    evidence = root / 'docs/tasks/W013/verification-r2'
    stream = io.StringIO()
    precheck = root / 'docs/tasks/W013/review-evidence/code-static/final_r2_precheck.py'
    with redirect_stdout(stream):
        runpy.run_path(str(precheck), run_name='__main__')
    earlier = json.loads(stream.getvalue())
    receipt_path = evidence / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['status'] == 'passed' and receipt['source_id'] == earlier['source_id']
    assert receipt['actual_test_counts'] == {'310': 1731, '312': 1731}
    assert receipt['expected_test_count'] == 1731 and receipt['retained_baseline_test_count'] == 1656
    assert receipt['source_identity_rechecked_after_all_commands']
    assert receipt['source_file_count'] == 273 and receipt['runtime_file_count'] == 106
    for key, name in (('source_manifest_sha256','source-manifest.json'), ('source_snapshot_sha256','source-snapshot.tar.gz'),
                      ('baseline_collection_sha256','baseline-collection.txt')):
        assert receipt[key] == sha(evidence / name)
    assert not (evidence / 'failure.json').exists()
    manifest = json.loads((evidence / 'evidence-manifest.json').read_text())
    actual_files = {str(p.relative_to(evidence)) for p in evidence.rglob('*') if p.is_file() and p.name != 'evidence-manifest.json'}
    assert set(manifest) == actual_files and len(manifest) == 81
    assert all(sha(evidence / name) == digest for name, digest in manifest.items())
    assert len(receipt['commands']) == 21 and all(row['exit_code'] == 0 for row in receipt['commands'])
    commands = {}
    for row in receipt['commands']:
        for log in ('stdout','stderr'):
            assert sha(evidence / row[log]) == row[log + '_sha256']
        stem = row['stdout'].removesuffix('.stdout.txt')
        assert json.loads((evidence / (stem + '.json')).read_text()) == row
        commands[stem] = row
    latest_matrix = max(datetime.fromisoformat(row['finished_at_utc']) for key,row in commands.items()
                        if key.startswith(('environment-','collection-','pytest-','typing-','pip-check-')))
    assert datetime.fromisoformat(commands['build']['started_at_utc']) > latest_matrix
    assert datetime.fromisoformat(commands['create-install-312']['started_at_utc']) > datetime.fromisoformat(commands['installed-smoke-310']['finished_at_utc'])
    installed = json.loads((evidence / 'installation-identity.json').read_text())
    frozen = json.loads((evidence / 'source-manifest.json').read_text())
    packages = json.loads((evidence / 'package-identity.json').read_text())
    smoke_rows = {}
    for tag, artifact in (('310','sdist'),('312','wheel')):
        identity = installed[tag]
        expected_root = Path('/workspace/work/w013-final-r2/clean-' + tag)
        assert identity['fresh_environment'] and identity['isolated'] == 1
        assert Path(identity['package']).is_relative_to(expected_root)
        assert 'site-packages' in Path(identity['package']).parts
        assert identity['artifact_sha256'] == packages[artifact]['sha256']
        assert identity['runtime_files'] == frozen['runtime_files']
        actual_runtime = {str(p.relative_to(Path(identity['package']).parent)): sha(p)
                          for p in Path(identity['package']).parent.rglob('*')
                          if p.is_file() and (p.suffix == '.py' or p.name == 'py.typed')}
        assert actual_runtime == frozen['runtime_files']
        command = commands['installed-smoke-' + tag]
        assert command['command'][1:3] == ['-I','-B']
        cwd = Path(command['cwd'])
        assert not cwd.is_relative_to(root) and not cwd.is_relative_to(Path('/workspace/work/w013-final-r2/source'))
        body = json.loads((evidence / command['stdout']).read_text())
        assert body['package'] == identity['package']
        assert body['attempt_unchanged'] and body['checkpoint_unchanged'] and body['terminal_absent']
        assert set(body['cases']) == {'normal-direct','normal-readback','extraction-mismatch'}
        for case,row in body['cases'].items():
            assert row['public_roundtrip_equal']
            assert (row['targets'],row['evidence'],row['classifications'],row['components']) == (14,8,40,6)
            assert (row['associated_components'],row['unknown_components']) == (4,2)
            assert row['target_area_nm2'] == (34634 if case == 'extraction-mismatch' else 35090)
            assert row['direct_area_nm2'] == 3170 and row['uncovered_area_nm2'] == row['target_area_nm2']-3170
            assert row['marker_area_nm2'] == 25 and row['scope'] == 'source_evidence_local_net_annotation/1'
            assert row['validity'] == 'source_evidence'
        assert body['cases']['normal-direct']['public_result_digest_checked']
        smoke_rows[tag] = {'elapsed_seconds':command['elapsed_seconds'],'package':identity['package'],
                           'artifact':artifact,'stdout_sha256':command['stdout_sha256'],'cases':body['cases']}
    for case in ('normal-direct','normal-readback'):
        assert smoke_rows['310']['cases'][case]['wire_sha256'] == smoke_rows['312']['cases'][case]['wire_sha256']
    # The mismatch temporary URI differs by invocation and is explicitly not a
    # fixed-input performance/digest equivalence pair.
    correction = json.loads((root / 'docs/tasks/W013/review-evidence/final-doc-precheck/neutral-readme-reference-correction.json').read_text())
    assert sha(root / correction['original_manifest']) == correction['original_manifest_sha256']
    assert sha(root / correction['recovered_initial_copy']) == correction['original_recorded_sha256']
    assert sha(root / correction['original_recorded_path']) == correction['current_appended_README_sha256']
    assert all(sha(root/name)==row['recorded']==row['actual'] for name,row in correction['original_probe_and_output_hashes'].items())
    original_review = subprocess.check_output(['git','show','8dca80fee138b48f353f791a70d96765426c342a:docs/tasks/W013/code-review.md'])
    assert hashlib.sha256(original_review).hexdigest() == '995c852dbb913b8153b373603c56a18d49d2b5fd01e2c15fb82c545c004ff349'
    result={'classification':'independent-final-W013-engineering-closure-read-only-audit',
        'status':'passed','source_id':receipt['source_id'],'commands_verified':21,'evidence_manifest_entries_verified':81,
        'source_files_verified':273,'runtime_files_verified':106,'precheck_script_sha256':sha(precheck),
        'receipt_sha256':sha(receipt_path),'evidence_manifest_sha256':sha(evidence/'evidence-manifest.json'),
        'matrix_summary':earlier['matrices'],'package_artifacts':earlier['artifacts'],
        'smokes':smoke_rows,'build_and_installs_after_matrices':True,'smokes_serial':True,
        'all_reference_corrections_closed':True,'not_run':['pytest','typing','build','install','capture','resource measurement'],
        'scope':'Existing actual commands adopted by exact source/input/tool/package identity. This audit does not constitute PM acceptance or complete M1/real EDA assurance.'}
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
