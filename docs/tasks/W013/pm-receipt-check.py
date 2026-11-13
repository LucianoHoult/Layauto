"""Read-only file/receipt verification; prints a compact result, runs no product."""
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / "docs/tasks/W013"
V = P / "verification-r2"
FROZEN = "2a45938aba8e751183d472d660a1ab66a1063636"
DELIVERY = "63a0962f1b56655f234140822bffa8f56b7bb15f"
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest = json.loads((V / "source-manifest.json").read_text())
receipt = json.loads((V / "receipt.json").read_text())
evidence = json.loads((V / "evidence-manifest.json").read_text())
for name, expected in manifest["files"].items():
    assert sha((ROOT / name).read_bytes()) == expected, name
    for rev in (FROZEN, DELIVERY):
        blob = subprocess.check_output(["git", "show", f"{rev}:{name}"], cwd=ROOT)
        assert sha(blob) == expected, (rev, name)
with tarfile.open(V / "source-snapshot.tar.gz") as archive:
    files = {m.name: m for m in archive.getmembers() if m.isfile()}
    assert set(files) == set(manifest["files"])
    for name, expected in manifest["files"].items():
        assert sha(archive.extractfile(files[name]).read()) == expected, name
for name, expected in evidence.items():
    assert sha((V / name).read_bytes()) == expected, name
assert receipt["status"] == "passed"
assert receipt["actual_test_counts"] == {"310": 1731, "312": 1731}
assert receipt["source_id"] == manifest["source_id"]
assert sha((V / "source-manifest.json").read_bytes()) == receipt["source_manifest_sha256"]
assert sha((V / "source-snapshot.tar.gz").read_bytes()) == receipt["source_snapshot_sha256"]
for command in receipt["commands"]:
    assert command["exit_code"] == 0
    for stream in ("stdout", "stderr"):
        assert sha((V / command[stream]).read_bytes()) == command[stream + "_sha256"]
runtime = {p: h for p, h in manifest["files"].items() if p.startswith("layauto_v2/")}
package_counts = {}
for package in (V / "dist").iterdir():
    if package.suffix == ".whl":
        with zipfile.ZipFile(package) as archive:
            actual = {n: sha(archive.read(n)) for n in archive.namelist()
                      if n.startswith("layauto_v2/") and not n.endswith("/")}
    else:
        with tarfile.open(package) as archive:
            actual = {m.name.split("/", 1)[1]: sha(archive.extractfile(m).read())
                      for m in archive.getmembers()
                      if m.isfile() and "/layauto_v2/" in m.name}
    assert actual == runtime, package.name
    package_counts[package.name] = len(actual)
protected = subprocess.check_output(
    ["git", "diff", "--name-only", "d6182fe6893c26490f9d58c6b808a5ce9910384b", DELIVERY,
     "--", "tests/fixtures", "layauto_v2/normalization/local_connectivity_codec.py",
     "layauto_v2/normalization/channel_identity_codec.py"], cwd=ROOT)
assert not protected
print(json.dumps({
    "date": "2026-11-13", "delivery": DELIVERY, "frozen": FROZEN,
    "source_id": manifest["source_id"], "source_files_checked": len(manifest["files"]),
    "runtime_files": len(runtime), "snapshot_matches": True,
    "evidence_hashes_checked": len(evidence), "commands_checked": len(receipt["commands"]),
    "adopted_test_counts": receipt["actual_test_counts"], "packages_checked": package_counts,
    "fixture_and_A2_codec_paths_unchanged": True,
    "review_findings": "CR-01..03 closure read and adopted; not independently re-executed here",
    "resource_scope": "resource04 adopted via documented R2 test-only delta; no fresh benchmark",
    "limits": ["No new product tests/full matrix/install execution or performance measurement",
               "Does not constitute final acceptance, independent premerge review or integration"],
}, ensure_ascii=False, indent=2))
