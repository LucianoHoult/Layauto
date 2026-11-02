# W008 execution and PM handoff

2026-11-02, execution role. This record covers the authorized geometry/base-occupancy component and its evidence. PM acceptance, main integration and later tasks remain pending.

## Recovery, ownership and reviewed identity

The requested and initially observed remote W008 start was `2d5f42258b5a2cf09f686a06c483e2a6915bc48c`. The original Mac checkout was on W003 at `765ae5ef4ebf50e6870c5a978795525261d89ff6`, with an existing `.DS_Store` modification and no staged changes. Work was isolated in `/private/tmp/layauto-w008`; the original checkout was preserved.

During execution, the remote branch advanced to `2560999021f2551793346187e3c4825276cba2ff`. Its diff contains only PM current-work/roadmap/task notes for U06 (production inputs without body tapcell evidence), expressly leaving W008 A1–A8 and the existing synthetic required body input unchanged. The worktree was fast-forwarded, preserving the execution section and all implementation files. The PM documents were not rewritten by execution. Remote main remained `765ff864f4341b91996f70f25723411eebc0d6c2` at that check.

The final [235-file source/test/config/smoke manifest](verification/source-manifest.json) has SHA-256 `30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881`. It covers all runtime files, current tests/fixtures/support, build/typing configuration, README, the reviewed plan and installed smoke script. Each final command receipt binds this identity. Final review binds the same files; subsequent task/review/receipt prose does not change the tested runtime identity. Git publication supplies the reconstructable complete delivery, with final branch SHA verified after push and reported to PM.

## Implementation and correctness

- `normalization/geometry_input.py` reuses the existing W007 receipt/readback validation, then authenticates consumed GDS/site/header/owner/policy/body fields by pure re-decoding from the same captured bytes. It uses explicit completed-record source roles, validates first-acquisition URI spelling and later historical aliases separately, and checks body/header source/top/unit/profile/scope relations. It neither reads files nor accesses or advances a repository.
- `domain/geometry.py` defines immutable exact rectangles, stream keys, units, policies and typed record/content refs. `state/layout_store.py` owns all local drawn records and preservation evidence. Every record remains traceable through original XY, BOUNDARY/XY positions, raw stream, exact REAL8/nominal/delta/ULP and policy-owner refs. Canonical geometry uses integer DBU with exact Fraction conversions; no source snap/rounding occurs.
- `state/coordinate.py` implements `drawn-layer-edges/1`: finite per-layer sorted edge axes, half-open boundary ownership, exact physical/index conversion and rectangle/cell intersections. It has no occupancy storage or legal-route/technology-grid claim. `state/occupancy.py` stores every exact record fragment, including overlapping/duplicate occupants, and regenerates the complete expected projection in its public constructor.
- `normalization/geometry.py` binds the single immutable `BaseOccupancy -> BasePartition -> LayoutDraft` chain to the authenticated input. Neutral state DTOs prove consistency with their supplied evidence; only the aggregate authenticates it against captured bytes. Closed versioned `geometry_codec.py` reruns those constructors on decode, preserving unexpected decoder exceptions and interrupts.
- Geometry semantic digest implements the selected top-plus-rectangle-multiset comparator, preserving multiplicity while ignoring declared nonsemantic stream/vertex order. Provenance/content identities additionally bind source positions, raw preservation, units and policies. W007 source, target, all differences and seeds remain separate.

Normal input has **40 local drawn records**, of which **38** are projected and **2** (BOUNDARY/MARKER under the selected policy) remain layout-only. The base index contains **41 fragments**: the long LI record crosses four y intervals. Six external body-context shapes remain independent input evidence. The special cut-islands stream has four drawn records and three base fragments; raw LI area remains 80 nm². The effective 72 nm² cut result and terminal/connectivity interpretation are deliberately not constructed.

## A1–A8 evidence

| Requirement | Actual evidence and result |
| --- | --- |
| A1 actual composition/no IO | Genuine W005 read and W006 prepare_inputs/repository readback feed W007 and W008. Construction/wire roundtrip with file IO and repository reads disabled passes. Semantic artifacts stay equal; attempt stays unsealed with no terminal. Real site/owner/header/source-target alias cases and wrong-run/readback negatives pass. |
| A2 fields/captures | Original bytes are independently re-decoded; coherent value/completed mutations in XY/bbox/layer/stream/units/top/positions/policy and omitted/duplicate records reject. Same-hash role substitution, including an absent original URI, rejects. Full 40 local records and independent body scope are checked. |
| A3 geometry/units | Handwritten full rectangle table, independent REAL8/Fraction arithmetic, exact inverse conversion, negative translation, legal renaming, reordered records/vertices, duplicate/overlap and nonrepresentable pure-conversion cases pass. Existing unsupported stream/nonrectangle reader regressions remain. No fixture/answer changes. |
| A4 reconstruction | Deterministic partition/occupancy rebuild, cross-hash-seed identities, exact min/max boundaries and changed-input/model identity checks pass. No example coordinate or 32×16 witness is used as runtime default. |
| A5 multi-occupancy | Independent per-record subset/area/intersection checks prove full coverage without internal overlap. Overlapping and duplicate records retain all occupants; a named test-only coarse partition holds two disjoint fragments in one cell. VIA/CONTACT remain on their own layer; CUT remains raw. |
| A6 public DTO/error/wire | Missing/foreign records/fragments, wrong refs/schema/units/policy, alias mutation, unknown wire fields and illegal result combinations reject. Coherently forged neutral drafts cannot become successful capture-bound results. Unexpected decoder/builder exceptions and interrupts propagate as the same objects. Dependency checks preserve domain/state isolation from decoders, publication and legacy. |
| A7 scope | Actual composition asserts no annotation/net/component/physical/body/no-change/baseline/terminal claims or publication. Cut-islands is tested only as drawn base; future terminal/CUT/body obligations remain in W008's task table and U06. |
| A8 engineering | Final **730 tests on each interpreter**, including the original 553 and 177 added checks; strict typing **40 modules** on both; fresh wheel and sdist; two brand-new installs (3.11 wheel, 3.10 sdist), pip check and source-external `-I -B` W005–W008/codec/failure smoke all pass. All 86 runtime files in both archives and both installations match the tested manifest. |

