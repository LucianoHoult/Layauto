"""Verify authorized review paths, links, unchanged source and check receipts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
HEAD = "88a7ae9d0330b7c7fddda0b07366c7a96552b65e"
TASK = "docs/tasks/W009-effective-geometry-terminals.md"
REPORT = "docs/tasks/W009/independent-premerge-review.md"
PREFIX = "docs/tasks/W009/independent-premerge-review/"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

observed_head = git("rev-parse", "HEAD").strip()
# Compare to the reviewed product, so this also works after the docs-only
# review commit. A later product fix must be reviewed under a new identity.
changed = set(git("diff", HEAD, "--name-only").splitlines())
changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
assert all(path in (TASK, REPORT) or path.startswith(PREFIX) for path in changed), changed
assert TASK in changed and REPORT in changed
assert "正在运行" not in (ROOT / REPORT).read_text(), "report still has a pending check"
before = git("show", HEAD + ":" + TASK)
after = (ROOT / TASK).read_text()
start = after.index("### R3 独立合并前复核（2026-11-03）")
end = after.index("## PM 验收与交接（PM）", start)
assert after[:start] + after[end:] == before, "task changed outside appended reviewer section"
assert "剩余必须修正项 1" in after[start:end]
manifest_path = ROOT / "docs/tasks/W009/verification/source-manifest.json"
source = json.loads(manifest_path.read_text())["files"]
assert len(source) == 240
assert all(sha(ROOT / path) == expected for path, expected in source.items())
assert not git("diff", HEAD, "--name-only", "--", "layauto_v2", "tests", "README.md", "pyproject.toml").strip()
for name in ("pytest", "typing", "pip-check"):
    receipt = json.loads((HERE / "validation" / (name + ".json")).read_text())
    assert receipt["returncode"] == 0 and receipt["head"] == HEAD and receipt["finished_head"] == HEAD
    for stream, output in receipt["outputs"].items():
        assert sha(HERE / "validation" / output["path"]) == output["sha256"]
assert "914 passed" in (HERE / "validation/pytest.stdout.txt").read_text()
assert "44 source files" in (HERE / "validation/typing.stdout.txt").read_text()
links_checked = 0
for relative in sorted(changed):
    if not relative.endswith(".md"):
        continue
    page = ROOT / relative
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", page.read_text()):
        if "://" in target or target.startswith("#"):
            continue
        target = target.split("#", 1)[0]
        assert (page.parent / target).exists(), (relative, target)
        links_checked += 1
receipt = dict(reviewed_head=HEAD, observed_checkout_head=observed_head, authorized_paths_only=True, appended_reviewer_section_only=True,
               source_manifest_sha256=sha(manifest_path), source_entries_unchanged=len(source),
               local_links_checked=links_checked, must_fix=1, recommend_integration=False,
               files={relative:sha(ROOT / relative) for relative in sorted(changed)
                      if relative != PREFIX + "delivery-audit.json"})
(HERE / "delivery-audit.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({k:v for k,v in receipt.items() if k != "files"}, indent=2, ensure_ascii=False))
