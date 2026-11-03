"""Execute the independent review probes and retain exact commands/raw outputs."""
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve()
python = Path(sys.argv[2]).absolute()  # preserve venv interpreter symlink
out = Path(__file__).resolve().parent
receipt = {"review_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
           "cwd": str(root), "environment": {"python": str(python), "host": platform.platform()}, "commands": []}
for name in ("geometry_probe", "unit_neutral_probe"):
    script = out / (name + ".py")
    log = out / (name.replace("_", "-") + ".txt")
    argv = [str(python), "-B", str(script), str(root)]
    start = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    with log.open("wb") as stream:
        result = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    receipt["commands"].append({"argv": argv, "started_utc": start, "seconds": time.monotonic() - tick,
                                "exit_code": result.returncode, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                                "output": log.name, "output_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
(out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
assert all(row["exit_code"] == 0 for row in receipt["commands"])
