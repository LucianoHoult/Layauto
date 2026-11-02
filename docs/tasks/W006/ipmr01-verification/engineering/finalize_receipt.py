"""Finalize this engineering evidence after all recorded checks have completed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shlex

base = Path(__file__).resolve().parent
source_manifest = json.loads((base / 'source-manifest.json').read_text())
commit = source_manifest['product_commit']
source = Path(source_manifest['snapshot'])
for name, sha in source_manifest['files'].items():
    assert hashlib.sha256((source / name).read_bytes()).hexdigest() == sha, name
required = ('pytest310', 'pytest310-f1-retest', 'snapshot-completion', 'mypy310', 'build', 'artifact-verification', 'wheel-install',
            'wheel-normal-f2-smoke', 'wheel-ipmr01-smoke', 'wheel-pip-check',
            'pip-check310', 'environment310', 'wheel-environment')
commands = []
for path in sorted(base.glob('*.result.json')):
    value = json.loads(path.read_text())
    if path.name == 'pytest310.result.json':
        assert value['exit_code'] == 1
        original_log = (base / value['combined_output']).read_text()
        assert '1 failed, 120 passed' in original_log and 'FileNotFoundError' in original_log
        assert 'docs/tasks/W003/examples/records.json' in original_log
    else:
        assert value['exit_code'] == 0, path
    log = base / value['combined_output']
    assert hashlib.sha256(log.read_bytes()).hexdigest() == value['log_sha256'], path
    if value.get('product_commit') is not None:
        assert value['product_commit'] == commit, path
    commands.append({'result_file': path.name, **value})
for name in required:
    assert (base / (name + '.result.json')).is_file(), name
normal = json.loads((base / 'wheel-normal-f2-smoke.txt').read_text())
diagnostic = json.loads((base / 'wheel-ipmr01-smoke.txt').read_text())
artifacts = json.loads((base / 'artifact-identity.json').read_text())
receipt = {
    'date': '2026-11-02',
    'role': 'execution engineering verification (not independent review or PM acceptance)',
    'product_commit': commit,
    'snapshot': str(source),
    'initial_snapshot_files_checked_against_git': 216,
    'completed_snapshot_files_checked_against_git': source_manifest['file_count'],
    'snapshot_unchanged_after_run': True,
    'python310_scope': 'All W006 unit/contracts: pipeline, publication, boundaries, historical review regressions, and new IPMR-01 regressions; not the full W005 suite',
    'python310_result': '120 cases passed in the initial run; one F1 sample-dependency error. Restored the unchanged same-commit sample and reran that one case successfully. 121 distinct cases passed across the two runs, not a single 121-pass run.',
    'python310_initial_log': 'pytest310.txt',
    'python310_retest_log': 'pytest310-f1-retest.txt',
    'harness_correction': source_manifest['harness_correction'],
    'python310_typing': (base / 'mypy310.txt').read_text().strip(),
    'new_artifacts': artifacts,
    'clean_wheel_install': True,
    'wheel_runtime': json.loads((base / 'wheel-environment.txt').read_text()),
    'normal_f2_smoke': normal,
    'ipmr01_smoke': diagnostic,
    'commands': commands,
    'limits': [
        'Python3.12 full source suite and typing are recorded separately by the main execution agent.',
        'No Python3.10 clean-wheel installation, other interpreter/platform, real EDA or production validation.',
        'No fixture generation; accepted fixtures copied unchanged; F2 overlay applies existing bad raw/header only to a temporary copy.',
        'No Stage2-6, baseline/seal/no_change, durable or cross-process recovery claim.',
        'Local build artifacts and venvs are transient; committed logs/manifests identify the actual new bytes, not a promise those paths exist in another session.'
    ]
}
(base / 'engineering-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
(base / 'commands.txt').write_text('\n'.join('cwd=' + item['cwd'] + '\n' + shlex.join(item['command']) + '\nexit=' + str(item['exit_code']) + '\n' for item in commands))
files = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
         for path in sorted(base.iterdir()) if path.is_file() and path.name != 'engineering-evidence-manifest.json'}
(base / 'engineering-evidence-manifest.json').write_text(json.dumps({'product_commit': commit, 'files': files}, indent=2) + '\n')
print(json.dumps({'product_commit': commit, 'recorded_commands': len(commands),
                  'evidence_files': len(files), 'source_snapshot_files': source_manifest['file_count'],
                  'pytest310_result': receipt['python310_result'], 'artifacts': artifacts['artifacts']}, indent=2))
