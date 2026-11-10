"""Independent, stdlib-only archive audit. Does not execute project code/tests.

Run from repository root: python -B docs/tasks/W011/independent-premerge-evidence/evidence-audit.py
"""
from pathlib import Path
import datetime as dt
import hashlib
import gzip
import json
import platform
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[4]
W = ROOT / "docs/tasks/W011"
V = W / "verification"
R = W / "resources"
BASE = "61775e8fde6e9ea247ec08a32067c44c3be48ff8"
PREP = "81e01da1e5a6ce8e7132f3cebf8ee92bc237246f"
PRODUCT = "8917d38d916c914bfa785cb116982f3f299b38de"
FROZEN = "e89bdaa6a091f56cfaf7862dced7232d34e22514"
DELIVERY = "3c464baade7b6ea8c712cfb84265490b8e3f754e"
HEAD = "8452027e57fb1c58607640d7eb755b38ffc70716"
checks = []
def check(label, condition, details=None):
    assert condition, (label, details)
    checks.append({"check": label, "details": details})
def sha(data):
    return hashlib.sha256(data).hexdigest()
def read(path):
    return json.loads(path.read_text())
def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)
def when(value):
    return dt.datetime.fromisoformat(value)
def tar_files(path):
    with tarfile.open(path) as arc:
        members = arc.getmembers()
        names = [m.name for m in members if m.isfile()]
        check("unique tar members: " + path.name, len(names) == len(set(names)))
        check("no links: " + path.name, all(not (m.issym() or m.islnk()) for m in members))
        return {m.name: sha(arc.extractfile(m).read()) for m in members if m.isfile()}
def index(directory, name="evidence-manifest.json", complete=True):
    manifest = read(directory / name)
    actual = {str(p.relative_to(directory)): sha(p.read_bytes()) for p in directory.rglob("*") if p.is_file() and p.name != name}
    check("index hashes: " + str(directory.relative_to(W)), all(actual.get(p) == h for p, h in manifest.items()), len(manifest))
    if complete:
        check("index complete: " + str(directory.relative_to(W)), actual == manifest)
    return len(manifest)

started = dt.datetime.now(dt.timezone.utc).isoformat()
for older, newer in zip((BASE, PREP, PRODUCT, FROZEN, DELIVERY), (PREP, PRODUCT, FROZEN, DELIVERY, HEAD)):
    check("ancestry " + older[:7] + " -> " + newer[:7], subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=ROOT).returncode == 0)
check("checkout reviewed head", git("rev-parse", "HEAD").decode().strip() == HEAD)
m = read(V / "source-manifest.json")
files = m["files"]
check("262 source entries", len(files) == 262 and m["git_head"] == FROZEN)
selection = ["layauto_v2", "tests", "pyproject.toml", "README.md", "docs/tasks/W003/examples/records.json"]
tracked = set(git("ls-tree", "-r", "--name-only", FROZEN, "--", *selection).decode().splitlines())
check("complete frozen tracked source selection", tracked == set(files))
check("complete tar snapshot equals manifest", tar_files(V / "source-snapshot.tar.gz") == files)
for version in (FROZEN, DELIVERY, HEAD):
    check("all source bytes at " + version[:7], all(sha(git("show", version + ":" + p)) == h for p, h in files.items()))
check("all live source bytes", all(sha((ROOT / p).read_bytes()) == h for p, h in files.items()))
runtime = {p.removeprefix("layauto_v2/"): h for p, h in files.items() if p.startswith("layauto_v2/")}
check("100 runtime entries", len(runtime) == 100 and runtime == m["runtime_files"])
check("runtime unchanged since product correction", all(sha(git("show", PRODUCT + ":layauto_v2/" + p)) == h for p, h in runtime.items()))
later = git("diff", "--name-only", FROZEN, HEAD).decode().splitlines()
check("post-freeze changes only docs", all(p.startswith("docs/") for p in later), later)
check("fixtures unmodified from main", git("diff", "--name-only", BASE, HEAD, "--", "tests/fixtures") == b"")
package_identity = read(V / "package-identity.json")
for kind, row in package_identity.items():
    path = V / "dist" / Path(row["path"]).name
    check(kind + " artifact hash", sha(path.read_bytes()) == row["sha256"], row["sha256"])
    if kind == "wheel":
        with zipfile.ZipFile(path) as arc:
            names = arc.namelist()
            check("unique wheel members", len(names) == len(set(names)))
            actual = {p.removeprefix("layauto_v2/"): sha(arc.read(p)) for p in names if p.startswith("layauto_v2/") and not p.endswith("/")}
    else:
        actual = {p.split("/layauto_v2/", 1)[1]: h for p, h in tar_files(path).items() if "/layauto_v2/" in p}
    check(kind + " actual 100 runtime bytes", actual == runtime == row["runtime_files"])

