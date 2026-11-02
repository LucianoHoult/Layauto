"""Print interpreter and package locations without exposing process secrets."""
import importlib.metadata
import json
import platform
import sys
import layauto_v2
print(json.dumps({'python': sys.version, 'executable': sys.executable,
                  'prefix': sys.prefix, 'platform': platform.platform(),
                  'module': layauto_v2.__file__,
                  'versions': {name: importlib.metadata.version(name)
                               for name in ('layauto', 'PyYAML', 'numpy', 'matplotlib')}}, indent=2))
