# W008 PM evidence audit

Result: **0 must-fix findings; 32/32 direct evidence consistency checks pass.**

Audited delivery: `aced62b0adda35fe7bcd8284a7354badc5b03649`; local HEAD: `baad5347627db194649430cf6b0f5ebf0aa1165e`. The later commit changes only `docs/current-work.md` and `docs/roadmap.md`.

Direct checks: all **235** source/test/config/smoke manifest entries match both local files and delivered Git objects; the manifest exactly covers tracked runtime/tests plus README, build/typing config, plan and installed smoke. All **84** evidence-manifest entries and **13** command receipt/output hashes match. Both actual attached package archives contain exactly **86** runtime files matching final source bytes; wheel RECORD hashes and sizes match. Recorded installed-file manifests from both execution and reviewer smoke logs match the same 86 source files, with isolated site-packages origins and identical checks.

Final and pre-CR01 evidence are distinct. The prior 713-test records remain historical; only README, input adapter, capture/wire regressions and installed smoke changed between the two 235-file snapshots. Corrected adapter hash and preserved pre-fix module match their respective manifests. All accepted fixtures/support, W003-W007 historical reports, W005/W006 implementation and W007 core normalizers remain unchanged. The sole existing test change is the reviewed W007 dependency guard's specific exceptions for W008 captured-byte decoders and pure state construction.

Adopted execution evidence (not rerun here): Python **3.10.22: 730 passed in 306.09s**, Python **3.11.5: 730 passed in 242.92s**; strict mypy each **40 source files**; fresh build, two clean installations and source-external smokes. Original Mac installation directories were not accessible in this audit. Python 3.10 sdist direct_url lacks an archive hash as explicitly documented; exact install input URI, attached artifact hash, and recorded 86 installed-file hashes agree. No missing metadata is invented.

This child audit ran only standard-library file/hash/archive/Git checks. It did not import or test product code, rerun build/install, change repository files, accept W008, merge, or start another task. Parent PM owns acceptance and separate local verification.

Artifacts: `check_evidence.py`, `checks.json`, `audit-output.txt`, `audit-receipt.json`. Reproduce with `python check_evidence.py /workspace/Layauto`.
