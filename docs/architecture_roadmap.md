# Layauto Architecture Roadmap

**Purpose.** Living tracker for the multi-milestone architectural evolution of the Layauto layout pipeline. This document is the canonical handoff artifact: any new contributor (human or Claude session) should read it first, re-verify the file/line references in [Verification Snapshot](#verification-snapshot), then pick the next milestone from [Milestone Roadmap](#milestone-roadmap).

**Last verified:** 2026-04-25 on branch `claude/check-stream-env-vars-N5suX`.

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

| # | Claim | Where (verified 2026-04-25) | State |
|---|-------|-----------------------------|-------|
| 1 | Two `EditOp` classes coexist | `core/diff.py:16-33` and `core/solver.py:28-45` | drift target |
| 2 | Per-layer hardcoded y1/y2 in writeback | `pipeline/run_mvp.py:31-155` (loops at 63-138) | drift target |
| 3 | `resize_device` bypasses CSP for geometry | `core/solver.py:208-419` | drift target |
| 4 | CSP engine has only `checkpoint`/`restore` + stateless `unassign` (no `propose_assign`/`commit_with_delta`) | `core/csp_engine.py:296-300, 334` | drift target |
| 5 | Anchor-layer propagation filter exists | `core/csp_engine.py:250-254` | OK to keep |
| 6 | Parser is net-primary, bbox auxiliary | `io_adapters/parser.py:71-198` | drift target |
| 7 | `OccupantType.BLOCKAGE` exists and is used by solver, but not for unannotated shapes | `core/data_model.py:21-28`, `core/solver.py:21` | half-built |
| 8 | `OccupantType.DEVICE_GATE` / `DEVICE_DIFF` defined but unused; no `CUT` | `core/data_model.py:21-28` | placeholder only |
| 9 | `MultiLayerGrid` is 1D-track only; no `CellOccupancy` | `core/grid.py:87-240` | not built |
| 10 | No net-equivalence union-find in CSP | `core/csp_engine.py` (whole file) | not built |
| 11 | NWELL / BOUNDARY produced by hardcoded loops | `pipeline/run_mvp.py:130-138` | drift target |
| 12 | No `core/drc_derivator.py`; no `is_derived` field | absent | not built |
| 13 | No `core/macros/` directory; no `pick_macro` dispatch | absent | not built |
| 14 | `diff_to_edit_ops` handles add/remove only (no device-level) | `core/diff.py:66-74` | drift target |
| 15 | SKILL emitter is `printf` placeholder | `io_adapters/writer_skill_script.py:76-78` | drift target |
| 16 | Three dummy Calibre JSON generators | `dummy/gen_buffer_layout.py:364, 402, 434` | OK for now |
| 17 | Per-layer DRC rule registration | `core/drc_constraints.py:131-161` | OK to keep |
| 18 | Layer map has no tier markers | `tech/layer_map.py:8-18` | drift target |
| 19 | Six-stage pipeline order: diff_cdl → build_layout_model → setup_engine → load_existing_layout → resize_device → apply_edits → write_gds | `pipeline/run_mvp.py:326-469` | OK structure |

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

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Eliminate the duplicate `EditOp` between `core/diff.py` and `core/solver.py`. Replace per-layer hardcoded geometry recomputation in `apply_edits_to_layout_data` with a decoder that consumes a unified `EditOp` stream and routes coordinate computation through `MultiLayerGrid.segment_to_physical`.
- **Files touched.**
  - `core/diff.py` — sole `EditOp` definition: `ShapeAdd` / `ShapeRemove` / `ShapeModify` + `layer` + `bbox_nm` + `provenance`.
  - `core/solver.py:208-419` — drop the local `EditOp` class; `resize_device` emits the unified format.
  - `pipeline/run_mvp.py:31-155` — `apply_edits_to_layout_data` becomes a decoder loop; keep the `deepcopy` transaction boundary.
  - `core/grid.py` — strengthen `segment_to_physical` to cover FIN / OD / POLY / LI / NWELL / BOUNDARY completely.
- **Change outline.**
  - Stop branching on layer to recompute y1/y2; iterate `EditOp`s and patch in place.
  - Migration strategy: dual-write — keep the legacy hardcoded path alongside the decoder, byte-diff golden against the live MVP, then remove the legacy path.
- **Acceptance.** Buffer resize (nfin 5↔7, 5↔3) passes end-to-end; output GDS/JSON byte-identical to current MVP golden.
- **Dependencies.** None — first PR.
- **Risks.** Hidden ordering coupling inside the legacy hardcoded branches (e.g., POLY y1 depending on OD already adjusted).

### M2 — CSP genuinely drives resize decisions, with strict layer-1/2/3 split

- **Status:** [ ] Not started
- **Owner:** _unassigned_
- **Goal.** Demote `resize_device` to a true L3 macro that expands into L2 primitives. L2 only proposes cell-level changes to the engine; the decoder synthesizes L1; the engine handles feasibility and transactions.
- **Files touched.**
  - `core/solver.py:208-419` — `resize_device` becomes an L3 macro; geometry recomputation moves out to the decoder.
  - `core/csp_engine.py` — expose stable API: `propose_assign` / `propose_release` / `checkpoint` / `restore` / `commit_with_delta`. Returns feasibility + cell delta.
  - **New** `core/atomic_ops.py` — L2 primitives: `add_segment`, `remove_segment`, `modify_segment`, `add_via`, `remove_via`, `add_cell_occupancy`, `remove_cell_occupancy`, `extend_od`, `extend_poly`, `add_fin_strip`, `remove_fin_strip`, `add_cut_cell`, `remove_cut_cell`, `mark_shared_diffusion`.
  - **New** `core/decoder.py` — subscribes to commit deltas; emits L1 `EditOp`s and updates `LayoutModel` indexes; sole holder of `segment_to_physical`.
- **Change outline.**
  - L2 must not touch `LayoutModel`, must not produce L1, must not decide feasibility.
  - `device_resize` macro: metadata delta → ordered sequence of `extend_od` + `extend_poly` + `add/remove_fin_strip` calls, wrapped by `engine.checkpoint`/`restore`.
  - Decoder + derivator push L1 in commit-delta order.
- **Acceptance.** Inject a deliberate conflict (e.g., LI shrink collides with a VIA enclosure) → macro returns `infeasible`, CSP state is restored to pre-call snapshot. Byte-golden with M1 baseline preserved on the no-conflict path.
- **Dependencies.** M1.
- **Risks.** CSP rollback semantics are currently weak (`unassign` does not restore domains). Land checkpoint/restore unit tests *before* wiring primitives. Decoder + L1 emission order must be deterministic to preserve golden.

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
  - `pipeline/run_mvp.py` — delete the NWELL and BOUNDARY hardcoded loops.
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

If only one milestone is in scope: **start with M1.** It addresses the largest writeback inconsistency (the duplicate `EditOp` + per-layer hardcoded geometry), and every later milestone depends on a unified `EditOp` plus a decoder. M2 onward layer in transactional CSP, parser inversion, B-tier cells, derivators, macros, and tool closure on top of the M1 foundation.

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
| 6. Emit output | `apply_edits_to_layout_data()` → `write_gds()` | `pipeline/run_mvp.py:425, 432` |

The pipeline is **incremental, not from-scratch**: `build_layout_model` reads existing layout, `load_existing_layout` pre-stamps every existing segment as `FIXED`, and `apply_edits_to_layout_data` deep-copies + patches per-layer rather than re-laying out.

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

`pipeline/run_mvp.py::apply_edits_to_layout_data()` (line 31-155). Inputs: `orig_data` + solver `edit_ops_n` / `edit_ops_p` + new `nfin`. `EditOp` is *parameter-level*, not GDS-level patch; geometry is recomputed per-layer.

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
| 2026-04-25 | Claude (session `claude/check-stream-env-vars-N5suX`) | Initial English roadmap created from Chinese architecture-analysis source. Verification snapshot generated against branch state on this date. All seven milestones marked Not started. |
