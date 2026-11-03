"""Read-only independent premerge audit of W009 archived evidence.

Run from the repository root with Python 3.10+, -B, and bytecode disabled.
This reads artifacts and records; it does not rerun their historical commands.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import zipfile


ROOT = Path.cwd()
W = ROOT / "docs/tasks/W009"
V = W / "verification"
HEAD = "88a7ae9d0330b7c7fddda0b07366c7a96552b65e"
PRODUCT = "5b1d9b5196a7c5181822c4dd0f1bd2f678475116"
PREP = "4975e565a33d9594782645b6ad0f944b78ee6ae8"
BASE = "4df07e68b05df4c57a8b8d44bc41e7e073938d3a"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def json_values(raw):
    decoder = json.JSONDecoder()
    values = []
    while raw.strip():
        raw = raw.lstrip()
        item, end = decoder.raw_decode(raw)
        values.append(item)
        raw = raw[end:]
    return values


audit_head = git("rev-parse", "HEAD")
assert subprocess.run(["git", "merge-base", "--is-ancestor", HEAD, audit_head], cwd=ROOT).returncode == 0
for parent, child in ((BASE, PREP), (PREP, PRODUCT), (PRODUCT, HEAD)):
    assert subprocess.run(["git", "merge-base", "--is-ancestor", parent, child], cwd=ROOT).returncode == 0

manifest = load(V / "source-manifest.json")
receipt = load(V / "receipt.json")
manifest_hash = digest((V / "source-manifest.json").read_bytes())
assert manifest_hash == receipt["source_manifest_sha256"]
assert manifest["git_head"] == PREP  # This is the pre-commit workspace baseline.
for path, expected in manifest["files"].items():
    assert digest((ROOT / path).read_bytes()) == expected, path
    for commit in (PRODUCT, HEAD):
        assert digest(subprocess.check_output(["git", "show", commit + ":" + path], cwd=ROOT)) == expected, (commit, path)

tracked = git("ls-files", "layauto_v2", "tests", "README.md", "pyproject.toml").splitlines()
required = {
    name for name in tracked
    if (name.startswith("layauto_v2/") and (name.endswith(".py") or name.endswith("/py.typed")))
    or (name.startswith(("tests/unit/", "tests/contracts/")) and name.endswith(".py"))
    or name in {"README.md", "pyproject.toml"}
}
assert required <= set(manifest["files"])
runtime = {
    str(path.relative_to(ROOT / "layauto_v2")): digest(path.read_bytes())
    for path in (ROOT / "layauto_v2").rglob("*")
    if path.is_file() and (path.suffix == ".py" or path.name == "py.typed")
}
assert runtime == manifest["runtime_files"]
with tarfile.open(V / "source-snapshot.tar.gz") as archive:
    members = [m for m in archive.getmembers() if m.isfile()]
    assert len(members) == len({m.name for m in members})
    snapshot = {m.name: digest(archive.extractfile(m).read()) for m in members}
assert snapshot == manifest["files"]
assert digest((V / "source-snapshot.tar.gz").read_bytes()) == receipt["source_snapshot_sha256"]

historical = {}
for label in ("pre-cr02", "pre-container"):
    directory = V / label
    status = load(directory / "status.json")
    old = load(directory / "source-manifest.json")
    assert digest((directory / "source-manifest.json").read_bytes()) == status["source_manifest_sha256"]
    assert digest((directory / "source-snapshot.tar.gz").read_bytes()) == status["source_snapshot_sha256"]
    with tarfile.open(directory / "source-snapshot.tar.gz") as archive:
        old_snapshot = {m.name: digest(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
    assert old_snapshot == old["files"]
    historical[label] = {"source_manifest_sha256": status["source_manifest_sha256"], "source_files": len(old_snapshot), "scope": status["scope"], "complete_final_matrix": False}
old = load(V / "pre-cr02/source-manifest.json")
assert old == load(W / "review/pre-cr02-source-manifest.json")
for name in ("exception-after312.json", "exception-after310.json"):
    result = load(W / "review" / name)
    assert result["all_same_object"]
    assert all(old["files"][source] == expected for source, expected in result["sources"].items())
zip_path = W / "review/pre-container-source.zip"
assert digest(zip_path.read_bytes()) == load(V / "pre-container/status.json")["independent_source_zip_sha256"]
with zipfile.ZipFile(zip_path) as archive:
    old = load(V / "pre-container/source-manifest.json")
    assert json.loads(archive.read("source-manifest.json")) == old
    assert {name: digest(archive.read(name)) for name in archive.namelist() if name != "source-manifest.json"} == old["files"]

evidence = load(V / "evidence-manifest.json")["sha256"]
for path, expected in evidence.items():
    assert digest((V / path).read_bytes()) == expected, path
assert receipt["status"] == "passed" and len(receipt["commands"]) == 15
assert digest((V / "verify_final.py").read_bytes()) == receipt["runner_sha256"]
commands = []
for row in receipt["commands"]:
    assert row["exit_code"] == 0
    raw = (V / row["output"]).read_bytes()
    assert digest(raw) == row["output_sha256"], row["output"]
    detail = load(V / Path(row["output"]).with_suffix(".json"))
    for key in ("command", "cwd", "exit_code", "output", "output_sha256"):
        assert detail[key] == row[key], (row["output"], key)
    if row["output"].startswith("pytest-"):
        assert re.search(rb"\b914 passed\b", raw)
    if row["output"].startswith("typing-"):
        assert b"Success: no issues found in 44 source files" in raw
    commands.append({"output": row["output"], "exit_code": row["exit_code"], "sha256": digest(raw)})

packages = load(V / "package-identity.json")
package_report = {}
for kind, info in packages.items():
    artifact = V / "dist" / Path(info["path"]).name
    assert digest(artifact.read_bytes()) == info["sha256"]
    if kind == "wheel":
        with zipfile.ZipFile(artifact) as archive:
            names = [n for n in archive.namelist() if n.startswith("layauto_v2/") and (n.endswith(".py") or n.endswith("/py.typed"))]
            assert len(names) == len(set(names))
            packaged = {n[len("layauto_v2/"):]: digest(archive.read(n)) for n in names}
    else:
        with tarfile.open(artifact) as archive:
            members = [m for m in archive.getmembers() if m.isfile() and "/layauto_v2/" in m.name and (m.name.endswith(".py") or m.name.endswith("/py.typed"))]
            names = [m.name.split("/layauto_v2/", 1)[1] for m in members]
            assert len(names) == len(set(names))
            packaged = {m.name.split("/layauto_v2/", 1)[1]: digest(archive.extractfile(m).read()) for m in members}
    assert packaged == runtime == info["runtime_files"]
    package_report[kind] = {"sha256": info["sha256"], "runtime_files": len(packaged)}

installs = load(V / "installation-identity.json")
installation_report = {}
for tag, info in installs.items():
    assert info["runtime_files"] == runtime
    artifact = V / "dist" / Path(info["source_artifact"]).name
    assert digest(artifact.read_bytes()) == info["source_sha256"]
    report = load(V / ("install-" + tag + "-report.json"))
    package = next(row for row in report["install"] if row["metadata"]["name"].lower() == "layauto")
    assert package["download_info"]["url"] == Path(info["source_artifact"]).as_uri()
    archive_info = package["download_info"]["archive_info"]
    assert (archive_info.get("hashes", {}).get("sha256") or archive_info["hash"].removeprefix("sha256=")) == info["source_sha256"]
    smoke = load(V / ("installed-smoke-" + tag + ".json"))
    assert smoke["exit_code"] == 0 and "-I" in smoke["command"] and "-B" in smoke["command"]
    # Compare with historical checkout location, not this new worktree location.
    assert not Path(smoke["cwd"]).is_relative_to(Path("/workspace/Layauto"))
    records = json_values((V / smoke["output"]).read_text())
    environment, checks = records[0]["environment"], records[-1]["checks"]
    assert environment["isolated"] == 1 and environment["dont_write_bytecode"]
    assert environment["package_manifest"] == runtime
    assert environment["installed_package"] == info["installed_package"]
    assert "site-packages" in Path(environment["installed_package"]).parts
    assert checks["status"] == "passed"
    installation_report[tag] = {"historical_tree_present": Path(info["installed_package"]).exists(), "recorded_runtime_files": len(info["runtime_files"]), "recorded_smoke_cwd": smoke["cwd"], "artifact_sha256": info["source_sha256"], "checks": checks}

probes = load(W / "review/final-probe-identity-audit.json")
for path, info in probes.items():
    assert info["all_match"]
    assert load(W / "review" / path)["source_sha256"] == info["source_sha256"]
    for source, expected in info["source_sha256"].items():
        assert manifest["files"][source] == expected
for tag in ("310", "312"):
    assert b"67 passed" in (W / "review" / ("cr02-final" + tag + ".txt")).read_bytes()
assert digest((W / "plan.md").read_bytes()) == "b14226b6aa68dae2f9d305b57adf5f5bb27eaa6e61c4eb625847786133d37deb"

performance = load(V / "performance.json")
assert len(performance["executions"]) == 10
for source, expected in performance["source_sha256"].items():
    assert manifest["files"][source] == expected
for name, row in performance["executions"].items():
    assert row["source_sha256"] == performance["source_sha256"]
    assert row["elapsed_seconds"] >= 0
    assert "--case " + name + " " in row["command"]

pm = load(W / "pm-receipt.json")
assert pm["reviewed_head"] == PRODUCT and pm["preparation_head"] == PREP and pm["main_observed"] == BASE
assert pm["source_manifest_sha256"] == manifest_hash
for name, expected in pm["pm_evidence_sha256"].items():
    assert digest((W / "pm-evidence" / name).read_bytes()) == expected, name
for name, row in pm["actual_checks"].items():
    assert row["head"] == PRODUCT and row["returncode"] == 0
    for output in row["outputs"].values():
        assert digest((W / "pm-evidence" / output["path"]).read_bytes()) == output["sha256"]
assert b"914 passed" in (W / "pm-evidence/pytest.stdout.txt").read_bytes()
assert b"Success: no issues found in 44 source files" in (W / "pm-evidence/typing.stdout.txt").read_bytes()
for name in ("exception-probe.stdout.txt", "fraction-probe.stdout.txt"):
    result = load(W / "pm-evidence" / name)
    for source, expected in (result.get("sources") or result["source_sha256"]).items():
        assert manifest["files"][source] == expected

protected = git("diff", "--name-only", PREP, HEAD, "--", "tests/fixtures", "docs/tasks/W003*", "docs/tasks/W004*", "docs/tasks/W005*", "docs/tasks/W006*", "docs/tasks/W007*", "docs/tasks/W008*").splitlines()
assert not protected
post_product = git("diff", "--name-only", PRODUCT, HEAD).splitlines()
assert all(path.startswith("docs/tasks/W009/") or path in {"docs/tasks/W009-effective-geometry-terminals.md", "docs/current-work.md", "docs/README.md"} for path in post_product)

print(json.dumps({
    "status": "passed", "actual_audit_python": sys.version,
    "reviewed_head": HEAD, "audit_checkout_head": audit_head, "product_head": PRODUCT, "preparation_head": PREP, "main_base": BASE,
    "source_manifest_sha256": manifest_hash, "source_manifest_baseline": manifest["git_head"],
    "source_files_current_product_head_all_equal": len(manifest["files"]),
    "required_tracked_source_files_covered": len(required), "source_archive_files": len(snapshot),
    "runtime_files": len(runtime), "verification_evidence_files": len(evidence),
    "historical_snapshots_separately_verified": historical,
    "archived_commands": commands, "packages": package_report, "installation_records": installation_report,
    "final_review_probe_identity_files": list(probes), "performance_executions": len(performance["executions"]),
    "pm_evidence_files": len(pm["pm_evidence_sha256"]), "pm_actual_check_records": list(pm["actual_checks"]),
    "protected_paths_changed_since_preparation": protected, "post_product_paths": post_product,
    "limitations": ["No historical command was re-executed by this audit.", "No build, installation, Python 3.10 regression, or historical installation-tree traversal was performed.", "Artifact bytes and archived command/install records are mutually consistent; this is not an independent observation of historical execution.", "Full Python 3.12 regression and typing for this review are recorded separately by the primary reviewer."]
}, ensure_ascii=False, indent=2, sort_keys=True))
