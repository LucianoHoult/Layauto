"""Audit the reviewed source scope and preserve its byte identity."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
base = 'cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa'
head = '73e38df8f932bbb5bd9caf074b442ad2f5c286e9'
observed_head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
subprocess.run(['git','merge-base','--is-ancestor',head,observed_head],check=True)
paths = subprocess.check_output(['git','diff','--name-only',base,head],text=True).splitlines()
runtime = [p for p in paths if p.startswith('layauto_v2/')]
tests = [p for p in paths if p.startswith('tests/')]
assert len(paths) == 11 and len(runtime) == 8 and len(tests) == 3
protected = ['tests/fixtures','legacy_mvp','docs/architecture.md','docs/current-work.md','docs/tasks/W009/independent-premerge-review.md','docs/tasks/W009/independent-premerge-review','docs/tasks/W009/verification','docs/tasks/W009/code-review.md','docs/tasks/W009/plan-review.md']
assert not subprocess.check_output(['git','diff','--name-only',base,head,'--',*protected],text=True)
manifest = {}
source_paths = subprocess.check_output(['git','ls-files','layauto_v2','tests/contracts','tests/unit','pyproject.toml'],text=True).splitlines()
for path in source_paths:
    if Path(path).is_file():
        raw = Path(path).read_bytes()
        assert raw == subprocess.check_output(['git','show',head+':'+path])
        manifest[path] = dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
out = dict(base=base,head=head,observed_head=observed_head,changed_paths=paths,runtime_count=len(runtime),test_count=len(tests),protected_paths=protected,protected_difference=[],source_file_count=len(manifest),sources=manifest)
Path('docs/tasks/W009/ipmr01-verification/review/version-scope.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(base=base,head=head,changed_paths=paths,source_file_count=len(manifest),protected_difference=[]),indent=2))
