"""Read-only version and protected-path audit for the W010 premerge review."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
REFS = {'main': '3be0b98359038bab6c23980b55a48987cc71a369',
        'preparation': '9758a157115cc22d91ce095ac2002209b9f210d3',
        'product': '0f5029df935bc0acd106aad1bc2be81304d4f442',
        'delivery': 'ca39aedcb71fda02f77ffda1eb5d5dddc598226e',
        'head': 'c4909ab679d0c0806200fcb132db8a5de1ad3e75'}
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
result = {'refs': REFS, 'review_checkout': str(ROOT), 'actual_head': git('rev-parse','HEAD'),
          'original_checkout': '/workspace/Layauto',
          'original_status': subprocess.check_output(['git','status','--porcelain=v1','--branch'], cwd='/workspace/Layauto',text=True),
          'remote': git('remote','get-url','origin'), 'diffs': {}, 'runtime_sha256': {}}
assert result['actual_head'] == REFS['head']
for a,b in [('main','head'),('preparation','product'),('product','head'),('delivery','head')]:
    result['diffs'][a+'..'+b] = {'name_status':git('diff','--name-status',REFS[a],REFS[b]), 'stat':git('diff','--stat',REFS[a],REFS[b]), 'commits':git('log','--format=%H %s',REFS[a]+'..'+REFS[b])}
for p in sorted((ROOT/'layauto_v2').rglob('*.py')):
    result['runtime_sha256'][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
protected = ['tests/fixtures','tests/support','legacy_mvp','docs/architecture.md','docs/collaboration','docs/environment']
result['protected_diff'] = git('diff',REFS['main'],REFS['head'],'--',*protected)
assert result['protected_diff'] == ''
result['product_to_head_runtime_tests_config'] = git('diff',REFS['product'],REFS['head'],'--','layauto_v2','tests','pyproject.toml','README.md')
assert result['product_to_head_runtime_tests_config'] == ''
(OUT/'version-scope.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'head': result['actual_head'], 'protected_unchanged':True,'product_frozen':True,'runtime_python_files':len(result['runtime_sha256'])}))
