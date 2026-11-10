# W011 consumed-owner boundary witness repair

This supplement preserves the second Python 3.10 full-matrix failure discovered at source `02725e2e90be6b3145be915be699aa64ce998ed7`, on parameter ID `physical-effective_fin_operator-foreign`. It does not replace that original full-matrix result.

The existing physical owner schema defines `effective_fin_operator` as literal `identity`. Actual `read_inputs` therefore rejects `foreign` with `config / InvalidSchema` at `tech/physical.json#/fin_count_profile/effective_fin_operator`. The former test incorrectly passed this malformed owner through a helper that requires successful W005/W010 input before invoking W011, and failed at that helper's success assertion. This is a test boundary error; the runtime and owner schema already rejected the input.

The repair retains all four original parameter IDs. For the literal schema case, it explicitly checks the actual entry-point error, exact source field and SHA, all five captured files against their actual bytes, and the one completed config record with its captured source. The other three schema-valid but unsupported semantic variants still traverse the complete W011 chain and require error / no draft / unchanged completed, plus the exact `UnsupportedChannelOperator` code, owner field and captured owner SHA. No exception is swallowed, no case is deleted, and no fixture, runtime, schema or expected semantics changes.

The original node was reproduced with Python 3.10: **1 failed in 0.42 s**, exit 1, child maximum RSS 39,444 KiB. After the repair, the entire four-case parameter group ran serially in one process: **4 passed in 182.45 s**, exit 0, child maximum RSS 1,181,168 KiB. No other probe was started for this repair. This is targeted evidence; it is not the final dual-interpreter 1605-test matrix.

Both runs used frozen worktree HEAD `05009b8c57b88d4dc051df2711db79cb8fae5346`. Its runtime is identical to `02725e2`; the earlier target-order test repair and its documentation are already present. The test-only owner-boundary repair commit is `1cb7e1bc654c61690427ac22481b985156d9c9e6`. The corrected run preceded that commit, so its manifest accurately records the parent SHA and dirty test file. Across the 260 recorded runtime/test/build files, only `tests/contracts/test_w011_geometry.py` differs between these two probes.

- `original-05009b8-source-tests.tar.gz`: complete tracked runtime, tests (including fixtures/support), and pyproject inputs at the frozen parent. Documentation is excluded; this snapshot covers the targeted node/group rather than unrelated documentation-dependent full-suite tests.
- `corrected-test.patch.gz`: exact original correction diff bytes, compressed to preserve its blank context lines.
- `original-manifest.json` / `corrected-manifest.json`: exact commands, worktree and interpreter identities, per-file hashes, UTC bounds, exit code, elapsed time and maximum RSS. The original command names one parameter ID; the corrected command names the same function's four-case group.
- `original-pytest.txt` / `corrected-pytest.txt`: complete, unmodified pytest outputs.
- `run_owner.py`: final replay helper for the two commands; the recorded per-run command manifests remain authoritative.
- `environment.json`: interpreter package inventory and shared-container resource limits, recorded after the runs.
- `test-fix-commit.txt`: repair identity and change summary.
- `artifact-manifest.json`: byte lengths and SHA-256 values for this evidence bundle.

The baseline archive and corrected checkout were checked against every recorded input hash. Independent review and the final full matrix are reported separately; this execution note does not claim PM acceptance.
