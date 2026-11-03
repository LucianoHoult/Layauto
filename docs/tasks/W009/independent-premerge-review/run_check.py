"""Run a premerge check with preserved output and version identity."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "validation"
OUT.mkdir(parents=True, exist_ok=True)
kind = sys.argv[1]
commands = {
    "pytest": [sys.executable, "-B", "-m", "pytest", "tests/unit", "tests/contracts", "-q", "-p", "no:cacheprovider"],
    "typing": [sys.executable, "-B", "-m", "mypy", "--cache-dir", "/workspace/work/w009-premerge-cache/mypy"],
    "pip-check": [sys.executable, "-B", "-m", "pip", "check"],
}
env = dict(os.environ)
env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT) + os.pathsep + "/workspace/work/w009-premerge-deps", XDG_CACHE_HOME="/workspace/work/w009-premerge-cache", MPLCONFIGDIR="/workspace/work/w009-premerge-cache/mpl", MPLBACKEND="Agg")
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
t0 = time.monotonic()
with (OUT / f"{kind}.stdout.txt").open("wb") as stdout, (OUT / f"{kind}.stderr.txt").open("wb") as stderr:
    result = subprocess.run(commands[kind], cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
receipt = dict(command=commands[kind], cwd=str(ROOT), head=before, finished_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), started_utc=started, elapsed_seconds=round(time.monotonic()-t0, 3), returncode=result.returncode, python=sys.version, executable=sys.executable, platform=platform.platform(), environment_scope="existing cloud development venv; mypy and stubs in isolated task target; not a clean install", env_overrides={k: env[k] for k in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "XDG_CACHE_HOME", "MPLCONFIGDIR", "MPLBACKEND")}, packages={}, outputs={})
for package in ("pytest", "mypy", "PyYAML", "types-PyYAML"):
    try:
        receipt["packages"][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        receipt["packages"][package] = None
for stream in ("stdout", "stderr"):
    path = OUT / f"{kind}.{stream}.txt"
    receipt["outputs"][stream] = dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(OUT / f"{kind}.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
raise SystemExit(result.returncode)
