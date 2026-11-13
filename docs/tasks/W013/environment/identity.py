"""Environment-only identity and dependency import check; no product import."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import sys

import build
import matplotlib
import mypy.version
import numpy
import pytest
import yaml


assert sys.version_info[:2] in ((3, 10), (3, 12))
assert Path(sys.prefix).parent == Path('/workspace/work/w013-env')
assert importlib.util.find_spec('layauto_v2') is None, 'Product must not be installed in setup environments'
try:
    importlib.metadata.version('layauto')
except importlib.metadata.PackageNotFoundError:
    pass
else:
    raise AssertionError('Product distribution unexpectedly installed')
executable = Path(sys.executable).resolve()
print(json.dumps({
    'executable': sys.executable, 'resolved_executable': str(executable),
    'resolved_executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
    'version': sys.version, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix,
    'platform': platform.platform(),
    'dependency_imports': {'numpy': numpy.__version__, 'matplotlib': matplotlib.__version__,
                           'yaml': yaml.__version__, 'pytest': pytest.__version__,
                           'mypy': mypy.version.__version__, 'build': build.__version__},
    'packages': {dist.metadata['Name']: dist.version for dist in importlib.metadata.distributions()},
    'layauto_product_installed': False,
}, indent=2))
