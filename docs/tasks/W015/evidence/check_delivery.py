"""Document/identity handoff checks only; no product test matrix."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'docs/tasks/W015-single-cell-analysis-entry.md'
HERE = ROOT / 'docs/tasks/W015'
BASE = 'e7c92c03d0b48aa143259da4fc9fbedc382efee0'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)

base_task = git('show', BASE + ':docs/tasks/W015-single-cell-analysis-entry.md')
current_task = TASK.read_text()
# Respect PM ownership: no modifications to requirements/phase or PM section.
assert base_task.split('## 方案与决定')[0] == current_task.split('## 方案与决定')[0]
assert base_task.split('## PM验收与交接（PM）')[1] == current_task.split('## PM验收与交接（PM）')[1]
paths = set(git('diff', '--name-only', BASE).splitlines())
paths |= set(git('ls-files', '--others', '--exclude-standard').splitlines())
assert all(p == 'docs/tasks/W015-single-cell-analysis-entry.md' or p.startswith('docs/tasks/W015/') for p in paths), paths
assert not git('diff', '--name-only', '3b8d78902591bca32ec9b8ee5d3167d115e1a974', '--', 'layauto_v2', 'tests', 'pyproject.toml').strip()
identity = json.loads((HERE / 'evidence/source-identity.json').read_text())
for row in identity['files']:
    assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']

links = 0
for p in [TASK, *HERE.rglob('*.md')]:
    outside_fences = re.sub(r'```.*?```', '', p.read_text(), flags=re.S)
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', outside_fences):
        if target.startswith(('http:', 'https:', '#')):
            continue
        target = target.split('#')[0]
        assert (p.parent / target).exists(), (str(p.relative_to(ROOT)), target)
        links += 1
json_count = 0
for p in HERE.rglob('*.json'):
    if not p.stat().st_size:  # stdout artifacts for preserved failed commands
        continue
    json.loads(p.read_text())
    json_count += 1
print(json.dumps({'check': 'documentation/source identity only',
                  'head': git('rev-parse', 'HEAD').strip(),
                  'checked_source_test_config_files': len(identity['files']),
                  'checked_local_markdown_links': links, 'parsed_json_artifacts': json_count,
                  'changed_paths_within_scope': len(paths), 'pm_sections_unchanged': True,
                  'product_diff_from_main': [], 'status': 'passed'}, ensure_ascii=False, indent=2))