check("engineering index", index(V) == 83)
check("resource index", index(R) == 16)
check("failed-attempt index", index(W / "verification-attempt-01") == 31)
index(W / "preflight", "archive-manifest.json", complete=False)
receipt = read(V / "receipt.json")
check("receipt binds source manifest and snapshot", receipt["source_manifest_sha256"] == sha((V / "source-manifest.json").read_bytes()) and receipt["source_snapshot_sha256"] == sha((V / "source-snapshot.tar.gz").read_bytes()))
commands = receipt["commands"]
check("21 archived command records", len(commands) == 21)
individual = []
for row in commands:
    check("command exit/UTC: " + row["stdout"], row["exit_code"] == 0 and when(row["finished_at_utc"]) >= when(row["started_at_utc"]))
    for stream in ("stdout", "stderr"):
        check("raw " + row[stream], sha((V / row[stream]).read_bytes()) == row[stream + "_sha256"])
    one = read(V / row["stdout"].replace(".stdout.txt", ".json"))
    check("command record equals aggregate: " + row["stdout"], one == row)
    individual.append(row)
outer = [json.loads(line) for line in (W / "preflight/final-attempt02/final-runner.stdout.txt").read_text().splitlines()]
check("outer runner preserves all 21 command records", len(outer) == 21 and sorted(map(lambda r: json.dumps(r, sort_keys=True), outer)) == sorted(map(lambda r: json.dumps(r, sort_keys=True), commands)))
check("runner/smoke bytes bound", receipt["runner_sha256"] == sha((V / "prepare_final.py").read_bytes()) == sha((W / "prepare_final.py").read_bytes()) and receipt["smoke_sha256"] == sha((V / "installed_smoke.py").read_bytes()) == sha((W / "installed_smoke.py").read_bytes()))
def ids(path):
    return [line for line in path.read_text().splitlines() if line.startswith("tests/") and "::" in line]
baseline = ids(V / "baseline-collection.txt")
check("1465 baseline unique IDs", len(baseline) == len(set(baseline)) == 1465)
check("baseline preserved from preflight", baseline == ids(W / "preflight/baseline-collection312.txt"))
collections = []
installation_presence = {}
smokes = {}
for tag in ("310", "312"):
    current = ids(V / ("collection-" + tag + ".stdout.txt"))
    added = set(current) - set(baseline)
    check(tag + " full ID coverage", len(current) == len(set(current)) == 1605 and set(baseline) <= set(current) and len(added) == 140 and all("test_w011_" in p for p in added))
    collections.append(current)
    check(tag + " full pytest raw summary", "1605 passed" in (V / ("pytest-" + tag + ".stdout.txt")).read_text() and "failed" not in (V / ("pytest-" + tag + ".stdout.txt")).read_text())
    check(tag + " strict typing54", (V / ("typing-" + tag + ".stdout.txt")).read_text().strip() == "Success: no issues found in 54 source files" and "strict = true" in (ROOT / "pyproject.toml").read_text())
    environment = read(V / ("environment-" + tag + ".stdout.txt"))
    check(tag + " interpreter version", environment["version"].startswith("3.10.22" if tag == "310" else "3.12.14"))
    identity = read(V / "installation-identity.json")[tag]
    installation_presence[tag] = Path(identity["package"]).exists()
    check(tag + " archived installed runtime hashes", identity["runtime_files"] == runtime and identity["fresh_environment"] and identity["isolated"] == 1 and "/site-packages/" in identity["package"])
    kind = "sdist" if tag == "310" else "wheel"
    check(tag + " archived artifact identity", identity["artifact_sha256"] == package_identity[kind]["sha256"])
    raw_identity = read(V / ("installed-identity-" + tag + ".stdout.txt"))
    check(tag + " archived import identity", all(raw_identity[k] == identity[k] for k in raw_identity))
    pip = read(V / ("install-" + tag + "-report.json"))
    installed = [r for r in pip["install"] if r["metadata"]["name"].lower() == "layauto"]
    archive_info = installed[0]["download_info"]["archive_info"]
    artifact_hash = archive_info.get("hashes", {}).get("sha256") or archive_info.get("hash", "").removeprefix("sha256=")
    check(tag + " pip report artifact", len(installed) == 1 and artifact_hash == identity["artifact_sha256"])
    smoke_cmd = read(V / ("installed-smoke-" + tag + ".json"))
    check(tag + " source-external isolated smoke command", smoke_cmd["command"][1:3] == ["-I", "-B"] and smoke_cmd["cwd"].endswith("/installed-cwd") and "source" not in Path(smoke_cmd["cwd"]).parts)
    smoke = read(V / ("installed-smoke-" + tag + ".stdout.txt"))
    check(tag + " archived smoke import", smoke["package"] == identity["package"] and smoke["attempt_unchanged"])
    check(tag + " direct/readback full set smoke", smoke["direct"]["counts"] == smoke["readback"]["counts"] == {"MN0": 5, "MP0": 7} and smoke["extraction_mismatch"]["counts"] == {"MN0": 4, "MP0": 7} and smoke["extraction_mismatch"]["difference_count"] == 1 and smoke["extraction_mismatch"]["comparison_status"] == "mismatch")
    smokes[tag] = smoke
