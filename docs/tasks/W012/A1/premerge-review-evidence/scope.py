"""Pin main-to-delivery scope and this session's environment without heavy work."""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE = '0a3326aa363477724465886cd05874d0997fba3e'
HEAD = 'e4179dd42cc0de853df73bafd9140a363c8fa5be'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


refs = dict(line.split()[::-1] for line in git('ls-remote', 'origin',
    'refs/heads/main', 'refs/heads/codex/w012-compatible-hex-validation').splitlines())
assert refs == {'refs/heads/main': BASE, 'refs/heads/codex/w012-compatible-hex-validation': HEAD}
assert git('rev-parse', 'HEAD').strip() == HEAD
ancestry = [BASE, '7f7c1304bdafd941791421cef64864fb1616303c',
    'ca1f810c3c97376f71089d8b4054760ff198012f',
    'd9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec',
    '212554cdc402f6b86e92b8b81cd43752a01ff858',
    '44a91c472fdeba5bb4b8a6071c0580313336c379',
    'db07a16fb7cbbac030adae84a9eb88cc0c8aa650', HEAD]
for left, right in zip(ancestry, ancestry[1:]):
    subprocess.run(['git', 'merge-base', '--is-ancestor', left, right], cwd=ROOT, check=True)
changes = [dict(zip(('status', 'path'), line.split('\t'))) for line in git('diff', '--name-status', BASE, HEAD).splitlines()]
assert len(changes) == 595
assert [r['path'] for r in changes if r['path'].startswith('layauto_v2/')] == ['layauto_v2/domain/codec.py']
assert [r['path'] for r in changes if r['path'].startswith('tests/')] == ['tests/contracts/test_w012_hex_validation.py']
assert [str(p.relative_to(ROOT)) for p in ROOT.rglob('AGENTS.md')] == ['AGENTS.md']
rules = ['AGENTS.md', 'README.md', 'docs/README.md', 'docs/collaboration/rules.md',
    'docs/environment/local-setup.md', 'docs/environment/remote-development.md', 'docs/architecture.md']
result = {
    'base': BASE, 'head': HEAD, 'remote_refs_observed': refs,
    'worktree_list': git('worktree', 'list', '--porcelain'),
    'ancestry_verified': ancestry,
    'complete_main_to_head_changes': changes,
    'scope_counts': dict(Counter('runtime' if r['path'].startswith('layauto_v2/') else
        'tests' if r['path'].startswith('tests/') else 'docs' for r in changes)),
    'post_original_review_changes': git('diff', '--name-status', ancestry[5], HEAD).splitlines(),
    'applicable_agents': ['AGENTS.md'],
    'normative_file_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in rules},
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
    'distributions': {d.metadata['Name']: d.version for d in metadata.distributions()},
    'current_process_memory': subprocess.check_output(['ps', '-eo', 'pid,rss,comm', '--sort=-rss'], text=True).splitlines()[:12],
    'memory_info': Path('/proc/meminfo').read_text(),
    'note': 'New risk-selected tests use the current 3.12 environment; no claim that it reproduces the historical benchmark machine/dependency timing.',
}
(OUT / 'scope.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'scope_counts': result['scope_counts'], 'remote_refs': refs}, indent=2))
