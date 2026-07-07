# Layauto backlog

> Things not implemented but worth considering. For shipped work see [`changelog.md`](changelog.md). For the architectural model these items extend, see [`architecture.md`](architecture.md).

**Categories** (top to bottom): milestones in flight → milestones not started → cross-cutting deferrals → tooling / production integration → test-coverage gaps.

---

## Next milestone — M6c (routing subsystem)

The recommended starter PR. Unblocks M6d (the routing-dependent macros).

**Goal.** Add a CSP-aware path-search subsystem that L3 connectivity-changing macros can call. Single-source, single-target, single-cell scope.

**Files to create.**
- `core/router/__init__.py`
- `core/router/astar.py` (or `maze.py`) — path search proper.
- `core/router/cost.py` — cost function (layer-change penalty, preferred direction, blockage proximity).
- `core/router/obstacles.py` — obstacle queries against `engine.cells` / `engine.layer_dims` / `engine.connected_cells(net_id)`. (If **M11** lands first, these queries target the unified occupancy store + connectivity index instead — see M11.)
- `tests/unit/test_router*.py` — synthetic clear-path / obstacle-detour / no-path fixtures.

**Behaviour.** Read-only over the engine. Consumes current cell state (assignments + domains + blockages + cuts) as obstacles, produces a *plan* — a sequence of cell positions on legal layers. The plan is handed to a macro that calls `propose_assign` per cell inside a transaction. Router itself never calls `propose_assign`.

**Bounded scope.** Single-source single-target; single-cell only; capped iteration count; surface a "no-path" outcome cleanly so callers don't loop indefinitely. Multi-target / multi-cell / global routing are post-M7.

**Acceptance.** Synthetic single-source single-target fixture with one obstacle: router returns a plan that avoids the obstacle, and the plan's `propose_assign` chain is feasible end-to-end (no DRC violation on commit). Rip-up: when no path exists, returns `None` (or raises) — caller decides whether to release a conflicting route and retry.

**Risks.** Search-space explosion. Bound the search to the engine's current bounds plus a small margin; cap iteration count.

**Dependencies.** M2, M3, M4.

---

## M6d — routing-dependent macros

**Goal.** Ship the macros that need M6c's router. Closes the M6 milestone.

**Files to create.**
- `core/macros/device_add.py` — projects FIN/OD/POLY shapes; calls router for G/D/S/B pin connections.
- `core/macros/device_remove.py` — drops the device's owned shapes; calls router to clean up orphan segments.
- `core/macros/net_reroute.py` — rip-up + reroute via M6c.
- `core/macros/buffer_insert.py` — `device_add × 2` (NMOS + PMOS) plus router calls to splice the buffer into the existing net.

**Pipeline-side wiring.**
- `io_adapters/cdl_parser.py::diff_cdl` extends to detect device add / remove deltas (currently only `nfin` parameter changes are recognised).
- `core/macros/pick_macro.py` dispatch table grows to route the new diff entries.
- `tech/layer_map.yaml` — add GDS-number entries for `CPO` / `M0_CUT` / `FIN_CUT`. The fixture doesn't generate cut-layer geometry yet, so the `gds:` entries are write-only until M6a's `add_cut` macro is exercised by a fixture that needs them.

**Acceptance.**
- CDL gains an inverter → pipeline emits a legal layout.
- CDL drops a device → released shapes cleared, annotations updated, shared diffusion auto-degrades to single-owner.
- Two devices request shared S/D → `share_diffusion` macro lands legally with full L1 emission.
- Same poly must be cut → `add_cut` macro inserts a CPO mid-span and splits the net.

**Risks.** Order-of-operations bugs around `split_diffusion` + `add_cut` + rip-up. Engine-rollback discipline must hold across the entire macro transaction.

**Dependencies.** M6a, M6b, M6c.

---

## M7 — Virtuoso SKILL and Calibre DRC/LVS closure

**Goal.** Replace placeholder SKILL emission and dummy Calibre with real tool integration. First exit from the dummy environment.

**In flight (precursor).** Four LVS-query slices have landed (all 2026-05-07):

  * **iXref** (`INSTANCE XREF WRITE`) — saves `output/ixref.yaml` mapping layout devices to source devices (with the `X` swap flag).
  * **nXref + NET NAMES** (`NET XREF WRITE` + `NET NAMES`) — saves `output/net_xref.yaml` joining schematic_name → lvs_name → lvs_index.
  * **DEVICE INFO** (per-device `DEVICE INFO <layout_inst>`) — saves `output/device_info.yaml` per-device {layer → [bbox_um, ...]} for LVS-derived seed shapes.
  * **NET SHAPES** (per-net `NET SHAPES <lvs_name>`) — saves `output/net_shapes.yaml` per-net {layer → [bbox_um, ...]} for routing-layer (LI / VIA0 / M1) shapes that belong to each net.

All four run from `io_adapters/calibre_query.py`'s Stage 1.5 with `mode={dummy,calibre}` (CLI `--lvs-mode`). Save-only today; M7-main will wire the YAMLs into LVS-driven macros (net-equivalence overrides for swapped S/D, layout-vs-source device-identity reconciliation, schematic-net → lvs-index lookup for DRC-violation localisation, derived-shape bbox lookup for per-device DRC error mapping, per-net routing-shape bbox lookup for net-aware DRC violation tracing).

**Files to create / replace.**
- **New** `io_adapters/skill_emitter.py` — replaces the `printf` placeholder in `writer_skill_script.py`. Walks `shape_pool` + `EditOp` records; every emitted edit gets a provenance comment.
- **Extend** `io_adapters/calibre_query.py` (or rename to `calibre_runner.py` if it outgrows its current scope) to also host real DRC + LVS subprocess invocations. Reuse the `mode` / `svdb_dir` / `timeout_s` plumbing already in place. Consider consolidating the per-query subprocess calls into a single interactive HDB session (one Popen, multiple commands streamed in order) — the current per-query pattern is fine for testing but needlessly slow against a real `calibre` binary.
- `io_adapters/parser.py::build_layout_model` — optional `ixref_yaml` / `net_xref_yaml` / `device_info_yaml` / `net_shapes_yaml` params; when supplied, S/D-swapped devices use the iXref-corrected pin map, net annotations look up via `net_xref.yaml`'s lvs_index, and per-device + per-net derived-shape bboxes from `device_info.yaml` / `net_shapes.yaml` feed into the C1 derivator's coverage check + DRC violation tracing.
- `pipeline/run_mvp.py` — append DRC/LVS calls; feed results back to L3 macro provenance; consume `ixref_yaml` + `net_xref_yaml` + `device_info_yaml` + `net_shapes_yaml` for net-equivalence overrides, DRC-error → device-name localisation, and DRC-error → schematic-net localisation.

**Sub-slice 1.6 (deferred): LVS layer-name mapping + effective-region trimming.** The current 1.5 slices use GDS layer names directly (`LI` / `VIA0` / `M1` / `ngate_lvt` / `pgate_lvt`) and report whatever bbox the parametric generator emits. Production LVS may use different layer-name conventions (e.g., `ngate_lvt_eff`, `m1_routing`) and must trim cut/extension regions so the bbox represents the effective conducting (or device-active) region only. 1.6 will land:
  * a layer-name mapping table in `tech/layer_map.yaml` (or a sibling `lvs_layer_map.yaml`) translating GDS → LVS-derived layer names per direction.
  * a trimming pass in `io_adapters/calibre_query.py` (or a downstream consumer) that subtracts cut shapes / extension margins from the raw seed bbox before reporting `bbox_um`.
  * tests exercising both the mapped layer name and the trimmed bbox against synthetic inputs that include cuts.

