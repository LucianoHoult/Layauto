"""Read-only W010 premerge handoff identity and resource-summary audit."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tarfile

ROOT = Path('/workspace/Layauto')
HEAD = 'f99b59abc88305133661dd2a510fbcaf36a9c6c6'
REVIEWED = 'c4909ab679d0c0806200fcb132db8a5de1ad3e75'
PRODUCT = '0f5029df935bc0acd106aad1bc2be81304d4f442'
DIR = 'docs/tasks/W010/'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def blob(path, revision=HEAD):
    return git('show', revision + ':' + path)


def read(path):
    return json.loads(blob(path))


def sha(data):
    return hashlib.sha256(data).hexdigest()


changes = [line.split('\t', 1) for line in git('diff', '--name-status', REVIEWED, HEAD).decode().splitlines()]
task_path = 'docs/tasks/W010-local-contact-connectivity.md'
assert all((state == 'M' and path == task_path) or
           (state == 'A' and (path == DIR + 'independent-premerge-review.md' or
                            path.startswith(DIR + 'independent-premerge-review/')))
           for state, path in changes)
old = blob(task_path, REVIEWED).decode()
new = blob(task_path).decode()
old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
review_start = next(i for i,line in enumerate(old_lines) if line.startswith('## Review结论（reviewer）'))
pm_start = next(i for i,line in enumerate(old_lines) if line.startswith('## PM验收与交接（PM）'))
insertions = []
for tag, i, j, k, l in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
    if tag == 'equal':
        continue
    assert tag == 'insert' and review_start <= i <= pm_start, (tag, i, j)
    insertions.append(''.join(new_lines[k:l]))
assert len(insertions) == 1 and '### R2 独立合并前复核' in insertions[0]

manifest_path = DIR + 'verification/source-manifest.json'
manifest = read(manifest_path)
assert len(manifest['files']) == 252 and len(manifest['runtime_files']) == 94
assert sha(blob(manifest_path)) == 'cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889'
for path, expected in manifest['files'].items():
    assert sha(blob(path, PRODUCT)) == expected, ('product', path)
    assert sha(blob(path, REVIEWED)) == expected, ('reviewed', path)
    assert sha(blob(path)) == expected, ('handoff', path)
    assert sha((ROOT / path).read_bytes()) == expected, ('current', path)
with tarfile.open(ROOT / (DIR + 'verification/source-snapshot.tar.gz')) as archive:
    entries = [m for m in archive.getmembers() if m.isfile()]
    assert len(entries) == len({m.name for m in entries}) == 252
    assert {m.name: sha(archive.extractfile(m).read()) for m in entries} == manifest['files']

validation = DIR + 'independent-premerge-review/validation/'
command_checks = {}
for name in ('pytest', 'typing'):
    receipt = read(validation + name + '.json')
    assert receipt['head'] == receipt['finished_head'] == REVIEWED
    assert receipt['returncode'] == 0
    for output in receipt['outputs'].values():
        assert sha(blob(validation + output['path'])) == output['sha256']
    command_checks[name] = {'head': receipt['head'], 'returncode': receipt['returncode'],
                           'command': receipt['command'], 'elapsed_seconds': receipt['elapsed_seconds'],
                           'outputs': receipt['outputs']}
pytest_output = blob(validation + 'pytest.stdout.txt').decode()
assert re.search(r'1465 passed in [\d.]+s', pytest_output)
assert 'failed' not in pytest_output and 'skipped' not in pytest_output and 'deselected' not in pytest_output
assert 'Success: no issues found in 48 source files' in blob(validation + 'typing.stdout.txt').decode()

review_dir = DIR + 'independent-premerge-review/'
source = read(review_dir + 'source-receipt.json')
assert source['head'] == REVIEWED and source['exit_code'] == 0
assert sha(blob(review_dir + 'source-probe.py')) == source['script_sha256']
for name, expected in source['outputs'].items():
    assert sha(blob(review_dir + name)) == expected
source_output = read(review_dir + 'source-probe.stdout.json')
assert source_output['status'] == 'pass' and source_output['wire_bytes'] == 59422834
geometry = read(review_dir + 'geometry-receipt.json')
assert geometry['head'] == REVIEWED and geometry['remaining_must_fix'] == 0
for name, expected in geometry['files_sha256'].items():
    assert sha(blob(review_dir + name)) == expected
for path, expected in geometry['product_sha256'].items():
    assert manifest['files'][path] == expected
exception = read(review_dir + 'exception-command.json')
assert exception['head'] == REVIEWED and exception['exit_code'] == 0
assert sha(blob(review_dir + 'exception-probe.py')) == exception['script_sha256']
assert sha(blob(review_dir + 'exception-stdout.txt')) == exception['stdout_sha256']
assert sha(blob(review_dir + 'exception-stderr.txt')) == exception['stderr_sha256']
audit = read(review_dir + 'evidence-audit-run.json')
assert audit['exit_code'] == 0
assert sha(blob(review_dir + 'evidence-audit.py')) == audit['script_sha256']
historical_checks = read(review_dir + 'evidence-result.json')
assert historical_checks['status'] == 'pass' and len(historical_checks['checks']) == 45
assert all(row['pass'] for row in historical_checks['checks'])

perf = read(DIR + 'performance.json')
assert perf['status'] == 'pass' and len(perf['cases']) == 4
for path, expected in perf['source_files_sha256'].items():
    assert manifest['files'][path] == expected
cases = [{'case': row['case'], 'result_wire_bytes': row['result_wire_bytes'],
          'max_pieces_per_region': row['counts']['max_pieces_per_region'],
          'process_peak_rss_kib_cumulative': row['process_peak_rss_kib_cumulative']}
         for row in perf['cases']]
assert min(row['result_wire_bytes'] for row in cases) == 12579736
assert max(row['result_wire_bytes'] for row in cases) == 17086974
result = {
    'status': 'passed', 'must_fix': 0,
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python': sys.version, 'head_observed_at_completion': git('rev-parse', 'HEAD').decode().strip(),
    'pinned_handoff': HEAD, 'reviewed_head': REVIEWED, 'product': PRODUCT,
    'diff_files': len(changes), 'diff_limited_to_review_materials_and_reviewer_append': True,
    'source_files': 252, 'runtime_files': 94, 'source_archive_matches': True,
    'command_checks': command_checks, 'original_review_evidence_checks': 45,
    'p3': {'id': 'E-N01', 'blocking': False, 'direct_uncached_cases': cases,
           'wire_min_bytes': 12579736, 'wire_max_bytes': 17086974,
           'correct_decimal_MB_summary': '12.58–17.09 MB',
           'peak_cumulative_rss_MiB': max(row['process_peak_rss_kib_cumulative'] for row in cases)/1024,
           'supplemental_readback_wire_bytes': 59422834,
           'note': 'Readback carries a different retained chain, not the same identity as direct; no production upper bound.'},
    'limitations': ['Read-only current/Git/archive and archived command-output identity audit.',
                    'No pytest, typing, build, installation or performance command was rerun.',
                    'Historical commands remain adopted reviewer execution evidence, not newly observed executions.'],
}
print(json.dumps(result, indent=2, ensure_ascii=False))
