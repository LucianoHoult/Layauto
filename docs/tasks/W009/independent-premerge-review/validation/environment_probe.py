"""Observe the command environment with the recorded task PYTHONPATH."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import layauto_v2

print(json.dumps(dict(
    command=[sys.executable, "-B", *sys.argv], cwd=str(Path.cwd()),
    head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    python=sys.version, platform=platform.platform(),
    imported_package=layauto_v2.__file__,
    packages={name:importlib.metadata.version(name) for name in ("pytest", "mypy", "types-PyYAML", "PyYAML")},
    selected_environment={name:os.environ.get(name) for name in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "XDG_CACHE_HOME", "MPLCONFIGDIR", "MPLBACKEND")},
    note="The pytest wrapper began without the task dependency path in its own sys.path, so its mypy/stub metadata is null. Its child command used the PYTHONPATH override recorded in pytest.json. This probe observes that same command path explicitly; it is not a new test or clean-install run."
), indent=2))
