"""Validate and identify this review's artifacts without rewriting prior evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
TASK = 'docs/tasks/W012-capture-wire-performance.md'
REPORT = 'docs/tasks/W012/A1/independent-premerge-review.md'
HEAD = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert git('rev-parse', 'HEAD').strip() == HEAD
assert git('diff', '--name-only', '--diff-filter=MDR', 'HEAD').splitlines() == [TASK]
for name in git('ls-files', '--others', '--exclude-standard').splitlines():
    assert name == REPORT or name.startswith(str(OUT.relative_to(ROOT)) + '/')
commands = {}
for path in OUT.glob('*.command.json'):
    record = json.loads(path.read_text())
    name = path.name.removesuffix('.command.json')
    for stream in ('stdout', 'stderr'):
        assert sha(OUT / (name + '.' + stream + '.txt')) == record[stream + '_sha256'], name
    commands[name] = record['exit_code']
assert commands['independent-probe'] == commands['independent-probe-r2'] == 1
assert commands['independent-probe-r3'] == commands['targeted-formal'] == commands['affected-formal'] == 0
assert commands['affected-collection'] == commands['scope'] == commands['current-environment'] == 0
assert commands['reviewed-diff-check'] == 2
assert commands['new-diff-check'] == 0
assert (OUT / 'targeted-formal.stdout.txt').read_text().strip().endswith('89 passed in 0.50s')
assert '22 passed in ' in (OUT / 'affected-formal.stdout.txt').read_text()
assert json.loads((OUT / 'contracts/result.json').read_text())['checks_by_kind']['candidates'] == 150728
assert (OUT / 'contracts/probe-attempt01.py.txt').is_file()
assert (OUT / 'contracts/probe-attempt02.py.txt').is_file()
bad_links = []
for path in [ROOT / REPORT, *OUT.rglob('*.md')]:
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text()):
        if '://' in link or link.startswith('#'):
            continue
        target = link.split('#', 1)[0]
        if target and not (path.parent / target).exists():
            bad_links.append((str(path.relative_to(ROOT)), link))
assert not bad_links, bad_links
excluded = {'files-manifest.json', 'seal-result.json', 'seal.stdout.txt', 'seal.stderr.txt', 'seal.command.json'}
paths = [ROOT / REPORT, ROOT / TASK, *(p for p in OUT.rglob('*') if p.is_file() and p.name not in excluded)]
manifest = {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
(OUT / 'files-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
result = {
    'status': 'passed', 'reviewed_head': HEAD, 'new_formal_passed': 111,
    'finite_candidates': 150728, 'new_mandatory_findings': 0, 'remaining_mandatory_findings': 0,
    'root_command_exit_codes': commands, 'manifest_files': len(manifest),
    'manifest_sha256': sha(OUT / 'files-manifest.json'), 'broken_local_links': bad_links,
    'probe_source_snapshots': {label: sha(OUT / 'contracts' / source) for label, source in (
        ('independent-probe', 'probe-attempt01.py.txt'),
        ('independent-probe-r2', 'probe-attempt02.py.txt'), ('independent-probe-r3', 'probe.py'))},
    'scope_note': 'Only the reviewer addition to W012, the new report and independent review evidence; no source/formal-test/history/PM/current-work edits.',
    'self_identity_note': 'Manifest excludes the manifest, its result and still-open capture streams to avoid circular hashes; Git identifies final delivery.',
}
(OUT / 'seal-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
