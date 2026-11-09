# W011 target-only witness setup repair

This supplement preserves the original failure discovered by the Python 3.10 full matrix at source commit `02725e2e90be6b3145be915be699aa64ce998ed7`. It does not replace or reinterpret that matrix result.

The fixture intentionally uses target parameter order `VT=toy W=2n L=4n M=1 NF=1 NFIN=5`. The test passed source parameter order to `change_cdl`, so its `assert before in text` failed before the target variant entered W011. The fix changes only the two replacement strings to target order, leaving the helper, all assertions, runtime, fixtures and expected results unchanged. MN0 target intent still changes NFIN 5 to 3, L 4n to 6n and W 2n to 3n; source geometry must remain MN0 5 / MP0 7 with equal source comparisons and three retained target differences.

Both probes used the same frozen runtime and Python 3.10 environment, one targeted process at a time. The original run failed at the helper assertion: **1 failed in 72.55 s**, exit 1, child maximum RSS 1,734,684 KiB. The corrected run completed all assertions: **1 passed in 136.82 s**, exit 0, child maximum RSS 1,733,588 KiB. No other probe was started for this repair. Shared-container limits and the interpreter package inventory are recorded in `environment.json`.

The test-only correction commit is `27f885497634d0f2ed50d293e00603309d34c0cd`, with parent `02725e2e90be6b3145be915be699aa64ce998ed7`. The corrected probe ran before that commit and its manifest therefore correctly records the parent SHA and dirty test file. The 260 recorded runtime/test/build input hashes differ in exactly `tests/contracts/test_w011_geometry.py`.

- `original-02725e2-source-tests.tar.gz`: complete tracked runtime, tests (including fixtures and support), and pyproject inputs at the frozen parent. Documentation is not included; this is a replay snapshot for the named targeted node, not a full-suite snapshot.
- `corrected-test.patch.gz`: exact two-line test repair applied to that snapshot, compressed without changing the original diff bytes (including blank context lines).
- `original-manifest.json` / `corrected-manifest.json`: full command, cwd, interpreter, UTC start/end, exit code, elapsed time, maximum RSS, worktree state and SHA-256 for all 260 code/test/build files.
- `original-pytest.txt` / `corrected-pytest.txt`: unmodified complete pytest output for each probe.
- `run_target.py`: original evidence runner, with recorded workspace-specific paths.
- `test-fix-commit.txt`: correction commit identity and change summary.
- `artifact-manifest.json`: byte lengths and SHA-256 values for this evidence bundle.

This targeted pass establishes the repaired witness only. The final full Python 3.10/3.12 matrices, build/install smoke and PM acceptance remain separate evidence. The earlier interrupted `geometry-r2` preflight had no terminal traceback; its observation about an unsupported VT witness did not establish the cause of its progress-marker failure. This complete traceback now establishes the target-order setup failure for the frozen `02725e2` test.
