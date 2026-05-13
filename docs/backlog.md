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
- `core/router/obstacles.py` — obstacle queries against `engine.cells` / `engine.layer_dims` / `engine.connected_cells(net_id)`.
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
  * **Out of scope.** Multi-Vt fixtures, SDT / LIG, multi-finger devices — 1.7 lands the seam against the current single-cell fixture; richer LVS-layer set lands as fixtures grow (and forces 1.6 to materialise).

**Acceptance.** Real PDK environment: buffer resize → SKILL load → DRC clean → LVS match. Inject a violating edit → DRC fail localizes to the responsible L2 op.

**Risks.** PDK redaction may block end-to-end validation. Keep an injection harness that mocks DRC violations.

**Dependencies.** M1–M6 all complete; iXref + nXref + DEVICE INFO + NET SHAPES slices already in.

---

## Cross-cutting deferrals

### Derivator subscription model

Today the C1 derivator (`core/drc_derivator.py`) is **pull-based** — the pipeline calls `derive_c1(...)` after the L3 macro commits, and the derivator does a full recompute. The architectural model (§ A4) calls for **push-based subscription**: `engine.commit_with_full_delta`'s cell delta hands the affected-neighborhood radius directly to the derivator for incremental recompute.

The infrastructure is in place (`CommitDelta` lands in M4b; M6a flipped `device_resize` to `commit_with_full_delta`); only the wiring is deferred. Earns its keep when derivator runtime starts to dominate (multi-cell layouts).

### Engine union-find: path-aware split

The current `_uf_undo_one` undoes the *most recent* union — it does not selectively split a component. As a result, M6b's `split_diffusion` does not actively un-merge the engine union-find; it relies on the §B "no CUT between adjacent cells" rule (preventing future unions across the cut) plus the natural checkpoint/restore lifecycle.

A path-aware union-find (or a fully recomputed component on each split) is needed before multi-step diffusion split-then-share-elsewhere becomes a real workload. M6d / M7 will surface the requirement in earnest.

### Geometric-overlap suspect tagging (M3 §D rule 3)

`ShapeRecord.suspect_tags` exists as the M3 seam but stays empty. The "geometric-overlap cross-check at parse time tagging suspicious shapes `SUSPECT_CONNECTED_TO_*`" rule is not implemented. The MVP fixture's unannotated shapes are FIN / OD / POLY (non-CSP) and NWELL / BOUNDARY (cell-level wrappers), so the tag would not fire on it. The check earns its keep on a real production layout where filler / ESD shapes overlap LVS-tagged routing.

### LVS bbox tolerance

The M3 `(layer, bbox_nm)` overlay key works because the dummy generator's GDS shapes and the dummy LVS shapes share an exact bbox-tuple representation. Production LVS geometry can drift sub-nm. M7 will need a tolerance / containment match in `apply_lvs_overlay`.

### iXref + net_xref + device_info + net_shapes consumption

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
