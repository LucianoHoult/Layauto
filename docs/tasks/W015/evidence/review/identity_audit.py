"""Bounded immutable product/source and review scope audit."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[5]
BASE = 'e7c92c03d0b48aa143259da4fc9fbedc382efee0'
PRODUCT = '3b8d78902591bca32ec9b8ee5d3167d115e1a974'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def sha(data):
    return hashlib.sha256(data).hexdigest()

identity = json.loads((ROOT / 'docs/tasks/W015/evidence/source-identity.json').read_text())
for row in identity['files']:
    actual = (ROOT / row['path']).read_bytes()
    assert sha(actual) == row['sha256'], row['path']
    assert actual == git('show', f'{PRODUCT}:{row["path"]}'), row['path']
assert not git('diff', '--name-only', PRODUCT, '--', 'layauto_v2', 'tests', 'pyproject.toml').strip()
reader = (ROOT / 'layauto_v2/importers/reader.py').read_text()
assert reader.index("body_file = yield from files.read") < reader.index('gds = parse_gds')
assert reader.index("record('gds'") < reader.index('_body(body,') < reader.index('query = parse_query')
geometry = (ROOT / 'layauto_v2/normalization/geometry_input.py').read_text()
assert "body_source = capture('body', 0, 2)" in geometry
assert "records['body'].sources[1] != records['gds'].sources[0]" in geometry
net = (ROOT / 'layauto_v2/domain/net_annotation.py').read_text()
assert "{'schema', 'normalization_input_sha256', 'sources', 'readback'}" in net
body = (ROOT / 'layauto_v2/derive/body_relations.py').read_text()
assert "annotation.binding.capture_binding['sources']" in body
assert "body.sources[1] != layout.gds.sources[0]" in body
# Direct AST confirms W009 checks encode only, W010 checks roundtrip.
effective = ast.parse((ROOT / 'layauto_v2/normalization/effective.py').read_text())
check = next(node for node in effective.body if isinstance(node, ast.FunctionDef) and node.name == '_require_input')
assert any(isinstance(node, ast.Attribute) and node.attr == 'encode_record' for node in ast.walk(check))
assert not any(isinstance(node, ast.Attribute) and node.attr == 'decode_record' for node in ast.walk(check))
protected = ['docs/architecture.md','docs/collaboration/rules.md','docs/current-work.md','docs/roadmap.md']
assert not git('diff','--name-only',BASE,'--',*protected).strip()
task = 'docs/tasks/W015-single-cell-analysis-entry.md'
original = git('show', f'{BASE}:{task}').decode()
current = (ROOT / task).read_text()
assert original.split('## 方案与决定')[0] == current.split('## 方案与决定')[0]
assert original.split('## PM验收与交接')[1] == current.split('## PM验收与交接')[1]
reviewed = []
for path in sorted((ROOT / 'docs/tasks/W015').glob('*.md')):
    if path.name != 'independent-review.md':
        reviewed.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())})
for path in sorted((ROOT / 'docs/tasks/W015/evidence/candidate-input').glob('*.json')):
    reviewed.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes())})
print(json.dumps({'python':sys.version,'head':git('rev-parse','HEAD').decode().strip(),
                  'product_main':PRODUCT,'base':BASE,'unchanged_product_file_count':len(identity['files']),
                  'reader_body_precedes_gds_parse':True,'strict_geometry_body_roles':True,
                  'strict_old_annotation_normalization_binding':True,'body_requires_annotation_capture':True,
                  'w009_encode_without_decode_confirmed':True,'protected_owner_sections_unchanged':True,
                  'reviewed_worktree_files':reviewed},indent=2))
