"""Check active task links and the exact historical README at its original base."""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re

root = Path.cwd()
task = root / 'docs/tasks/W013'
correction = json.loads((task / 'review-evidence/final-doc-precheck/neutral-readme-reference-correction.json').read_text())
archive = root / correction['recovered_initial_copy']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == correction['original_recorded_sha256']
origin = root / correction['original_recorded_path']
assert origin.is_file()
paths = [root / 'docs/tasks/W013-net-annotation-coverage.md', *sorted(task.rglob('*.md'))]
naive_missing = []
resolved_missing = []
count = 0
for path in paths:
    for match in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        target = match.strip('<>').split('#', 1)[0]
        if not target or re.match(r'^[a-z]+:', target):
            continue
        count += 1
        row = {'file': str(path.relative_to(root)), 'target': match}
        if not (path.parent / unquote(target)).exists():
            naive_missing.append(row)
        base = origin.parent if path == archive else path.parent
        if not (base / unquote(target)).exists():
            resolved_missing.append(row)
print(json.dumps({'markdown_files': len(paths), 'local_links_checked': count,
    'initial_naive_check_failure_preserved': naive_missing,
    'historical_snapshot': str(archive.relative_to(root)),
    'historical_snapshot_sha256': correction['original_recorded_sha256'],
    'historical_link_base': str(origin.parent.relative_to(root)),
    'basis': 'Byte-exact historical README is evidence, not a relocated active document. Its relative links retain the original recorded parent; all active links use their actual parent. No raw evidence bytes are edited or probes duplicated.',
    'resolved_missing': resolved_missing}, indent=2))
assert naive_missing and all(row['file'] == str(archive.relative_to(root)) for row in naive_missing)
assert not resolved_missing
