"""Record exact review scope without changing source or historical evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
MAIN = "4df07e68b05df4c57a8b8d44bc41e7e073938d3a"
PREP = "4975e565a33d9594782645b6ad0f944b78ee6ae8"
PRODUCT = "5b1d9b5196a7c5181822c4dd0f1bd2f678475116"
HEAD = "88a7ae9d0330b7c7fddda0b07366c7a96552b65e"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

observed_head = git("rev-parse", "HEAD")
assert not git("diff", "--name-only", HEAD, observed_head, "--", "layauto_v2", "tests", "README.md", "pyproject.toml"), "checkout product differs from reviewed source"
for old, new in ((MAIN, PREP), (PREP, PRODUCT), (PRODUCT, HEAD)):
    assert git("rev-parse", new + "^") == old
protected = ["tests/fixtures", "tests/support", "docs/architecture.md", "docs/tasks/W003", "docs/tasks/W004-fixture-revision.md", "docs/tasks/W005", "docs/tasks/W006", "docs/tasks/W007", "docs/tasks/W008"]
assert not git("diff", "--name-only", PREP, HEAD, "--", *protected)
product_paths = git("diff", "--name-status", PREP, PRODUCT, "--", "layauto_v2", "tests", "pyproject.toml", "README.md").splitlines()
files = sorted(path for path in git("diff", "--name-only", PREP, PRODUCT, "--", "layauto_v2", "tests", "pyproject.toml", "README.md").splitlines())
result = dict(reviewed_head=HEAD, product_head=PRODUCT, preparation_head=PREP, main_baseline=MAIN, review_checkout=str(ROOT), original_checkout="/workspace/Layauto", original_branch="work", original_head=MAIN, original_status_porcelain_v2="# branch.oid " + MAIN + "\n# branch.head work\n", original_staged_unstaged_untracked="all empty", remote="https://github.com/LucianoHoult/Layauto.git", observed_remote_before_fetch=dict(main=MAIN, w009=HEAD), branch=git("branch", "--show-current"), commits=git("log", "--format=%H %P %s", MAIN + ".." + HEAD).splitlines(), full_delivery_paths=git("diff", "--name-status", MAIN, HEAD).splitlines(), implementation_paths=product_paths, pm_only_paths=git("diff", "--name-status", PRODUCT, HEAD).splitlines(), protected_paths_checked=protected, protected_paths_changes=[], implementation_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in files})
result["observed_checkout_head"] = observed_head
(OUT / "version-scope.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({key: result[key] for key in ("reviewed_head", "commits", "implementation_paths", "protected_paths_changes")}, indent=2))