check("dual collection identical", collections[0] == collections[1])
for case in ("direct", "readback"):
    check(case + " cross-interpreter wire stable", smokes["310"][case]["wire_sha256"] == smokes["312"][case]["wire_sha256"])
matrices = [read(V / ("pytest-" + tag + ".json")) for tag in ("310", "312")]
build = read(V / "build.json")
check("build follows both matrices", all(when(build["started_at_utc"]) >= when(r["finished_at_utc"]) for r in matrices))
check("smokes serialized", when(read(V / "installed-smoke-312.json")["started_at_utc"]) > when(read(V / "installed-smoke-310.json")["finished_at_utc"]))
gate_hash = sha((W / "w011_resource_gate.py").read_bytes())
check("gate unchanged archived copy", gate_hash == receipt["resource_gate"]["sha256"] == sha((V / "w011_resource_gate.py").read_bytes()))
events = {tag: [json.loads(line) for line in (V / ("resource-gate-" + tag + ".jsonl")).read_text().splitlines()] for tag in ("310", "312")}
for tag, rows in events.items():
    check(tag + " four lock events", [r["event"] for r in rows] == ["WAIT", "ACQUIRED", "SESSION_FINISH_LOCK_RETAINED", "RELEASED"] and all(r["plugin_sha256"] == gate_hash and not r["lock_fd_inheritable"] for r in rows))
check("same lock inode", len({(r["lock_path"], r["lock_device"], r["lock_inode"]) for rows in events.values() for r in rows}) == 1)
check("lock W011 intervals separate", when(events["310"][1]["observed_at_utc"]) >= when(events["312"][2]["observed_at_utc"]))
waits = {tag: (when(rows[1]["observed_at_utc"]) - when(rows[0]["observed_at_utc"])).total_seconds() for tag, rows in events.items()}
old = W / "verification-attempt-01"
check("old failure retained", "2 failed, 1603 passed" in (old / "pytest-310.stdout.txt").read_text() and read(old / "pytest-310.json")["exit_code"] == 1 and read(old / "attempt-closure.json")["status"] == "failed_and_superseded")
check("old 312 full not claimed", not (old / "pytest-312.json").exists())
check("two setup repairs tests-only", git("diff", "--name-only", "02725e2", FROZEN, "--", "layauto_v2", "tests", "pyproject.toml").decode().splitlines() == ["tests/contracts/test_w011_geometry.py"])
for archive_dir, original, integrated in (("target-only-repair", "27f885497634d0f2ed50d293e00603309d34c0cd", "75c846fb1d0d75a392f3a2eeacb87b98ddd0c008"), ("owner-boundary-repair", "1cb7e1bc654c61690427ac22481b985156d9c9e6", "6ea8b0a933650633e0c4ee1d3ca1bc21e9f9c6ff")):
    archived = W / "test-preflight" / archive_dir
    check("repair archived original identity " + integrated[:7], original in (archived / "test-fix-commit.txt").read_text())
    check("repair archived patch equivalence " + integrated[:7], gzip.decompress((archived / "corrected-test.patch.gz").read_bytes()) == git("show", "--format=", integrated, "--", "tests"))

