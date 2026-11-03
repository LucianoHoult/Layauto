import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

print(json.dumps({
    'python': sys.version,
    'executable': sys.executable,
    'prefix': sys.prefix,
    'base_prefix': sys.base_prefix,
    'platform': platform.platform(),
    'source_root': str(Path.cwd()),
    'branch': git('branch', '--show-current'),
    'head': git('rev-parse', 'HEAD'),
    'tree': git('rev-parse', 'HEAD^{tree}'),
    'status': git('status', '--porcelain=v1'),
    'remotes': git('remote', '-v').splitlines(),
    'packages': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
}, indent=2, sort_keys=True))