Test implementations are [capture binding](../../../tests/contracts/test_w008_capture_binding.py), [geometry and scope](../../../tests/contracts/test_w008_geometry.py), [wire authentication/errors](../../../tests/contracts/test_w008_geometry_wire.py) and [independent byte transformations](../../../tests/contracts/w008_geometry_cases.py). They use actual temporary captured inputs and hand expectations; expected/spec/oracle files are not runtime truth.

## Validation commands, environments and artifacts

The Mac's configured Python 3.11.5 was used to create a temporary dev environment outside iCloud; Python 3.10.22 was installed as a temporary portable interpreter. The original shared environment was not modified. Exact versions and preparation commands are in [environment.json](verification/environment.json).

[receipt.json](verification/receipt.json) records all final command arrays, working directories, elapsed times, exit codes, output hashes and tested identity. Raw logs:

| Check | Python 3.11.5 | Python 3.10.22 |
| --- | --- | --- |
| `python -m pytest tests/unit tests/contracts -q -p no:cacheprovider` | [730 passed, 242.92 s](verification/pytest-311.txt) | [730 passed, 306.09 s](verification/pytest-310.txt) |
| `python -m mypy --cache-dir <temporary cache>` | [40 modules, no issues](verification/mypy-311.txt) | [40 modules, no issues](verification/mypy-310.txt) |
| clean install / dependencies | [wheel install](verification/install-311.txt), [pip check](verification/pip-check-311.txt) | [sdist install](verification/install-310.txt), [pip check](verification/pip-check-310.txt) |
| outside-source `python -I -B wheel_smoke.py <absolute fixture>` | [passed, including CR-01](verification/smoke-311.txt) | [passed, including CR-01](verification/smoke-310.txt) |

`PYTHONDONTWRITEBYTECODE=1` was set for checks. The two final installation environments were newly created as `/private/tmp/layauto-w008-final-installed-311` and `...-310`; creation receipts are included. The installed [smoke script](verification/wheel_smoke.py) checks site-packages origin and prints all runtime file hashes. [Installation identity](verification/installation-identity.json) compares those actual files and records direct_url metadata. Pip 23.0.1 leaves the local sdist's archive_info empty; its actual install command, input archive identity, source URI and complete installed-file equality are retained rather than inventing a metadata hash.

`python -m build --outdir docs/tasks/W008/verification/packages` produced the attached fresh [wheel](verification/packages/layauto-0.2.0-py3-none-any.whl) and [sdist](verification/packages/layauto-0.2.0.tar.gz); [raw build log](verification/build.txt) and [package identity](verification/package-identity.json) are included. Wheel SHA-256 is `64526a5b675048c55505fe4d81fa95408ca74c7c91176c1a4a098cafbca5740f`; sdist SHA-256 is `e600e0735dadae75248675fcc4ec18355b48a29847e4af4424714bc5ec5345b4`.

## Review corrections and retained limits

The [independent plan review](plan-review.md) required explicit body/header cross-document bindings (IR-01), amended and independently closed before implementation. The [independent code review](code-review.md) exposed CR-01: absent first-acquisition URI could be mistaken for a historical alias. Execution added exact first-role selection checks, genuine shared-target alias support, 15 negative role variants, nested input/result wire rejection and installed smoke regression. The reviewer owns the original finding and closure; execution does not substitute tests for that independent decision.

[pre-cr01](verification/pre-cr01/) preserves the earlier 713-test matrix, packages and identities, which did not detect the defect. Only the corrected 730-test logs and `30b4e446…` manifest support final delivery. The original reproducer and affected module snapshot remain in the review attachments.

Not implemented or validated here: a full process/technology coordinate model or legal routing/movement space; effective CUT Boolean and gate-terminal splitting; spatial annotation, physical connectivity, body/extraction/mandatory closure; complete ProposedInitialState, baseline/seal/CAS, ECO/no_change/Stage6; real Calibre/Virtuoso/PDK, production admission, isolated-server behavior, other operating systems or other interpreter versions. The existing synthetic required-body contract remains. U06 production missing-body scenarios are a separately recorded future obligation, not a new W008 optional-input mode. No legacy runtime/checks or fixture generators were used to create this implementation.

Next action is PM receipt against the published branch SHA, requirements, evidence and independent closure. Execution does not accept W008, merge main, delete the branch or start another task.
