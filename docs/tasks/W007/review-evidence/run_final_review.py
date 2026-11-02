"""Run the independent W007 review checks and save their exact local receipt."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
DEST = Path(__file__).resolve().parent
MANIFEST = ROOT / "docs/tasks/W007/verification/source-manifest.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads(MANIFEST.read_text())
assert all(digest(ROOT / name) == expected for name, expected in manifest["files"].items())
probe_directory = DEST / "final-probes"
probe_directory.mkdir(exist_ok=True)
adaptations = []
for script in ("probe", "relabel", "readback", "whitespace", "seed_capture", "seed_capture_metadata"):
    source = DEST / f"{script}.py"
    adapted = probe_directory / source.name
    text = source.read_text().replace("Path(__file__).resolve().parents[4]", "Path(__file__).resolve().parents[5]")
    text = text.replace("layauto_v2.domain.normalization_codec", "layauto_v2.normalization.codec")
    text = text.replace("layauto_v2.domain.normalization", "layauto_v2.normalization.contracts")
    adapted.write_text(text)
    adaptations.append({"original": source.name, "original_sha256": digest(source),
                        "adapted": "final-probes/" + source.name, "adapted_sha256": digest(adapted),
                        "changes": "Only repo bootstrap depth and approved FR3 internal module moves; probe logic unchanged."})
commands = [
    ("w007-tests", [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
                    "tests/contracts/test_w007_inputs.py", "tests/contracts/test_w007_contracts.py", "-q"]),
    *[(name, [sys.executable, "-B", f"docs/tasks/W007/review-evidence/final-probes/{script}.py"])
      for name, script in (("original-probe", "probe"), ("original-relabel", "relabel"),
                           ("readback", "readback"), ("whitespace", "whitespace"),
                           ("seed-capture", "seed_capture"), ("seed-capture-metadata", "seed_capture_metadata"))],
]
receipt = {
    "reviewer": "/root/code_review",
    "tested_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "python": sys.version,
    "platform": platform.platform(),
    "cwd": str(ROOT),
    "source_manifest_sha256": digest(MANIFEST),
    "source_manifest_files": len(manifest["files"]),
    "source_manifest_verified_before": True,
    "probe_adaptations": adaptations,
    "checks": [],
}
for name, command in commands:
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = DEST / f"final-{name}.txt"
    output.write_text(result.stdout + result.stderr)
    receipt["checks"].append({"name": name, "command": command, "returncode": result.returncode,
                              "duration_seconds": round(time.monotonic() - started, 3),
                              "output": output.name, "output_sha256": digest(output)})
    print(name, "exit", result.returncode, flush=True)
receipt["source_manifest_verified_after"] = all(
    digest(ROOT / name) == expected for name, expected in manifest["files"].items())
assert receipt["source_manifest_verified_after"]
(DEST / "final-review.json").write_text(json.dumps(receipt, indent=2) + "\n")
