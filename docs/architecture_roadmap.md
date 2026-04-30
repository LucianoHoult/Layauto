# Layauto Architecture Roadmap

**Purpose.** Living tracker for the multi-milestone architectural evolution of the Layauto layout pipeline. This document is the canonical handoff artifact: any new contributor (human or Claude session) should read it first, re-verify the file/line references in [Verification Snapshot](#verification-snapshot), then pick the next milestone from [Milestone Roadmap](#milestone-roadmap).

**Last verified:** 2026-04-30 on branch `claude/review-arch-plan-fk4Og` (post-M6b).

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

| # | Claim | Where (verified 2026-04-27) | State |
|---|-------|-----------------------------|-------|
| 1 | ~~Two `EditOp` classes coexist~~ | Single canonical class at `core/diff.py:16-40`; `core/solver.py:50` imports it | resolved by M1 (2026-04-25) |
| 2 | ~~Per-layer hardcoded y1/y2 in writeback~~ | `apply_edits_to_layout_data` removed; writeback consolidated in `core/decoder.py::WritebackDecoder` (`pipeline/run_mvp.py:298-302` is the sole call site) | resolved by M1 (2026-04-25) |
| 3 | ~~`resize_device` bypasses CSP for geometry~~ | `resize_device` is the L3 macro at `core/solver.py:226-322`; LI cell-level changes go through `core/atomic_ops.py::modify_segment` (L2 → CSP); FIN/OD/POLY emitted as L1 via the non-CSP side-channel pending M4/M5 | resolved by M2 (2026-04-26) |
| 4 | ~~CSP engine has only `checkpoint`/`restore`~~ | Engine exposes `propose_assign` / `propose_release` / `commit_with_delta` at `core/csp_engine.py:206-285`; trail captures `(pos, prev_domain, prev_assignment)` so `restore` reverts both | resolved by M2 (2026-04-26) |
| 5 | Anchor-layer propagation filter exists | `core/csp_engine.py:265-269` | OK to keep |
| 6 | ~~Parser is net-primary, bbox auxiliary~~ | M3 inverted: `parse_bbox_by_layer` → `build_shape_pool` is geometric-first (`io_adapters/parser.py:80-100`); `apply_lvs_overlay` (`io_adapters/parser.py:113-160`) stamps `net_id` / `device_id` / `pin_role` onto matching records by `(layer, bbox)` key. `LayoutModel.shape_pool` carries the result; `TrackSegment.shape_record` is the per-segment backlink. | resolved by M3 (2026-04-27) |
| 7 | ~~`OccupantType.BLOCKAGE` exists and is used by solver, but not for unannotated shapes~~ | M3 added `core/csp_engine.py::ConstraintEngine.mark_blockage` and `core/solver.py::LayoutSolver.project_unannotated_blockages`. Pipeline calls the projection in `pipeline/run_mvp.py:262-269` after `load_existing_layout`. No-op for the MVP fixture (zero unannotated LI/M1 shapes); test scaffolding exercises end-to-end. | resolved by M3 (2026-04-27) |
| 8 | ~~`OccupantType.DEVICE_GATE` / `DEVICE_DIFF` defined but unused; no `CUT`~~ | M4a added `OccupantType.CUT` (`core/data_model.py:21-32`); `DEVICE_GATE` / `DEVICE_DIFF` / `CUT` are validated as legal `CellOccupancy.occ_type`s by the dataclass `__post_init__`. M4b/c will activate them in CSP cells and parser projection. | half-built (M4a wired the seam; M4b lights it up) |
| 9 | ~~`MultiLayerGrid` is 1D-track only; no `CellOccupancy` *cell-grid wiring*~~ | M4b added `MultiLayerGrid.b_tier_axes` / `b_tier_cells` plus `register_b_tier_axes()` / `bbox_to_b_tier_cells()` / `set_b_tier_cell` / `get_b_tier_cell` / `b_tier_cells_of()` (`core/grid.py`). Storage is sparse and registration is opt-in per layer; the parser doesn't yet populate it (M4c does that), so the byte-golden pipeline is unaffected. | resolved by M4b (2026-04-27) |
| 10 | ~~No net-equivalence union-find in CSP~~ | M4b added `ConstraintEngine` union-find: `_uf_parent` / `_uf_size` / `_uf_trail` state, `union()` (adjacent + same-net + non-CUT precondition), `net_of()` / `connected_to()` / `connected_cells()` queries, and `commit_with_full_delta()` returning a `CommitDelta(cells, unions)`. `restore` undoes unions in reverse order alongside cell-trail rollback. `mark_cut()` mirrors `mark_blockage` (M3) for stamping CPO/M0_CUT/FIN_CUT cells. The legacy `commit_with_delta` keeps its single-list return. | resolved by M4b (2026-04-27) |
| 11 | ~~NWELL / BOUNDARY produced by hardcoded formulas~~ | M5 lifted both into `core/drc_derivator.py::DRCDerivator`; the constants live in `tech/process_config.yaml` under `derivation:` and on `TechConfig.NWELL_MARGIN_BEYOND_FIN` / `BOUNDARY_MARGIN_BEYOND_FIN`. Decoder Phase 2 is empty; Phase 1 grows `_apply_nwell_modifies` / `_apply_boundary_modifies`. | resolved by M5 (2026-04-28) |
| 12 | ~~No `is_derived` field~~ | M5 lit up the M3 seam: `DRCDerivator._mark_derived` stamps `is_derived=True` and `provenance='drc_derivator._derive_<layer>'` on every C1 shape it owns. M6 adds the decoder's rejection of macro-emitted edits to those shapes. | resolved by M5 (2026-04-28) |
| 13 | ~~No `core/macros/` directory; no `pick_macro` dispatch~~ | M6a created `core/macros/` with `cut_ops.py` (`add_cut` / `remove_cut`) and `share_diffusion.py` (`share_diffusion`); M6b added `split_diffusion.py` and `pick_macro.py` (`MacroCall`, `pick_macro`, `pick_macros`). `pipeline/run_mvp.py` Stage 5 drives Stage 5 through `pick_macros(...)`. The dispatch table currently routes `nfin` → `device_resize` only; M6d adds device_add / device_remove / net_reroute / buffer_insert dispatch once routing (M6c) lands. `device_resize` remains on `LayoutSolver` for backward compatibility; M6d may consolidate it into `core/macros/`. | resolved by M6b (2026-04-30) |
| 14 | `diff_to_edit_ops` handles add/remove only (no device-level) | `core/diff.py:73-81` | drift target |
| 15 | SKILL emitter is `printf` placeholder | `io_adapters/writer_skill_script.py:76-78` | drift target |
| 16 | Three dummy Calibre JSON generators | `dummy/gen_buffer_layout.py:364, 402, 434` | OK for now |
| 17 | Per-layer DRC rule registration | `core/drc_constraints.py:131-161` | OK to keep |
| 18 | ~~Layer map has no tier markers~~ | M4a added `LAYER_TIER` + `A/B/C1/C2_TIER_LAYERS` + `CUT_LAYERS` + `tier_of()` / `layers_in_tier()` / `is_cut_layer()` helpers in `tech/layer_map.py`. CPO / M0_CUT / FIN_CUT / VT / PP / NP / DNW / DIODE / ESD / TEXT have tier markers despite lacking `LAYER_MAP` GDS-number entries — locks tier intent before geometry shows up. | resolved by M4a (2026-04-27) |
| 19 | Six-stage pipeline order: diff_cdl → build_layout_model → setup_engine → load_existing_layout → resize_device → apply_edits → write_gds | `pipeline/run_mvp.py:222-411` (M3 added `project_unannotated_blockages` between stages 4 and 5) | OK structure |
| 20 | L2 atomic ops module exists with `release_segment_cells` / `assign_segment_cells` / `modify_segment` | `core/atomic_ops.py` (M2 minimal subset; `extend_od`, `extend_poly`, `add/remove_fin_strip`, `add/remove_cut_cell`, `mark_shared_diffusion` deferred to M4) | half-built |
| 21 | `ShapeRecord` (geometric truth) + `LayoutModel.shape_pool` exist | `core/data_model.py::ShapeRecord` (with `provenance`, `is_derived`, `suspect_tags`); `LayoutModel.shape_pool` carries the pool; `LayoutModel.annotation_coverage()` returns per-layer LVS-coverage stats | resolved by M3 (2026-04-27) |
| 22 | Annotation-coverage report emitted by pipeline | `output/annotation_coverage.txt` written from `pipeline/run_mvp.py` after Stage 6 | resolved by M3 (2026-04-27) |

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

- **Status:** [x] Done (2026-04-27)
- **Owner:** Claude (`claude/review-arch-plan-LKbJL`)
- **Goal.** Invert the parser to "GDS `shape_pool` is geometric truth, LVS is annotation overlay." All unannotated shapes enter CSP as `BLOCKAGE`.
- **Sub-milestones (all complete).**
  - **M3a (Done, 2026-04-27):** Added `core/data_model.py::ShapeRecord` (geometric record with optional LVS overlay: `net_id` / `device_id` / `pin_role`; plus `provenance`, `is_derived`, and `suspect_tags` seams that M5 / M7 will light up). Added `LayoutModel.shape_pool: List[ShapeRecord]` and `LayoutModel.annotation_coverage()`. The M2-era `TrackSegment.bbox_nm` stamp is retained as a denormalised cache; the new `TrackSegment.shape_record` field is the canonical backlink to the matching pool entry.
  - **M3b (Done, 2026-04-27):** Inverted `io_adapters/parser.py`. New `build_shape_pool(bbox_data)` is the geometric-first pass — every GDS rectangle becomes a `ShapeRecord` with `net_id=None`. New `apply_lvs_overlay(pool, net_data, devices)` is the annotation pass — stamps `net_id` / `device_id` / `pin_role` onto matching records by `(layer, bbox)` key. `build_layout_model` now runs both, attaches the pool to `LayoutModel`, and stamps each `TrackSegment.shape_record` from the pool index. Net-primary loop kept for backward-compat (still drives `Net.segments` / `Net.vias`); the inversion shows up at the data-model level.
  - **M3c (Done, 2026-04-27):** Added `ConstraintEngine.mark_blockage(pos)` (`core/csp_engine.py`). Sets `cell.assignment = BLOCKAGE`, `cell.domain = {BLOCKAGE}`, `cell.fixed = True`. Idempotent on already-blocked cells; refuses to overwrite cells already carrying a non-EMPTY annotated assignment (conservative-default rule from §D — "treat collisions as real conflicts"). Subsequent `propose_assign(pos, *)` returns `False` because the cell is fixed and the requested state isn't in the singleton domain — no engine logic change required, the existing `assign` short-circuit handles it.
  - **M3d (Done, 2026-04-27):** Added `LayoutSolver.project_unannotated_blockages()` (`core/solver.py`). Iterates `model.shape_pool`; for every unannotated record on a CSP-modelled layer (today LI / M1) it maps the bbox to grid cells via `MultiLayerGrid.physical_to_segment_coords` and calls `engine.mark_blockage`. Returns per-layer cell counts plus a `skipped_conflict` count for cells that the engine refused to overwrite. Pipeline calls it after `load_existing_layout` (`pipeline/run_mvp.py:262-269`).
  - **M3e (Done, 2026-04-27):** Pipeline emits `output/annotation_coverage.txt` from `LayoutModel.annotation_coverage()` — per-layer total / annotated / unannotated counts. The MVP fixture today reports 14 / 32 LVS-annotated shapes (LI 5/5, M1 4/4, VIA0 4/4, POLY 1/3 — the two boundary dummy gates are unannotated; FIN / OD / NWELL / BOUNDARY are unannotated since LVS doesn't enumerate them).
- **Files touched.**
  - `core/data_model.py` — `ShapeRecord` dataclass + `LayoutModel.shape_pool` field + `annotation_coverage` helper + `TrackSegment.shape_record` backlink.
  - `io_adapters/parser.py` — `build_shape_pool` + `apply_lvs_overlay` helpers; `build_layout_model` rewired to shape_pool-primary; segments stamp the per-record backlink.
  - `core/csp_engine.py` — `mark_blockage` primitive.
  - `core/solver.py` — `project_unannotated_blockages` projection method.
  - `pipeline/run_mvp.py` — calls projection after Stage 4; emits annotation-coverage report after Stage 6.
  - **New** `tests/unit/test_shape_pool.py` (7 tests) — covers ShapeRecord defaults, overlay stamping, dummy-gate non-annotation, model exposure, and the per-segment backlink.
  - **New** `tests/unit/test_blockage.py` (8 tests) — covers `mark_blockage` semantics, conservative-default refusal, fixture no-op, synthetic LI-stub projection, and the M3 acceptance: an unannotated LI stub makes `assign_segment_cells` return `failed_pos` instead of silently overwriting.
- **Acceptance (verified).**
  - **M3 acceptance contract.** `tests/unit/test_blockage.py::test_li_stub_makes_assign_segment_cells_infeasible` injects an unannotated LI ShapeRecord on an empty cell, runs `project_unannotated_blockages`, then attempts `atomic_ops.assign_segment_cells` against that cell; the result is `success=False` with `failed_pos` pinned to the blocked position, and `engine.restore` returns the engine to its pre-call state.
  - **Annotation coverage report emitted.** `output/annotation_coverage.txt` lists per-layer total / annotated / unannotated counts.
  - **Byte-golden preservation.** `output/buffer_resized.json` and `output/buffer_resized.cdl` are byte-identical to the M2 baseline; `output/resize_report.txt` is byte-identical (the resize report comes from `EditOp.__repr__` which M3 didn't touch); `output/buffer_resized.gds` is polygon-set-identical (30/30 (layer, datatype, points) tuples match — the GDS library timestamp differs per write call but is not part of the golden contract).
  - **Tests:** pytest 65/65 green (50 pre-M3 + 15 new).
- **Dependencies.** M1 (decoder must understand `ShapeRecord` — backlink seam was wired in M2).
- **Notes for downstream milestones.**
  - The `(layer, bbox_nm)` overlay key works because the dummy generator's GDS shapes and the dummy LVS shapes share an exact bbox-tuple representation. Production LVS geometry can drift by sub-nm; M7 will need a tolerance / containment match.
  - `pin_role` inference uses `Device.pins[role] -> net_name` to back-stamp the role. When a net hits multiple pins on the same device (e.g. VSS = S + B for an NMOS), the stamp records the last role iterated. M4's B-tier `CellOccupancy.owner_device_id` + per-cell `pin_role` rasterisation is the principled fix.
  - `ShapeRecord.is_derived` is currently always `False`. M5's `core/drc_derivator.py` will set it to `True` when emitting NWELL / BOUNDARY / VT / PP / NP / DNW shapes; the decoder should then reject direct edits to derived shapes.
  - The geometric-overlap cross-check in §D ("`SUSPECT_CONNECTED_TO_*` tagging") is not implemented — `ShapeRecord.suspect_tags` exists as the seam but stays empty for the MVP fixture, where unannotated shapes are FIN / OD / POLY (non-CSP) and NWELL / BOUNDARY (cell-level wrappers). The cross-check will earn its keep on a real production layout where filler / ESD shapes overlap LVS-tagged routing.
  - Dummy fixture left unchanged. `dummy/gen_buffer_layout.py` already produces the two unannotated POLY dummy gates (`dummy_gate_0`, `dummy_gate_2`); they don't enter CSP because POLY isn't a CSP-modelled layer today. Adding more unannotated fillers would have shifted the byte-golden envelope without exercising any new code path. Tests inject scaffolding inline.

### M4 — B-tier `CellOccupancy` + diffusion sharing + CUT + net-equivalence

- **Status:** [x] Done (M4a Done 2026-04-27; M4b Done 2026-04-27; M4c Done 2026-04-28; M4d Done 2026-04-28; M4e Done 2026-04-28)
- **Owner:** Claude (`claude/review-arch-plan-Niwe4`) for M4a–M4e
- **Goal.** Promote 2D-grid layers (OD, VIA0, CPO/M0_CUT/FIN_CUT) into first-class `CellOccupancy(track_a, track_b)`. OD cells carry `owner_device_id` + `shared_with[]`. CUT is its own occupant type that breaks net-equivalence. CSP engine grows an internal net-equivalence union-find, updated incrementally.
- **Sub-milestones.**
  - **M4a (Done, 2026-04-27).** Data-model + tier-marker foundation. Purely additive — no current pipeline path keys off the new surfaces, so byte-golden is preserved by construction.
    - `core/data_model.py`: added `OccupantType.CUT`; defined `CellOccupancy(layer, track_a, track_b, occ_type, net_id, owner_device_id, shared_with, shape_record)` with `add_sharer` / `remove_sharer` / `pos` accessors and a `__post_init__` guard that rejects A-tier occupants (`WIRE`) so M4c projection can't silently mis-route a layer.
    - `tech/layer_map.py`: added `LAYER_TIER` (A/B/C1/C2 markers per §B), `A/B/C1/C2_TIER_LAYERS` subsets, `CUT_LAYERS = ('CPO', 'M0_CUT', 'FIN_CUT')`, plus `tier_of()` / `layers_in_tier()` / `is_cut_layer()` helpers. CPO / M0_CUT / FIN_CUT / VT / PP / NP / DNW / DIODE / ESD / TEXT have tier markers without yet having GDS-number entries — locks tier intent before geometry shows up.
    - **New** `tests/unit/test_cell_occupancy.py` (9 tests) and `tests/unit/test_layer_tiers.py` (7 tests). The structural test `test_every_layer_map_entry_has_a_tier` is the fail-loud guard for future `LAYER_MAP` entries that forget a tier marker.
  - **M4b (Done, 2026-04-27).** CSP cell-grid axis + net-equivalence union-find. Purely additive — no current pipeline path keys off the new surfaces, so byte-golden is preserved by construction.
    - `core/grid.py`: `MultiLayerGrid` gains parallel storage for B-tier layers — `b_tier_axes: Dict[layer, (axis_a_layer, axis_b_layer)]` plus sparse `b_tier_cells: Dict[layer, Dict[(track_a, track_b), CellOccupancy]]`. New API: `is_b_tier_layer()` (consults `tech.layer_map.tier_of`), `register_b_tier_axes()` (rejects A-tier layers and unregistered axes), `bbox_to_b_tier_cells(layer, x1, y1, x2, y2)` (projects a physical bbox to its `(track_a, track_b)` cell list, sorted), `set_b_tier_cell` / `get_b_tier_cell` (with pos/key consistency check), `b_tier_cells_of(layer)` iterator. `summary()` extended to print the B-tier section when registered.
    - `core/csp_engine.py`: net-equivalence union-find lives on `ConstraintEngine`. `_uf_parent` + `_uf_size` (no path compression — keeps `restore` simple) plus `_uf_trail` (per-union `(child_root, prev_child_parent, parent_root, prev_parent_size)` so `_uf_undo_one` reverts one step) and `_uf_checkpoints` mapping `len(self.trail)` at checkpoint time → `len(self._uf_trail)` so `restore` and `commit_with_full_delta` can bracket union events without changing `checkpoint`'s public return type.
    - New methods: `mark_cut(pos)` (mirrors `mark_blockage` from M3 — pins the cell as fixed `OccupantType.CUT`, idempotent, refuses to overwrite an annotated assignment); `union(pos_a, pos_b)` (adjacent + same-net + non-CUT preconditions; union-by-size; returns `False` on any precondition failure); `net_of(pos)`; `connected_to(pos)`; `connected_cells(net_id)`. `restore` extended to undo unions in reverse order before the cell-trail rollback, so net-equivalence is consistent with cell state on rollback.
    - New `CommitDelta(cells, unions)` dataclass returned by `commit_with_full_delta`. Legacy `commit_with_delta` is **preserved verbatim** for backward compatibility (`core/solver.py:351` does `len(delta)` on it; M2 tests index it as a list); the legacy method still drops the union trail on commit so a subsequent `restore` doesn't try to revert committed unions.
    - **New** `tests/unit/test_b_tier_grid.py` (11 tests) covering tier dispatch, axis registration, bbox-to-cells projection, set/get round-trip, ordered iteration.
    - **New** `tests/unit/test_net_equivalence.py` (23 tests) covering `mark_cut` semantics, all `union` preconditions (including the `cut_endpoint` case that exercises §B's "no CUT between adjacent cells"), the query API, restore-undoes-unions for both single and chained cases, `commit_with_full_delta` shape + truncation, and the legacy `commit_with_delta` invariant.
  - **M4c (Done, 2026-04-28).** Parser tier-dispatch + B-tier projection + per-shape `device_id` refinement + retirement of the desc-substring filter. Byte-golden — all four golden artifacts md5-identical to the M4b baseline.
    - `io_adapters/parser.py`: `apply_lvs_overlay` no longer uses the M3 "first-pin-wins" placeholder for `device_id`. It now calls a new `_device_for_shape(sr, devices, candidates=...)` helper that picks the device whose bbox contains the shape's center (with a max-overlap fallback for shapes spanning a gap). The per-net `pin_devices` list from `nd['pins']` is the candidate filter, so multi-pin nets like `OUT` get the right device per shape (NMOS drain LI → MN0; PMOS drain LI → MP0). Shared-rail shapes that sit outside any device bbox (e.g. the VSS / VDD M1 straps) end up with `device_id=None` — that's the correct semantics; the solver's LI-only filter never reaches them.
    - **New** `project_b_tier_shapes(model, grid, devices)` in `io_adapters/parser.py`. For every B-tier `ShapeRecord`: registers axes (OD: POLY × FIN; VIA0: LI × M1; CPO/FIN_CUT: POLY × FIN; M0_CUT: LI × M1), projects bbox via `MultiLayerGrid.bbox_to_b_tier_cells`, and stamps a `CellOccupancy` per cell with `owner_device_id` from `_device_for_shape` and `occ_type` from a layer→type table (OD → `DEVICE_DIFF`; VIA0 → `VIA`; cut layers → `CUT`). After projection, walks every OD shape and appends sibling devices to `shared_with[]` whenever their bboxes overlap the shape — diffusion sharing. The MVP fixture has zero overlapping device bboxes so `shared_with` stays empty there; a synthetic two-device-overlap test exercises the sharing path. Idempotent over re-invocation. Wired into `build_layout_model` after the existing pool/overlay stages.
    - `core/solver.py::_reshape_li_sd_bars`: replaces the `device_y_marker not in seg.desc` filter with `seg.shape_record.device_id == device.inst_name`. The geometry-driven M4c stamp is the source of truth; the legacy desc-substring fallback stays available only for callers that build `TrackSegment`s directly without going through `build_layout_model` (older tests / ad-hoc fixtures).
    - **New** `tests/unit/test_parser_tier_dispatch.py` (15 tests): per-shape `device_id` refinement on the OUT net; single-pin nets unchanged for in-device shapes; `_device_for_shape` containment / fallback / candidate-filter semantics; B-tier projection registers OD/VIA0 axes; OD cells get the right owner per device; MVP fixture's `shared_with` stays empty; synthetic two-device-overlap fixture exercises the sharing path; `TrackSegment.shape_record.device_id` is per-segment correct (the seam the solver migration reads from).
  - **M4d (Done, 2026-04-28).** B-tier + FIN/POLY L2 atomics; macro stops computing geometry inline and starts asking L2 for it.
    - `core/atomic_ops.py` gains `add_cut_cell` / `remove_cut_cell` / `mark_shared_diffusion` / `extend_od` / `add_fin_strip` / `remove_fin_strip` / `extend_poly`. Two new result types: `FinStripResult(success, fin_track_idx, bbox, desc, shape_record)` and `PolyExtendResult(success, target, old_value, new_value)`. `add_cut_cell` integrates with the M4b union-find: a CUT pinned through this primitive makes any subsequent `engine.union` across that cell fail, exercising §B's "no CUT between adjacent cells" rule end-to-end through the L2 surface.
    - `core/solver.py`: `_emit_fin_removes` calls `atomic_ops.remove_fin_strip` (mutates `model.shape_pool`); `_emit_od_modify` accepts the `device` argument and calls `atomic_ops.extend_od` (re-projects the cell-grid + updates the matching `ShapeRecord.bbox_nm`); `_emit_poly_modify_if_endpoint_changed` builds its partial-bbox EditOp from `atomic_ops.extend_poly`'s return value. The macro continues to emit L1 records but the geometry now flows through L2 atomics — closes the §C "L2 mutates state, macro builds L1 from L2 results" half of M4d. The other half ("decoder consumes CSP delta") stays for M5/M6.
    - The L2 surface is intentionally engine-aware where it makes sense: `add_cut_cell` calls `engine.mark_cut` when the layer is CSP-modelled; `mark_shared_diffusion` calls `engine.union` opportunistically. For layers not yet in the engine (FIN/POLY today), the L2 atomic mutates `model.shape_pool` only — the engine integration drops in cleanly when M5+ adds those layers.
    - **New** `tests/unit/test_b_tier_atomics.py` (21 tests): `add_cut_cell` engine + grid stamping, end-to-end §B "no CUT between adjacent cells" via the L2 primitive, refusal-surfaces-failed_pos; `remove_cut_cell` round-trip + idempotency; `mark_shared_diffusion` grid-only behaviour with `engine=None`; `extend_od` shrink / no-op / unregistered-axes / new-cell owner stamping; `add_fin_strip` / `remove_fin_strip` find-by-center-Y / synthesised-bbox fallback; `extend_poly` y1/y2 + invalid-target rejection; **solver integration acceptance** (post-resize `model.shape_pool` reflects the dropped FIN strips and the narrowed OD bbox; cell-grid post-resize matches the new geometry).
    - **Byte-golden caveat.** `output/buffer_resized.{json,cdl}` are byte-identical to the M4c baseline (the decoder matches FIN remove by center-Y, which is invariant under the bbox shift). `output/resize_report.txt` evolves intentionally — `remove_fin_strip` now returns the actual fixture bbox (`y1=136`) instead of the legacy synthesised one (`y1=137`); the 1 nm cosmetic drift on two FIN remove records is the price of routing through the L2 atomic. Same pattern as the M2 entry's "report evolves intentionally" note.
  - **M4e (Done, 2026-04-28).** B-tier engine layers + cell-level DRC + performance instrumentation. Closes the M4 milestone. Byte-golden — all four tracked artifacts md5-identical to the M4d baseline.
    - `core/csp_engine.py`: `__init__` reserves `_default_occ_types` + `_layer_occ_types` for per-layer domain control; `initialize_domains` accepts a `layer_occ_types: Dict[layer, Set[OccupantType]]` override so B-tier cells admit `DEVICE_DIFF` / `VIA` / `CUT` (each with both the `net_id=None` un-netted variant and per-net variants — LVS doesn't enumerate diffusion). Replaced `_initial_domain` with `_initial_domain_for_layer(layer)`; `propose_release`'s no-op fast-path consults the per-layer variant.
    - Perf instrumentation: new `propagate_stats: Dict[layer, {'calls', 'cells_visited', 'time_ns'}]` updated by `_propagate` (try/finally so early-exit paths still record time). `_perf_counter_ns = time.perf_counter_ns` is a module-level alias so tests can monkey-patch a deterministic clock. New `get_propagate_stats(layer=None)` and `reset_propagate_stats()` query / reset API. Hot loop adds one int increment + one `perf_counter_ns` subtraction per cell visit; overhead is negligible and on by default.
    - `core/solver.py::setup_engine`: extended with a `b_tier_layers` arg defaulting to "every B-tier layer the parser populated on the grid" (today: OD + VIA0). Computes engine bounds from `grid.b_tier_cells` keys plus a 1-cell margin. Builds the `layer_occ_types` mapping and threads it through `initialize_domains`. Skips B-tier registration cleanly when the grid is empty (legacy A-tier-only fixtures).
    - **New** `core/solver.py::load_b_tier_cells_into_engine`. After `load_existing_layout`, walks `grid.b_tier_cells_of('OD')` / `('VIA0')` and `engine.assign`s each populated cell to a `CellState(occ_type, net_id=cell.net_id)`. Returns the count of cells loaded; harmless when the engine doesn't model B-tier (no-op).
    - `core/solver.py::project_unannotated_blockages`: now skips layers absent from `grid.layers` (i.e. B-tier layers) so the A-tier-only `physical_to_segment_coords` projection stays sound. The M3 BLOCKAGE projection remains an A-tier-only mechanism; B-tier blockages would need a separate cell-grid projection that M5 can lift.
    - `core/drc_constraints.py`: `SameLayerMinSpacing` and `SameLayerAlongTrackSpacing` gain a `trigger_types` constructor arg (default `(WIRE, VIA)` — A-tier behaviour preserved). `forbidden_states` mirrors the trigger set so B-tier rules are symmetric. `create_mvp_drc_rules` registers OD same-layer min spacing + along-track spacing on `(DEVICE_DIFF,)` triggers, and a VIA0 min-spacing rule on `(VIA,)` triggers. The MVP fixture's two unannotated OD shapes coexist (None-vs-None = same net), so byte-golden output is unchanged.
    - `pipeline/run_mvp.py`: calls `solver.load_b_tier_cells_into_engine()` after `load_existing_layout` and prints the count.
    - **New** `tests/unit/test_b_tier_drc.py` (19 tests).
- **Files touched.**
  - `core/data_model.py:21-32` (M4a) — `OccupantType.CUT` added; `DEVICE_GATE` / `DEVICE_DIFF` / `CUT` validated as legal B-tier occupants.
  - `core/data_model.py` (M4a) — new `CellOccupancy` dataclass.
  - `core/grid.py` (M4b) — `MultiLayerGrid` cell-grid axis (`b_tier_axes`, `b_tier_cells`, `register_b_tier_axes`, `bbox_to_b_tier_cells`, `set/get/iter` cell helpers).
  - `core/csp_engine.py` (M4b) — net-equivalence union-find (`union`, `net_of`, `connected_to`, `connected_cells`, `mark_cut`, `commit_with_full_delta` returning `CommitDelta(cells, unions)`); union precondition includes "no CUT between adjacent cells".
  - `core/drc_constraints.py` (M4e) — `SameLayerMinSpacing` / `SameLayerAlongTrackSpacing` gain `trigger_types` arg; `create_mvp_drc_rules` adds OD spacing + VIA0 spacing.
  - `core/csp_engine.py` (M4e) — `propagate_stats` perf instrumentation + per-layer `initialize_domains` override.
  - `core/solver.py` (M4e) — `setup_engine` adds B-tier layers; `load_b_tier_cells_into_engine` seeds engine state; `project_unannotated_blockages` filtered to A-tier layers.
  - `pipeline/run_mvp.py` (M4e) — calls `load_b_tier_cells_into_engine` after `load_existing_layout`.
  - `core/atomic_ops.py` (M4d) — B-tier + FIN/POLY L2 primitives (`add_cut_cell`, `remove_cut_cell`, `mark_shared_diffusion`, `extend_od`, `add_fin_strip`, `remove_fin_strip`, `extend_poly`); new result types `FinStripResult` and `PolyExtendResult`.
  - `io_adapters/parser.py` (M4c) — `_device_for_shape` + `project_b_tier_shapes`; OD/VIA0 cells stamped with owner; LI `device_id` refined by geometric containment so `core/solver.py::_reshape_li_sd_bars` can retire the desc-substring filter.
  - `core/solver.py` (M4c) — `_reshape_li_sd_bars` keys off `shape_record.device_id`; legacy desc-substring fallback retained for direct-construction callers.
  - `tech/layer_map.py` (M4a) — tier markers + helpers; M4d/e will add cut-layer GDS numbers as fixtures grow them.
- **Change outline.**
  - Parser tier-dispatches via `tech/layer_map.py` to `TrackSegment` / `CellOccupancy` / derived.
  - The hardcoded FIN / OD / POLY loops in `pipeline/run_mvp.py` are fully replaced by M1 decoder + M4 cell projection.
  - Shared S/D semantics: between two adjacent gates, the OD cells' `owner_device_id` is the primary device and `shared_with` lists secondaries. SKILL/GDS still emits a single OD shape.
  - Net-equivalence API: `engine.net_of(cell)` / `engine.connected_cells(net_id)` for LVS cross-check and decoder provenance.
- **Acceptance.**
  - **M4a (verified).** Pytest 81/81 green (65 pre-M4a + 16 new); `output/buffer_resized.{json,cdl}` and `output/resize_report.txt` byte-identical to the M3 baseline; `output/buffer_resized.gds` polygon-set identical (only LIBNAME / timestamp differ, neither is part of the golden contract — the run that produced the noted LIBNAME diff used the manual writer because the test environment lacks gdstk).
  - **M4b (verified).** Pytest 119/119 green (85 post-M4a follow-up + 34 new — 11 in `tests/unit/test_b_tier_grid.py`, 23 in `tests/unit/test_net_equivalence.py`); `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` byte-identical to the M4a baseline. Acceptance for the §B "no CUT between adjacent cells" rule is `tests/unit/test_net_equivalence.py::test_union_rejects_cut_endpoint`: a chain of unions across a CUT cell fails at the cut step, leaving the two endpoints in disjoint components. Restore-undoes-unions is verified for both single and chained cases (`test_restore_undoes_unions`, `test_restore_undoes_chain_in_reverse`).
  - **M4c (verified).** Pytest 134/134 green (119 post-M4b + 15 new in `tests/unit/test_parser_tier_dispatch.py`); `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M4b baseline. Acceptance for the desc-filter retirement: `tests/unit/test_parser_tier_dispatch.py::test_overlay_disambiguates_out_net_per_shape` proves the OUT net's two LI shapes carry distinct `device_id`s (MN0 / MP0) post-M4c — the seam `core/solver.py::_reshape_li_sd_bars` now reads from. Acceptance for diffusion sharing: `test_project_records_shared_with_when_two_devices_overlap` runs `project_b_tier_shapes` on a synthetic two-device-overlap fixture and verifies every covered cell records the sibling device on `shared_with`. The MVP fixture's `shared_with` stays empty (no overlapping device bboxes); golden output is unchanged.
  - **M4d (verified).** Pytest 155/155 green (134 post-M4c + 21 new in `tests/unit/test_b_tier_atomics.py`). `output/buffer_resized.{json,cdl}` md5-identical to the M4c baseline; `output/resize_report.txt` evolves intentionally on the two FIN remove records (1 nm cosmetic shift documented above). Acceptance for the §B rule via L2: `tests/unit/test_b_tier_atomics.py::test_add_cut_cell_breaks_union_chain_via_engine` exercises a chain of unions across a CUT cell stamped via `add_cut_cell` and verifies the endpoints stay disjoint. Acceptance for solver-side state mutation: `test_solver_remove_fin_drops_shape_pool_record` and `test_solver_extend_od_updates_shape_record_bbox` confirm the post-resize `LayoutModel` reflects the L2 atomics' mutations.
  - **M4e (verified).** Pytest 174/174 green (155 post-M4d + 19 new in `tests/unit/test_b_tier_drc.py`). All four tracked golden artifacts md5-identical to the M4d baseline. The engine's cell count grew from 256 to 411 (LI/M1 plus the new OD/VIA0 layers); the MVP fixture's unannotated OD shapes (`net_id=None`) coexist with the new spacing rule because None-vs-None is "same net". The §M4 "shared OD" acceptance lands as `tests/unit/test_b_tier_drc.py::test_mark_shared_diffusion_unions_engine_cells_holds_post_drc`: a synthetic two-device-overlap fixture stamps OD cells through `project_b_tier_shapes`, runs `mark_shared_diffusion` against an engine that has the OD spacing rule registered, and verifies every engine cell stays feasible after DRC propagation.
- **Dependencies.** M1, M2 (M4a needs neither in practice — purely additive — but M4b–e build on the M2 transactional CSP API).
- **Notes for downstream M4 sub-milestones.**
  - `CellOccupancy.shape_record` is the M3 backlink seam — M4c stamps it on every projected cell so the SKILL/DRC closure in M7 can walk back to the geometric source of truth. (M4c done; M4d/M6 macros consume the backlink.)
  - The `CellOccupancy.__post_init__` rejection of `OccupantType.WIRE` is the structural guard against silently mis-routing an A-tier layer through the B-tier projection.
  - `LAYER_TIER` is the dispatch table; the `test_every_layer_map_entry_has_a_tier` structural test is the regression guard if a future fixture adds a layer without a tier marker.
  - **M4c ↦ M4d.** OD cells now carry `owner_device_id` + (for overlapping fixtures) `shared_with[]`. The M4d L2 op `mark_shared_diffusion(dev_a, dev_b)` walks `grid.b_tier_cells_of('OD')`, finds cells whose owner is `dev_a` and `shared_with` includes `dev_b`, and calls `engine.union` on adjacent pairs. The §B "no CUT between adjacent cells" rule then naturally manifests because a CUT cell on the chain fails the union step. The L2 ops `add_cut_cell` / `remove_cut_cell` go through `engine.mark_cut` (and a future inverse).
  - **M4b ↦ M4d/M6.** Macros that need to surface union events to L1 (M4d `mark_shared_diffusion`, M6 `share_diffusion` / `split_diffusion`) call `commit_with_full_delta` instead of `commit_with_delta`. The legacy method stays for the M2 `device_resize` macro until M4d converts it.
  - **Cycle-of-restore note.** The union-find `_uf_undo_one` reconstructs the child component's prior size by subtracting from the parent's stored size. This is exact for the union-by-size algorithm here; if M4d/M6 add path compression for performance the undo logic must be revisited.
  - **M4c legacy fallback.** `_reshape_li_sd_bars` retains a `if seg.shape_record is None: ... device.dev_type in seg.desc` fallback for callers that build `TrackSegment`s without going through `build_layout_model`. M4d should migrate the last such callers and remove the fallback.
- **Risks.** Performance regression as layer count + incremental net-equiv grow — instrument `propagate` from this milestone. Shared-tag identification depends on gate-position precision; use golden references.

### M5 — C1 derivator (NWELL / VT / PP / NP / BOUNDARY / DNW)

- **Status:** [x] Done (2026-04-28)
- **Owner:** Claude (`claude/m5-drc-derivator`)
- **Goal.** Pull all C1 derived markings out of `pipeline/run_mvp.py` hardcoded loops + the decoder's transitional Phase 2 helpers. A `drc_derivator` emits these shapes as L1 ``EditOp``s consumed by the decoder's Phase 1 path; subscribes to the L3 macro's commit point so it runs on a clean post-resize state.
- **What landed.**
  - **New** `core/drc_derivator.py::DRCDerivator(model, grid, config)` with `derive_c1(nmos_fin_y_new, pmos_fin_y_new) -> List[EditOp]`. Walks `model.shape_pool` for each C1 layer; for NWELL `y2 = pmos_fin_y_new[-1] + config.NWELL_MARGIN_BEYOND_FIN`, for BOUNDARY `y2 = pmos_fin_y_new[-1] + config.BOUNDARY_MARGIN_BEYOND_FIN`. Emits one `EditOp(modify_shape, layer, old_bbox, new_bbox, desc='derived_<layer>_y2_shift')` per shape whose bbox actually changes; idempotent on re-call. Stamps `sr.is_derived = True` and `sr.provenance = 'drc_derivator._derive_<layer>'` on every derived ShapeRecord — lights up the M3 seam.
  - `core/decoder.py`: Deleted the transitional Phase 2 helpers `_derive_nwell` and `_derive_boundary`. Phase 2 (derived synthesis) is now empty; the decoder is a pure L1 consumer. Added `_apply_nwell_modifies` and `_apply_boundary_modifies` to Phase 1, mirroring `_apply_od_modifies` (match by exact `old_bbox`, replace coords). `_update_metadata`'s hardcoded `40` for `cell_height` now reads `config.BOUNDARY_MARGIN_BEYOND_FIN` so a PDK swap cascades through both the derivator's BOUNDARY shape and the metadata field.
  - `tech/process_config.yaml`: new `derivation:` section with `nwell_margin_beyond_fin: 30` and `boundary_margin_beyond_fin: 40` (the literals the decoder used to inline). `tech/config_loader.py` exposes them as `TechConfig.NWELL_MARGIN_BEYOND_FIN` and `BOUNDARY_MARGIN_BEYOND_FIN`.
  - `pipeline/run_mvp.py`: Instantiates `DRCDerivator` after the L3 resize macro and appends `derive_c1(...)`'s ops to the combined edit-op stream passed to `WritebackDecoder.apply()`.
  - **New** `tests/unit/test_drc_derivator.py` (13 tests) covering: config exposes margins; `derive_nwell` / `derive_boundary` emit correct `y2`; idempotent on steady-state fixture; stamps `is_derived` + `provenance` on the matched ShapeRecord (including idempotent shapes); `bbox_nm` updated post-emit so subsequent calls see new geometry; empty fin lists short-circuit; layers absent from pool yield zero ops; decoder Phase 1 round-trip applies derivator ops; decoder skips unmatched modify ops; **MVP fixture** end-to-end — NWELL `y2 = 395`, BOUNDARY `y2 = 405`, both derived shape_pool records carry `is_derived=True`.
- **Change outline.**
  - Derivator inputs: post-commit fin Y positions (from `Device` metadata) + rule table (config). Output: L1 `EditOp` through the M1 decoder.
  - Subscription granularity for M5: full recompute on every pipeline call. Per-cell-delta affected-neighborhood recomputation is a future optimization (the seam stays — `engine.commit_with_full_delta` is available; the M5 PR doesn't consume it directly).
  - C2 markers (DIODE / ESD / TEXT) are *not* in the derivator — they go through the M3 `shape_pool` direct-edit path.
- **Acceptance.** Pytest 187/187 (174 post-M4e + 13 new). `output/buffer_resized.{json,cdl}` md5-identical to the M4e baseline (`47412996…` / `676823e7…`). `output/annotation_coverage.txt` md5-identical (`f1582221…`). The MVP `resize_report.txt` is *unchanged* — the report iterates the L3 macro's `ResizeResult.edit_ops` per device, which doesn't include the derivator's C1 ops; the C1 ops still flow through the decoder's combined-list parameter and produce identical layout JSON. NWELL `y2 = 395` and BOUNDARY `y2 = 405` in the resized JSON, matching the M4e baseline. The derivator's output passes through the decoder's new Phase 1 NWELL/BOUNDARY apply paths to byte-identical effect.
- **Dependencies.** M1 (decoder), M3 (`is_derived` seam), M4 (the macro/L2/L3 architecture the derivator slots into).
- **Notes for downstream milestones.**
  - VT / PP / NP / DNW geometry has no fixture coverage today. The derivator's `derive_c1` walks the pool by layer; adding new derivation rules is one new helper per layer that mirrors `_derive_nwell`. The seams support these without a refactor.
  - `is_derived` is now load-bearing on every C1 shape post-derivator-call, but **the decoder does not yet reject macro-emitted edits to derived shapes**. M6 (L3 macro family) is the right place to land that check — adding it now would create no observable behaviour because the M5 macro doesn't try to edit C1 directly.
  - The "subscribes to CSP commit deltas" requirement is satisfied lightly. M5's derivator is pull-based (the pipeline calls it). A push-based subscription model — where `engine.commit_with_full_delta`'s cell delta hands the affected-neighborhood radius directly to the derivator for incremental recompute — is a follow-up. The M4b infrastructure (`CommitDelta`) is already in place; only the wiring is deferred.
- **Risks (residual).** Multi-cell layouts where NWELL/BOUNDARY span outside a single cell will need a richer rule than "y2 = topmost-fin + margin". M5 ships single-cell semantics; add multi-cell rules when fixtures grow.

### M6 — L3 macro family (device / net / diffusion / cut)

- **Status:** [ ] In progress (M6a Done 2026-04-29; M6b Done 2026-04-30)
- **Owner:** Claude (`claude/review-arch-plan-fk4Og`) for M6a/M6b
- **Goal.** With M2 L2 primitives + engine transactions in place, add the macro families that validate the four-layer architecture beyond resize.
- **Sub-milestones.**
  - **M6a (Done, 2026-04-29).** `core/macros/` directory + `add_cut` / `remove_cut` / `share_diffusion` macros + decoder rejection of derived-shape edits + `device_resize` flip to `commit_with_full_delta`. Purely additive (modulo the flip); byte-golden preserved.
    - **New** `core/macros/__init__.py`, `core/macros/cut_ops.py`, `core/macros/share_diffusion.py`. Each macro brackets its L2 call in `engine.checkpoint` / `engine.commit_with_full_delta`, restoring the engine on L2 atomic failure. Result types `CutMacroResult` / `ShareDiffusionResult` carry the engine's `CommitDelta` (cells + unions since the checkpoint) so M6b can subscribe to union events for L1 synthesis.
    - `core/decoder.py`: `WritebackDecoder.apply` accepts an optional `model: LayoutModel` parameter; when provided, every incoming `EditOp` is checked against `model.shape_pool`. An op whose `(layer, old_bbox)` matches a `ShapeRecord` with `is_derived=True` is rejected with `DerivedShapeEditError` *unless* the op carries the M5 derivator's `desc='derived_<layer>_y2_shift'` prefix (the disambiguator). Closes Minimal Starter PR item 4 — the M5 `is_derived` seam goes load-bearing here. Legacy callers that pass no model are unaffected.
    - `core/solver.py::resize_device`: switched from `commit_with_delta` to `commit_with_full_delta` on the L3 transaction commit. Closes Minimal Starter PR item 5. The MVP buffer-resize transaction emits zero union events (LI/M1 are A-tier WIRE cells), so byte-golden output is unaffected; the print line gains a "{N} union events" suffix that M6b's `share_diffusion` / `split_diffusion` macros will exercise non-trivially.
    - `pipeline/run_mvp.py`: passes `model=model` into `decoder.apply(...)` so the rejection check is active in the pipeline path. The MVP fixture's derivator-emitted NWELL / BOUNDARY ops carry the exempt `derived_*` desc, so the check is a no-op for the byte-golden case.
    - **New** `tests/unit/test_m6_macros.py` (14 tests): decoder rejection (macro-emitted edit raises, derivator-emitted exempt, no-model legacy path, no-derived-shapes short-circuit, MVP pipeline path stays clean); `add_cut` macro (transaction brackets, engine state pinned, restore-on-refusal, end-to-end §B no-CUT-between-adjacent-cells, grid-stamp-when-engine-lacks-layer); `remove_cut` macro (drop + idempotent); `share_diffusion` macro (no-engine grid-only path, with-engine union-records-in-delta, no-grid short-circuit); `device_resize` flip (capsys verifies "union events" marker).
    - **Acceptance (verified).** Pytest 201/201 green (187 pre-M6a + 14 new). All four golden artifacts md5-identical to the M5 baseline: `47412996…` JSON / `676823e7…` CDL / `0b427f45…` resize_report / `f1582221…` annotation_coverage.
  - **M6b (Done, 2026-04-30).** Routing-free macro extensions + `pick_macro` dispatch. Trimmed scope per the "MVP — no maze routing or large-scale rip-up" ground rule (see [§ Routing scope](#routing-scope-mvp-bound)). Macros that orchestrate over already-existing primitives only. Byte-golden preserved.
    - **New** `core/macros/split_diffusion.py` — inverse of M6a's `share_diffusion`. Walks `grid.b_tier_cells_of('OD')`, removes the sibling from each cell's `shared_with`. Optionally calls `add_cut` at an explicitly-passed POLY track index (`cut_at_track_a`) to physically isolate the previously-shared region — per § C, the cut must land before the metadata mutation lands externally, but for the M6b macro we run them in sequence atomically (the macro itself is the transaction boundary). The engine union-find is *not* actively split — the M4b union-find's `_uf_undo_one` undoes only the most recent union, not arbitrary subsets; instead, the §B "no CUT between adjacent cells" rule prevents *future* unions across the cut, and the next checkpoint/restore cycle clears the merged component naturally. Auto-detection of the boundary track is M6d's job (depends on `Device.gate_track_idx` end-to-end through the parser); for M6b the explicit form keeps the macro testable without a half-baked heuristic.
    - **New** `core/macros/pick_macro.py` — dispatch table. `MacroCall(macro_name, args, kwargs, diff)` dataclass + `pick_macro(diff_entry, model)` function + `pick_macros(diffs, model)` list helper. For the MVP, dispatches `nfin` parameter changes to `device_resize`. Other parameters return `None` (caller logs + skips). The share/split/cut macros stay importable Python API; the pipeline does not auto-invoke them from CDL because diffusion-share / cut deltas are *layout-side intent*, not netlist semantics — a future "layout intent" file format (out of M6 scope) would route them.
    - `pipeline/run_mvp.py` — replaces the inlined `solver.resize_device('MN0', 4)` / `solver.resize_device('MP0', 6)` calls with a `pick_macros(...)`-driven loop. Each `MacroCall.execute(solver)` invokes the right method by name. Byte-golden preserved (the dispatch table is a pure refactor; iteration order matches the prior `for target in nfin_targets` loop).
    - `core/macros/__init__.py` — re-exports `split_diffusion`, `SplitDiffusionResult`, `pick_macro`, `pick_macros`, `MacroCall`.
    - **New** `tests/unit/test_m6b_macros.py` (15 tests): split_diffusion clears shared_with links / round-trip share→split / idempotent / no-grid no-OD short-circuits / explicit `cut_at_track_a` calls add_cut / default no-cut path / pick_macro routes nfin to device_resize / returns None for unknown params / pick_macros filters / MacroCall.execute dispatches / raises on unknown method / pipeline byte-golden md5 match.
    - **Out of scope for M6b** (deferred to M6c / M6d):
      - `device_add` / `device_remove`: connecting a new device's pins to existing nets, or cleanly retiring a removed device's orphan segments, both require routing.
      - `net_reroute`, `buffer_insert`: routing-dependent.
      - `diff_cdl` extension to detect device add/remove deltas: blocks on macro implementation.
      - GDS layer-number entries for CPO/M0_CUT/FIN_CUT: the MVP fixture doesn't generate cut-layer geometry; adding the entries is write-only until a fixture exercises them.
      - Auto-detection of the gate-cut boundary track inside `split_diffusion`: depends on `Device.gate_track_idx` being reliably set, which the synthetic test fixture doesn't model.
    - **Acceptance (verified).** Pytest 214/214 green (201 pre-M6b + 13 new). All four golden artifacts md5-identical to the M6a baseline: `47412996…` JSON / `676823e7…` CDL / `0b427f45…` resize_report / `f1582221…` annotation_coverage.
  - **M6c (Not started).** Routing subsystem.
    - **New** `core/router/` (path-search subsystem). Contains a CSP-aware A* (or maze) router that, given (source_pin, target_pin) and the engine's current cell state, finds a sequence of cells on legal layers connecting them. Cost function accounts for layer changes (vias), preferred direction, blockage proximity. Rip-up-and-reroute is the obstacle-handling escape hatch.
    - The router is consulted by L3 macros that need new connectivity (M6d below). It is *not* part of L2 — L2 atomics remain assignment / release / segment-modify primitives. The router synthesises a *plan* (a sequence of L2 calls); the macro brackets that plan in a transaction.
    - Scope is intentionally bounded for the MVP: single-source single-target routes within one cell (no multi-cell routing, no global routing, no buffer-tree synthesis). Multi-target / multi-cell are post-M7 territory.
  - **M6d (Not started).** Routing-dependent macros.
    - **New** `core/macros/{device_add,device_remove,net_reroute,buffer_insert}.py`. Each consults M6c's router for its connectivity-changing work.
    - `device_add(device_spec, placement_hint)` — projects FIN/OD/POLY shapes; consults router to wire G/D/S/B pins to their target nets.
    - `device_remove(inst_name)` — drops the device's owned shapes; calls router to clean up orphan segments (or rip-up routes that landed on its pins).
    - `net_reroute(net_id)` — rip-up-and-reroute the entire net.
    - `buffer_insert(net_id, position)` — `device_add × 2` (the buffer's NMOS + PMOS) plus router calls to splice the buffer into the existing net.
    - `diff_cdl` extends to detect device add/remove deltas; `pick_macro` dispatch grows to route them.
- **Files touched (cumulative).**
  - **M6a:** `core/decoder.py`, `core/solver.py`, `pipeline/run_mvp.py`; **new** `core/macros/__init__.py`, `core/macros/cut_ops.py`, `core/macros/share_diffusion.py`, `tests/unit/test_m6_macros.py`.
  - **M6b:** **new** `core/macros/split_diffusion.py`, `core/macros/pick_macro.py`, `tests/unit/test_m6b_macros.py`; `pipeline/run_mvp.py` (pick_macro loop), `core/macros/__init__.py` (re-exports).
  - **M6c:** **new** `core/router/` (path-search subsystem) + tests.
  - **M6d:** **new** `core/macros/{device_add,device_remove,net_reroute,buffer_insert}.py`; `io_adapters/cdl_parser.py::diff_cdl` extends to device add/remove; `core/macros/pick_macro.py` dispatch grows.
- **Change outline.**
  - Macros call only L2; transaction boundaries live at the macro top.
  - `share_diffusion(dev_a.pin, dev_b.pin)` — calls `mark_shared_diffusion` to update `shared_with`, triggers net-equivalence remerge. (M6a done.)
  - `split_diffusion(...)` — inverse; if devices are physically adjacent, must call `add_cut_cell` first to ensure isolation. (M6b — no engine union-undo; relies on §B "no CUT between adjacent cells" + checkpoint/restore.)
  - `add_cut` / `remove_cut` — direct calls to `add_cut_cell` / `remove_cut_cell`; CSP recomputes net-equivalence. (M6a done.)
  - `device_add` / `device_remove` / `net_reroute` / `buffer_insert` — depend on M6c routing subsystem. (M6d.)
- **Acceptance (M6 milestone-level).**
  - **M6b acceptance.** Round-trip share/split symmetry — running `share_diffusion(A, B)` then `split_diffusion(A, B)` returns each OD cell's `shared_with` to its pre-share state. `pick_macro` routes the MVP fixture's `nfin` deltas to `device_resize` correctly; byte-golden preserved.
  - **M6d acceptance** (deferred until routing lands).
    - CDL gains an inverter → pipeline emits a legal layout.
    - CDL drops a device → released shapes cleared, annotations updated, shared diffusion auto-degrades to single-owner.
    - "Two devices request shared S/D" → `share_diffusion` macro lands legally with full L1 emission. (M6a smoke-test passes today.)
    - "Same poly must be cut" → `add_cut` macro inserts a CPO mid-span and splits the net. (M6a smoke-test passes; M6d adds the cut-layer GDS-number entries to `tech/layer_map.py` so a CPO add_shape is emitted in the L1 stream.)
- **Dependencies.** M2, M3, M4, M5. M6d additionally depends on M6c.
- **Risks.** L3 risks degenerating into a glue-script layer — enforce layered-call lints. Diffusion split + cut order matters; reversed order produces transient short circuits and must be guarded by engine transactions. **M6c routing risk:** the search space scales fast with cell count and via cost; an unbounded router will dominate pipeline cost. Bound the search to single-cell single-target for the MVP.
- **Notes for downstream sub-milestones.**
  - The M6a `CutMacroResult.commit_delta` is typically empty for `add_cut` because `engine.mark_cut` pins the cell directly (bypassing the trail). The structural change lives on `cell.fixed` / `cell.assignment`. Consumers read the macro result, not the cell delta.
  - M6a's `share_diffusion` `cells_unioned` count and `commit_delta.unions` length differ: the L2 atomic counts every `engine.union` True return (including no-op successes when the cells are already in the same component), while `commit_delta.unions` only carries actual merges. Pick the right count for the purpose (display vs. L1 emission).
  - The M5 derivator's exempt-prefix convention (`desc='derived_<layer>_y2_shift'`) is the M6a contract for derived-shape edits. Future derivator extensions (VT / PP / NP / DNW) must keep the prefix, or extend the exempt check.
  - **M6b → M6d note on engine union-find.** The current `_uf_undo_one` undoes the *most recent* union; it does not selectively split a component. So `split_diffusion` does not actively un-merge the engine union-find — it relies on the §B "no CUT between adjacent cells" rule (preventing *future* unions across the cut) plus the natural checkpoint/restore lifecycle. M6d / M7 may need a path-aware union-find if multi-step diffusion split-then-share-elsewhere becomes a real workload.

#### Routing scope (MVP-bound)

For the MVP fixture (single-cell inverter buffer, single-cell shared-diffusion synthetic), no maze / global routing is implemented. M6b ships only macros that orchestrate over **already-existing** L2 primitives (resize an existing segment, mark an existing cell, walk pre-projected OD cells). Connectivity-changing operations — `device_add`, `device_remove`, `net_reroute`, `buffer_insert` — block on M6c's routing subsystem and ship in M6d.

This split keeps each milestone's scope verifiable against the MVP fixture. M6c is its own milestone because (a) it's a substantial subsystem (path search, cost function, obstacle queries, rip-up logic), (b) its design choices (A* vs. maze, bounded vs. global, single-source vs. multi-source) deserve their own discussion, and (c) shipping the macros without routing would smuggle a substantial implementation into a "macro PR" review.

### M6c — Routing subsystem (path search)

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Add a CSP-aware path-search subsystem that L3 connectivity-changing macros can call. Single-source single-target, single-cell scope. Unblocks M6d.
- **Files touched.**
  - **New** `core/router/__init__.py`, `core/router/astar.py` (or `maze.py`), `core/router/cost.py`, `core/router/obstacles.py`.
  - **New** `tests/unit/test_router*.py`.
- **Change outline.** Router consumes the engine's current cell state (assignments + domains + blockages + cuts) as obstacles and produces a *plan* — a sequence of cell positions on legal layers. The plan is handed to a macro that calls `propose_assign` per cell inside a transaction. Router itself is read-only over the engine.
- **Acceptance.** Given a synthetic single-source single-target fixture with one obstacle, the router returns a plan that avoids the obstacle and connects source to target; the plan's `propose_assign` chain is feasible end-to-end (no DRC violation on commit). Rip-up: when no path exists, returns `None` (or raises) — caller decides whether to release a conflicting route and retry.
- **Dependencies.** M2, M3, M4.
- **Risks.** Search-space explosion. Bound the search to the engine's current bounds plus a small margin; cap the iteration count; surface a "no-path" outcome cleanly so callers don't loop indefinitely.

### M6d — Routing-dependent macros (device_add / device_remove / net_reroute / buffer_insert)

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Ship the macros that need M6c's router. Closes the M6 milestone.
- **Files touched.**
  - **New** `core/macros/{device_add,device_remove,net_reroute,buffer_insert}.py`.
  - `io_adapters/cdl_parser.py::diff_cdl` extends to detect device add/remove deltas.
  - `core/macros/pick_macro.py` dispatch table grows.
  - `tech/layer_map.py` — GDS-number entries for CPO/M0_CUT/FIN_CUT so M6a's `add_cut` macro starts emitting `add_shape` L1 records.
- **Change outline.**
  - `device_add(device_spec, placement)` — projects FIN/OD/POLY shapes, calls router for G/D/S/B pin connections.
  - `device_remove(inst_name)` — drops owned shapes, calls router to clean up orphan segments.
  - `net_reroute(net_id)` — rip-up + reroute via M6c.
  - `buffer_insert(net_id, position)` — `device_add × 2` + router calls to splice into the existing net.
- **Acceptance.** See M6 milestone-level "M6d acceptance" — covers the four CDL-delta scenarios (device add, device remove, share, cut).
- **Dependencies.** M6a, M6b, M6c.
- **Risks.** Order-of-operations bugs around `split_diffusion` + `add_cut` + rip-up. Engine-rollback discipline must hold across the entire macro transaction.

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

**M6a + M6b are complete.** The next move is **M6c** — the routing subsystem that unblocks the routing-dependent macros (M6d):

1. **New** `core/router/__init__.py`, `core/router/astar.py` (or `maze.py`), `core/router/cost.py`, `core/router/obstacles.py`. CSP-aware path search: given (source_pin, target_pin) and the engine's current cell state, returns a sequence of cell positions on legal layers.
2. **Read-only over the engine.** The router consumes `engine.cells` / `engine.layer_dims` / `engine.connected_cells(net_id)` to identify obstacles (BLOCKAGE, CUT, or wrong-net WIRE assignments). It does NOT call `propose_assign` itself — it returns a *plan*; macros bracket the plan in a transaction and call L2 atomics per cell.
3. **Bounded scope.** Single-source single-target, single-cell, capped iteration count. Multi-target / multi-cell / global routing are post-M7. The "no path" outcome must surface cleanly so callers don't loop indefinitely.
4. **Tests.** Synthetic fixtures: a clear path (no obstacles), an obstacle-detour path, a no-path scenario (rip-up needed). The path's `propose_assign` chain must be feasible end-to-end (no DRC violation on commit).

After M6c, **M6d** ships the macros that consume the router (`device_add`, `device_remove`, `net_reroute`, `buffer_insert`) plus the `diff_cdl` / `pick_macro` extensions to dispatch them. Then **M7** — Virtuoso SKILL + Calibre DRC/LVS closure.

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
| 2026-04-30 | Claude (`claude/review-arch-plan-fk4Og`) | **M6b complete + M6 decomposed into M6a/M6b/M6c/M6d.** Per user's "MVP scope, no maze routing or large-scale break-and-reconstruct" ground rule, the original M6 milestone was decomposed: M6b ships the routing-free macros, M6c ships the routing subsystem, M6d ships the routing-dependent macros (`device_add` / `device_remove` / `net_reroute` / `buffer_insert`). New "Routing scope (MVP-bound)" subsection added under M6 with the rationale. **M6b deliverables.** **New** `core/macros/split_diffusion.py::split_diffusion(engine, grid, dev_a_inst, dev_b_inst, cut_at_track_a=None, cut_layer='CPO')` — inverse of M6a's `share_diffusion`. Walks `grid.b_tier_cells_of('OD')`, removes the sibling from each cell's `shared_with`. Optionally calls `add_cut` at an explicit POLY track index (every track_b row in the affected region) to physically isolate the previously-shared region. Auto-detection of the boundary track is M6d's job (depends on reliable `Device.gate_track_idx`). Engine union-find is *not* actively split — relies on §B "no CUT between adjacent cells" + checkpoint/restore. **New** `core/macros/pick_macro.py::MacroCall + pick_macro(diff_entry, model) + pick_macros(diffs, model)` — L4 dispatch table. For MVP, routes `nfin` parameter changes to `device_resize`; other params return `None`. The share/split/cut macros stay importable Python API (CDL can't express layout-side intent). `pipeline/run_mvp.py` Stage 5 refactored to `pick_macros(...)` loop — pure refactor, byte-golden preserved. `core/macros/__init__.py` re-exports `split_diffusion`, `SplitDiffusionResult`, `pick_macro`, `pick_macros`, `MacroCall`. **New** `tests/unit/test_m6b_macros.py` (13 tests): split_diffusion clears shared_with / round-trip share→split / idempotent on second call / no-grid + no-OD short-circuits / explicit `cut_at_track_a` calls add_cut and stamps CPO at every FIN row / default no-cut path / pick_macro routes nfin / returns None for unknown params / pick_macros filters None entries / MacroCall.execute dispatches by name / raises on unknown method / pipeline byte-golden md5 verification. **Acceptance.** Pytest 214/214 green (201 pre-M6b + 13 new). `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M6a baseline. M6 milestone block: M6a/M6b sub-milestones marked Done, M6c/M6d added with full structure (Goal / Files touched / Change outline / Acceptance / Dependencies / Risks). Verification snapshot row 13 (`core/macros/`) updated — directory now houses cut_ops.py, share_diffusion.py, split_diffusion.py, pick_macro.py; `pick_macro` dispatch landed but only `nfin` → `device_resize` populates the table for now. Minimal Starter PR pointer flipped from **M6b** to **M6c** (routing subsystem). |
| 2026-04-29 | Claude (`claude/review-arch-plan-fk4Og`) | **M6a complete.** First slice of M6 — created `core/macros/` directory with `cut_ops.py` (`add_cut` / `remove_cut`) and `share_diffusion.py` (`share_diffusion`), each bracketing the M4d L2 atomics in `engine.checkpoint` / `engine.commit_with_full_delta` and returning a result type carrying the engine's `CommitDelta`. Added decoder rejection of direct edits to derived (`is_derived=True`) shapes — `WritebackDecoder.apply` accepts an optional `model: LayoutModel`, walks `model.shape_pool` for derived shapes, and raises `DerivedShapeEditError` on any incoming `EditOp` whose `(layer, old_bbox)` matches unless the op carries the M5 derivator's `desc='derived_<layer>_y2_shift'` prefix (the disambiguator). The M5 `is_derived` seam goes load-bearing here, closing Minimal Starter PR item 4. Flipped the L3 `device_resize` macro from `commit_with_delta` to `commit_with_full_delta` (Minimal Starter PR item 5) — the MVP buffer-resize transaction prints "0 union events" because LI/M1 are A-tier WIRE-only cells, so byte-golden output is unaffected. `pipeline/run_mvp.py` passes `model=model` into `decoder.apply(...)`. New `tests/unit/test_m6_macros.py` (14 tests) covers: decoder rejection (5 tests — macro raises, derivator exempt, no-model legacy path, no-derived-shapes short-circuit, MVP pipeline path); `add_cut` macro (4 tests — transaction brackets + engine pin, restore-on-refusal, end-to-end §B no-CUT-between-adjacent-cells via L3, grid-stamp-when-engine-lacks-layer); `remove_cut` macro (1 test — drop + idempotent); `share_diffusion` macro (3 tests — no-engine grid-only path, with-engine union events land in CommitDelta, no-grid short-circuit); `device_resize` flip (1 test — capsys captures "union events" marker from `commit_with_full_delta`'s print). Acceptance: pytest 201/201 (187 pre-M6a + 14 new); `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M5 baseline (`47412996…` / `676823e7…` / `0b427f45…` / `f1582221…`). Verification snapshot row 13 marked half-built (M6a created the directory; M6b lights up dispatch + remaining macros). M6 milestone block decomposed into M6a/M6b sub-milestones; M6a marked Done with file/test references and notes for M6b. Minimal Starter PR pointer flipped from **M6** to **M6b** (device_add / device_remove / net_reroute / buffer_insert / split_diffusion + `pick_macro` dispatch). |
| 2026-04-28 | Claude (`claude/m5-drc-derivator`) | **M5 complete.** C1 derivator lifted out of the decoder's transitional Phase 2 into a standalone module. **New** `core/drc_derivator.py::DRCDerivator(model, grid, config)` with `derive_c1(nmos_fin_y_new, pmos_fin_y_new) -> List[EditOp]`: walks `model.shape_pool` for each C1 layer; emits one `modify_shape` EditOp per shape whose Y2 actually changed; idempotent on re-call (updates `sr.bbox_nm` post-emit); stamps `is_derived=True` and `provenance='drc_derivator._derive_<layer>'` on every C1 shape it owns (lights up the M3 seam). NWELL `y2 = pmos_fin_y_new[-1] + config.NWELL_MARGIN_BEYOND_FIN` (30 nm); BOUNDARY `y2 = ... + config.BOUNDARY_MARGIN_BEYOND_FIN` (40 nm). VT/PP/NP/DNW seams reserved but no-op until fixture geometry shows up. `core/decoder.py`: deleted `_derive_nwell` / `_derive_boundary`; Phase 2 (derived synthesis) is now empty. Added `_apply_nwell_modifies` and `_apply_boundary_modifies` to Phase 1 mirroring `_apply_od_modifies` (match by exact `old_bbox`, replace coords). `_update_metadata`'s `cell_height` reads `config.BOUNDARY_MARGIN_BEYOND_FIN` instead of a hardcoded 40. `tech/process_config.yaml`: new `derivation:` section with the two margins. `tech/config_loader.py`: exposes `NWELL_MARGIN_BEYOND_FIN` and `BOUNDARY_MARGIN_BEYOND_FIN` on `TechConfig`. `pipeline/run_mvp.py`: instantiates `DRCDerivator` after the L3 resize macro and appends `derive_c1(...)`'s ops to the combined edit-op stream passed to `WritebackDecoder.apply()`. **New** `tests/unit/test_drc_derivator.py` (13 tests): config exposure; `derive_nwell` / `derive_boundary` correct y2; idempotency on steady-state; `is_derived` + provenance stamping (including idempotent shapes); `bbox_nm` updates post-emit; empty fin lists short-circuit; layers-absent-from-pool no-op; decoder Phase 1 round-trip; decoder skips unmatched modify ops; **MVP fixture** end-to-end — NWELL `y2=395`, BOUNDARY `y2=405`, both pool records carry `is_derived=True`. Acceptance: pytest 187/187 green (174 post-M4e + 13 new); `output/buffer_resized.{json,cdl}` and `output/annotation_coverage.txt` md5-identical to the M4e baseline; `resize_report.txt` unchanged (the per-device report iterates `ResizeResult.edit_ops` which doesn't include the derivator's ops; the layout JSON still reflects the C1 changes). Verification snapshot rows 11 (NWELL/BOUNDARY hardcoded formulas) and 12 (`is_derived` half-built) marked resolved. M5 milestone marked Done. Minimal Starter PR pointer flipped to **M6** (L3 macro family). Branch: fresh `claude/m5-drc-derivator` per user request. |
| 2026-04-28 | Claude (`claude/review-arch-plan-Niwe4`) | **M4e complete — M4 milestone closed.** B-tier engine layers + cell-level DRC + performance instrumentation. `core/csp_engine.py`: `initialize_domains` accepts a `layer_occ_types: Dict[layer, Set[OccupantType]]` per-layer override so B-tier cells admit `DEVICE_DIFF` / `VIA` / `CUT` (with both `net_id=None` and per-net variants). Replaced `_initial_domain` with `_initial_domain_for_layer(layer)`; `propose_release` consults the per-layer variant. New `propagate_stats` perf instrumentation (`calls`, `cells_visited`, `time_ns` per layer) updated by `_propagate` via try/finally; `_perf_counter_ns = time.perf_counter_ns` module alias for test-time monkey-patching; `get_propagate_stats(layer=None)` + `reset_propagate_stats()` query API. `core/solver.py::setup_engine` extended with `b_tier_layers` (default: every B-tier layer the parser populated on the grid — today OD + VIA0); computes engine bounds from `grid.b_tier_cells` keys with a 1-cell margin; threads the right `layer_occ_types` into `initialize_domains`. New `core/solver.py::load_b_tier_cells_into_engine` seeds engine state from `grid.b_tier_cells_of` after `load_existing_layout`. `core/solver.py::project_unannotated_blockages` now skips layers absent from `grid.layers` so the A-tier-only `physical_to_segment_coords` path stays sound. `core/drc_constraints.py`: `SameLayerMinSpacing` and `SameLayerAlongTrackSpacing` gain a `trigger_types` constructor arg (default preserves A-tier `(WIRE, VIA)` behaviour); `create_mvp_drc_rules` adds OD same-layer + along-track spacing on `(DEVICE_DIFF,)` triggers and a VIA0 min-spacing rule on `(VIA,)` triggers. `pipeline/run_mvp.py` calls `solver.load_b_tier_cells_into_engine()` after `load_existing_layout`. New `tests/unit/test_b_tier_drc.py` (19 tests): propagate_stats counters; per-layer initialize_domains; engine.assign accepts DEVICE_DIFF after override; setup_engine adds OD/VIA0 when grid is populated, skips when empty; load_b_tier_cells_into_engine seeds OD with DEVICE_DIFF + VIA0 with VIA; pipeline byte-golden post-M4e (engine 256→411 cells); create_mvp_drc_rules includes OD/VIA0; OD rule trigger/forbidden semantics; MVP unannotated cells coexist; **end-to-end M4 acceptance** — synthetic two-device-overlap fixture exercises `mark_shared_diffusion` against the engine and verifies DRC propagation doesn't break feasibility. Acceptance: pytest 174/174 (155 post-M4d + 19 new); `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M4d baseline. M4 milestone marked Done; verification snapshot stamp updated. Minimal Starter PR pointer flipped to **M5** (C1 derivator). |
| 2026-04-28 | Claude (`claude/review-arch-plan-Niwe4`) | **M4d complete.** B-tier + FIN/POLY L2 atomics; macro stops computing geometry inline. `core/atomic_ops.py` gains `add_cut_cell` / `remove_cut_cell` / `mark_shared_diffusion` / `extend_od` / `add_fin_strip` / `remove_fin_strip` / `extend_poly`. Two new result types: `FinStripResult` (track_idx, bbox, desc, shape_record backlink) and `PolyExtendResult` (target, old_value, new_value). `add_cut_cell` integrates with the M4b union-find — `tests/unit/test_b_tier_atomics.py::test_add_cut_cell_breaks_union_chain_via_engine` exercises §B's "no CUT between adjacent cells" end-to-end via the L2 primitive. `core/solver.py`: `_emit_fin_removes` calls `remove_fin_strip` (mutates `model.shape_pool`); `_emit_od_modify` calls `extend_od` (re-projects the cell-grid + updates ShapeRecord bbox); `_emit_poly_modify_if_endpoint_changed` builds its EditOp from `extend_poly`'s return. New `tests/unit/test_b_tier_atomics.py` (21 tests) covering all atomics in isolation + solver-integration acceptance. Byte-golden: `output/buffer_resized.{json,cdl}` md5-identical to the M4c baseline (the decoder matches FIN remove by center-Y, invariant under the bbox shift); `output/resize_report.txt` evolves intentionally on the two FIN remove records — `remove_fin_strip` returns the actual fixture bbox (`y1=136`) instead of the legacy synthesised one (`y1=137`). Same precedent as M2's "report evolves intentionally" note. Pytest 155/155 (134 post-M4c + 21 new). M4 milestone block: M4d marked Done with file/atomic-by-atomic notes for M4e. Verification snapshot row 8 (DEVICE_GATE/DEVICE_DIFF/CUT) updated — CUT now lit by `add_cut_cell`. Minimal Starter PR pointer flipped to **M4e** (cell-level DRC + performance instrumentation). |
| 2026-04-28 | Claude (`claude/review-arch-plan-Niwe4`) | **M4c complete.** Parser tier-dispatch + B-tier projection + per-shape `device_id` refinement + retirement of the desc-substring filter. `io_adapters/parser.py`: `apply_lvs_overlay` now picks `device_id` per shape via the new `_device_for_shape(sr, devices, candidates=...)` helper — bbox-containment with a max-overlap-area fallback, scoped by the LVS net's pin-device list. The OUT net's two LI shapes get distinct `device_id`s (MN0 / MP0); the VSS / VDD M1 power rails end up with `device_id=None` because they sit outside any device bbox (correct semantics; the solver's LI-only filter never reaches them). New `project_b_tier_shapes(model, grid, devices)` registers OD/VIA0 axes and stamps a `CellOccupancy` per projected cell with `owner_device_id` + `shape_record` backlink + the right `OccupantType` (`DEVICE_DIFF` / `VIA` / `CUT`); a second pass appends every sibling device whose bbox overlaps an OD shape to that shape's cells' `shared_with[]` (diffusion sharing). The MVP fixture has no overlapping device bboxes so `shared_with` stays empty; a synthetic two-device-overlap test exercises the sharing path. `core/solver.py::_reshape_li_sd_bars`: replaces the `device_y_marker not in seg.desc` filter with `seg.shape_record.device_id == device.inst_name`. The legacy desc-substring fallback stays available for callers that build `TrackSegment`s without going through `build_layout_model` (M4d removes it). New `tests/unit/test_parser_tier_dispatch.py` (15 tests) covering: per-shape device_id refinement on OUT, single-pin nets unchanged for in-device shapes, `_device_for_shape` containment / fallback / candidate-filter, B-tier axis registration, OD cell ownership split across MN0/MP0, MVP `shared_with` empty, synthetic two-device overlap exercises sharing, VIA0 cells carry `OccupantType.VIA`, `TrackSegment.shape_record.device_id` per-segment correct. Acceptance: pytest 134/134 green (119 post-M4b + 15 new); `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M4b baseline. M4 milestone block: M4c marked Done, files-touched and notes refreshed; Minimal Starter PR pointer flipped to **M4d** (B-tier L2 atomics + macro migration). |
| 2026-04-27 | Claude (`claude/review-arch-plan-Niwe4`) | **M4b complete.** CSP cell-grid axis + net-equivalence union-find. Purely additive — no current pipeline path keys off the new surfaces, byte-golden preserved by construction. `core/grid.py`: `MultiLayerGrid` gains `b_tier_axes` + sparse `b_tier_cells` storage plus `is_b_tier_layer()` / `register_b_tier_axes()` / `bbox_to_b_tier_cells()` / `set_b_tier_cell` / `get_b_tier_cell` / `b_tier_cells_of()` / `_axis_track_range()`. Registration rejects A-tier layers and unregistered axis layers (fail-loud); the bbox projection sorts output for determinism. `core/csp_engine.py`: union-find lives on `ConstraintEngine` — `_uf_parent` + `_uf_size` (union-by-size, no path compression so `restore` stays simple) plus `_uf_trail` and `_uf_checkpoints` (maps each `checkpoint()` return to the matching `_uf_trail` length without changing the public return type). New methods `mark_cut(pos)` (mirrors M3 `mark_blockage`), `union(pos_a, pos_b)` (adjacent + same-net + non-CUT preconditions; the §B "no CUT between adjacent cells" rule is enforced because a chain of adjacent unions across a CUT fails at the cut step), `net_of(pos)`, `connected_to(pos)`, `connected_cells(net_id)`. `restore` extended to undo unions in reverse order before cell-trail rollback. New `CommitDelta(cells, unions)` dataclass returned by `commit_with_full_delta`; the M2-era `commit_with_delta` is preserved verbatim (the solver's `len(delta)` call site at `core/solver.py:351` and the M2 list-indexing tests stay green) and now also drops the union trail on commit. Verification snapshot rows 9 + 10 marked resolved. M4 milestone block updated: M4b sub-block marked Done with file references; Minimal Starter PR pointer flipped to M4c (parser tier-dispatch). Acceptance: pytest 119/119 green (85 post-M4a + 34 new — 11 in `tests/unit/test_b_tier_grid.py` covering tier dispatch / axis registration / bbox-to-cells / set-get round-trip / ordered iteration; 23 in `tests/unit/test_net_equivalence.py` covering `mark_cut` semantics, all `union` preconditions including the cut-endpoint case, query API, restore-undoes-unions for both single and chained cases, `commit_with_full_delta` shape + truncation, legacy `commit_with_delta` invariant). `output/buffer_resized.{json,cdl}`, `output/resize_report.txt`, and `output/annotation_coverage.txt` md5-identical to the M4a baseline. |
| 2026-04-27 | Claude (`claude/review-arch-plan-Niwe4`) | **M4a follow-up (Codex P2 review).** Tightened `CellOccupancy` structural guards. `__post_init__` now requires `tier_of(layer) == 'B'` (deferred import of `tech.layer_map.tier_of` to avoid a module-load-time `core <-> tech` cycle); `KeyError` from `tier_of` propagates so unmapped layers surface loud. `add_sharer` now requires `occ_type == DEVICE_DIFF` per §B's "shared_with is OD/diffusion-only" rule — a CUT / VIA / BLOCKAGE cell with `owner_device_id` set still cannot record sharers. Existing `test_cell_occupancy_rejects_non_b_tier_occupant` switched layer from `'LI'` to `'OD'` so it isolates the occ_type check. New tests: `test_cell_occupancy_rejects_a_tier_layer`, `test_cell_occupancy_rejects_c1_c2_layers`, `test_cell_occupancy_unknown_layer_raises`, `test_add_sharer_requires_device_diff`. Pytest 85/85 (81 from M4a + 4 new). |
| 2026-04-27 | Claude (`claude/review-arch-plan-Niwe4`) | **M4a complete.** Data-model + tier-marker foundation for M4. Purely additive — no current pipeline path keys off the new surfaces, byte-golden preserved by construction. `core/data_model.py`: added `OccupantType.CUT`; defined `CellOccupancy(layer, track_a, track_b, occ_type, net_id, owner_device_id, shared_with, shape_record)` with `add_sharer` / `remove_sharer` / `pos` accessors and a `__post_init__` guard that rejects A-tier `OccupantType.WIRE` so M4c projection can't silently mis-route a layer. The `shape_record` field carries through the M3 backlink seam. `tech/layer_map.py`: added `LAYER_TIER` (A/B/C1/C2 markers per §B), `A/B/C1/C2_TIER_LAYERS` subsets, `CUT_LAYERS = ('CPO', 'M0_CUT', 'FIN_CUT')`, plus `tier_of()` / `layers_in_tier()` / `is_cut_layer()` helpers. CPO / M0_CUT / FIN_CUT / VT / PP / NP / DNW / DIODE / ESD / TEXT have tier markers without yet having `LAYER_MAP` GDS-number entries — locks tier intent before geometry shows up. Verification snapshot rows 8 and 9 marked half-built (M4a wired the seam, M4b lights it up); row 18 marked resolved. M4 milestone block decomposed into M4a–e sub-milestones; M4a marked Done with file/line references. Acceptance: pytest 81/81 green (65 pre-M4a + 16 new — 9 in `tests/unit/test_cell_occupancy.py`, 7 in `tests/unit/test_layer_tiers.py`); `output/buffer_resized.{json,cdl}` and `output/resize_report.txt` byte-identical to the M3 baseline. The structural test `test_every_layer_map_entry_has_a_tier` is the fail-loud guard for future `LAYER_MAP` entries that forget a tier marker. Minimal Starter PR pointer flipped to M4b (CSP cell-grid axis + net-equivalence union-find). |
| 2026-04-27 | Claude (`claude/review-arch-plan-LKbJL`) | **M3 complete.** M3a: added `core/data_model.py::ShapeRecord` (geometric record with optional LVS overlay — `net_id` / `device_id` / `pin_role` — plus `provenance` / `is_derived` / `suspect_tags` seams) and `LayoutModel.shape_pool` + `LayoutModel.annotation_coverage()`. `TrackSegment.shape_record` is the canonical per-segment backlink; the M2 `bbox_nm` cache is retained for byte-golden writeback. M3b: inverted `io_adapters/parser.py`. New `build_shape_pool(bbox_data)` + `apply_lvs_overlay(pool, net_data, devices)` make GDS the geometric truth and LVS an annotation overlay matched by `(layer, bbox)`; `build_layout_model` runs both, attaches the pool, and stamps each `TrackSegment.shape_record`. M3c: `core/csp_engine.py::ConstraintEngine.mark_blockage` — sets `cell.assignment=BLOCKAGE`, `domain={BLOCKAGE}`, `fixed=True`, idempotent, and refuses to overwrite annotated assignments (conservative-default rule §D). The existing `assign` short-circuit (`if cell.fixed: return cell.assignment == state`) makes subsequent `propose_assign` rejections automatic. M3d: `core/solver.py::LayoutSolver.project_unannotated_blockages` — iterates `model.shape_pool`, projects unannotated CSP-layer shapes through `MultiLayerGrid.physical_to_segment_coords`, marks each cell as BLOCKAGE; pipeline calls it after `load_existing_layout`. M3e: pipeline emits `output/annotation_coverage.txt` from `LayoutModel.annotation_coverage()`. Verification snapshot rows 6 and 7 marked resolved; row 12 marked half-built (M3 added the `is_derived` field, M5 lights it up); rows 21 and 22 added for shape_pool + coverage report. Acceptance: `tests/unit/test_blockage.py::test_li_stub_makes_assign_segment_cells_infeasible` injects an unannotated LI stub, projects to BLOCKAGE, then verifies `atomic_ops.assign_segment_cells` returns `failed_pos` with engine state restorable. Byte-golden: `buffer_resized.{json,cdl}` and `resize_report.txt` byte-identical to M2 baseline; `buffer_resized.gds` polygon-set identical (30/30) — only the GDS library timestamp differs per write. Pytest 65/65 (50 pre-M3 + 15 new). Minimal Starter PR pointer flipped to M4. |
| 2026-04-26 | Claude (`claude/review-arch-plan-Li1Az`) | **M2 complete.** M2a: extended CSP trail to `(pos, prev_domain, prev_assignment)` and added `propose_assign` / `propose_release` / `commit_with_delta` (`core/csp_engine.py:206-285`); 6 new unit tests cover round-trip restore, trail truncation, propose-assign rollback, and intra-transaction release+reassign. M2b: created `core/atomic_ops.py` with the M2 minimal L2 subset (`release_segment_cells`, `assign_segment_cells`, `modify_segment` with `failed_pos` localisation). M2c: refactored `resize_device` (`core/solver.py:226-322`) into the L3 `device_resize` macro, routing LI cell-level changes through L2 + CSP, with stricter device-marker filtering on LI segments. M2d: deleted Phase 2 helpers `_shrink_li_sd_bars`, `_derive_poly_span`, `_extend_li_for_vias` from the decoder; Phase 1 grew `_apply_li_modifies` and `_apply_poly_modifies` (the latter accepts partial-bbox EditOps with `None` sentinels). M2e: added `TrackSegment.bbox_nm` stamping in the parser so emitted L1 `old_bbox` records are pixel-accurate even on odd-width layers (LI = 17 nm). Verification snapshot rows 3, 4 marked resolved; row 11 noted as smaller; new row 20 records the L2 module. Acceptance: `output/buffer_resized.{gds,json,cdl}` byte-identical to M1 baseline; conflict-injection test exercises macro-level rollback; pytest 50/50 (12 new). Resize report now lists 7 ops vs M1's 6 — the macro lifted POLY span derivation (and the M1 cross-net leakage in MN0's report) into explicit L1 EditOps. Minimal Starter PR pointer flipped to M3. |
| 2026-04-25 | Claude (`claude/m1-decoder-writeback`) | Roadmap refinement after M1 implementation: M2 milestone block now records that it deletes the decoder's `_derive_poly_span` and `_extend_li_for_vias` helpers; M5 block records that it deletes `_derive_nwell` / `_derive_boundary`. Verification snapshot row 11 updated — the NWELL/BOUNDARY formulas are no longer in `pipeline/run_mvp.py:130-138` (M1c removed those loops); they are consolidated as transitional Phase 2 helpers in `core/decoder.py` awaiting the M5 derivator. Makes the M1 → M2 / M5 eviction path mechanical rather than implicit. |
| 2026-04-25 | Claude (`claude/m1-decoder-writeback`) | **M1 complete.** M1a: unified `EditOp` (`core/diff.py:16-37`; `core/solver.py:26` imports); duplicate dataclass removed. M1b: built `core/decoder.py::WritebackDecoder` consolidating writeback geometry into Phase 1 (explicit EditOp apply: FIN remove + OD modify) and Phase 2 (derived: POLY span, LI shrink + via-coverage extension, NWELL/BOUNDARY extents). M1c: removed legacy 125-line `apply_edits_to_layout_data` from `pipeline/run_mvp.py`; sole call site is the decoder. Verification snapshot rows 1 and 2 marked resolved. Acceptance: pipeline JSON/CDL/report byte-identical under fixed `PYTHONHASHSEED`; GDS polygons identical (30/30); pytest 38/38 (added 5 decoder tests). Discovery: M1's "decoder consumes EditOp stream" goal is partial — the solver emits EditOps for FIN/OD/LI but not POLY/NWELL/BOUNDARY; the decoder's Phase 2 fills the gap and is the seam where M5's derivator will plug in. |
| 2026-04-25 | Claude (session `claude/check-stream-env-vars-N5suX`) | Initial English roadmap created from Chinese architecture-analysis source. Verification snapshot generated against branch state on this date. All seven milestones marked Not started. |
