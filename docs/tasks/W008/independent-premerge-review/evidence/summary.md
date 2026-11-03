# W008 independent A8 evidence audit

Reviewer `/root/evidence_audit`, 2026-11-03. No W008 implementation or original review participation. Read-only audit of `131f66dfadd77b5fb9073db999d6939051c3addf`, delivery `aced62b0adda35fe7bcd8284a7354badc5b03649`. No historical evidence, product, fixture or task document was modified.

Independent standard-library/Git/archive audit: **29/29 checks passed; must-fix findings 0**. New script, raw output, machine result and command receipt are `audit.py`, `audit-output.txt`, `audit-result.json`, `audit-receipt.json`. Run via `python3 -B run.py /workspace/work/w008-review`; Python 3.12.14 Linux, exit 0. This audit does not import product code.

- All 235 final source/test/config/plan/smoke entries exactly match both the current checkout and delivery Git bytes. The complete tracked runtime/test set plus four named owner files equals the manifest path set; no omitted/extra path. Manifest SHA-256 remains `30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881`.
- All 84 historical evidence entries match delivery Git. The task document's recorded `9f281a9f…` hash was checked at `aced62b` only; its current PM additions intentionally differ. The remaining 83 entries match current bytes. Historical manifest unchanged.
- All 13 final command receipts exactly match their individual JSON records, source identity and raw-output hashes, with recorded return code 0. Final 730-test logs are separate from pre-CR01 713-test logs. Recorded Python 3.10.22/3.11.5 environments, two 40-module strict checks and commands are internally consistent.
- Actual wheel and sdist each contain all 86 runtime files equal to final source hashes. Full wheel RECORD member set, sizes and hashes independently verified. Wheel `64526a5b675048c55505fe4d81fa95408ca74c7c91176c1a4a098cafbca5740f`; sdist `e600e0735dadae75248675fcc4ec18355b48a29847e4af4424714bc5ec5345b4`.
- Both recorded clean-install origins, 86 installed runtime hashes, source-external `-I -B` commands and creation/install receipts agree with source/artifact identities. Recorded execution and original review smoke outputs agree exactly. Python 3.10 pip metadata has empty archive_info, as previously disclosed; recorded install path, actual attached archive identity and installed-file hashes are corroboration, not an invented missing hash.
- Product/runtime/tests/config have no post-delivery change. Fixtures, support, unit tests, W005/W006 implementation, architecture and legacy are unchanged from main. PM saved evidence's 15 hashes all match.

The old PM audit script was inspected but not replayed: it requires historical `baad534` HEAD and writes beside itself. This audit uses a new script and new output directory.

Adopted evidence: original Mac Python 3.10/3.11 full suites, strict typing, build, clean installations and installed smoke execution. Direct checks here authenticate their artifacts/logs/recorded hashes; they do not establish independent access to original Mac installation trees or rerun those commands. Product tests/typing/smokes are outside this delegated audit. No evidence identity gap requiring merge blockage was found within this scope.
