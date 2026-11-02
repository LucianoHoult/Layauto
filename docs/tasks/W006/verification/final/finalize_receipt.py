from pathlib import Path
import datetime
import hashlib
import json
import re

base = Path(__file__).parent
commit = 'cc42ae62585755b0b914d4dbec43324941bfe7c6'
pytest_summary = re.search(r'\d+ passed in [^\n]+', (base / 'pytest-310.txt').read_text())
assert pytest_summary is not None
assert pytest_summary.group().startswith('389 passed '), pytest_summary.group()
fixture = base / 'source/tests/fixtures/w003_m1'
files = {str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(fixture.rglob('*')) if p.is_file()}
(base / 'fixture-snapshot-manifest.json').write_text(json.dumps({
    'commit': commit, 'root': 'tests/fixtures/w003_m1', 'files': files,
}, indent=2) + '\n')
checks = {p.name.removesuffix('.result.json'): json.loads(p.read_text())
          for p in sorted(base.glob('*.result.json'))}
assert all(x['returncode'] == 0 for x in checks.values()), checks
receipt = {
    'iteration': 'Final engineering matrix after CR01/CR02 corrections',
    'tested_commit': commit,
    'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'role': 'engineering verification only; not independent code review or PM acceptance',
    'results': {
        'python310_pytest': pytest_summary.group(),
        'python310_mypy': (base / 'mypy-310.txt').read_text().strip(),
        'build': 'sdist and wheel built in isolated environment; wheel built from sdist',
        'wheel_python312_install': 'passed in newly created venv',
        'wheel_source_outside_smoke': json.loads((base / 'wheel-smoke.txt').read_text()),
        'pip_check_310': (base / 'pip-check-310.txt').read_text().strip(),
        'pip_check_wheel312': (base / 'wheel-pip-check.txt').read_text().strip(),
    },
    'commands_and_exit_codes': checks,
    'artifacts': json.loads((base / 'build-artifact-identity.json').read_text()),
    'environments': {
        'python310': json.loads((base / 'environment310.txt').read_text()),
        'wheel_python312': json.loads((base / 'environment-wheel312.txt').read_text()),
    },
    'notes': [
        'Source suite/typing, build source, fixture and wheel smoke script were exported from this exact commit; no mutable main-tree inputs were used.',
        '3.10 python -m pytest/mypy used snapshot working directory; environment310.txt verifies import from that snapshot.',
        'All 74 package source files and py.typed in wheel/sdist match exact commit-derived source; verify_artifacts.py is retained.',
        'Clean wheel smoke verifies site-packages import, 27 request declarations, inputs_ready/unsealed, idempotent replay, codec roundtrip and readback, actual F2 MissingTerminator failure/hash and terminal reject.',
        'R1 36161ca and cancelled 3a59774 preparation are separate historical evidence and were not substituted for final checks.',
    ],
    'not_executed': [
        'No Python3.10 clean wheel installation smoke: source suite/typing verified on 3.10; clean wheel install/smoke on 3.12.',
        'No CI service execution, legacy suite, Stage2 normalization/baseline/no_change, Stage5 mutations, Stage6 export/report, real EDA/PDK/production upload, durability or cross-process recovery.',
        'No final independent review conclusion or PM acceptance; review and parent Python3.12 source suite are reported by their owners.',
    ],
    'fixture_files': len(files),
}
(base / 'engineering-receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
owned = [
    'commands.txt', 'run_check.py', 'environment_probe.py', 'verify_artifacts.py',
    'finalize_receipt.py', 'tested-source-manifest.json', 'build-artifact-identity.json',
    'fixture-snapshot-manifest.json', 'engineering-receipt.json',
]
owned += [p.name for p in base.glob('*.result.json')]
owned += [p.name.removesuffix('.result.json') + '.txt' for p in base.glob('*.result.json')]
manifest = {p: hashlib.sha256((base / p).read_bytes()).hexdigest() for p in sorted(set(owned))}
(base / 'engineering-evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'commit': commit, 'pytest': pytest_summary.group(),
                  'receipt': str(base / 'engineering-receipt.json'),
                  'checks': {k: v['returncode'] for k, v in checks.items()},
                  'fixture_files': len(files), 'evidence_files': len(manifest)}, indent=2))