**Sub-slice 1.7 (planned): retire `calibre_device_query.json` / `calibre_net_query.json`, feed `build_layout_model` from the 1.5 YAMLs.** Today Stage 2 reads three JSON inputs — `calibre_device_query.json`, `calibre_net_query.json`, `bbox_by_layer.json`. The first two are *legacy convenience formats* written by `dummy/gen_buffer_layout.py:generate_calibre_{device,net}_query` (Python-dict serialisation, not actual Calibre output formats); the third is already production-clean (`gds_to_bbox_by_layer` → GDS round-trip via gdstk, the M3 §A "geometry truth" path). The four 1.5 YAMLs (`ixref` / `net_xref` / `device_info` / `net_shapes`) carry the same information the legacy two JSONs do, sourced from actual Calibre HDB queries, but split along the three-sources-of-truth axes. 1.7 closes the loop.

  * **Keep.** `bbox_by_layer.json` as the geometric source — GDS round-trip already works on production GDS, and it's the only path that sees *unannotated* shapes (filler / ESD / dummy gates) that `project_unannotated_blockages` needs as BLOCKAGE seeds. LVS-only sourcing would render those invisible.
  * **Retire.** `calibre_device_query.json` and `calibre_net_query.json` from `inputs:`. Their fields fan out as follows:
    - `device.instance` / `device_type` ← `ixref.devices[].source_inst` joined with parsed CDL device records.
    - `device.parameters.{nfin,l,w}` ← parsed CDL (Stage 1 output) — these have never been a Calibre query field anyway; they were just bundled into the dummy JSON for convenience.
    - `device.pins.{G,D,S,B}` ← reconstructed from `(CDL terminal-order DGSB) ⊕ (net_xref.schematic_name → lvs_name) ⊕ (ixref.sd_swapped flips D↔S only)`. Use `net_xref.lvs_index` as the stable key for unnamed nets — Calibre re-numbering renames `net9` between runs.
    - `device.bbox` ← envelope of `device_info.devices[].layers[gate-layer].shapes[*].bbox_um` (×1000 → nm). Gate-layer name (`ngate_lvt` / `pgate_lvt` / …) translates back to a GDS layer via the 1.6 mapping table.
    - `device.fin_y_positions` ← derived two ways and cross-checked: (a) **geometric** — pick FIN rectangles from `bbox_by_layer['FIN']` whose center lies inside the device bbox.x range, sort by center_y, dedupe; (b) **arithmetic** — `[gate_bbox.y1 + pitch/2 + k*pitch for k in range(nfin)]`. Geometric wins; arithmetic disagreeing → log a warning (NMOS/PMOS gap that isn't a fin-pitch multiple).
    - `net.type` ← heuristic (`VSS`/`VDD` → power, else signal); promotable to `.GLOBAL` / `.POWER` parsing in the CDL parser if needed.
    - `net.pins` ← walk parsed CDL devices; for every `(inst, terminal)` whose schematic-side net equals this net, emit `(layout_inst, pin)` via the iXref translation (apply S/D swap).
    - `net.shapes` ← `net_shapes.nets[k].layers[*].shapes[*].bbox_um` (×1000 → nm), grouped by GDS-layer (1.6 mapping). Direct replacement.
  * **Files to land.**
    - **New** `io_adapters/lvs_loader.py` with `LvsBundle` dataclass (`ixref / net_xref / device_info / net_shapes` parsed dicts) and helpers `load_lvs_bundle(paths)`, `lvs_layer_to_gds_layer(name)` (delegates to 1.6 table once available, in-line minimal table until then), `reconstruct_device_pins(cdl_dev, ixref_entry, net_xref)`, `derive_fin_y_positions_{geometric,arithmetic}(device_info, bbox_by_layer, nfin, config)`, `_um_to_nm(bbox)` with ±1 nm round-trip assertion.
    - **New** `io_adapters/parser.py::apply_lvs_overlay_v2(pool, bundle, cdl_data)` — stamps `net_id` (from `net_shapes` keyed by `lvs_index`) / `device_id` (from `device_info` gate shapes + the existing `_device_for_shape` geometric tiebreaker for OUT-style multi-device routing nets) / `pin_role` (from reconstructed pins) onto `ShapeRecord`s. Keep the M3 conservative-defaults rule: no traversal, no silent merges, sub-nm drift handled by the M3 tolerance check (see "LVS bbox tolerance" below).
    - **New** `io_adapters/parser.py::build_layout_model_v2(bbox_path, cdl_data, lvs_bundle, config)` — replaces the two `parse_calibre_*` calls. Same return type `(LayoutModel, MultiLayerGrid)`; alive alongside the legacy entry behind a site_config flag during transition.
    - **Pipeline-side** `pipeline/run_mvp.py` — pass Stage 1.5's already-parsed `parsed_ixref / parsed_net_xref / parsed_device_info / parsed_net_shapes` straight into `build_layout_model_v2` (no second YAML round-trip).
    - **Tests.** Unit-tests for each helper against the existing dummy fixtures — `reconstruct_device_pins(MN0)` must produce `{G:IN, D:OUT, S:VSS, B:VSS}` byte-equal to today's `calibre_device_query.json`. Integration test: byte-golden equivalence of the v2 pipeline output against `output/buffer_resized.gds`.
  * **Site-config impact.** `inputs.device_query` / `inputs.net_query` retired; `inputs.{ixref,net_xref,device_info,net_shapes}_yaml` (already present) become required for the v2 path. Add `format.parser_path: legacy | v2` flag for the transition window.
  * **Coordinate with sub-slice 1.6.** `apply_lvs_overlay_v2`'s layer-name translation depends on 1.6's `lvs_layer_map.yaml`. Landing 1.7 ahead of 1.6 means an in-line minimal map (`{ngate_lvt, pgate_lvt, ngate_*, pgate_*} → POLY`, `{nsd, psd} → OD`, identity otherwise) that 1.6 deletes — acceptable, just keep the call site singular.
  * **Depends on M9 for segment construction.** Today `Net.segments` / `Net.vias` are built by iterating `net_data['shapes']` (the net-query JSON), so 1.7 cannot simply delete `calibre_net_query.json` without first inverting segment/via construction to read the annotated `shape_pool` instead. That inversion is M9's job. Land M9 first (or fold the segment-inversion part of M9 into 1.7); `build_layout_model_v2` then groups A-tier segments by `ShapeRecord.net_id` rather than from `net_data`.
  * **Out of scope.** Multi-Vt fixtures, SDT / LIG, multi-finger devices — 1.7 lands the seam against the current single-cell fixture; richer LVS-layer set lands as fixtures grow (and forces 1.6 to materialise).

**Acceptance.** Real PDK environment: buffer resize → SKILL load → DRC clean → LVS match. Inject a violating edit → DRC fail localizes to the responsible L2 op.

**Risks.** PDK redaction may block end-to-end validation. Keep an injection harness that mocks DRC violations.

**Dependencies.** M1–M6 all complete; iXref + nXref + DEVICE INFO + NET SHAPES slices already in.

---

## M8 — FIN as static backdrop (de-edit FIN, derive fin attribution from OD)

**Goal.** Bring the FIN layer in line with FinFET reality: fins are **continuous horizontal stripes across the entire cell at fixed pitch**, never drawn or edited by designers. The only thing a resize touches is the **OD** layer; which fins are electrically active is then a geometric consequence of `FIN ∩ OD`, computed on demand. Removes the per-device fin add/remove edit path from L1/L2/L3 entirely.

**Motivation — three violations of the foundry-PCell mental model the current code embeds.**

  1. **Dummy generator draws FIN per device, not as cell-wide stripes.** `dummy/gen_buffer_layout.py:163-168` loops over `nmos_fin_y` / `pmos_fin_y` and emits `nfin_n + nfin_p` separate FIN rectangles; the resulting `bbox_by_layer.json` has 12 FIN shapes covering only the device-local Y intervals and **no FIN geometry across the NMOS↔PMOS gap** (y=143..236). Production GDS has continuous stripes at every fin track across the full cell (often across cell boundaries).
  2. **`device_resize` treats FIN as an editable layer.** `core/solver.py:_emit_fin_removes` → `core/atomic_ops.py:remove_fin_strip` actually deletes FIN `ShapeRecord`s from `model.shape_pool`; `core/diff.py` emits `EditOp('remove_shape', layer='FIN', ...)`; `core/decoder.py:_apply_fin_removes` drops the matching FIN rectangle from the output JSON/GDS. A foundry `nfin: 5→4` ECO modifies only OD; FIN geometry is invariant. The current path therefore produces a GDS whose FIN layer doesn't look like what Virtuoso shows for the same PCell.
  3. **Fin → device attribution is Y-only, breaks for multi-device-along-X.** `Device.fin_track_indices` is built in `io_adapters/parser.py:454-458` from `dev._raw_fin_y` (the `fin_y_positions` JSON field) — a flat list of Y values with no X gating. Two same-type devices placed at separate X ranges that share fin tracks would both "own" all the fin tracks. `Device.bbox_nm` carries the X range (and `device_info.yaml`'s gate bbox does too), but the fin path doesn't consult it. `_device_for_shape` in `io_adapters/parser.py:156` already does the right geometric containment for OD and routing shapes — the fix is to put fin attribution through the same primitive.

**Files to land.**

  * **`tech/layer_map.yaml`** — mark FIN with `derived: true`. Tier stays A (the 1D fin-track grid is the right abstraction; only the *edit* status changes). The M6 decoder seam (`core/decoder.py:_reject_derived_edits`) will then refuse any macro-emitted `EditOp(layer='FIN')`, surfacing future violations loud.
  * **`dummy/gen_buffer_layout.py:163-168`** — rewrite the FIN emission loop to draw stripes at every fin track across the full cell height, not per device:
    ```python
    # Sketch: enumerate the full fin-track grid; stamp one stripe per track.
    fin_offset, n_tracks = _cell_fin_grid(cell_height, FIN_PITCH, FIN_OFFSET)
    for k in range(n_tracks):
        fy = fin_offset + k * FIN_PITCH
        add_shape('FIN', 0, fy - hw, cell_width, fy + hw, desc=f'fin_track_{k}')
    ```
    The NMOS↔PMOS gap region now also carries FIN stripes; OD remains unchanged (still two blocks covering the device-local fin set).
  * **`core/data_model.py`** — make `Device.fin_track_indices` a derived `@property` that consults the current shape pool + grid + the device's own `bbox_nm`. The stored attribute becomes a lazy view:
    ```python
    @property
    def fin_track_indices(self) -> List[int]:
        # Geometric: FIN tracks whose stripe center (x_center, y_center)
        # falls inside this device's gate footprint.
        return _fin_tracks_inside_device_bbox(self, shape_pool, fin_grid)
    ```
    The helper uses the same `_device_for_shape`-style center-containment primitive so X disambiguation is free.
  * **Retire** `_raw_fin_y` and `fin_y_positions` from the parser path. (1.7 already pulls the JSON-side field out of `inputs:`; this milestone removes the model-side cache too.)
  * **Delete** `core/solver.py:_emit_fin_removes` (`solver.py:479`), `core/atomic_ops.py:remove_fin_strip` (`atomic_ops.py:406`) and `core/atomic_ops.py:add_fin_strip` (`atomic_ops.py:375`), `core/decoder.py:_apply_fin_removes` (`decoder.py:165`), the `'FIN'` branches in `core/diff.py:EditOp.__repr__`. The `device_resize` macro's step list shrinks to `(OD modify) + (LI reshape) + (POLY modify-if-endpoint-moved) + (C1 derive)`.
  * **Update derivator (optional, recommended).** Add `core/drc_derivator.py:_derive_fin_attribution` that walks the static FIN stripes and stamps each `ShapeRecord` with `device_id` derived from `FIN-stripe ∩ OD-shape ∩ Device.bbox_nm`. Lets downstream consumers (DRC localisation in M7, multi-cell parasitic extraction later) ask "whose fin is this?" without re-running geometry.
  * **`io_adapters/parser.py:build_layout_model`** — drop the `dev._raw_fin_y` assignment branch; pass `shape_pool` to grid construction so `create_mvp_grid` can infer `fin_offset` from the static FIN stripe set rather than from a per-device list.
  * **Tests.**
    - Rebuild byte-golden fixtures (`tests/integration/test_dummy_roundtrip.py` will fail until regenerated — expected; commit the new fixtures with a change-note).
    - `tests/unit/test_atomic_ops.py` — drop the fin-strip atomics' tests (the functions are gone).
    - `tests/unit/test_solver.py` — change resize-result EditOp count assertions (no more `remove_shape FIN` records).
    - **New** `tests/unit/test_fin_attribution.py` — multi-device-along-X synthetic fixture: place two NMOS at `bbox.x=[0,50]` and `[60,110]` on the same fin tracks; assert each device's `fin_track_indices` returns exactly the tracks geometrically contained in its own bbox.x — fail loud if the implementation regresses to Y-only attribution.
  * **Output / reporting.**
    - `output/resize_report.txt` no longer prints `REMOVE FIN ...` lines; update the report template + golden text.
    - `output/buffer_resized.gds` FIN layer matches the input GDS FIN layer byte-for-byte (modulo precision); validates the "FIN is invariant under resize" claim.

**Acceptance.**

  * `nfin: 5→4` resize emits zero FIN EditOps; output GDS has identical FIN stripes to input.
  * Output GDS opens in KLayout / Virtuoso with FIN stripes spanning the full cell (across the NMOS↔PMOS gap), visually indistinguishable from a re-run of the foundry PCell.
  * Synthetic two-NMOS-along-X fixture: each device's `fin_track_indices` returns its own X-bounded fin subset; total cell-level fin track count is the union of both, with overlap counted once.
  * `tech/layer_map.yaml`'s `is_derived` marker actively rejects a macro that tries to `EditOp(layer='FIN', ...)` (regression test).

**Risks.**

  * Byte-golden fixture churn. Mitigated by regenerating + committing new fixtures in the same PR; the new fixtures match production GDS more closely, so this is a one-time pay-down.
  * The "geometric attribution" primitive must be performant on multi-cell layouts. The current shape pool walk is O(devices × fin shapes); when device counts grow, switch the helper to an interval-tree on `device_bbox.x`. M8 ships the O(n×m) version; a follow-up under "Performance & scalability" optimises.
  * `Device.fin_track_indices` becoming property-derived means callers that cached the list now see live values. Audit `core/solver.py:apply_resize_to_model` (which currently slices `fin_track_indices[:new_nfin]`) — that line goes away with the static-backdrop model anyway (FIN doesn't change), but the surrounding state-update pattern needs a re-read.

**Sequencing note.** Land **after** M7 sub-slice 1.7 (which retires `calibre_device_query.json` / `calibre_net_query.json` and forces `fin_y_positions` through a geometric derivation already). 1.7 decouples the LVS-input path from the per-device-fin model; M8 then deletes the per-device-fin model itself. Doing them in the reverse order requires touching the JSON loader twice.

**Dependencies.** M3 (shape_pool primary), M4d (atomic_ops surface), M5 (derivator pattern), M6 (decoder rejection of derived edits), M7 sub-slice 1.7 (LVS-driven device construction).

---

## M9 — Stage 2 normalization: shape_pool single-source, Device/Net as pure semantic IR

**Goal.** Finish the M3 inversion and de-duplicate the Stage 2 object graph. Today `build_layout_model` produces, for a single physical via, up to **six** representations (one `ShapeRecord`, one `ViaInstance`, one `CellOccupancy`, plus three CSP engine cells); and `Device` / `Net` carry denormalized copies of geometry that the annotated `shape_pool` already holds. M9 collapses Stage 2 to one geometric source (`shape_pool` + LVS overlay) and one semantic source (`Device` / `Net` as pure CDL IR), bound by `net_id` / `device_id` / `pin_role` foreign keys.

**Motivation — the representation matrix.** After Stage 2 today (`✓` = a working representation exists):

| Layer | tier | shape_pool | TrackSegment | ViaInstance | CellOccupancy | CSP engine cells |
|-------|------|:---:|:---:|:---:|:---:|:---|
| FIN | A | ✓ | ✗ | ✗ | ✗ | — |
| POLY | A | ✓ | ✗ | ✗ | ✗ | — |
| LI | A | ✓ | ✓ | ✗ | ✗ | WIRE |
| M1 | A | ✓ | ✓ | ✗ | ✗ | WIRE |
| OD | B | ✓ | ✗ | ✗ | ✓ | DEVICE_DIFF |
| **VIA0** | B | ✓ | ✗ | **✓** | **✓** | **VIA + LI-WIRE + M1-WIRE** |

VIA0 is the only layer with four working representations — the visible symptom. The root cause is **stacked migrations that never retired their predecessors**:
- M2: net-primary parser; vias modelled as WIRE cells on LI/M1; A-tier only.
- M3: added `shape_pool` as geometric truth + LVS overlay — but inverted **only the geometry pass**; segment/via construction still iterates `net_data['shapes']` (`io_adapters/parser.py:468`) and merely back-references `shape_pool` via `pool_by_key`.
- M4/M4e: added B-tier `CellOccupancy` (OD/VIA0) + a second engine-load path (`load_b_tier_cells_into_engine`), without removing the M2 via-as-WIRE path.

**Two distinct redundancy classes (only the second is in scope).**
- *Defensible (keep):* `ShapeRecord` (physical-nm geometry) ↔ `TrackSegment` (track-index working repr) — different abstraction levels bound by `shape_record`; and A-tier-1D ↔ B-tier-2D — physically motivated.
- *Genuine (remove):* (1) `ViaInstance` ↔ `CellOccupancy(VIA0)` — both are the via's working form, and `ViaInstance`'s only real consumer (`core/solver.py:_reshape_li_sd_bars:609-616` via-coverage query) is fully answerable from `b_tier_cells['VIA0']` since VIA0's axes are `(LI, M1)`. (2) via-as-LI/M1-WIRE (`load_existing_layout:284-313`) ↔ the LI/M1 segment's own cell stamping — the existing `if cell.is_assigned and ... continue` guard proves the overlap. (3) The net-loop reading `net_data` vs `project_b_tier_shapes` reading `shape_pool` — two passes over two possibly-drifting sources for the same VIA0 geometry, with no reconciliation.

**Device / Net are NOT redundant — they are the semantic-truth IR.** What an annotated `shape_pool` cannot recover: device parameters absent from geometry (`l` / `w` / `nf`), the circuit topology (which devices sit on a net; nets with no shapes), and the resize macro's operand identity (`resize_device('MN0', ...)` needs a `Device('MN0')` to point at). So M9 **keeps** `Device` / `Net` but **slims them to pure semantic fields**, demoting the denormalized geometry to derived views:

| Field | Class | After M9 |
|-------|-------|----------|
| `Device.{inst_name, dev_type, nfin, nf, pins}` | semantic (CDL) | stored |
| `Device.bbox_nm` | LVS anchor (device_info gate bbox) | stored (breaks the stamping cycle — see below) |
| `Device.gate_track_idx` | geometric | `@property` over shape_pool |
| `Device.fin_track_indices` | geometric | `@property` over shape_pool (also M8) |
| `Net.{name, net_type, pins}` | semantic (CDL) | stored |
| `Net.segments` | geometric working repr | view over annotated A-tier `shape_pool` |
| `Net.vias` | geometric working repr | view over `b_tier_cells['VIA0']` (or thin shim type) |

**Prerequisite (do first): close the `engine → shape_pool` writeback loop.** A subtlety that gates the whole view-ification. The DRC "allowed design space" is **not** `Net.segments` / `b_tier_cells` — it is the CSP engine (`engine.cells`, in track coords). Edits are `propose_assign` / `propose_release` against the engine, DRC-checked by propagation; M9 leaves that surface untouched, so "edit only within the legal grid space, never on raw shapes" is preserved exactly. The catch is that today **committed geometry does not uniformly land back in `shape_pool`**: `extend_od` / `remove_fin_strip` update the pool (OD / FIN), but LI / M1 changes from `modify_segment` only touch `engine.cells` and flow out as `EditOp → decoder → output JSON` — the pool's LI / M1 `ShapeRecord`s stay **stale after a resize**. This is harmless today (the single-resize MVP regenerates output from the EditOp stream and never re-reads pool LI), but it breaks the instant `segments` becomes a *view over `shape_pool`* (the view would faithfully reflect the stale record), or a second edit re-reads it (shared-net resize, any M6 macro). So M9 must make `shape_pool` the **authoritative post-edit geometry**: at macro commit, apply the emitted `EditOp` stream — which already carries final nm bboxes — to the matching `ShapeRecord`s, reusing the decoder's `_apply_*_modifies` match-by-bbox logic factored to also target the pool. This fixes a latent inconsistency M9 *surfaces*, it does not introduce one; and it is the hard precondition for everything below. Order: writeback loop → then view-ification.

**Acyclicity.** `Device.bbox_nm` stays a stored field sourced from `device_info.yaml`'s gate bbox (an LVS *input*), not derived from the GDS pool. Dependency order is acyclic: `device_info.yaml → Device.bbox_nm → (geometric containment) → stamp device_id on shape_pool → derive fin/gate/segments/vias as views`.

**State ownership: `grid` is a coordinate system, `model` is the state container.** A second asymmetry M9 must fix (same root cause as the via): A-tier working repr (`TrackSegment`) lives on `model.nets[].segments`, but B-tier working repr (`CellOccupancy`) lives on **`grid.b_tier_cells`**. So `MultiLayerGrid` currently carries *two* responsibilities — coordinate-system definition (pitch / offset / axes / physical↔track transforms) **and** layout state (`b_tier_cells`). The normalization target is a clean split:
- `grid` = pure coordinate system; holds `b_tier_axes` (axis *definitions* are coordinate-system data) but **not** occupancy. Independently testable / swappable.
- `model` = the single layout-state container (geometry `shape_pool` + semantic `Device`/`Net` + derived working views, A-tier *and* B-tier symmetric).

Resolution, staged:
- **Stage A (relocate):** move `b_tier_cells` storage off `grid` onto `model` (or a `model`-held occupancy store). `grid` keeps only `b_tier_axes`. A-tier and B-tier working state now co-locate on `model`.
- **Stage B (derive):** make `b_tier_cells` a derived view over (`shape_pool` B-tier records + grid axes + device bboxes), symmetric with `Net.segments`. `owner_device_id` / `shared_with` are already computed by `_device_for_shape`; the only blocker is that `atomic_ops.extend_od` / `mark_shared_diffusion` mutate cells incrementally — under M9's philosophy those mutations move to `shape_pool` and the view re-derives. Ship A first (smaller blast radius), B when the incremental-mutation audit is done.

**`project_b_tier_shapes` is three phases, not one merge.** `io_adapters/parser.py:305-385` reads `model.shape_pool` and writes `grid.b_tier_cells` — that cross-object write is exactly the ownership violation above. Decompose, don't inline-collapse:

| Phase | Today (`parser.py`) | Lands in |
|-------|--------------------|----------|
| 1. register axes | `:330-342` walk `_B_TIER_AXIS_DEFAULTS` → `grid.register_b_tier_axes` | **grid setup** (coordinate-system data; runs before content traversal; stays on `grid`) |
| 2. project cells | `:344-363` per B-tier `ShapeRecord` → `bbox_to_b_tier_cells` → `set_b_tier_cell`, owner via `_device_for_shape` | **B-tier branch of the single tier-dispatch pass** (writes `model`-side store) |
| 3. diffusion sharing | `:365-384` walk OD shapes, sibling-bbox overlap → `add_sharer` | **post-pass** (depends on phase 2 fully stamped — must stay a separate sweep, not fused into phase 2) |

After the split the cross-object read/write disappears: phase 1 is grid-only, phases 2–3 are model-only.

**Files to land.**
- **Writeback loop (land first):** factor the decoder's `_apply_{od,li,poly,nwell,boundary}_modifies` match-and-update logic out of `core/decoder.py` into a shared helper that can target *either* the output layout dict (today's consumer) *or* `shape_pool` `ShapeRecord`s (new). Call it at macro commit (`core/solver.py:resize_device`, after `commit_with_full_delta`) so every committed edit — LI / M1 included, not just OD / FIN — lands in `shape_pool`. Without this, the views below reflect stale geometry.
- `io_adapters/parser.py` — replace the net-primary segment/via loop (`:468-516`) with a **single tier-dispatch pass over `shape_pool`**: for each `ShapeRecord`, switch on `tier_of(sr.layer)` → A-tier LI/M1 become `TrackSegment` grouped into `nets[sr.net_id]`; B-tier OD/VIA0/cuts become `CellOccupancy`; FIN/POLY stay pool-only; C1/C2 untouched. Deterministic order via a stable `sorted(shape_pool, key=(layer, bbox))`. Fold `project_b_tier_shapes` phase 2 into this pass's B-tier branch; keep phase 1 (axis registration) in grid setup and phase 3 (diffusion sharing) as an explicit post-pass.
- `core/grid.py` — remove `b_tier_cells` field + its accessors (`set_b_tier_cell` / `get_b_tier_cell` / `b_tier_cells_of`); keep `b_tier_axes` + `register_b_tier_axes` + `bbox_to_b_tier_cells` (pure coordinate math). `MultiLayerGrid` becomes state-free w.r.t. layout content.
- `core/data_model.py` — (a) `LayoutModel` gains the B-tier occupancy store (the home `b_tier_cells` moves to in Stage A; or the derivation entry point in Stage B); update `summary()` to report B-tier cell counts from the new home; confirm `Net.__repr__` / `Device.__repr__` still resolve once `segments` / `vias` / `fin_track_indices` are properties (they call `len(...)` — fine, just now computed). (b) demote `Device.{gate_track_idx, fin_track_indices}` and `Net.{segments, vias}` to derived properties / views; keep semantic fields stored. (c) decide `ViaInstance`: delete in favour of direct VIA0-occupancy queries, **or** keep as a thin read-only view type for solver API compatibility (recommended first step — smaller blast radius).
- `core/solver.py` — `load_existing_layout` drops the via-as-LI/M1-WIRE block (segment stamping covers it) and reads the B-tier store from `model` not `grid`; `load_b_tier_cells_into_engine` re-points to the `model`-side store; `_reshape_li_sd_bars` queries VIA0 occupancy instead of `net.vias`; `apply_resize_to_model` stops mutating `Net.segments` directly (mutates `shape_pool`; the view reflects it).
- `core/atomic_ops.py` — `extend_od` / `mark_shared_diffusion` / `add_cut_cell` / `remove_cut_cell` re-point B-tier writes from `grid.b_tier_cells` to the `model`-side store (Stage A); under Stage B they mutate `shape_pool` and let the view re-derive.
- `core/macros/pick_macro.py` / `resize_device` — unaffected (operate on `Device` semantic identity).
- Tests — `tests/unit/test_parser_tier_dispatch.py` extends to assert one-pass dispatch + the three-phase B-tier ordering; `tests/unit/test_b_tier_grid.py` / `test_b_tier_atomics.py` re-point at the `model`-side store; `test_solver.py` via-coverage assertions re-pointed at VIA0 occupancy; a new test asserts no object-count regression (one via → one ShapeRecord + one CellOccupancy, zero ViaInstance if deleted) and that `grid` holds no occupancy after construction.

**Acceptance.**
- After any committed edit, `shape_pool` reflects the new geometry for *every* layer (LI / M1 included, not just OD / FIN), so re-reading the pool — or any view over it — returns current state. Verified by a resize-then-re-read test that today would observe a stale LI record.
- One physical via yields exactly one geometric record (`ShapeRecord`) + one working record (`CellOccupancy(VIA0)`); `ViaInstance` is either gone or a zero-storage view.
- `Device` / `Net` carry no stored geometry beyond `Device.bbox_nm`; `Net.segments` / `vias` and `Device.fin_track_indices` / `gate_track_idx` return live views over `shape_pool` / B-tier occupancy.
- `MultiLayerGrid` holds zero layout state after construction (only axes + transforms); a test constructs a grid and asserts no occupancy is reachable from it.
- Segment/via construction reads `shape_pool` (grouped by `net_id`), not `net_data` — which unblocks 1.7's retirement of `calibre_net_query.json`.
- Byte-golden pipeline output unchanged (the determinism sort preserves emission order).

**Risks.**
- The `shape_pool` writeback must use the exact nm representation the parser/decoder produce (the macro's `EditOp` bboxes are already final nm) so the pool mirror and the byte-golden output agree — reuse the decoder's match-and-update logic rather than re-deriving bboxes, or the two surfaces drift.
- Byte-golden emission order: iterating `shape_pool` vs `net_data` changes traversal order; the stable sort is load-bearing — pin it and snapshot-test it.
- Solver currently mutates `Net.segments` during resize; converting to a view means the mutation must move to `shape_pool`. Audit every `net.segments[...] =` / `.append` site (`core/solver.py:apply_resize_to_model:742-754`) before flipping.
- Relocating `b_tier_cells` touches every B-tier read/write site (`core/solver.py`, `core/atomic_ops.py`, `tests/unit/test_b_tier_*`). Do Stage A (relocate, mechanical) as its own commit before Stage B (derive, semantic) to keep the diff reviewable.
- View recompute cost: lazy views recompute per access. Trivial at one-cell scale; memoize-with-invalidation later (mirrors the "Derivator subscription model" deferral). Don't pre-optimize.

**Sequencing.** Land **before** M7 sub-slice 1.7 (1.7's `calibre_net_query.json` retirement depends on segment construction reading `shape_pool`). Composes cleanly with M8 (both make `Device` geometry derived) — do M9's `Device`/`Net` slimming and M8's `fin_track_indices` property in the same pass if scheduled together. Internally: **(0) close the `engine → shape_pool` writeback loop** (precondition for any view-ification — without it the views reflect stale LI/M1 geometry) → Stage A (relocate `b_tier_cells` to `model`, mechanical) → tier-dispatch unification + `project_b_tier_shapes` decomposition → `Device`/`Net` slimming → Stage B (derive B-tier view) as an optional follow-up. **M11** (below) extends this normalization across the CSP boundary — keep the writeback-loop implementation minimal: M11-U1 retires it by construction.

**Dependencies.** M3 (shape_pool + LVS overlay), M4e (b_tier_cells engine-load), M6 (decoder is L1-only, so removing working-repr duplication doesn't disturb writeback).

---

## M10 — GDS↔LVS layer-map consumption (per-cell annotation overlay)

**Goal.** Consume the Stage 1.5 middle files (`device_info.yaml`, `net_shapes.yaml`, joined with `ixref.yaml` / `net_xref.yaml`) to stamp per-cell `device_id` / `net_id` / `color` onto the grid via a GDS↔LVS-derived-layer mapping. This is the concrete design behind the "iXref + … consumption" cross-cutting deferral below; it turns the write-only middle files into the authoritative annotation source.

**Prototype reference.** A working, byte-golden-tested implementation of this design exists on the unmerged branch `claude/refine-test-fixtures-nIkdZ` (PR #30, slices "1.6a/1.6b"): `io_adapters/calibre_layer_map.py` (`load_layer_map_with_derived` + `apply_calibre_layer_overlay`), the `tech/layer_map.yaml::derived_layers` schema, `tech/calibre_layer_map.yaml` registry, and `tests/unit/test_calibre_layer_map.py`. **Re-land it on top of M9's normalized parser** (don't merge PR #30 as-is — its 1.6b net-source adapter feeds the old net-primary loop that M9 deletes). The schema + overlay logic + tests below are directly reusable; only the call site moves.

**Sequencing.** Land **after** M9 (so the overlay walks M9's `shape_pool`-derived `TrackSegment`/`CellOccupancy` views, not the pre-M9 net-primary segments) and **after** M9's `device_id`-via-containment stamping is in place (M10 refines it with derived-layer evidence; design them together to avoid two stamping mechanisms). Composes with 1.7 (both consume `net_shapes.yaml`).

### Mapping schema

Canonical forward index: per-GDS-layer `derived_layers` list in `tech/layer_map.yaml`. Each entry `{name, carries, [color]}` names an LVS-side derived layer that carries annotations *back* to this GDS layer:

```yaml
- name: POLY
  derived_layers:
    # Vt-flavour gate alternates — deck emits exactly ONE per device;
    # runtime stamps whichever has shapes.
    - { name: ngate_lvt,  carries: [device_id] }
    - { name: pgate_lvt,  carries: [device_id] }
    # …slvt / rvt variants…
    - { name: POLY,       carries: [net_id] }   # whole gate strip's net
- name: M1
  derived_layers:
    - { name: M1a, carries: [net_id], color: a }  # SADP cut colours
    - { name: M1b, carries: [net_id], color: b }
    - { name: M1,  carries: [net_id] }            # MVP single-colour passthrough
- name: OD
  derived_layers:
    # OD itself is NOT a device-id source; the nsd/psd S/D layers are.
    - { name: nsd, carries: [device_id, net_id] }
    - { name: psd, carries: [device_id, net_id] }
```

Reference registry: `tech/calibre_layer_map.yaml` holds derivation docs (`derivation_doc`), SADP `multi_patterning` colour metadata (load-bearing for metal-cut editing), and semantic hints. The loader cross-checks every `derived_layers[*].name` resolves in the registry.

### Annotation home (the load-bearing decision)

Per-cell on the grid carriers is **authoritative**; `ShapeRecord.{net_id, device_id}` are **best-effort summaries** derived from per-cell consensus. Rationale: a single GDS shape can be cut into multiple net regions (M1) or shared between devices (OD), so whole-shape annotation is wrong for those; the grid handles cuts (per-cell net) and diffusion sharing (`CellOccupancy.shared_with`) naturally. The summary stays `None` when cells disagree — the resize macro's `sr.device_id == device.inst_name` filter then skips the ambiguous shape, which is correct (it only targets whole-device shapes). Keep the `ShapeRecord` fields because the solver + atomic_ops read them (`core/solver.py:resize_device` / `_reshape_li_sd_bars`; `core/atomic_ops.py`).

### Overlay pass

Two sub-passes:
1. **Per-cell stamping (authoritative).** For each `TrackSegment` (A-tier) and `CellOccupancy` (B-tier), look up the GDS layer's `derived_layers`, find matching shapes in `device_info.yaml` / `net_shapes.yaml`, stamp the `carries` fields + `color`.
2. **ShapeRecord summary (best-effort).** Per shape, set `net_id` / `device_id` from cell consensus; leave `None` on disagreement.

**Containment rule.** A-tier: cell-center inside derived-shape bbox. B-tier: ≥50% area overlap. Both tolerate the sub-nm "effective region" trim from slice 1.5 (real Calibre shapes can be slightly smaller than GDS).

**Conflict policy.** B-tier `device_id` collisions → recorded as diffusion sharing (`owner_device_id` + `shared_with`), not a conflict. A-tier `device_id` collisions / any-tier `net_id` collisions → raise `LayerOverlayConflictError` (real short circuit / overlapping active). Co-occurrence of `device_id` (from `ngate_lvt`) + `net_id` (from POLY passthrough) on the same active-gate cell is **allowed** — it's the gate's normal state.

**LVS→schematic device-name translation (load-bearing).** `device_info.yaml`'s `layout_inst` is the LVS name (`M0`/`M1`); the rest of the model uses the schematic `Device.inst_name` (`MN0`/`MP0`). Translate via `ixref.yaml`'s `layout_inst → source_inst` map **before** stamping `device_id`, or the solver's `sr.device_id == device.inst_name` filter silently skips every shape in production. (This was a P1 review catch on the prototype.)

### Dummy/real coverage-gap handling

Real Calibre annotation is precise but **incomplete** (filler / ESD / cut-shadow cells get no LVS shape), unlike the 100%-covered dummy. Cells with no annotation are correct: `project_unannotated_blockages` projects GDS-covered-but-unannotated cells as CSP `BLOCKAGE`. Add a per-layer coverage report distinguishing `gds_cells / lvs_annotated / blockage_projected` so engineers can audit a real run. A buffer-fixture parity check (per-cell `(net_id, device_id)` diff between the legacy overlay and the new pass) gates the re-land — the prototype proved zero divergence.

### Sub-slice M10.1 — layer-name mapping + cut/extension trimming

The prototype uses GDS layer names directly and the raw GDS bbox. Production needs: a layer-name mapping table (GDS ↔ LVS-derived names, e.g. `LI` → `LIG`/`LISD`, `VIA0` → `V0`) and a trimming pass that subtracts cut shapes / extension margins so the derived bbox is the *effective conducting/active* region. Deferred from slice 1.5; design alongside M8 (cut-layer geometry) and the SADP colour metadata already in `tech/calibre_layer_map.yaml`.

**Files (re-land target, post-M9).** `io_adapters/calibre_layer_map.py` (new); `tech/layer_map.yaml` (`derived_layers` blocks); `tech/calibre_layer_map.yaml` (registry, drop bogus whole-metal passthroughs — production has only SADP cut colours); `core/data_model.py` (`TrackSegment.{device_id,color}`, `CellOccupancy.color`); `io_adapters/parser.py` (call the overlay inside/after M9's single-pass dispatch); `core/solver.py::project_unannotated_blockages` + `core/data_model.py::LayoutModel.annotation_coverage` (grid-level predicates); `tests/unit/test_calibre_layer_map.py`.

**Acceptance.** Re-landed overlay stamps per-cell device_id/net_id/color from the middle files (LVS→schematic translated); diffusion sharing + cut + conflict cases covered by unit tests; buffer-fixture per-cell parity vs the prototype; byte-golden pipeline output preserved (or documented if the coverage report changes shape).

**Dependencies.** M9 (normalized parser), Stage 1.5 middle files (`ixref` / `net_xref` / `device_info` / `net_shapes`, all merged), M5 (derivator pattern for derived-layer semantics).

---

## M11 — unified cell-state substrate (M9 across the CSP boundary; connectivity-based DRC identity)

> Filed 2026-06 from the domain-initialization review of `initialize_domains` / `_initial_domain_for_layer` / `forbidden_states`. Absorbs that review's findings (below) — no separate per-finding entries.

**Goal.** One occupancy store, four layered concerns. M9 collapses the *model-side* representations of "what occupies cell `(layer, a, b)`" but stops at the engine boundary: `engine.cells` stays a third materialization of the same fact, populated by copy at load time and reconciled by M9's writeback loop. M11 finishes the inversion: the CSP engine stops owning an occupancy copy and becomes a domain/trail overlay plus DRC checker *over* the unified store — and net/device identity leaves per-cell state entirely: DRC "same-net" becomes "same connected component", computed from geometry.

**Motivation — grid and CSP already share one substrate.**

| Representation | Home | Payload | Serves |
|---|---|---|---|
| `TrackSegment` | `Net.segments` (model) | layer, track, span, `net_id` | A-tier occupancy |
| `CellOccupancy` | `grid.b_tier_cells` | layer, a, b, `occ_type`, `net_id`, `owner_device_id`, `shared_with` | B-tier occupancy |
| `GridCell` + `CellState` | `engine.cells` | `occ_type`, `net_id` (+ domain, fixed) | CSP / DRC |

Findings against current code:

1. **`CellState.net_id` is a load-time copy.** Only `load_existing_layout` / `load_b_tier_cells_into_engine` write it (`core/solver.py:273,310,345`). The engine's net knowledge is a cache of Stage 2's — a copy that can only drift.
2. **Two "same-net" judgements coexist.** Spacing rules compare the scalar label (`core/drc_constraints.py:87-93,132-138`); the M4b union-find is documented as the net-equivalence truth and the diffusion-sharing "safety valve" — but `forbidden_states` never consults `net_of`.
3. **The union-find query surface has zero production consumers.** `net_of` / `connected_to` / `connected_cells` (`core/csp_engine.py:823-875`) are exercised by unit tests only; the write side (`union`, `mark_cut`) is live. Infrastructure waiting for its consumer (M6c).
4. **Per-net domain fan-out manufactures dead states.** `_initial_domain_for_layer` (`core/csp_engine.py:287-313`) enumerates `occ_type × net` for every non-WIRE occupant, but `mark_cut` only ever writes a net-less `CellState(CUT)` (`:690-718`) — every `(CUT, net)` element is unreachable. Domain size is 1+N (A-tier) / 2+N (B-tier) in net count, and nothing exploits it: the engine never branches over domains (no search exists — macros propose, the engine checks; `width_code` / `is_line_end` are likewise never branched on).
5. **`occ_type` restates the layer.** Under one-occupant-kind-per-layer, the B-tier trigger sets (`(DEVICE_DIFF,)` for OD, `(VIA,)` for VIA0 — `core/drc_constraints.py:200-214`) re-encode what the layer name already says.
6. **`net_id=None` is asymmetrically optimistic.** A `None` trigger forbids all named nets nearby, but a named trigger never forbids `None` neighbours (`forbidden_states` enumerates `all_net_ids` only) — "unknown" behaves as compatible-with-everything, the unsafe direction for unannotated geometry.
7. **Cross-layer connectivity is faked by labels.** `union` requires same-layer Manhattan-1 adjacency (`core/csp_engine.py:734-741`), so via equivalence (LI-net == M1-net) is expressible only through the M2 via-as-WIRE double-stamp — exactly the redundancy M9 deletes. Once via-as-WIRE is gone, nothing connects layers.

**The model (one store, four layers).**

1. **Coordinate system** — stateless math: pitch / offset / orientation / axes; physical↔track; bbox→cells. (= M9's slimmed `MultiLayerGrid`.)
2. **Occupancy store** — the single `(layer, a, b) → {shape ref, occupant kind, identity ref}` map, A-tier and B-tier symmetric. (= M9's model-side store, now *also* the engine's working state.)
3. **Identity & connectivity** — two halves. *Semantic identity registry* (net names, device instances): model/LVS-side; serves edit localisation and CDL-diff semantics — the resize path already works purely on it (`core/solver.py:527,578`). *Topological connectivity index*: components over store geometry — same-layer adjacency ∪ **via edges** (fixing finding 7), CUT cells as barriers; label-free; serves DRC same-conductor tests. The index is the M4b union-find relocated and made authoritative — one instance, engine-side copy deleted.
4. **DRC/CSP checker** — domains + trail keyed by the same cell ids, overlaid on (2); spacing's same-conductor exemption queries (3). Cell state shrinks to `{EMPTY, OCCUPIED, BARRIER}` (+ width as a decision axis only where a layer has >1 legal width — none today). No `net_id`, no `device_id`, no occupant-kind taxonomy in CSP state.

**Why connectivity, not labels, is the DRC identity.** The same-net spacing exemption exists because *the same conductor* may abut or merge harmlessly — a topological fact, exactly what the index answers. (Same-conductor notch/width interactions stay purely geometric; they never needed identity.) What the label model additionally grants is the *same-net-but-disconnected* relaxation; connectivity-only treats those conservatively (spacing enforced) — the safe direction for an edit/resize tool, and it fixes finding 6 for free: two disconnected unannotated shapes are distinct components, so spacing applies, instead of `None == None` → exempt. If the relaxation is ever needed it returns as a *component → net-property* lookup — labels as properties of components, never of cells. Device identity never enters DRC at all: cross-device rules are geometric; localisation stays model-side.

**Staged plan.**

* **U0 = M9**, unchanged (writeback loop, Stage A/B, tier-dispatch, `Device`/`Net` slimming). Keep the writeback implementation minimal — U1 retires it by construction.
* **U1 — engine on the store.** `engine.cells` stops holding occupancy; `GridCell` reduces to domain + trail hooks keyed by store cell ids; `load_existing_layout` / `load_b_tier_cells_into_engine` collapse into "attach domains over store cells"; macro commits mutate the store directly; delete the M9 writeback scaffolding.
* **U2 — connectivity identity.** Build the index (adjacency ∪ via edges, CUT barriers) over the store; rewrite spacing's same-net test from label comparison to component comparison; delete `CellState.net_id`; relocate `_uf_*` out of the engine as the index (no-compression + trail discipline unchanged). **Gate:** DRC accept/reject decisions on the buffer fixture byte-identical — the fixture has no same-net-disconnected pair within any stencil radius (verify by test, not assumption).
* **U3 — cell-state shrink.** Domain elements reduce to `{EMPTY, OCCUPIED, BARRIER}`; occupant kind lives on the store record (decoder/output still consume it); per-net fan-out deleted (kills the dead `(CUT, net)` states; domain size O(1) in net count). Spacing evaluates "occupied by a different component" at propose time, parameterised by the index — sound because nothing searches over domains (finding 4).
* **U4 (deferred).** Attribution axis: BLOCKAGE returns as *pinned/foreign* occupancy rather than a domain value; unannotated-but-recoverable geometry gets M3 §D suspect-tagging + connectivity-based identity recovery; optional same-net-disconnected relaxation as the component→net lookup.

**Backlog entries this revises.**
- **M9** — extended, not contradicted; its writeback loop is demoted to transitional scaffolding (deleted in U1).
- **"Engine union-find: path-aware split"** (cross-cutting) — requirement transfers to the unified index unchanged.
- **M6c** — `obstacles.py` targets the store + index if M11 lands first; otherwise one re-point in U1.
- **M10** — per-cell stamping writes identity *references* into the store; the annotation-home decision carries over unchanged.
- **M12** — Stage 5 macros target the same store; candidate planning and transaction semantics become the edit-side consumer of the unified substrate.

**Acceptance.**
- One physical occupant ⇒ exactly one store record, observed identically through model views and the engine; an L2 edit is visible to both with no writeback step.
- `CellState` carries no `net_id`; `_uf_*` gone from the engine; the U2 spacing path is the index's first production consumer.
- Per-cell domain size ≤ 3 and independent of net count; buffer-fixture propagation decisions unchanged (U2/U3 gates); byte-golden pipeline output preserved.

**Risks.**
- Propagation shifts from value-pruning over net-enumerated domains to index-parameterised checks at propose time — mechanically invasive in `_propagate`; mitigated by finding 4 (no consumer branches over domains).
- The conservative flip on same-net-disconnected spacing could reject edits the label model accepts — none in the fixture; pin with a regression test; U4's relaxation is the escape hatch.
- Connectivity lookups land on the propagation hot path (label compare was O(1)); the no-compression find degrades on deep trees — watch `propagate_stats`, revisit compression + undo discipline if it surfaces (existing perf note).
- Transactionality: store mutations + index unions + domain changes must share one checkpoint/restore bracket; the trail already brackets cells + unions, but the store write path is new surface.

**Sequencing.** After M9. Before or interleaved with M10 (coordinate the stamping target). M6c may land first against the engine surface at the cost of one re-point. U1 → U2 → U3 are separately commitable; U2 is the semantic pivot and carries the gate.

**Dependencies.** M9 (store + views), M4b (union-find + trail), M4e (per-layer engine bounds), M6a/b (macro transaction discipline).

---

## M13 — Stage 6 artifact/export boundary (post-commit files, scripts, reports, validation)

**Goal.** Stage 6 begins only after Stage 5 has committed the layout model / occupancy store and any post-commit derived layers. It must not repair or mutate internal layout state. Its job is to serialize the committed state into production-facing artifacts — GDS, JSON, CDL, SKILL/edit scripts, reports, visualizations, and validation results — and to provide the engineer/tool interaction surface around those artifacts.

**Why this matters.** Today Stage 6 is still a late writeback stage, not just an export stage:

1. **Stage 6 constructs the output layout by replaying edits over `orig_data`.** `pipeline/run_mvp.py` reopens the original JSON, collects `edit_ops_n` / `edit_ops_p`, runs C1 derivation, then calls `WritebackDecoder.apply(...)` to build `resized_data`. That makes Stage 6 the place where some geometry becomes real, which conflicts with M12's contract that successful Stage 5 macros commit to the canonical model before the next macro runs.
2. **C1 derivation mutates model geometry during export.** `DRCDerivator._emit_y2_shift_ops` stamps `ShapeRecord.is_derived` / `provenance` and updates `sr.bbox_nm`. Derived-layer refresh is a post-commit model update (or future commit-delta subscription), not a file-export side effect.
3. **`WritebackDecoder` conflates commit writeback, derived-shape guarding, output-dict mutation, and metadata updates.** Its layer helpers are the match/update logic M9/M12 need, but Stage 6 should not be the canonical state updater. Split shared writeback from artifact serialization.
4. **Metadata export is hardcoded around the MVP inverter.** Stage 6 re-derives `new_nmos_nfin` / `new_pmos_nfin` from `nfin_targets` and updates output params/devices there. Production export should read committed `Device` / `Net` semantic state, not Stage 1 diff globals or `MN0` / `MP0` naming assumptions.
5. **SKILL is the production-facing artifact but remains a placeholder.** `writer_skill_script.py` emits bbox-based helper calls whose helpers only print. A real Stage 6 must generate actionable scripts with layer-purpose mapping, units, shape-location dry-run, ambiguity checks, and provenance comments.
6. **Validation is stdout-oriented and target-golden-centric.** GDS readback and target comparison currently print pass/fail summaries. Production runs usually have no unique golden layout; validation must be expressed as structured artifact contracts.

**Stage 6 contract.**

- **Inputs:** committed model / unified-store snapshot; committed change log with provenance; optional regression golden target; site/tool configuration; validation policy.
- **No internal mutation:** Stage 6 exporters and validators must not mutate `LayoutModel`, `MultiLayerGrid`, CSP engine, or the unified store. Running Stage 6 twice over the same snapshot must be idempotent.
- **Outputs:** layout artifacts (`.gds`, `.json`, `.cdl`), edit/interaction artifacts (`.il` / SKILL or future Skillbridge script), human reports, machine-readable report JSON, visualizations, and validation result JSON.
- **Boundary with M12:** L1 `EditOp`s are post-commit event/provenance records. Stage 6 may consume them to produce SKILL/report/diff visualizations, but they are not the only source of committed geometry.

**Validation model: contract-based, not always golden-target-based.**

A hand-built target GDS/JSON is useful for the MVP fixture and regression tests, but it is not a production oracle. Real ECO runs often have many legal layouts and no pre-existing "correct output". Stage 6 validation therefore has four tiers:

1. **Golden regression (fixture-only when available).** If a target GDS/JSON exists, exact comparison may be fatal in CI to preserve byte-golden behaviour. Outside regression mode, target comparison is optional/warning because a different DRC/LVS-clean edit may be valid.
2. **Self-consistency (always required).** Exported GDS must round-trip to the committed/exported geometry; JSON/CDL/SKILL/report counts must agree with the committed model and change log; layer-map and unit conversions must be explicit and checked.
3. **Signoff/tool validation (production fatal).** DRC must be clean; LVS must match the target CDL; SKILL dry-run must locate exactly the intended shapes before editing; any Calibre/Virtuoso command drift must surface as a failed validation result, not a silent stdout note.
4. **Audit/human validation (diagnostic but required artifact).** Reports and visualizations should explain what changed, why, which macro/candidate produced it, which edits are derived, which checks ran, and which checks were skipped or degraded to warnings.

**Files to land.**

- `pipeline/run_mvp.py` — replace the monolithic Stage 6 block with an exporter/validator orchestration layer. Consume the committed model snapshot and change log instead of replaying edits over `orig_data` as the canonical output path.
- `core/drc_derivator.py` — move C1 refresh to Stage 5 post-commit / Stage 5.5 derived-state refresh. Stage 6 should serialize already-derived C1 state.
- `core/decoder.py` — split shared writeback helpers from artifact serializers. Keep `WritebackDecoder.apply` only as a legacy adapter during transition; it should not be the long-term state-commit mechanism.
- `io_adapters/gds_io.py` / JSON exporter — export directly from committed model or a pure immutable layout snapshot. Preserve GDS readback, but return structured `ValidationResult` records.
- `io_adapters/writer_cdl.py` — graduate from MVP inverter hardcoding to committed semantic-model export (device list, pins, params, subckt metadata). Keep the old writer as a fixture adapter if needed.
- `io_adapters/skill_emitter.py` (new, replacing/retiring `writer_skill_script.py`) — emit production-oriented SKILL with layer-purpose mapping, units, bbox tolerance / shape id matching where available, dry-run assertions, and provenance comments for every operation.
- Reporting / visualization modules — generate human text + machine-readable JSON reports from committed state, change log, and validation results; feed visualization from committed deltas and mismatch data rather than raw pre-commit edit streams.
- Tests — Stage 6 idempotency/no-mutation tests; exporter round-trip tests; validation severity policy tests; no-golden production-mode validation tests; golden fixture comparison tests; SKILL dry-run ambiguity tests; report-count consistency tests.

**Acceptance.**

- Stage 6 can run twice on the same committed snapshot and produce identical artifacts without changing any internal model/store object.
- Removing the hand-built target GDS does not make validation meaningless: self-consistency + DRC/LVS + SKILL dry-run + change-envelope checks still produce pass/fail results.
- With a fixture golden target present, exact GDS/JSON comparison remains available as a regression gate.
- Reports include every committed change, including derived C1 changes and validation outcomes; they do not count only macro-emitted Stage 5 edit ops.
- SKILL output is either a real executable/dry-runnable artifact or clearly omitted with a validation warning; placeholder printf-only helpers are not treated as production success.
- Validation results are machine-readable and can make the pipeline fail according to policy; stdout-only mismatch messages are insufficient.

**Sequencing.** Land after or alongside M12's Stage 5 commit cleanup. The minimal bridge is: Stage 5 still emits an edit/change log, but Stage 6 treats it as provenance/export input while serializers read the committed model snapshot. Full cleanup becomes easier after M9/M11 because the exporter can walk one occupancy/geometric store instead of replaying EditOps over legacy JSON.

**Dependencies.** M12 commit semantics; M9 shared writeback / shape_pool normalization; M11 unified store when available; M7 real SKILL + Calibre DRC/LVS integration for production signoff. Independent of the long-term choice of search/RL/LLM policy in Stage 5.

---

## Cross-cutting deferrals

### Derivator subscription model

Today the C1 derivator (`core/drc_derivator.py`) is **pull-based** — the pipeline calls `derive_c1(...)` after the L3 macro commits, and the derivator does a full recompute. The architectural model (§ A4) calls for **push-based subscription**: `engine.commit_with_full_delta`'s cell delta hands the affected-neighborhood radius directly to the derivator for incremental recompute.

The infrastructure is in place (`CommitDelta` lands in M4b; M6a flipped `device_resize` to `commit_with_full_delta`); only the wiring is deferred. Earns its keep when derivator runtime starts to dominate (multi-cell layouts).

### Engine union-find: path-aware split

The current `_uf_undo_one` undoes the *most recent* union — it does not selectively split a component. As a result, M6b's `split_diffusion` does not actively un-merge the engine union-find; it relies on the §B "no CUT between adjacent cells" rule (preventing future unions across the cut) plus the natural checkpoint/restore lifecycle.

A path-aware union-find (or a fully recomputed component on each split) is needed before multi-step diffusion split-then-share-elsewhere becomes a real workload. M6d / M7 will surface the requirement in earnest. Under **M11** the union-find relocates to the unified connectivity index over the occupancy store (engine-side copy deleted); the path-aware-split requirement transfers to that index unchanged.

### Geometric-overlap suspect tagging (M3 §D rule 3)

`ShapeRecord.suspect_tags` exists as the M3 seam but stays empty. The "geometric-overlap cross-check at parse time tagging suspicious shapes `SUSPECT_CONNECTED_TO_*`" rule is not implemented. The MVP fixture's unannotated shapes are FIN / OD / POLY (non-CSP) and NWELL / BOUNDARY (cell-level wrappers), so the tag would not fire on it. The check earns its keep on a real production layout where filler / ESD shapes overlap LVS-tagged routing.

### LVS bbox tolerance

The M3 `(layer, bbox_nm)` overlay key works because the dummy generator's GDS shapes and the dummy LVS shapes share an exact bbox-tuple representation. Production LVS geometry can drift sub-nm. M7 will need a tolerance / containment match in `apply_lvs_overlay`.

### iXref + net_xref + device_info + net_shapes consumption

> **Concrete design:** see **M10 — GDS↔LVS layer-map consumption** above for the per-cell annotation overlay that realises this (mapping schema, annotation-home decision, conflict policy, LVS→schematic translation, coverage-gap handling). A working prototype lives on PR #30's branch. This section keeps the higher-level "what each middle file unlocks" checklist.

The four middle files produced by Stage 1.5 — `output/ixref.yaml` (devices), `output/net_xref.yaml` (nets + lvs_index), `output/device_info.yaml` (per-device LVS-derived-shape bboxes), and `output/net_shapes.yaml` (per-net LVS-derived metal/via bboxes) — are currently write-only. Future consumers — once we land them — should:
- Cross-check the iXref's source-side instance ids against the parsed CDL `Device.inst_name` set; flag mismatches.
- Use the `sd_swapped` flag when projecting LVS shapes through `apply_lvs_overlay` to flip source/drain pin roles for any device the layout-side LVS run flipped.
- Use `net_xref.yaml`'s `schematic_name → lvs_index` map to localise DRC/LVS errors back to the schematic net the engineer recognises (Calibre reports errors against `lvs_index`).
- Use `device_info.yaml`'s per-device derived-shape bboxes to map per-device DRC violations back to the responsible L2 op — the M5 derivator already produces NWELL / BOUNDARY shapes from device metadata, so a DRC error on `pgate_lvt` localises immediately to the device whose seed shape contains the violation point.
- Use `net_shapes.yaml`'s per-net routing-layer bboxes for DRC error → net-name traceback: a spacing violation on M1 between two shapes lands directly on the two `lvs_name`s that own the shapes; the join with `net_xref.yaml` then yields the `schematic_name`s the engineer recognises.
- Feed all mismatches into the L3 macro provenance for blast-radius computation in the LVS feedback closure (M7 main).

### Calibre HDB command-string drift

`run_calibre_ixref` hard-codes `INSTANCE XREF WRITE <path>` + `EXIT` as the stdin script. Some Calibre versions accept lower-case `iXref`, `Quit` instead of `EXIT`, or require additional preamble lines. Today the commands are not exposed as configuration; if a production user hits a version mismatch, they can monkey-patch the function or extend it to accept a `commands:` list. Make this a config field once a second deployment surfaces a real conflict.

### Multi-cell C1 derivation

M5 ships single-cell semantics for NWELL / BOUNDARY (`y2 = topmost-fin + margin`). Multi-cell layouts where wells span outside a single cell will need a richer rule. Add when fixtures grow.

### Universal `LayerGrid` offset derivation

`core/grid.py::create_mvp_grid` and `io_adapters/parser.py:422-450` currently set each layer's offset by ad-hoc rules: FIN takes `nmos_fin_y[0]` literally (so track 0 == first NMOS fin); M1 takes `first_track_y % pitch` (residue class); POLY and LI are hardcoded to `0` because dummy track 0 happens to land at coord 0. The four cases collapse to one universal formula:

```python
offset = min(centers) % pitch        # centers = shape centers on this axis
assert all((c - offset) % pitch == 0 for c in centers), \
    f"{layer}: off-grid centers (offset={offset}, pitch={pitch})"
```

* **Why this form (not "offset = first center"):** the residue class is the global truth — two cells that share the same fin row must agree on the residue mod pitch, but they will *not* agree on "where the first occupied fin sits" once the cells are placed at different Y offsets in a global layout. The mod form is the one that survives multi-cell stitching; the residue is the invariant DRC / equivalence checks across cells will key off.
* **What "centers" means per layer:** for H-tracks (FIN, M1) use shape `(y1+y2)//2`; for V-tracks (POLY, LI) use `(x1+x2)//2`. Both pull from `model.shape_pool` (already populated by the time `create_mvp_grid` runs).
* **Validation, not silent inference.** The `assert` line is load-bearing — off-grid centers silently absorbed by `round()` in `physical_to_track` are how an upstream parser/LVS bug becomes a downstream byte-golden mystery. Surface loud at grid construction; the M3 conservative-defaults rule (§D) covers this case too.
* **Empty-sample policy.** No centers on a layer → raise, do not fall back to a magic number. Today's `nmos_fin_y[0] if nmos_fin_y else 40` and `m1_offset = M1_PITCH // 2` defaults are dummy artefacts; production should require at least one sample (the cell-row template guarantees it).
* **Files to land.**
  * `core/grid.py::create_mvp_grid` — refactor signature from `(config, nmos_fin_y, pmos_fin_y, m1_tracks_y)` to `(config, shape_pool)`. Internally compute offsets per A-tier layer via the formula.
  * `io_adapters/parser.py:422-450` — collapse the four `nmos_fin_y / pmos_fin_y / m1_tracks_y / _raw_fin_y` plumbing into `grid = create_mvp_grid(config, shape_pool)`. Removes the dict-with-only-`min`-used `m1_tracks_y` artefact.
  * `tests/unit/test_grid.py` — add cases: off-grid drift (must raise), single-sample (must succeed), negative coords (Python mod handles), multi-cell-equivalent (two simulated cell-local center sets must produce equal offsets).
* **Sequencing.** Implementable *today* — `shape_pool` is already populated before the offset-extraction step runs (`parser.py:418-419`). Lands cleanly **before** M7-1.7 (1.7 then doesn't need to keep the per-device `_raw_fin_y` plumbing alive) and **before** M8 (M8's "NMOS/PMOS fin bucket" deletion is a no-op once offsets stop caring about device type). Doing this first removes the FIN-as-edited-layer assumption from one more call site.
* **Out of scope.** Per-layer offset *overrides* in `site_config.yaml` for cells whose first shape isn't representative (e.g., dummy-padded rows). Add a `tech.grid_offset_overrides: {layer: nm}` knob if a fixture ever needs it; today none does.

### Config-driven orthogonal pairing & orientation

`core/grid.py::create_mvp_grid` (`:438-469`) hardcodes two things that are properly *foundry* data: each layer's `orientation` (`'H'`/`'V'`) and its **orthogonal partner** — the `ortho_layer=` kwarg that populates `MultiLayerGrid.ortho_pairs` (`grid.py:125`, set by `add_layer` at `:139-143`). Every A-tier layer's along-track anchor keys off this partner (`get_ortho_layer` → `physical_to_segment_coords` / `segment_to_physical`), so it is load-bearing, yet it lives as four literal kwargs:

```
FIN  → ortho POLY    POLY → ortho FIN
LI   → ortho M1      M1   → ortho LI
```

The B-tier analogue is `io_adapters/parser.py::_B_TIER_AXIS_DEFAULTS` (`:278-284`) — a module constant mapping each B-tier layer to its `(axis_a, axis_b)` A-tier pair (`OD → (POLY, FIN)`, `VIA0 → (LI, M1)`, cuts → …), consumed by `project_b_tier_shapes` → `register_b_tier_axes` (`:331-342`). Same smell, second copy.

**The config already half-exists; the loader just drops it.** `tech/layer_map.yaml` *already* carries `orientation: H|V|null` on every layer (`:34/41/48/55/…`) and VIA0's axis pair is *already* there as `connects: [LI, M1]` (`:65`; schema doc `:19`). But `tech/layer_map.py` parses only `gds` / `tier` / `role` / `color` into module constants — `orientation` and `connects` are read by nobody, so `create_mvp_grid` and `_B_TIER_AXIS_DEFAULTS` re-hardcode them. The only genuinely-missing config is (a) the A-tier ortho partner and (b) the non-via B-tier axis pair (OD, cuts), neither of which has a YAML field yet.

**Target.** `layer_map.yaml` becomes the single source for grid topology; `create_mvp_grid` and the parser read it.
* Add `ortho: <layer>` to the four A-tier layers (`LI: ortho: M1`, …); reuse `orientation` as-is.
* Add `axes: [<a>, <b>]` to B-tier non-via layers (`OD: axes: [POLY, FIN]`; cuts when they grow geometry). For vias, reuse the existing `connects` (`[lower, upper]` *is* the axis pair) — don't duplicate it as `axes`.
* `tech/layer_map.py` exposes `LAYER_ORIENTATION`, `ORTHO_PAIRS`, and `B_TIER_AXES` (the last folding `connects` for vias + `axes` for the rest), plus `orientation_of` / `ortho_of` / `axes_of` accessors mirroring `tier_of`.

**Validation (surface loud, per the M3 conservative-defaults discipline).**
* Ortho symmetry: `ortho_of(ortho_of(L)) == L` for every A-tier layer — a one-sided `LI→M1` with `M1→LI` missing is a typo, not a config.
* Perpendicularity: a layer and its ortho partner must carry opposite `orientation` (one `H`, one `V`); assert at load.
* B-tier axes must resolve to registered A-tier layers — `register_b_tier_axes` already raises on an unregistered axis (`grid.py:301-306`); keep that as the second gate.

**Files to land.**
* `tech/layer_map.yaml` — `ortho:` on the 4 A-tier layers; `axes:` on OD (+ cuts later).
* `tech/layer_map.py` — parse + expose the three new constants/accessors with the validation asserts.
* `core/grid.py::create_mvp_grid` — drop the literal `orientation=` / `ortho_layer=` kwargs; loop over the A-tier layers reading `LAYER_ORIENTATION` / `ORTHO_PAIRS`. (Pitch/width still come from `config`; offset from the sibling "Universal `LayerGrid` offset derivation" item.)
* `io_adapters/parser.py` — delete `_B_TIER_AXIS_DEFAULTS`; `project_b_tier_shapes` phase-1 reads `B_TIER_AXES`.
* `tests/unit/test_grid.py` / `test_layer_map.py` — assert the loaded pairing byte-matches today's hardcoded values; a fixture with an asymmetric `ortho` (or an H↔H pairing) must raise.

**Sequencing.** Composes with **Universal `LayerGrid` offset derivation** above — same call site (`create_mvp_grid`), same test file; landing them together turns the factory into a pure assembler (pitch/width ← `drc_rules`, orientation/ortho/axes ← `layer_map`, offset ← `shape_pool`). Independent of M9, but tidy to land first: M9's `project_b_tier_shapes` phase-1 (axis registration, which M9 keeps on `grid`) then reads the config constant instead of the parser constant it is about to delete anyway. Implementable today.

**Out of scope.** Per-experiment ortho/axis *overrides* in `site_config.yaml` — `layer_map.yaml` is the foundry-level source of record; add a knob only if a fixture ever needs a non-standard pairing (none does). Non-Manhattan / multi-orientation layers stay out — the H⊥V assumption is load-bearing in the via-position and segment-projection math.

### Derived-marker layers without geometry yet

`tech/layer_map.yaml` declares `VT`, `PP`, `NP`, `DNW` as `tier: C1` + `derived: true`, but no fixture emits them. The derivator's `_derive_*` shape mirrors `_derive_nwell` — adding any of these is one new helper plus a config entry under `tech/drc_rules.yaml::extension`. Activates when a fixture needs them.

### C2 annotations (DIODE / ESD / TEXT)

`tier: C2` declared in the YAML; no fixture geometry; no L3 macro yet edits them. The path is "L3 emits L1 directly; never enters CSP" per § C. Wire when needed.

### Decoder-rejection prefix convention extension

M6a's decoder rejection check exempts ops whose `desc` starts with `derived_<layer>_y2_shift`. Future derivator extensions (VT / PP / NP / DNW) must keep the prefix, **or** extend the exempt check to cover their `desc` shape. Easy to forget; consider hardening the check by using the `is_derived` flag on the source `ShapeRecord` directly rather than parsing `desc`.

### M4c legacy fallback

`core/solver.py::_reshape_li_sd_bars` retains a `if seg.shape_record is None: ... device.dev_type in seg.desc` fallback for callers that build `TrackSegment`s without going through `build_layout_model`. M4d should have removed it; in practice, M5 / M6 didn't need to and didn't. Worth removing once a milestone audits direct-construction call sites (the legacy desc-substring filter is the kind of seam that quietly papers over upstream bugs).

---

## Tooling / production integration

### `site_config.yaml` extensions (deferred from PR #19)

The configurable surface currently stops at `tech` + `inputs` + `output`. Two more blocks were intentionally deferred:

```yaml
# Not yet wired into config_loader / pipeline:
calibre:
  svdb_dir:   /path/to/svdb
  drc_rules:  /pdk/drm/calibre.drc
  lvs_rules:  /pdk/drm/calibre.lvs
  cell_name:  INV_X1

virtuoso:
  lib_name:   YOUR_LIB
  cell_name:  INV_CELL
  view_name:  layout
```

**Wiring.** `tech/config_loader.py::load_site_config` would resolve any path-valued fields; `pipeline/run_mvp.py` and `scripts/calibre_*.sh` / `scripts/virtuoso_apply_edit.il` would consume them. Lands with M7 (it's the same set of integration points).

### Production-CDL parser variants

`io_adapters/cdl_parser.py` handles the dummy fixture's plain CDL but production CDL may have:
- Line continuations (`+` prefix).
- Multi-line params.
- Per-foundry SPICE flavours.
- Hierarchical net names.

These need real-CDL test fixtures before being adapted. Not blocking M6c/M6d but will block M7.

### Calibre query format adapters

> Largely **superseded by M7 sub-slice 1.7** (above): the legacy `parse_calibre_*` JSON path is being retired in favour of the four 1.5 YAMLs, which handle the unit / pin / fin-derivation drifts at the loader boundary. The remarks below stay as the catalogue of *what* drifts production hits, so 1.7's helpers know what to cover.

`io_adapters/parser.py::parse_calibre_*` assumes the dummy generator's exact JSON shape. Known production drift:
- Coordinates may be microns, not nm. (1.7: `_um_to_nm` at loader boundary.)
- Pin names may be case-sensitive. (1.7: pin roles come from CDL terminal order, not LVS — case is fixed by the CDL parser.)
- Net names may include hierarchy separators. (1.7: `net_xref.lvs_index` is the stable key; names are display-only.)
- `fin_y_positions` may not be explicit. (1.7: derived geometric + arithmetic cross-check.)

If 1.7 slips and the legacy path stays in production temporarily, a `format:` block in `site_config.yaml` (`{units: nm|um, fin_y_field: fin_y_positions | derive}`) is the minimum-disruption escape hatch.

### SKILL helper implementations

`scripts/virtuoso_apply_edit.il` has stub `_removeShapeByBBox` / `_resizeShapeByBBox` placeholders. Real implementations need to bind to PDK-specific shape-find / shape-modify APIs. M7 deliverable.

---

## Test-coverage gaps

- **Production-CDL parser variants** — see above.
- **Calibre format adapters** — see above.
- **`--config` override flow** — the new `pipeline/run_mvp.py --config <site_config.yaml>` path is wired but only manually exercised. Needs an integration test that points at an alternate `site_config.yaml` (with different fixture paths) and verifies the output goes to the right place.
- **`layermap_override` end-to-end** — the optional foundry `.layermap` override is supported by `tech/config_loader.py` and `tech/layermap_parser.py` but no test exercises it on a fresh `site_config.yaml`. Needs a tiny `.layermap` fixture + a test that verifies the gds-pair gets patched.
- **Multi-device regression** — planned from M6d. Extend `dummy/gen_buffer_layout.py` to inverter / 2-stage buffer / latch fixtures so the macro family gets non-trivial coverage. Today the only fixture is a single inverter, which is structurally too small to find cross-cell bugs.
- **Diffusion-sharing fixture** — synthetic two-device-overlap fixtures are inline in tests; promote them to a real `dummy/fixtures/` artifact so the visualization scripts and round-trip tests can also consume them.

---

## Performance & scalability

- **CSP `propagate` profile.** `core/csp_engine.py::propagate_stats` is on by default since M4e. Currently no consumer reads it. First useful checkpoint: dump the table at end of pipeline, identify the dominant layer × constraint pair as the engine grows.
- **Decoder full-recompute.** The decoder deep-copies `orig_data` once per `apply` call. For single-cell MVP fixtures this is microseconds; for multi-cell layouts the deep-copy cost will grow linearly. The natural fix is structural sharing (shape dicts that record a delta against the parent) but no concrete pressure yet.
- **Derivator full-recompute.** See "Derivator subscription model" above. Same shape: incremental recompute lands when the runtime starts to matter.
- **Union-find without path compression.** Deliberately so that `restore` stays simple. If propagation chains grow long enough that union-find lookup becomes a bottleneck, revisit (and update `_uf_undo_one` accordingly).

---

## Notes lifted from completed-milestone "downstream notes"

These are seams that completed milestones identified as relevant to future work. Most don't need action *now*; listed so they're not forgotten.

- **M2 → M3.** `TrackSegment.bbox_nm` was the seam where the M3 `ShapeRecord` provenance backlink plugged in. Single-tuple field still exists alongside `shape_record` as a denormalised cache. The M2 partial-bbox `None` sentinel pattern in `_apply_poly_modifies` could be re-keyed off `ShapeRecord` ids once the macro family is fully event-sourced.
- **M3 → M5.** `pin_role` inference stamps the *last* role iterated when a net hits multiple pins on the same device (e.g. VSS = S + B for an NMOS). M4's per-cell `pin_role` rasterisation is the principled fix.
- **M4 → M6.** The §M4 "shared OD" acceptance test (`mark_shared_diffusion` against an engine with the OD spacing rule) is in place. M6a's `share_diffusion` macro consumes it; M6d's connectivity macros will further exercise the pattern.
- **M4 cycle-of-restore note.** The union-find `_uf_undo_one` reconstructs the child component's prior size by subtracting from the parent's stored size. Exact for the union-by-size algorithm here; if path compression lands for performance the undo logic must be revisited.
- **M5 → M6.** The "subscribes to CSP commit deltas" requirement was satisfied lightly — derivator is pull-based. M4b's `CommitDelta` infra is in place; only the wiring is deferred.
- **M6a / M6b → M6d.** The `cells_unioned` count and `commit_delta.unions` length differ: the L2 atomic counts every `engine.union` True return (including no-op successes when cells are already in the same component), while `commit_delta.unions` only carries actual merges. Pick the right count for the purpose (display vs. L1 emission).

---

## Decision log entries that need a home

These came up as architectural decisions during shipped work. None of them block anything; preserved here so a future contributor doesn't re-litigate them.

- **Decoder match by center-Y, not bbox.** M1's `_apply_fin_removes` matches by center-Y because the solver and the layout generator disagree on `FIN_WIDTH//2` vs `FIN_WIDTH/2`; center-Y is invariant. M4d's `remove_fin_strip` returns the actual fixture bbox; the resulting 1 nm cosmetic shift in `resize_report.txt` is documented as "report evolves intentionally".
- **Legacy `commit_with_delta` preserved verbatim.** M4b added `commit_with_full_delta` returning `CommitDelta(cells, unions)`. The legacy method stays for the M2 `device_resize` macro until M6a flipped it; older tests that index it as a list keep working.
- **Push vs. pull derivator.** Pull (current) is easier to debug; push wins when runtime matters. Cross-reference: "Derivator subscription model" above.
- **One mega-config vs. layered.** PR #19 chose layered (`drc_rules.yaml` + `layer_map.yaml` + `site_config.yaml`). The composability lets the foundry supply the first two as-is and only `site_config.yaml` per-experiment.
