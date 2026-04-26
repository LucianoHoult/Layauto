# Layauto Architecture Roadmap

**Purpose.** Living tracker for the multi-milestone architectural evolution of the Layauto layout pipeline. This document is the canonical handoff artifact: any new contributor (human or Claude session) should read it first, re-verify the file/line references in [Verification Snapshot](#verification-snapshot), then pick the next milestone from [Milestone Roadmap](#milestone-roadmap).

**Last verified:** 2026-04-26 on branch `claude/review-arch-plan-Li1Az` (post-M2).

**How to update.**
- When a milestone moves status, flip its checkbox and append a [Change Log](#change-log) entry (date, milestone, what changed).
- When the verification snapshot drifts (lines move, files renamed), re-run the spot checks and update the table + the "Last verified" stamp.
- Keep this doc lean. Implementation details belong in PR descriptions; design decisions belong in [Architectural Principles](#architectural-principles); progress tracking belongs in the milestone blocks and change log.
- Source for sections [A](#a-three-sources-of-truth-and-annotation-inversion)–[D](#d-annotation-depth-and-incompleteness) and [M1](#m1--unify-editop-and-route-writeback-through-a-decoder)–[M7](#m7--virtuoso-skill-and-calibre-drclvs-closure) is the user's design discussion archived in this branch's PR thread.

---

## Context

The Layauto pipeline today (`pipeline/run_mvp.py`) performs a narrow demo task: resize an inverter buffer (NMOS/PMOS `nfin` 5↔7 etc.) by reading existing layout JSON, computing parameter-level edits, and writing a new GDS. The MVP works, but the architecture has known faults that block expansion to general device-graph edits:

1. Two competing `EditOp` definitions (one in `core/diff.py`, one inside `core/solver.py`) with hardcoded per-layer geometry recomputation in `apply_edits_to_layout_data`.
2. The CSP engine (`core/csp_engine.py`) is consulted as a sanity-check but does not actually drive resize decisions; geometry is computed directly in `solver.resize_device`.
3. The parser is **net-JSON-primary**: `io_adapters/parser.py` builds `Net` objects first, treats GDS bbox JSON as an afterthought. This breaks down once unannotated shapes (LVS-incomplete) or shape-level edits matter.
4. Only A-tier (1D track) layers participate in CSP. B-tier (2D cell: OD, VIA, cuts), C1 (derived markings: NWELL, BOUNDARY, …), and C2 (editable annotations: DIODE, ESD markers) are either bypassed or hardcoded.
5. SKILL emission is a `printf` placeholder; Calibre is dummy JSON only.

This document captures the agreed evolution path: a 7-milestone refactor that does **not** rewrite from scratch, preserves the current MVP byte-level golden, and progressively pulls each layer category into the right abstraction.

---

## Verification Snapshot

The roadmap below assumes specific file/line locations. These were confirmed on the date stamped above. Any contributor picking up the work should re-run the checks (file paths and line ranges drift with refactors).

| # | Claim | Where (verified 2026-04-26) | State |
|---|-------|-----------------------------|-------|
| 1 | ~~Two `EditOp` classes coexist~~ | Single canonical class at `core/diff.py:16-40`; `core/solver.py:50` imports it | resolved by M1 (2026-04-25) |
| 2 | ~~Per-layer hardcoded y1/y2 in writeback~~ | `apply_edits_to_layout_data` removed; writeback consolidated in `core/decoder.py::WritebackDecoder` (`pipeline/run_mvp.py:298-302` is the sole call site) | resolved by M1 (2026-04-25) |
| 3 | ~~`resize_device` bypasses CSP for geometry~~ | `resize_device` is the L3 macro at `core/solver.py:226-322`; LI cell-level changes go through `core/atomic_ops.py::modify_segment` (L2 → CSP); FIN/OD/POLY emitted as L1 via the non-CSP side-channel pending M3/M4/M5 | resolved by M2 (2026-04-26) |
| 4 | ~~CSP engine has only `checkpoint`/`restore`~~ | Engine exposes `propose_assign` / `propose_release` / `commit_with_delta` at `core/csp_engine.py:206-285`; trail captures `(pos, prev_domain, prev_assignment)` so `restore` reverts both | resolved by M2 (2026-04-26) |
| 5 | Anchor-layer propagation filter exists | `core/csp_engine.py:265-269` | OK to keep |
| 6 | Parser is net-primary, bbox auxiliary | `io_adapters/parser.py:71-200`; M2 added a parser-side `bbox_nm` stamp on `TrackSegment` so L1 EditOps can carry the layout's pixel-accurate rectangle, but the inversion (shape_pool primary) is still pending | drift target |
| 7 | `OccupantType.BLOCKAGE` exists and is used by solver, but not for unannotated shapes | `core/data_model.py:21-28`, `core/solver.py:45` | half-built |
| 8 | `OccupantType.DEVICE_GATE` / `DEVICE_DIFF` defined but unused; no `CUT` | `core/data_model.py:21-28` | placeholder only |
| 9 | `MultiLayerGrid` is 1D-track only; no `CellOccupancy` | `core/grid.py:87-240` | not built |
| 10 | No net-equivalence union-find in CSP | `core/csp_engine.py` (whole file) | not built |
| 11 | NWELL / BOUNDARY produced by hardcoded formulas | Loops removed from `pipeline/run_mvp.py` in M1c; formulas live as transitional Phase 2 helpers in `core/decoder.py` (`_derive_nwell`, `_derive_boundary`); the M2 milestone deleted the LI/POLY Phase 2 helpers; NWELL/BOUNDARY remain pending M5 | drift target (smaller surface, awaiting M5) |
| 12 | No `core/drc_derivator.py`; no `is_derived` field | absent | not built |
| 13 | No `core/macros/` directory; no `pick_macro` dispatch | absent — but `resize_device` is now an explicit L3 macro inside `core/solver.py` and the M6 dispatch table will lift it into `core/macros/` | half-built |
| 14 | `diff_to_edit_ops` handles add/remove only (no device-level) | `core/diff.py:73-81` | drift target |
| 15 | SKILL emitter is `printf` placeholder | `io_adapters/writer_skill_script.py:76-78` | drift target |
| 16 | Three dummy Calibre JSON generators | `dummy/gen_buffer_layout.py:364, 402, 434` | OK for now |
| 17 | Per-layer DRC rule registration | `core/drc_constraints.py:131-161` | OK to keep |
| 18 | Layer map has no tier markers | `tech/layer_map.py:8-18` | drift target |
| 19 | Six-stage pipeline order: diff_cdl → build_layout_model → setup_engine → load_existing_layout → resize_device → apply_edits → write_gds | `pipeline/run_mvp.py:222-411` | OK structure |
| 20 | L2 atomic ops module exists with `release_segment_cells` / `assign_segment_cells` / `modify_segment` | `core/atomic_ops.py` (M2 minimal subset; `extend_od`, `extend_poly`, `add/remove_fin_strip`, `add/remove_cut_cell`, `mark_shared_diffusion` deferred to M4) | half-built |

---

## Architectural Principles

### A. Three sources of truth and annotation inversion

- **GDS `shape_pool` is geometric truth** — complete, byte-precise.
- **CDL `Device`/`Net` is semantic truth** — what the circuit means.
- **LVS is incomplete annotation** — it binds geometry to semantics, but coverage is never guaranteed. Some shapes are correctly LVS-tagged, others (filler, ESD, dummies, hand-edits) are not.

The current parser is net-primary: it builds nets from LVS JSON, then attaches bbox geometry as an aside. This must invert. The new design:

1. Build `shape_pool` from GDS first — every shape is captured with full geometry.
2. Apply LVS as **annotation overlay** — a shape gets `net_id` / `device_id` / `pin_role` only if LVS provides them.
3. Unannotated shapes remain in `shape_pool` and project into CSP as `BLOCKAGE` occupants. They obstruct edits but carry no net identity.

### B. Tier-based layer dispatch

Layers are not equivalent; their physical role determines the right abstraction. Four tiers:

| Tier | Layers | Data structure | CSP participation |
|------|--------|----------------|-------------------|
| **A** (1D track) | FIN, POLY, LI, M1 | `TrackSegment` | Yes (current grid) |
| **B** (2D cell) | OD, VIA0, CPO, M0_CUT, FIN_CUT | `CellOccupancy(track_a, track_b)` with `owner_device_id` + `shared_with[]` (OD); `OccupantType.CUT` for cutters | Yes (new) |
| **C1** (derived marking) | NWELL, VT, PP, NP, BOUNDARY, DNW | No grid; pure-function derivation from A/B delta + Device metadata | No — derivator output |
| **C2** (editable annotation) | DIODE, ESD, TEXT marker | No grid, no derivation; `ShapeRecord` direct edit | No |

Two specific B-tier behaviors:

- **Diffusion sharing.** OD cells use `owner_device_id` as primary key. Devices that share S/D add themselves to the cell's `shared_with[]` list. Two adjacent gates with the same `owner` + `shared_with` set on the OD cells between them physically share diffusion. SKILL/GDS still emits a single OD shape.
- **CUT semantics.** A `CUT` occupant in `csp_engine` blocks `union` of net-equivalence classes across the cut location. Adding a POLY_CUT mid-span breaks one net into two; removing it re-merges them.

### C. Four-layer atomic-edit architecture

```
L4 Pipeline   :  diff_cdl → pick_macro → apply → writeback
L3 Macro      :  device_resize | device_add | device_remove | net_reroute |
                 buffer_insert | share_diffusion | split_diffusion |
                 add_cut | remove_cut
L2 Atomic op  :  add/remove/modify_segment | add/remove_via |
                 add/remove_cell_occupancy | extend_od | extend_poly |
                 add/remove_fin_strip | mark_shared_diffusion |
                 add/remove_cut_cell | update_device_metadata
L1 Shape rec  :  ShapeAdd | ShapeRemove | ShapeModify   (the only EditOp)
```

**Strict responsibility split** — three sources of truth maintained independently:

- **L2 ops** *only* submit cell-level proposals (a batch of `assign`/`release`) to the CSP engine. They do **not** produce L1 records, do **not** mutate `LayoutModel`, and do **not** decide feasibility.
- **CSP engine** receives proposals → runs DRC propagation + net-equivalence incremental update → returns feasibility + cell delta → commits or restores.
- **Decoder** subscribes to CSP commit deltas → derives L1 `EditOp`s and updates the `LayoutModel` `TrackSegment` / `CellOccupancy` indexes. The decoder is the *sole* holder of `MultiLayerGrid.segment_to_physical`.
- **`shape_pool`** consumes L1 `EditOp`s to update geometric truth.

L3 macros use `engine.checkpoint`/`restore` for transactional bracketing. `device_resize`, for example, expands a metadata delta into a sequence of `extend_od` + `extend_poly` + `add/remove_fin_strip` calls inside a single transaction.

**Non-CSP side-channels** (parallel to the main path):
- C1 derived markings → `drc_derivator` subscribes to commit deltas, emits L1 directly.
- C2 editable annotations → L3 may emit L1 directly without entering CSP.
- Pure metadata updates (e.g., non-geometric device parameters) → `update_device_metadata` writes Device fields only; no L1, no CSP.

### D. Annotation depth and incompleteness

- Annotation atomicity equals edit atomicity, dispatched per tier:
  - **A**: rectangle-level → copies into `TrackSegment` fields.
  - **B**: rectangle-level → rasterizes to cells; `pin_role` inferred from gate position; shared S/D segments tagged via `shared_with`.
  - **C1**: no annotation; derivator generates from rules.
  - **C2**: rectangle-level annotation attached to `ShapeRecord`; never enters CSP.
- Every atomic carries identity (`net_id` / `device_id` / `pin_role`). Every `ShapeEditRecord` carries a **provenance backlink** pointing to the L3 macro / L2 op / derivator rule that produced it. Used for: blast-radius computation, conflict localization, DRC/LVS feedback closure.
- **Four conservative rules for unannotated shapes** (LVS incompleteness):
  1. Unannotated shapes enter CSP as `BLOCKAGE` (currently absent).
  2. On CSP commit, the engine exports an "affected cell neighborhood" delta; derivator and decoder re-evaluate unannotated shapes inside it.
  3. At parse time, run geometric-overlap cross-check; tag suspicious shapes `SUSPECT_CONNECTED_TO_*`.
  4. Default conservatively: don't traverse, don't silently delete, don't auto-merge, treat collisions as real conflicts.

---

## Milestone Roadmap

Each milestone has a status checkbox (Not started / In progress / Done / Blocked), an owner field, and a fixed structure: Goal / Files touched / Change outline / Acceptance / Dependencies / Risks. None of this is detail to function-signature level — that belongs in PR descriptions.

### M1 — Unify `EditOp` and route writeback through a decoder

- **Status:** [x] Done (2026-04-25)
- **Owner:** Claude (`claude/m1-decoder-writeback`)
- **Goal.** Eliminate the duplicate `EditOp` between `core/diff.py` and `core/solver.py`. Replace per-layer hardcoded geometry recomputation in `apply_edits_to_layout_data` with a decoder that consumes a unified `EditOp` stream.
- **Sub-milestones (all complete).**
  - **M1a (Done, 2026-04-25):** Deleted the duplicate `EditOp` in `core/solver.py`; canonical class lives at `core/diff.py:16-37` with all four op_types (`remove_shape`, `add_shape`, `modify_shape`, `resize_device`).
  - **M1b (Done, 2026-04-25):** Built `core/decoder.py::WritebackDecoder` — Phase 1 applies explicit EditOps (FIN remove by center-Y match; OD modify by old-bbox match), Phase 2 derives geometry the solver does not yet emit (POLY span, LI shrink + via-coverage extension, NWELL/BOUNDARY extents), Phase 3 updates params + device metadata. The Phase 2 surface is the seam where the M5 derivator and richer M2 EditOps will land.
  - **M1c (Done, 2026-04-25):** Removed the legacy `apply_edits_to_layout_data` function from `pipeline/run_mvp.py`; the pipeline now calls `WritebackDecoder(grid, config).apply(...)` once at `pipeline/run_mvp.py:297-301`.
- **Files touched.**
  - `core/diff.py` — sole `EditOp` definition (M1a).
  - `core/solver.py:26` — imports `EditOp` from `core.diff` (M1a).
  - **New** `core/decoder.py` — `WritebackDecoder` class (M1b).
  - `pipeline/run_mvp.py` — removed 125-line `apply_edits_to_layout_data`; replaced with single decoder invocation (M1c).
  - **New** `tests/unit/test_decoder.py` — five direct decoder tests.
- **Acceptance (verified).** Pipeline buffer resize (5/7 → 4/6) byte-identical: JSON, CDL, and `resize_report.txt` byte-equal under fixed `PYTHONHASHSEED`; GDS polygons identical (30/30 (layer, datatype, points) tuples match). Pytest 38/38 green (33 existing + 5 new decoder tests).
- **Dependencies.** None — first PR.
- **Notes for downstream milestones.**
  - `core/grid.py::segment_to_physical` was *not* strengthened in M1; the decoder operates on shape dicts directly using EditOp bbox truth. M4 will add cell-grid coordinate translation when B-tier `CellOccupancy` lands.
  - The decoder's Phase 2 derivation (POLY span, NWELL/BOUNDARY) is where M5's `drc_derivator.py` will plug in. Each Phase 2 helper is named `_derive_*` to make the eviction surface explicit.
  - The shrink-then-extend ordering for LI (Phase 2 `_shrink_li_sd_bars` followed by `_extend_li_for_vias`) preserves the legacy ordering coupling identified in the original risk note.

### M2 — CSP genuinely drives resize decisions, with strict layer-1/2/3 split

- **Status:** [x] Done (2026-04-26)
- **Owner:** Claude (`claude/review-arch-plan-Li1Az`)
- **Goal.** Demote `resize_device` to a true L3 macro that expands into L2 primitives. L2 only proposes cell-level changes to the engine; the decoder synthesizes L1; the engine handles feasibility and transactions.
- **Sub-milestones (all complete).**
  - **M2a (Done, 2026-04-26):** Strengthened the CSP engine trail format to `(pos, prev_domain, prev_assignment)` so `restore` reverts both. Added `propose_assign` / `propose_release` / `commit_with_delta` (`core/csp_engine.py:206-285`). `unassign` is documented as legacy and superseded by `propose_release`. Six new unit tests cover round-trip restore, trail truncation on commit, propose-assign-failure rollback, and release-then-reassign within a transaction.
  - **M2b (Done, 2026-04-26):** Created `core/atomic_ops.py` with the M2 minimal L2 subset (`release_segment_cells`, `assign_segment_cells`, `modify_segment`). `AtomicResult.failed_pos` localises infeasible proposals. The fuller primitives listed in §C (`extend_od`, `extend_poly`, `add/remove_fin_strip`, `add/remove_cut_cell`, `mark_shared_diffusion`) wait for the B-tier `CellOccupancy` work in M4 — FIN/OD/POLY currently flow on the non-CSP side-channel.
  - **M2c (Done, 2026-04-26):** Refactored `resize_device` (`core/solver.py:226-322`) into the L3 `device_resize` macro: opens a checkpoint, drives LI cell-level changes through `atomic_ops.modify_segment`, emits L1 records, and `commit_with_delta`s on success / `restore`s on infeasibility. Per-helper split: `_emit_fin_removes`, `_emit_od_modify`, `_reshape_li_sd_bars`, `_emit_poly_modify_if_endpoint_changed`. Stricter device-marker filtering on LI (NMOS macros only touch `li_nmos_*`, PMOS only `li_pmos_*`) fixes the M1-era cross-net leakage in the resize report.
  - **M2d (Done, 2026-04-26):** Deleted the transitional Phase 2 helpers `_shrink_li_sd_bars`, `_derive_poly_span`, `_extend_li_for_vias` from `core/decoder.py`. Phase 1 grew `_apply_li_modifies` and `_apply_poly_modifies`; the latter accepts partial bboxes (`None` sentinels) so PMOS macros can shift POLY y2 without touching y1 / x. `_derive_nwell` and `_derive_boundary` remain — M5 will evict them.
  - **M2e (Done, 2026-04-26):** Added `bbox_nm: Optional[Tuple[int,int,int,int]]` to `TrackSegment` (`core/data_model.py`); `io_adapters/parser.py` stamps the layout's pixel-accurate rectangle on each segment. The L3 macro emits `EditOp.old_bbox = seg.bbox_nm` directly, avoiding off-by-1nm drift on odd-width layers (LI = 17 nm) that round-tripping through `segment_to_physical` would otherwise introduce.
- **Files touched.**
  - `core/csp_engine.py` — new trail format + transactional API (M2a).
  - **New** `core/atomic_ops.py` — L2 primitives subset (M2b).
  - `core/solver.py` — L3 macro + helpers (M2c).
  - `core/decoder.py` — Phase 1 grows; Phase 2 LI/POLY helpers deleted (M2d).
  - `core/data_model.py` + `io_adapters/parser.py` — `TrackSegment.bbox_nm` stamping (M2e).
  - **New** `tests/unit/test_atomic_ops.py` (4 tests); `tests/unit/test_csp_engine.py` (+6 transactional API tests); `tests/unit/test_solver.py` (+2 rollback / commit tests).
- **Acceptance (verified).**
  - Conflict-injection: monkey-patching `atomic_ops.modify_segment` to return failure causes `resize_device` to return `success=False` and the engine snapshot to match the pre-call snapshot byte-for-byte (`tests/unit/test_solver.py::test_resize_device_rolls_back_engine_on_csp_conflict`).
  - L2-level conflict: extending a segment into a cell pre-assigned to a conflicting net surfaces `failed_pos` and leaves the engine restorable (`tests/unit/test_atomic_ops.py::test_modify_segment_extension_conflict_returns_failure`).
  - Byte-golden: pipeline GDS, JSON, and CDL outputs are byte-identical to the M1 baseline under fixed `PYTHONHASHSEED`. (Note: `output/resize_report.txt` evolves intentionally — the macro now emits LI modify_shape ops with full bboxes and a POLY modify_shape op with partial bbox, lifting derivation that previously hid in the decoder.)
  - Pytest 50/50 green (38 pre-M2 + 12 new).
- **Dependencies.** M1.
- **Notes for downstream milestones.**
  - CSP cell delta from `commit_with_delta` is currently **informational** — the macro still emits L1 records directly. M3+ will drive L1 synthesis from the cell delta, at which point the decoder's Phase 1 LI/POLY apply paths can be re-keyed by delta rather than EditOp.
  - The `device_y_marker` desc-substring filter inside `_reshape_li_sd_bars` is the disambiguator for a net (e.g. `OUT`) that fans across NMOS and PMOS sides. M4's `CellOccupancy.owner_device_id` replaces this string match.
  - `TrackSegment.bbox_nm` is the seam where the M3 `ShapeRecord` provenance backlink will plug in. The current single-tuple field becomes a `ShapeRecord` reference there.
  - The L3 macro emits POLY ops with **partial bboxes** (`None` sentinels). When `shape_pool` lands in M3, the decoder's `_apply_poly_modifies` partial-edit path can be re-keyed off `ShapeRecord` ids and the sentinel pattern retired.

### M3 — `shape_pool` parser inversion + unannotated-shape BLOCKAGE projection

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Invert the parser to "GDS `shape_pool` is geometric truth, LVS is annotation overlay." All unannotated shapes enter CSP as `BLOCKAGE`.
- **Files touched.**
  - `io_adapters/parser.py:71-198` — `parse_bbox_by_layer` becomes a `shape_pool` builder; `parse_calibre_net_query` becomes annotation-apply.
  - `core/data_model.py` — add `ShapeRecord` with `provenance` field; enable backlinks.
  - `core/csp_engine.py` — accept `BLOCKAGE`-typed occupants on all relevant layers (currently only used by solver setup).
  - `dummy/gen_buffer_layout.py` — deliberately retain a few unannotated filler shapes as test scaffolding.
- **Change outline.**
  - Geometric-overlap cross-check: shapes touching multiple LVS-tagged neighbors but lacking a tag get `SUSPECT_CONNECTED_TO_*`.
  - Conservative defaults: don't traverse, don't silently delete, don't auto-merge.
- **Acceptance.** An unannotated LI stub blocking a resize path causes the solver to return `infeasible` rather than silently overwriting it. Annotation coverage report emitted.
- **Dependencies.** M1 (decoder must understand `ShapeRecord`).
- **Risks.** Dummy data may not exercise real LVS gaps — extend `gen_buffer_layout` first.

### M4 — B-tier `CellOccupancy` + diffusion sharing + CUT + net-equivalence

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Promote 2D-grid layers (OD, VIA0, CPO/M0_CUT/FIN_CUT) into first-class `CellOccupancy(track_a, track_b)`. OD cells carry `owner_device_id` + `shared_with[]`. CUT is its own occupant type that breaks net-equivalence. CSP engine grows an internal net-equivalence union-find, updated incrementally.
- **Files touched.**
  - `core/data_model.py:21-29` — activate `DEVICE_GATE` / `DEVICE_DIFF`; add `CUT`; `CellOccupancy` carries `owner_device_id` + `shared_with[]`.
  - `core/grid.py:87-240` — `MultiLayerGrid` gains a cell-grid dimension.
  - `core/csp_engine.py` — cell-level conflict detection; built-in net-equivalence union-find; `union` precondition includes "no CUT between adjacent cells"; commit also exports net-equivalence delta.
  - `core/drc_constraints.py` — cell-level rules for OD / VIA0; CUT-to-gate, CUT-to-via, CUT-to-CUT spacings.
  - `io_adapters/parser.py` — FIN / POLY / OD / CUT route through `CellOccupancy` projection; identify shared S/D segments and stamp `shared_with`.
  - `tech/layer_map.py` — add cut layer numbers + tier markers.
- **Change outline.**
  - Parser tier-dispatches via `tech/layer_map.py` to `TrackSegment` / `CellOccupancy` / derived.
  - The hardcoded FIN / OD / POLY loops in `pipeline/run_mvp.py` are fully replaced by M1 decoder + M4 cell projection.
  - Shared S/D semantics: between two adjacent gates, the OD cells' `owner_device_id` is the primary device and `shared_with` lists secondaries. SKILL/GDS still emits a single OD shape.
  - Net-equivalence API: `engine.net_of(cell)` / `engine.connected_cells(net_id)` for LVS cross-check and decoder provenance.
- **Acceptance.**
  - Two devices share an OD segment → CSP recognizes a single diffusion region, no conflict.
  - LI laid across two adjacent S/D cells → net-equivalence auto-merges.
  - POLY_CUT inserted mid-span on a full-span poly → net-equivalence splits into two; remove cut → re-merge.
  - Fin removal via cell release → downstream constraints recompute automatically.
- **Dependencies.** M1, M2.
- **Risks.** Performance regression as layer count + incremental net-equiv grow — instrument `propagate` from this milestone. Shared-tag identification depends on gate-position precision; use golden references.

### M5 — C1 derivator (NWELL / VT / PP / NP / BOUNDARY / DNW)

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Pull all C1 derived markings out of `pipeline/run_mvp.py` hardcoded loops. A `drc_derivator` subscribes to CSP commit deltas and emits these shapes as a pure function of A/B-tier state + Device metadata.
- **Files touched.**
  - **New** `core/drc_derivator.py` — subscribes to CSP commit deltas; pure-function derivation of C1 shape sets.
  - `core/decoder.py` (existing, M1) — delete the transitional Phase 2 helpers `_derive_nwell` and `_derive_boundary`; the derivator now emits these as L1 EditOps post-CSP-commit, consumed by the decoder's Phase 1 path.
  - `core/drc_constraints.py` — tabulate NWELL-to-OD, VT-to-OD, PP-to-NMOS, NP-to-PMOS, BOUNDARY margin, DNW-to-NWELL rules.
  - `core/data_model.py` — add `ShapeRecord.is_derived`; the decoder rejects direct edits to derived shapes.
- **Change outline.**
  - Derivator inputs: CSP state + Device metadata + rule table. Output: L1 `EditOp` through the M1 decoder.
  - Subscription granularity: per-cell-delta affected neighborhood. Local recomputation, not full rebuild.
  - C2 markers (DIODE / ESD / TEXT) are *not* in the derivator — they go through the M3 `shape_pool` direct-edit path.
- **Acceptance.** Across nfin variants, NWELL / BOUNDARY / VT y2 matches MVP golden. Tweaking enclosure parameters in the rule table changes geometry as expected. Editing a C2 marker does not trigger a derivator rebuild.
- **Dependencies.** M3, M4.
- **Risks.** Implicit dependencies on BOUNDARY in the pipeline may not be fully untangled. Underestimating the affected-neighborhood radius will cause silent DRC violations.

### M6 — L3 macro family (device / net / diffusion / cut)

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** With M2 L2 primitives + engine transactions in place, add six new macro families. Validates that the four-layer architecture generalizes beyond resize.
- **Files touched.**
  - **New** `core/macros/{device_add,device_remove,net_reroute,buffer_insert,share_diffusion,split_diffusion,cut_ops}.py`.
  - `core/diff.py` — `diff_cdl` extends to device add/remove + diffusion-share delta + cut delta.
  - `pipeline/run_mvp.py:357` — `pick_macro` dispatch table grows.
- **Change outline.**
  - Macros call only L2; transaction boundaries live at the macro top.
  - `share_diffusion(dev_a.pin, dev_b.pin)` — calls `mark_shared_diffusion` to update `shared_with`, triggers net-equivalence remerge.
  - `split_diffusion(...)` — inverse; if devices are physically adjacent, must call `add_cut_cell` first to ensure isolation.
  - `add_cut` / `remove_cut` — direct calls to `add_cut_cell` / `remove_cut_cell`; CSP recomputes net-equivalence.
- **Acceptance.**
  - CDL gains an inverter → pipeline emits a legal layout.
  - CDL drops a device → released shapes cleared, annotations updated, shared diffusion auto-degrades to single-owner.
  - "Two devices request shared S/D" → `share_diffusion` macro lands legally.
  - "Same poly must be cut" → `add_cut` macro inserts a CPO mid-span and splits the net.
- **Dependencies.** M2, M3, M4.
- **Risks.** L3 risks degenerating into a glue-script layer — enforce layered-call lints. Diffusion split + cut order matters; reversed order produces transient short circuits and must be guarded by engine transactions.

### M7 — Virtuoso SKILL and Calibre DRC/LVS closure

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Replace placeholder SKILL emission and dummy Calibre with real tool integration.
- **Files touched.**
  - **New** `io_adapters/skill_emitter.py` — replaces the `printf` placeholder in `writer_skill_script.py`.
  - **New** `io_adapters/calibre_runner.py` — replaces `dummy/gen_buffer_layout.py` for real LVS/DRC.
  - `pipeline/run_mvp.py` — append DRC/LVS calls and feed results back to L3 macro provenance.
- **Change outline.**
  - SKILL emission walks `shape_pool` + `EditOp` records; every emitted edit gets a provenance comment.
  - DRC/LVS failures → look up provenance → identify responsible macro → trigger M2 transactional rollback.
- **Acceptance.** Real PDK environment: buffer resize → SKILL load → DRC clean → LVS match. Inject a violating edit → DRC fail localizes to the responsible L2 op.
- **Dependencies.** M1–M6 all complete.
- **Risks.** PDK redaction may block end-to-end validation. Keep an injection harness that mocks DRC violations.

---

## Validation Methodology

- **Golden-diff baseline.** Current MVP output is the M0 baseline. M1 through M5 must preserve byte-level identity for the buffer-resize case. Any divergence requires explicit sign-off.
- **Conflict-injection harness, staged.**
  - From M2: LI-vs-VIA collision.
  - From M3: unannotated LI stub blocking a resize path.
  - From M4: OD-share, LI fanning across multiple S/D cells, CPO cutting a net.
  - From M6: diffusion share + diffusion split + cut-add sequencing.
  - From M7: DRC violation injection.
- **Performance instrumentation.** From M4, time CSP `propagate` per layer × track count.
- **Multi-device regression.** From M6, extend `dummy/gen_buffer_layout.py` to inverter / 2-stage buffer / latch.
- **Real-PDK closure.** First exit from dummy environment happens in M7.

---

## Minimal Starter PR

M1 and M2 have landed. The next minimal-blast-radius starter is **M3** — invert the parser to "GDS `shape_pool` is geometric truth, LVS is annotation overlay" and project unannotated shapes into CSP as `BLOCKAGE`. M3 unblocks (a) the M4 B-tier `CellOccupancy` work, because shapes need to enter CSP as cell-typed occupants before the OD-share / CUT semantics can be modelled, and (b) the M5 derivator, which expects a complete shape inventory to subscribe to. The half-built `TrackSegment.bbox_nm` field added in M2 is the natural seam where M3's `ShapeRecord` provenance backlink replaces the per-segment bbox stamp.

---

## Reference Appendix

### Pipeline 6-stage flow

Entry: `pipeline/run_mvp.py::run_full_pipeline()` (line 326). The `__main__` block at line 541 invokes it.

| Stage | Function | Location |
|-------|----------|----------|
| 1. Diff CDL | `diff_cdl()` | `pipeline/run_mvp.py:357` |
| 2. Build `LayoutModel` + `MultiLayerGrid` | `build_layout_model()` | `pipeline/run_mvp.py:376`, impl `io_adapters/parser.py:81` |
| 3. Set up CSP engine | `solver.setup_engine()` | `pipeline/run_mvp.py:388`, `core/solver.py:73` |
| 4. Load existing layout into CSP | `solver.load_existing_layout()` | `pipeline/run_mvp.py:389`, `core/solver.py:137` |
| 5. Solve resize | `solver.resize_device()` | `pipeline/run_mvp.py:398`, `core/solver.py:208` |
| 6. Emit output | `WritebackDecoder.apply()` → `write_gds()` | `pipeline/run_mvp.py:298-302, 305-306` |

The pipeline is **incremental, not from-scratch**: `build_layout_model` reads existing layout, `load_existing_layout` pre-stamps every existing segment as `FIXED`, and the decoder deep-copies + patches per-layer rather than re-laying out. After M2, the decoder's Phase 1 applies explicit FIN / OD / LI / POLY EditOps; Phase 2 derives only NWELL / BOUNDARY (M5 will move those into `core/drc_derivator.py`).

### Dummy Calibre JSONs

All generated by `dummy/gen_buffer_layout.py`. Three artifacts:

1. **`calibre_device_query.json`** — `generate_calibre_device_query()` at line 364.
   ```json
   { "instance": "MN0", "device_type": "NMOS",
     "parameters": { "nfin": 5, "nf": 1, "l": 20, "w": 125 },
     "pins": { "G": "IN", "D": "OUT", "S": "VSS", "B": "VSS" },
     "bbox": { "x1": 27, "y1": 28, "x2": 81, "y2": 152 },
     "fin_y_positions": [40, 65, 90, 115, 140] }
   ```
   Consumer: `io_adapters/parser.py::parse_calibre_device_query()` (line 23) → builds `Device` (`core/data_model.py:172`). Provides `nfin` / `gate_track_idx` / `fin_track_indices` topology metadata for resize.

2. **`calibre_net_query.json`** — `generate_calibre_net_query()` at line 402.
   ```json
   { "VSS": { "type": "power",
              "pins": [["MN0", "S"], ["MN0", "B"]],
              "shapes": [{ "layer": "LI", "x1": …, "y1": …, "x2": …, "y2": …, "desc": … }] } }
   ```
   Consumer: `parse_calibre_net_query()` (`io_adapters/parser.py:60`). Each shape passes through `MultiLayerGrid.physical_to_segment_coords()` to become a `TrackSegment` (`core/data_model.py:99`), then attaches to `Net` (`io_adapters/parser.py:184-198`). This is how the CSP solver learns about routed geometry.

3. **`bbox_by_layer.json`** — `generate_bbox_by_layer()` at line 434.
   ```json
   { "FIN": [{ "x1": …, "y1": …, "x2": …, "y2": …, "net": "", "desc": "fin_nmos_0" }],
     "POLY": [...], "LI": [...], ... }
   ```
   Consumer: `parse_bbox_by_layer()` (`io_adapters/parser.py:71`) — used for grid coordinate mapping and device-layer geometry tracking. Today these layers do not enter CSP; they go through direct hardcoded edit.

### Grid layer dispatch matrix

Mapping in `tech/layer_map.py:8-18`. Tier markers will be added in M4.

| Layer | Today | Target tier |
|-------|-------|-------------|
| FIN | Device metadata + bbox | A |
| POLY | Device metadata + bbox | A |
| OD | Device metadata + bbox | B (with `shared_with`) |
| NWELL | Hardcoded loop | C1 (derived) |
| LI | `TrackSegment` in CSP | A |
| M1 | `TrackSegment` in CSP | A |
| VIA0 | `ViaInstance` on Net (cell position implicit) | B |
| BOUNDARY | Hardcoded loop | C1 (derived) |
| CPO / M0_CUT / FIN_CUT | absent | B (`OccupantType.CUT`) |
| VT / PP / NP / DNW | absent | C1 (derived) |
| DIODE / ESD / TEXT | absent | C2 (annotation) |

### Writeback steps and atomicity

`core/decoder.py::WritebackDecoder.apply()` (post-M1). Inputs: `orig_data` + macro `edit_ops_n` / `edit_ops_p` + new `nfin`. `EditOp` is **shape-level** after M2 (the macro now emits LI bbox-accurate modifies and POLY partial-bbox endpoint shifts in addition to the M1-era FIN remove + OD modify). Phase 2 still derives NWELL / BOUNDARY pending M5.

Steps (line 50-138, sequential per-layer loops):

1. `result = copy.deepcopy(orig_data)` — full in-memory copy (transaction boundary).
2. `for s in result['shapes']['FIN']:` — drop deleted fins.
3. `for s in result['shapes']['OD']:` — adjust `y2` per NMOS/PMOS.
4. `for s in result['shapes']['POLY']:` — adjust `y1` / `y2`.
5. `for s in result['shapes']['LI']:` — shorten S/D contact bars.
6. `for s in result['shapes']['NWELL']:` — adjust `y2`.
7. `for s in result['shapes']['BOUNDARY']:` — adjust `y2`.
8. `io_adapters/gds_io.py::write_gds()` (line 432):
   - Preferred `_write_gds_gdstk()` (line 143-169) — fresh `gdstk.Library`, fresh cell, nested `for layer ... for shape: cell.add(rect)`, then `lib.write_gds(filename)`.
   - Fallback `_write_gds_manual()` (line 208-232) — uses `dummy/gds_writer.py`.
9. JSON written (line 435-436); CDL via `io_adapters/writer_cdl.py::write_cdl()`; report and visualization.

Atomicity:
- **In-memory:** non-atomic; per-layer per-shape accumulation. Mid-failure leaves a half-modified `result`, but it's a deep-copy of input so the original is untouched.
- **File-level:** atomic via single `lib.write_gds(filename)`. Either a complete new file is produced or no file at all (on crash). No tempfile + rename, no rollback.
- **Original GDS is read-only.** Each run rebuilds the output from scratch.

### Key file index

- `pipeline/run_mvp.py` — main pipeline + edit application.
- `core/solver.py` — resize solver + EditOp generation (lines 208-419).
- `core/data_model.py` — `Device`, `Net`, `TrackSegment`, `OccupantType`, `CellState`.
- `core/grid.py` — `LayerGrid` / `MultiLayerGrid`.
- `core/csp_engine.py` — constraint propagation; `anchor_layer` filter at line 250-254.
- `core/drc_constraints.py` — per-layer DRC registration (lines 131-161).
- `core/diff.py` — current `EditOp`; `diff_cdl` and `diff_to_edit_ops`.
- `io_adapters/parser.py` — Calibre JSON → `LayoutModel`.
- `io_adapters/gds_io.py` — GDS write (gdstk + manual fallback).
- `io_adapters/writer_cdl.py` — CDL emission.
- `io_adapters/writer_skill_script.py` — SKILL placeholder.
- `dummy/gen_buffer_layout.py` — three Calibre JSONs.
- `tech/layer_map.py` — layer→GDS code mapping.
- `tech/drc_rules.yaml` — DRC rule deck.

---

## Change Log

Append entries when status flips, when verification snapshot is refreshed, or when architectural sections change. Newest entry on top.

| Date | Author | Change |
|------|--------|--------|
| 2026-04-26 | Claude (`claude/review-arch-plan-Li1Az`) | **M2 complete.** M2a: extended CSP trail to `(pos, prev_domain, prev_assignment)` and added `propose_assign` / `propose_release` / `commit_with_delta` (`core/csp_engine.py:206-285`); 6 new unit tests cover round-trip restore, trail truncation, propose-assign rollback, and intra-transaction release+reassign. M2b: created `core/atomic_ops.py` with the M2 minimal L2 subset (`release_segment_cells`, `assign_segment_cells`, `modify_segment` with `failed_pos` localisation). M2c: refactored `resize_device` (`core/solver.py:226-322`) into the L3 `device_resize` macro, routing LI cell-level changes through L2 + CSP, with stricter device-marker filtering on LI segments. M2d: deleted Phase 2 helpers `_shrink_li_sd_bars`, `_derive_poly_span`, `_extend_li_for_vias` from the decoder; Phase 1 grew `_apply_li_modifies` and `_apply_poly_modifies` (the latter accepts partial-bbox EditOps with `None` sentinels). M2e: added `TrackSegment.bbox_nm` stamping in the parser so emitted L1 `old_bbox` records are pixel-accurate even on odd-width layers (LI = 17 nm). Verification snapshot rows 3, 4 marked resolved; row 11 noted as smaller; new row 20 records the L2 module. Acceptance: `output/buffer_resized.{gds,json,cdl}` byte-identical to M1 baseline; conflict-injection test exercises macro-level rollback; pytest 50/50 (12 new). Resize report now lists 7 ops vs M1's 6 — the macro lifted POLY span derivation (and the M1 cross-net leakage in MN0's report) into explicit L1 EditOps. Minimal Starter PR pointer flipped to M3. |
| 2026-04-25 | Claude (`claude/m1-decoder-writeback`) | Roadmap refinement after M1 implementation: M2 milestone block now records that it deletes the decoder's `_derive_poly_span` and `_extend_li_for_vias` helpers; M5 block records that it deletes `_derive_nwell` / `_derive_boundary`. Verification snapshot row 11 updated — the NWELL/BOUNDARY formulas are no longer in `pipeline/run_mvp.py:130-138` (M1c removed those loops); they are consolidated as transitional Phase 2 helpers in `core/decoder.py` awaiting the M5 derivator. Makes the M1 → M2 / M5 eviction path mechanical rather than implicit. |
| 2026-04-25 | Claude (`claude/m1-decoder-writeback`) | **M1 complete.** M1a: unified `EditOp` (`core/diff.py:16-37`; `core/solver.py:26` imports); duplicate dataclass removed. M1b: built `core/decoder.py::WritebackDecoder` consolidating writeback geometry into Phase 1 (explicit EditOp apply: FIN remove + OD modify) and Phase 2 (derived: POLY span, LI shrink + via-coverage extension, NWELL/BOUNDARY extents). M1c: removed legacy 125-line `apply_edits_to_layout_data` from `pipeline/run_mvp.py`; sole call site is the decoder. Verification snapshot rows 1 and 2 marked resolved. Acceptance: pipeline JSON/CDL/report byte-identical under fixed `PYTHONHASHSEED`; GDS polygons identical (30/30); pytest 38/38 (added 5 decoder tests). Discovery: M1's "decoder consumes EditOp stream" goal is partial — the solver emits EditOps for FIN/OD/LI but not POLY/NWELL/BOUNDARY; the decoder's Phase 2 fills the gap and is the seam where M5's derivator will plug in. |
| 2026-04-25 | Claude (session `claude/check-stream-env-vars-N5suX`) | Initial English roadmap created from Chinese architecture-analysis source. Verification snapshot generated against branch state on this date. All seven milestones marked Not started. |