resource_receipt = read(R / "receipt.json")
check("resources bound engineering identity", resource_receipt["source_identity"]["verification_source_manifest_sha256"] == sha((V / "source-manifest.json").read_bytes()) and resource_receipt["source_identity"]["verification_receipt_sha256"] == sha((V / "receipt.json").read_bytes()))
resource_table = {}
previous_end = None
fixture = ROOT / "tests/fixtures/w003_m1"
overlays = {"source.gds", "query/header.json", "query/raw/device_info_Q17.txt", "query/normalized/device_regions.yaml", "body/context.json"}
for command in resource_receipt["commands"]:
    case = command["case"]
    check(case + " resource command", command == read(R / (case + ".command.json")) and command["exit_code"] == 0 and command["tested_source_commit"] == FROZEN)
    if previous_end:
        check(case + " resource serial", when(command["started_at_utc"]) >= previous_end)
    previous_end = when(command["finished_at_utc"])
    for stream in ("stdout", "stderr"):
        check(case + " resource raw " + stream, sha((R / (case + "." + stream + ".txt")).read_bytes()) == command[stream + "_sha256"])
    probe = read(R / (case + ".json"))
    check(case + " probe/runtime identity", probe["source_unchanged_during_probe"] and all(files[p] == h for p, h in probe["source_manifest"].items()) and probe["probe_sha256"] == sha((R / "resource_probe.py").read_bytes()) == sha((W / "resource_probe.py").read_bytes()))
    result = probe["result"]
    for source in result["capture_sources"]:
        uri = source["uri"]
        rel = "query/normalized/" + uri.split("/query/normalized/", 1)[1] if uri.startswith("/") else uri
        path = fixture / ("failures/extraction_mismatch/" + rel if case == "extraction-mismatch" and rel in overlays else rel)
        check(case + " capture " + rel, sha(path.read_bytes()) == source["sha256"] and path.stat().st_size == source["bytes"])
    check(case + " finite input and full result", len(result["capture_sources"]) == 31 and sum(s["bytes"] for s in result["capture_sources"]) == result["raw_capture_bytes"] == 280706 and result["drawn_record_count"] == 40 and result["drawn_FIN_record_count"] == 18 and result["FIN_evaluations"] == 36 and result["public_roundtrip_equal"])
    resource_table[case] = {"wire_bytes": result["result_wire_bytes"], "process_peak_rss_kib": probe["process_peak_rss_kib"], "wall_seconds": probe["wall_seconds"]}
check("readback size/RSS observed values", resource_table["normal-readback"]["wire_bytes"] == 136461405 and resource_table["normal-readback"]["process_peak_rss_kib"] == 7322828)
O = W / "preflight/final-attempt02"
summary = read(O / "resource-observations-summary.json")
observations = [json.loads(line) for line in (O / "resource-observations.jsonl").read_text().splitlines()]
check("raw sample hash/count", sha((O / "resource-observations.jsonl").read_bytes()) == summary["raw_sha256"] and len(observations) == summary["sample_count"] == 1399)
max_cgroup = max(r["cgroup_memory_current_bytes"] for r in observations)
peaks = {}
for row in observations:
    for p in row["processes"]:
        pid = str(p["pid"])
        if pid not in peaks or p["rss_kib"] > peaks[pid]["rss_kib"]:
            peaks[pid] = {**p, "observed_at_utc": p.get("observed_at_utc", row["observed_at_utc"])}
without_time = lambda r: {k: v for k, v in r.items() if k != "observed_at_utc"}
check("every per-process sampled maximum", {k: without_time(v) for k, v in peaks.items()} == {k: without_time(v) for k, v in summary["max_sampled_process_rss_by_pid"].items()})
for pid, peak in summary["max_sampled_process_rss_by_pid"].items():
    witness = next(i for i, row in enumerate(observations) if row["observed_at_utc"] == peaks[pid]["observed_at_utc"])
    # Original observer takes the peak clock before the enclosing JSONL row clock.
    before = summary["started_at_utc"] if witness == 0 else observations[witness - 1]["observed_at_utc"]
    check("peak timestamp within original sample interval " + pid, when(before) <= when(peak["observed_at_utc"]) <= when(observations[witness]["observed_at_utc"]))
check("shared sampled maximum", max_cgroup == summary["max_sampled_cgroup_memory_bytes"] == 12299743232)
check("310 sampled RSS", peaks["21383"]["rss_kib"] == 9257804)
check("memory events unchanged zero", summary["initial_limits_and_cumulative_events"]["memory.events"] == summary["final_cumulative_events"]["memory.events"] and all(int(line.split()[1]) == 0 for line in summary["final_cumulative_events"]["memory.events"].splitlines()))
result = {"started_at_utc": started, "finished_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(), "command": [sys.executable, "-B", str(Path(__file__).relative_to(ROOT))], "cwd": str(ROOT), "base": BASE, "review_head": HEAD, "frozen_tested_source": FROZEN, "status": "passed", "check_count": len(checks), "checks": checks, "original_installation_paths_present_now": installation_presence, "resource_samples_archived": resource_table, "resource_gate_wait_seconds": waits, "sampled_process_rss_kib": {p: r["rss_kib"] for p, r in peaks.items()}, "max_sampled_cgroup_bytes": max_cgroup, "limits": ["This run reads Git, archives, packages, manifests and original outputs. It does not rerun full matrices, build/install, product readback/codec or resource benchmarks.", "Absent original installation trees are archival observations, not freshly observed site-packages.", "Sampled maxima are not exact peaks; ru_maxrss is whole-process including upstream and wire; constructors are included in build/decode."]}
print(json.dumps(result, ensure_ascii=False, indent=2))
