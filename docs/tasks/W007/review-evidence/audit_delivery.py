"""Independently verify final W007 command receipts and built artifact identity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / "docs/tasks/W007/verification"
TESTED = "0f879f01acbeac033173d0b6c6257c376bb9272a"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


manifest = json.loads((EVIDENCE / "source-manifest.json").read_text())
assert manifest["tested_commit"] == TESTED
for name, expected in manifest["files"].items():
    assert sha((ROOT / name).read_bytes()) == expected, name
    assert sha(subprocess.check_output(["git", "show", TESTED + ":" + name], cwd=ROOT)) == expected, name
runtime = {name: value for name, value in manifest["files"].items() if name.startswith("layauto_v2/")}
packages = json.loads((EVIDENCE / "package-identity.json").read_text())
assert packages["tested_commit"] == TESTED
assert packages["source_manifest_sha256"] == sha((EVIDENCE / "source-manifest.json").read_bytes())
for name, artifact in packages["artifacts"].items():
    path = EVIDENCE / "packages" / name
    assert sha(path.read_bytes()) == artifact["sha256"]
    if name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            assert {member for member in archive.namelist() if member.startswith("layauto_v2/") and not member.endswith("/")} == set(runtime)
            for member, expected in runtime.items():
                assert sha(archive.read(member)) == expected, member
            assert not any(member.startswith(("tests/", "legacy_mvp/")) for member in archive.namelist())
    else:
        with tarfile.open(path) as archive:
            assert {member.name.removeprefix("layauto-0.2.0/") for member in archive.getmembers()
                    if member.isfile() and member.name.startswith("layauto-0.2.0/layauto_v2/")} == set(runtime)
            for member, expected in runtime.items():
                stream = archive.extractfile("layauto-0.2.0/" + member)
                assert stream is not None
                assert sha(stream.read()) == expected, member
checks = []
for name in ("pytest-310", "pytest-312", "mypy-310", "mypy-312", "build", "install-wheel-310",
             "install-wheel-312", "wheel-smoke-310", "wheel-smoke-312", "pip-check-dev-310",
             "pip-check-dev-312", "pip-check-wheel-310", "pip-check-wheel-312"):
    receipt_path = EVIDENCE / (name + ".json")
    receipt = json.loads(receipt_path.read_text())
    assert receipt["git_head"] == TESTED and receipt["exit_code"] == 0, name
    output = EVIDENCE / receipt["log"]
    checks.append({"name": name, "receipt_sha256": sha(receipt_path.read_bytes()),
                   "output_sha256": sha(output.read_bytes()), "exit_code": receipt["exit_code"]})
protected = json.loads((EVIDENCE / "protected-paths.json").read_text())
assert protected["tested_commit"] == TESTED
for entry in protected["protected_paths"]:
    path = entry["path"]
    before = subprocess.check_output(["git", "rev-parse", protected["baseline_commit"] + ":" + path], cwd=ROOT)
    after = subprocess.check_output(["git", "rev-parse", TESTED + ":" + path], cwd=ROOT)
    assert before == after, path
    assert not subprocess.check_output(["git", "diff", "--name-only", TESTED, "--", path], cwd=ROOT), path
result = {"reviewer": "/root/code_review", "tested_commit": TESTED,
          "completed_utc": datetime.now(timezone.utc).isoformat(),
          "command": [sys.executable, "-B", "docs/tasks/W007/review-evidence/audit_delivery.py"],
          "source_manifest_sha256": sha((EVIDENCE / "source-manifest.json").read_bytes()),
          "source_manifest_content_sha256": manifest["content_sha256"],
          "verified_source_files": len(manifest["files"]), "verified_runtime_files_per_package": len(runtime),
          "verified_protected_paths": len(protected["protected_paths"]),
          "protected_paths_manifest_sha256": sha((EVIDENCE / "protected-paths.json").read_bytes()),
          "checks": checks, "result": "all recorded identities and success receipts independently matched"}
(Path(__file__).resolve().parent / "delivery-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["result"], "source files", len(manifest["files"]), "runtime files", len(runtime), "checks", len(checks))
