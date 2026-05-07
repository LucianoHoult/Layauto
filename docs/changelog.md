# Layauto changelog

> Time-ordered record of every shipped change. Newest entry first. For the architectural model these milestones evolve, see [`architecture.md`](architecture.md). For what is *not* yet shipped, see [`backlog.md`](backlog.md).

**Format.** One block per shipped milestone or sub-milestone. Each block carries: date / branch / what shipped / files touched / acceptance evidence / notes.

**Test-count series** (cumulative): M0 33 → M1 38 → M2 50 → M3 65 → M4a 81+4 → M4b 119 → M4c 134 → M4d 155 → M4e 174 → M5 187 → M6a 201 → M6b 214 (+ config-consolidation: no test delta) → iXref 243 → nXref+NET-NAMES 284.

---

## 2026-05-07 — Stage 1.5 extended: nXref + NET NAMES (M7 seam, second slice)

**Branch:** `claude/refine-test-fixtures-nIkdZ`

Extends the iXref slice with the two remaining LVS query commands needed for net-level cross-reference:

  * `NET XREF WRITE nXref.temp` — net-granular cross-reference between schematic and LVS svdb. Same SVDB nxf format (file format 1) as iXref but with a leading `%` on the cell-summary line and net rows in the form `<layout_idx> <layout_net> <source_idx> <source_net>`.
  * `NET NAMES` — stdout-only Calibre HDB response listing every net in the svdb in 1-indexed order. Parsed from the bounded `Net_Names ... END OF RESPONSE` block.

The two outputs are joined into a `schematic_name → lvs_name → lvs_index` middle file (`output/net_xref.yaml`) that tells downstream code which schematic-side net corresponds to which LVS svdb index — including renumbered internal nets (`net9 → 2 → 2`) where LVS replaces an unnamed schematic net with its numeric position. Saved for later use; not consumed by `build_layout_model` today.

- **`io_adapters/calibre_query.py`** — six new functions: `parse_nxref` (header skip + cell summary `%`-tolerant + net-row parsing), `parse_net_names` (locates the `Nets:` anchor, reads the count line, validates `count == len(names)`, accepts truncated stdout when `END OF RESPONSE` is missing), `join_net_xref` (raises `KeyError` if any nXref layout net is missing from the index — that's a real LVS inconsistency), `write_net_xref_yaml`, `run_calibre_nxref` / `run_calibre_net_names` / `run_dummy_nxref` / `run_dummy_net_names` runners, and `extract_net_xref` orchestrator (mirrors `extract_ixref` for both dummy and calibre modes). NET NAMES production runner slices the bounded response block from stdout via `_extract_net_names_block` so the on-disk shape matches the dummy fixture.
- **New `dummy/fixtures/nXref.temp`** — hand-written dummy nxf for `INV_N5_P7` (4 pins; layout names match source names since the inverter has no internal nets). Renumbering case (`0 2 0 net9`) is exercised in unit tests via synthetic input rather than committing inconsistent fixture data.
- **New `dummy/fixtures/net_names.txt`** — hand-written dummy NET NAMES response (4 nets: IN=1, OUT=2, VSS=3, VDD=4).
- **New `dummy/fixtures/net_xref.yaml`** — committed parsed reference for byte-comparison in tests.
- **`dummy/gen_buffer_layout.py`** — `generate_calibre_nxref` + `generate_calibre_net_names` wired into `generate_all_fixtures`. The order of nets is module-level (`DUMMY_NET_ORDER`) so the two generators stay byte-consistent.
- **`tech/site_config.yaml`** — adds `calibre.{nxref_temp, net_names_txt, dummy_nxref, dummy_net_names}` and `inputs.net_xref_yaml`.
- **`tech/config_loader.py::load_site_config`** — resolves the four new path-valued fields under `calibre:`.
- **`pipeline/run_mvp.py`** — Stage 1.5 now runs both `extract_ixref` and `extract_net_xref`. Banner shows iXref/nXref summaries (cell, device count, S/D-swap count; cell, net count, renumbered count). Legacy site_configs without `calibre:` paths get the same repo-default fallback as the iXref slice (`dummy/fixtures/{nXref.temp,net_names.txt}`).

**Files touched.** `io_adapters/calibre_query.py`, `dummy/gen_buffer_layout.py`, `tech/site_config.yaml`, `tech/config_loader.py`, `pipeline/run_mvp.py`, `tests/conftest.py`, `tests/unit/test_calibre_query.py`, `docs/architecture.md`, `docs/changelog.md`. New: `dummy/fixtures/nXref.temp`, `dummy/fixtures/net_names.txt`, `dummy/fixtures/net_xref.yaml`.

**Acceptance.** Pytest 284/284 (243 pre + 41 new in `test_calibre_query.py`). Existing four golden artifacts (`buffer_resized.{gds,json,cdl}`, `annotation_coverage.txt`) md5-identical to the iXref baseline. The new artifacts are `output/{nXref.temp, net_names.txt, net_xref.yaml}`. `python3 pipeline/run_mvp.py` prints `[Stage 1.5] Extracting LVS xrefs (mode=dummy)` followed by separate iXref / nXref summary lines.

**Notes.** Each Calibre query spawns its own subprocess; M7 may consolidate to a single interactive HDB session that runs all queries together (only relevant when actual `calibre` binaries are exercised in CI/production). The parser is tolerant of the missing `%` prefix and missing `END OF RESPONSE` terminator so real-world Calibre output variations don't trip it up.

---

## 2026-05-07 — Stage 1.5: LVS iXref extraction (M7 seam, partial)

**Branch:** `claude/refine-test-fixtures-nIkdZ`

First real Calibre subprocess seam in the codebase. Adds a Stage 1.5 LVS query that produces an `output/ixref.yaml` middle file from either a pre-staged `iXref.temp` (`mode=dummy`, default) or by spawning `calibre -query <svdb_dir>` and streaming HDB query commands (`mode=calibre`, production). The middle file is "saved for later use"; no current consumer reads it. M7 will wire it into LVS feedback closure (net-equivalence overrides for swapped S/D, layout-vs-source device-identity reconciliation).

- **New `io_adapters/calibre_query.py`** — `parse_ixref` (header skipping, cell-row + device-row + S/D-swap-marker parsing; loud `ValueError`s on every malformed-input path), `write_ixref_yaml` (round-trip-safe YAML), `run_calibre_ixref` (full `subprocess.run` with `INSTANCE XREF WRITE <path>` + `EXIT` over stdin, timeout, `CalibreNotFoundError` / `CalibreQueryError` for missing binary / non-zero exit / missing output), `run_dummy_ixref` (copy a fixture; no-op when src == dst), and `extract_ixref` as the top-level `mode={dummy,calibre}` dispatcher.
- **New `dummy/fixtures/iXref.temp`** — hand-written dummy SVDB ixf (cell `INV_N5_P7`, 4 pins, M0→MN0, M1→MP0 with S/D swap). Reproducible byte-identically from `dummy/gen_buffer_layout.py::generate_calibre_ixref` (parametric generator wired into `generate_all_fixtures`).
- **New `dummy/fixtures/ixref.yaml`** — committed parsed reference for byte-comparison in tests (`test_yaml_matches_committed_reference`).
- **`tech/site_config.yaml`** — replaced the deferred-placeholder `calibre:` block with a real one (`mode`, `svdb_dir`, `ixref_temp`, `dummy_ixref`, `timeout_s`); `inputs.ixref_yaml` names the parsed middle file.
- **`tech/config_loader.py::load_site_config`** — resolves the new path-valued fields under `calibre:` and defaults `calibre.mode` to `'dummy'` so legacy site_configs keep working.
- **`pipeline/run_mvp.py`** — new `--lvs-mode {dummy,calibre}` flag (overrides `calibre.mode` in the YAML); inserts "Stage 1.5: LVS extract" between Stage 1 (CDL diff) and Stage 2 (`build_layout_model`); prints a per-run summary (cell name, device count, S/D-swap count, output paths). The parsed dict is *not* fed into `build_layout_model` — save-only, by design.
- **`pipeline/run_mvp.py::resize_report.txt`** — switched to writing CDL basenames (was absolute paths), making the report md5-stable across environments. Existing byte-golden md5 in `tests/unit/test_m6b_macros.py` updated accordingly.
- **`tests/conftest.py`** — added `ixref_temp_path` fixture.

**Files touched.** New `io_adapters/calibre_query.py`, `dummy/fixtures/iXref.temp`, `dummy/fixtures/ixref.yaml`, `tests/unit/test_calibre_query.py`; `dummy/gen_buffer_layout.py`, `tech/site_config.yaml`, `tech/config_loader.py`, `pipeline/run_mvp.py`, `tests/conftest.py`, `tests/unit/test_m6b_macros.py`, `docs/architecture.md`, `docs/backlog.md`.

**Acceptance.** Pytest 243/243 (214 pre + 29 new). All four byte-golden artifacts (`buffer_resized.{json,cdl}`, `resize_report.txt`, `annotation_coverage.txt`) md5-clean to the updated baseline (`resize_report.txt` re-baselined per the basename change). The new `output/ixref.yaml` and `output/iXref.temp` are the only added runtime outputs; `dummy/fixtures/iXref.temp` and `dummy/fixtures/ixref.yaml` are the only added committed fixtures. Generator round-trip: `generate_calibre_ixref(generate_inverter_layout(5,7))` → byte-identical to the committed `dummy/fixtures/iXref.temp`.

**Notes.** `--lvs-mode calibre` was implemented in full but is untested with a real Calibre binary on this machine — `shutil.which('calibre')` returns `None`, so the runner raises `CalibreNotFoundError` cleanly. The subprocess wiring (`subprocess.run` args, stdin commands, capture_output, timeout, non-zero / missing-output diagnostics) is covered by `unittest.mock.patch`-driven tests so the call shape will not silently regress before the first real Calibre run.

---

## 2026-05-06 — Config consolidation (PR #19)

**Branch:** `claude/consolidate-config-parameters-0WrRX`

Restructured the parameter sources so production testing only needs to edit one path-only YAML. Three composable files now describe the bundle:

- **`tech/drc_rules.yaml`** rewritten in unified rule-record format. ASAP7-style ids (`FIN.P.1`, `V0.E.LI`, `NWELL.X.FIN`, etc.); pitch / width / spacing / enclosure / extension / exact_size are all expressed as one-rule-per-record entries with `layers: [...]` + `value_nm` (scalar or `{x, y}`) + `severity`. Easier to machine-parse from a foundry DRM later.
- **New `tech/layer_map.yaml`** in per-layer record format (`gds`, `tier`, `orientation`, `role`, `connects`, `derived`, `color`). Replaces the hardcoded `LAYER_MAP` / `LAYER_TIER` / `LAYER_COLORS` tables in `tech/layer_map.py`.
- **New `tech/site_config.yaml`** — top-level paths-only file: points at the drc_rules + layer_map yamls, lists run inputs (CDLs + Calibre JSONs + bbox) and the output dir. The only file that should be edited per-experiment in production.

`tech/layer_map.py` becomes a thin YAML loader that re-exports the same module-level constants and helpers. `TechConfig` public API is unchanged — every property (`FIN_PITCH`, `LI_MIN_SPACING`, `VIA0_ENC_BY_LI_X`, `LAYER_MAP`, ...) resolves through the new rule-id index. New helpers: `load_site_config()` (returns the parsed dict with paths resolved relative to the YAML), `load_tech_config_from_site()` (one-liner for the pipeline). `pipeline/run_mvp.py` accepts `--config <site_config.yaml>`.

Removed from config (extracted from input files instead): device instance names, device type, default fin counts, cell-name pattern. `NUM_GATE_SLOTS` / `NP_GAP_FINS` were only used by the dummy fixture generator — moved inline as module constants in `dummy/gen_buffer_layout.py`.

**Files touched.** `tech/drc_rules.yaml` (rewrite), `tech/layer_map.yaml` (new), `tech/site_config.yaml` (new), `tech/layer_map.py` (rewrite as YAML loader), `tech/config_loader.py` (rewrite), `tech/process_config.yaml` (deleted), `tech/tech_params.py` (deleted), `pipeline/run_mvp.py` (`--config` flag), `dummy/gen_buffer_layout.py` (cell-template constants).

**Acceptance.** All 187 tests pass (no test count delta — pure refactor). End-to-end pipeline run produces byte-identical resized GDS vs. the pre-refactor baseline (verified by `git stash` round-trip).

---

## 2026-04-30 — M6b: split_diffusion + pick_macro dispatch

**Branch:** `claude/review-arch-plan-fk4Og`

Second slice of M6, scoped to the MVP — no maze routing, no large-scale break-and-reconstruct (per user direction). M6 was decomposed into M6a (done) + M6b (this) + M6c (deferred routing) + M6d (deferred routing-dependent macros).

- **New `core/macros/split_diffusion.py::split_diffusion`** — inverse of M6a's `share_diffusion`. Walks `grid.b_tier_cells_of('OD')`, removes the sibling from each cell's `shared_with`. Optional `cut_at_track_a` parameter triggers `add_cut` calls at every track_b row in the affected region (the gate-cut pattern). Auto-detection of the boundary track is M6d's job (depends on reliable `Device.gate_track_idx`); for M6b the explicit form keeps the macro testable. The engine union-find is *not* actively split — relies on the §B "no CUT between adjacent cells" rule to prevent *future* unions across the cut, plus the natural checkpoint/restore lifecycle.
- **New `core/macros/pick_macro.py`** — L4 dispatch table. `MacroCall(macro_name, args, kwargs, diff)` dataclass + `pick_macro(diff_entry, model)` function + `pick_macros(diffs, model)` list helper. For the MVP, dispatches `nfin` parameter changes to `device_resize`. Other parameters return `None`. Share/split/cut macros stay importable Python API; the pipeline does not auto-invoke them from CDL because diffusion-share / cut deltas are *layout-side intent*, not netlist semantics.
- `pipeline/run_mvp.py` — replaces inlined `solver.resize_device('MN0', 4)` / `('MP0', 6)` with a `pick_macros(...)` loop. Pure refactor; byte-golden preserved.

**Files touched.** New `core/macros/split_diffusion.py`, `core/macros/pick_macro.py`, `tests/unit/test_m6b_macros.py`; `core/macros/__init__.py` (re-exports), `pipeline/run_mvp.py`.

**Acceptance.** Pytest 214/214 (201 pre-M6b + 13 new). All four golden artifacts md5-identical to the M6a baseline.

**Out of scope (deferred to M6c / M6d):** `device_add` / `device_remove` (need routing), `net_reroute`, `buffer_insert`, `diff_cdl` extension to detect device add/remove, GDS layer-number entries for cut layers, auto-detection of the gate-cut boundary track.

---

## 2026-04-29 — M6a: cut_ops + share_diffusion + decoder rejection of derived edits

**Branch:** `claude/review-arch-plan-fk4Og`

First slice of M6. Created the `core/macros/` directory with two L3 macros that bracket the M4d L2 atomics in `engine.checkpoint` / `engine.commit_with_full_delta`, plus a decoder-side guard that lights up the M5 `is_derived` seam.

- **New `core/macros/cut_ops.py::add_cut` / `remove_cut`** — wraps `atomic_ops.add_cut_cell` / `remove_cut_cell`. `CutMacroResult` carries the engine's `CommitDelta`. On L2 atomic refusal, the macro restores to the checkpoint and surfaces `failed_pos`.
- **New `core/macros/share_diffusion.py::share_diffusion`** — wraps `atomic_ops.mark_shared_diffusion`. `ShareDiffusionResult` carries the `CommitDelta` plus `cells_stamped` / `cells_unioned` counts. M4e wired OD into the engine, so the unions actually fire.
- **`core/decoder.py::DerivedShapeEditError`** — raised when a non-derivator caller passes a `modify_shape` op whose `(layer, old_bbox)` matches a `ShapeRecord` with `is_derived=True`. The M5 derivator's `desc='derived_<layer>_y2_shift'` prefix is the disambiguator that exempts derivator-emitted ops.
- **`core/solver.py::resize_device`** flipped from `commit_with_delta` to `commit_with_full_delta`. The MVP buffer-resize transaction prints "0 union events" because LI/M1 are A-tier WIRE-only cells, so byte-golden output is unaffected; the print line gains a "{N} union events" suffix that M6b's `share_diffusion` / `split_diffusion` exercise non-trivially.

**Files touched.** New `core/macros/__init__.py`, `core/macros/cut_ops.py`, `core/macros/share_diffusion.py`, `tests/unit/test_m6_macros.py`; `core/decoder.py`, `core/solver.py`, `pipeline/run_mvp.py`.

**Acceptance.** Pytest 201/201 (187 pre-M6a + 14 new). All four golden artifacts md5-identical to the M5 baseline.

---

## 2026-04-28 — M5: C1 derivator (NWELL / BOUNDARY) on its own module

**Branch:** `claude/m5-drc-derivator`

Pulled all C1 derived markings out of the decoder's transitional Phase 2 helpers. A standalone `drc_derivator` module emits these shapes as L1 `EditOp`s consumed by the decoder's Phase 1 path; subscribes to the L3 macro's commit point so it runs on a clean post-resize state.

- **New `core/drc_derivator.py::DRCDerivator(model, grid, config)`** with `derive_c1(nmos_fin_y_new, pmos_fin_y_new) -> List[EditOp]`. Walks `model.shape_pool` for each C1 layer; emits one `modify_shape` EditOp per shape whose y2 actually changed; idempotent on re-call (updates `sr.bbox_nm` post-emit); stamps `is_derived=True` and `provenance='drc_derivator._derive_<layer>'` on every C1 shape it owns (lights up the M3 seam). NWELL `y2 = pmos_fin_y_new[-1] + config.NWELL_MARGIN_BEYOND_FIN` (30 nm); BOUNDARY `y2 = ... + config.BOUNDARY_MARGIN_BEYOND_FIN` (40 nm).
- `core/decoder.py`: deleted `_derive_nwell` / `_derive_boundary`; Phase 2 (derived synthesis) is now empty. Added `_apply_nwell_modifies` / `_apply_boundary_modifies` to Phase 1 mirroring `_apply_od_modifies`. `_update_metadata`'s `cell_height` reads `config.BOUNDARY_MARGIN_BEYOND_FIN` instead of a hardcoded 40.

**Files touched.** New `core/drc_derivator.py`, `tests/unit/test_drc_derivator.py`; `core/decoder.py`, `tech/process_config.yaml` (added `derivation:` section — superseded by 2026-05-06 config consolidation), `tech/config_loader.py` (added `NWELL_MARGIN_BEYOND_FIN` / `BOUNDARY_MARGIN_BEYOND_FIN` properties), `pipeline/run_mvp.py`.

**Acceptance.** Pytest 187/187 (174 post-M4e + 13 new). `output/buffer_resized.{json,cdl}` and `output/annotation_coverage.txt` md5-identical to M4e baseline. NWELL `y2 = 395`, BOUNDARY `y2 = 405`. Both pool records carry `is_derived=True` post-derivator.

**Notes.** `is_derived` is now load-bearing on every C1 shape post-derivator, but the decoder doesn't yet reject macro-emitted edits to derived shapes — M6a added that check.

---

## 2026-04-28 — M4e: B-tier engine layers + cell-level DRC + propagate_stats (closes M4)

**Branch:** `claude/review-arch-plan-Niwe4`

- `core/csp_engine.py`: `initialize_domains` accepts a `layer_occ_types: Dict[layer, Set[OccupantType]]` per-layer override so B-tier cells admit `DEVICE_DIFF` / `VIA` / `CUT` (with both `net_id=None` and per-net variants). New `propagate_stats` instrumentation (`calls`, `cells_visited`, `time_ns` per layer) updated by `_propagate` via try/finally; `_perf_counter_ns = time.perf_counter_ns` module alias for test-time monkey-patching; `get_propagate_stats(layer=None)` + `reset_propagate_stats()` query API.
- `core/solver.py::setup_engine` extended with `b_tier_layers` (default: every B-tier layer the parser populated on the grid — today OD + VIA0); computes engine bounds from `grid.b_tier_cells` keys with a 1-cell margin. **New `load_b_tier_cells_into_engine`** seeds engine state from `grid.b_tier_cells_of`. `project_unannotated_blockages` now skips layers absent from `grid.layers` so the A-tier-only `physical_to_segment_coords` path stays sound.
- `core/drc_constraints.py`: `SameLayerMinSpacing` and `SameLayerAlongTrackSpacing` gain a `trigger_types` constructor arg; `create_mvp_drc_rules` adds OD same-layer + along-track spacing on `(DEVICE_DIFF,)` triggers and a VIA0 min-spacing rule on `(VIA,)` triggers.

**Files touched.** `core/csp_engine.py`, `core/solver.py`, `core/drc_constraints.py`, `pipeline/run_mvp.py`; new `tests/unit/test_b_tier_drc.py`.

**Acceptance.** Pytest 174/174 (155 post-M4d + 19 new). All four golden artifacts md5-identical to the M4d baseline. Engine cell count grew from 256 to 411 with OD/VIA0 added.

---

## 2026-04-28 — M4d: B-tier + FIN/POLY L2 atomics; macro consumes L2 results

**Branch:** `claude/review-arch-plan-Niwe4`

`core/atomic_ops.py` gains `add_cut_cell` / `remove_cut_cell` / `mark_shared_diffusion` / `extend_od` / `add_fin_strip` / `remove_fin_strip` / `extend_poly`. New result types: `FinStripResult` (track_idx, bbox, desc, shape_record backlink) and `PolyExtendResult` (target, old_value, new_value). `add_cut_cell` integrates with the M4b union-find — exercising §B's "no CUT between adjacent cells" end-to-end via the L2 primitive.

`core/solver.py`: `_emit_fin_removes` calls `remove_fin_strip` (mutates `model.shape_pool`); `_emit_od_modify` calls `extend_od` (re-projects the cell-grid + updates ShapeRecord bbox); `_emit_poly_modify_if_endpoint_changed` builds its EditOp from `extend_poly`'s return. The macro continues to emit L1 records but the geometry now flows through L2 atomics.

**Files touched.** `core/atomic_ops.py`, `core/solver.py`, `pipeline/run_mvp.py`; new `tests/unit/test_b_tier_atomics.py`.

**Acceptance.** Pytest 155/155 (134 post-M4c + 21 new). `output/buffer_resized.{json,cdl}` md5-identical to the M4c baseline. **`output/resize_report.txt` evolves intentionally** on the two FIN remove records — `remove_fin_strip` returns the actual fixture bbox (`y1=136`) instead of the legacy synthesised one (`y1=137`); 1 nm cosmetic shift.

---

## 2026-04-28 — M4c: parser tier-dispatch + B-tier projection + desc-filter retirement

**Branch:** `claude/review-arch-plan-Niwe4`

- `io_adapters/parser.py::apply_lvs_overlay` no longer uses the M3 "first-pin-wins" placeholder for `device_id`. New `_device_for_shape(sr, devices, candidates=...)` helper picks the device whose bbox contains the shape's center (with a max-overlap-area fallback). The OUT net's two LI shapes get distinct `device_id`s (MN0 / MP0); the VSS / VDD M1 power rails end up with `device_id=None`.
- **New `project_b_tier_shapes(model, grid, devices)`** — registers axes (OD: POLY × FIN; VIA0: LI × M1; CPO/FIN_CUT: POLY × FIN; M0_CUT: LI × M1), projects bbox via `MultiLayerGrid.bbox_to_b_tier_cells`, stamps a `CellOccupancy` per cell with `owner_device_id` from `_device_for_shape` and `occ_type` from a layer→type table. Walks every OD shape and appends sibling devices to `shared_with[]` whenever their bboxes overlap (diffusion sharing).
- `core/solver.py::_reshape_li_sd_bars`: replaces the `device_y_marker not in seg.desc` filter with `seg.shape_record.device_id == device.inst_name`. Legacy desc-substring fallback retained for direct-construction callers.

**Files touched.** `io_adapters/parser.py`, `core/solver.py`; new `tests/unit/test_parser_tier_dispatch.py`.

**Acceptance.** Pytest 134/134 (119 post-M4b + 15 new). All four golden artifacts md5-identical to the M4b baseline.

---

## 2026-04-27 — M4b: CSP cell-grid axis + net-equivalence union-find

**Branch:** `claude/review-arch-plan-Niwe4`

Purely additive — no current pipeline path keys off the new surfaces, byte-golden preserved by construction.

- `core/grid.py`: `MultiLayerGrid` gains parallel storage for B-tier layers — `b_tier_axes: Dict[layer, (axis_a_layer, axis_b_layer)]` plus sparse `b_tier_cells: Dict[layer, Dict[(track_a, track_b), CellOccupancy]]`. New API: `is_b_tier_layer()`, `register_b_tier_axes()`, `bbox_to_b_tier_cells()`, `set_b_tier_cell` / `get_b_tier_cell`, `b_tier_cells_of()`. Registration rejects A-tier layers and unregistered axes (fail-loud).
- `core/csp_engine.py`: net-equivalence union-find lives on `ConstraintEngine`. `_uf_parent` + `_uf_size` (no path compression — keeps `restore` simple) plus `_uf_trail` and `_uf_checkpoints` (maps each `checkpoint()` return to the matching `_uf_trail` length without changing the public return type). New methods: `mark_cut(pos)` (mirrors M3 `mark_blockage`), `union(pos_a, pos_b)` (adjacent + same-net + non-CUT preconditions; the §B "no CUT between adjacent cells" rule is enforced because a chain of adjacent unions across a CUT fails at the cut step), `net_of(pos)`, `connected_to(pos)`, `connected_cells(net_id)`. `restore` extended to undo unions in reverse order before cell-trail rollback.
- New `CommitDelta(cells, unions)` dataclass returned by `commit_with_full_delta`. Legacy `commit_with_delta` is preserved verbatim for backward compatibility.

**Files touched.** `core/grid.py`, `core/csp_engine.py`; new `tests/unit/test_b_tier_grid.py` (11 tests), `tests/unit/test_net_equivalence.py` (23 tests).

**Acceptance.** Pytest 119/119 (85 post-M4a + 34 new). All four golden artifacts md5-identical to the M4a baseline.

---

## 2026-04-27 — M4a (+ Codex P2 follow-up): data-model + tier-marker foundation

**Branch:** `claude/review-arch-plan-Niwe4`

Purely additive; byte-golden preserved by construction.

- `core/data_model.py`: added `OccupantType.CUT`; defined `CellOccupancy(layer, track_a, track_b, occ_type, net_id, owner_device_id, shared_with, shape_record)` with `add_sharer` / `remove_sharer` / `pos` accessors. `__post_init__` rejects A-tier `OccupantType.WIRE` so M4c projection can't silently mis-route a layer.
- `tech/layer_map.py`: added `LAYER_TIER` (A/B/C1/C2 markers), `A/B/C1/C2_TIER_LAYERS` subsets, `CUT_LAYERS = ('CPO', 'M0_CUT', 'FIN_CUT')`, plus `tier_of()` / `layers_in_tier()` / `is_cut_layer()` helpers. CPO / M0_CUT / FIN_CUT / VT / PP / NP / DNW / DIODE / ESD / TEXT have tier markers without yet having `LAYER_MAP` GDS-number entries — locks tier intent before geometry shows up.

**Codex P2 follow-up** (same day): `__post_init__` now requires `tier_of(layer) == 'B'` (deferred import of `tech.layer_map.tier_of` to avoid a module-load-time `core <-> tech` cycle). `add_sharer` now requires `occ_type == DEVICE_DIFF`.

**Files touched.** `core/data_model.py`, `tech/layer_map.py`; new `tests/unit/test_cell_occupancy.py`, `tests/unit/test_layer_tiers.py`.

**Acceptance.** Pytest 85/85 (65 pre-M4a + 16 + 4 follow-up). `output/buffer_resized.{json,cdl}` and `output/resize_report.txt` byte-identical to the M3 baseline. The structural test `test_every_layer_map_entry_has_a_tier` is the fail-loud guard for future LAYER_MAP entries that forget a tier marker.

---

## 2026-04-27 — M3: shape_pool parser inversion + unannotated-shape BLOCKAGE projection

**Branch:** `claude/review-arch-plan-LKbJL`

Inverted the parser to "GDS `shape_pool` is geometric truth, LVS is annotation overlay." All unannotated shapes enter CSP as `BLOCKAGE`.

- **M3a.** Added `core/data_model.py::ShapeRecord` (geometric record with optional LVS overlay: `net_id` / `device_id` / `pin_role`; plus `provenance` / `is_derived` / `suspect_tags` seams). Added `LayoutModel.shape_pool` and `LayoutModel.annotation_coverage()`. `TrackSegment.shape_record` is the canonical per-segment backlink.
- **M3b.** Inverted `io_adapters/parser.py`. New `build_shape_pool(bbox_data)` is the geometric-first pass — every GDS rectangle becomes a `ShapeRecord` with `net_id=None`. New `apply_lvs_overlay(pool, net_data, devices)` stamps `net_id` / `device_id` / `pin_role` onto matching records by `(layer, bbox)` key.
- **M3c.** Added `ConstraintEngine.mark_blockage(pos)` — sets `cell.assignment = BLOCKAGE`, `cell.domain = {BLOCKAGE}`, `cell.fixed = True`. Idempotent; refuses to overwrite annotated assignments (conservative-default rule §D).
- **M3d.** Added `LayoutSolver.project_unannotated_blockages()` — iterates `model.shape_pool`, projects unannotated CSP-layer shapes through `MultiLayerGrid.physical_to_segment_coords`, marks each cell as BLOCKAGE.
- **M3e.** Pipeline emits `output/annotation_coverage.txt` from `LayoutModel.annotation_coverage()`. MVP fixture today reports 14 / 32 LVS-annotated shapes.

**Files touched.** `core/data_model.py`, `io_adapters/parser.py`, `core/csp_engine.py`, `core/solver.py`, `pipeline/run_mvp.py`; new `tests/unit/test_shape_pool.py` (7 tests), `tests/unit/test_blockage.py` (8 tests).

**Acceptance.** Pytest 65/65 (50 pre-M3 + 15 new). `output/buffer_resized.{json,cdl}` and `resize_report.txt` byte-identical to M2 baseline; GDS polygon-set identical (30/30). Acceptance contract: `tests/unit/test_blockage.py::test_li_stub_makes_assign_segment_cells_infeasible` injects an unannotated LI ShapeRecord on an empty cell, projects to BLOCKAGE, then verifies `atomic_ops.assign_segment_cells` returns `failed_pos` with engine state restorable.

---

## 2026-04-26 — M2: CSP transactional API + L3 device_resize macro + L2 atomics

**Branch:** `claude/review-arch-plan-Li1Az`

Demoted `resize_device` to a true L3 macro that expands into L2 primitives. L2 only proposes cell-level changes to the engine; the decoder synthesizes L1; the engine handles feasibility and transactions.

- **M2a.** Strengthened the CSP engine trail format to `(pos, prev_domain, prev_assignment)` so `restore` reverts both. Added `propose_assign` / `propose_release` / `commit_with_delta`.
- **M2b.** Created `core/atomic_ops.py` with the M2 minimal L2 subset (`release_segment_cells`, `assign_segment_cells`, `modify_segment`). `AtomicResult.failed_pos` localises infeasible proposals.
- **M2c.** Refactored `resize_device` into the L3 `device_resize` macro: opens a checkpoint, drives LI cell-level changes through `atomic_ops.modify_segment`, emits L1 records, and `commit_with_delta`s on success / `restore`s on infeasibility.
- **M2d.** Deleted the transitional Phase 2 helpers `_shrink_li_sd_bars`, `_derive_poly_span`, `_extend_li_for_vias` from `core/decoder.py`. Phase 1 grew `_apply_li_modifies` and `_apply_poly_modifies`.
- **M2e.** Added `bbox_nm: Optional[Tuple[int,int,int,int]]` to `TrackSegment` so emitted L1 `old_bbox` records are pixel-accurate even on odd-width layers (LI = 17 nm).

**Files touched.** `core/csp_engine.py`, `core/solver.py`, `core/decoder.py`, `core/data_model.py`, `io_adapters/parser.py`; new `core/atomic_ops.py`, `tests/unit/test_atomic_ops.py`.

**Acceptance.** Pytest 50/50 (38 pre-M2 + 12 new). `output/buffer_resized.{gds,json,cdl}` byte-identical to M1 baseline. **`output/resize_report.txt` evolves intentionally** — the macro now lifts POLY span derivation (and the M1 cross-net leakage in MN0's report) into explicit L1 EditOps; 7 ops vs. M1's 6.

---

## 2026-04-25 — M1: unify EditOp + route writeback through a decoder

**Branch:** `claude/m1-decoder-writeback`

- **M1a.** Deleted the duplicate `EditOp` in `core/solver.py`; canonical class lives at `core/diff.py:16-37` with all four op_types.
- **M1b.** Built `core/decoder.py::WritebackDecoder` — Phase 1 applies explicit EditOps (FIN remove by center-Y match; OD modify by old-bbox match), Phase 2 derives geometry the solver did not yet emit (POLY span, LI shrink + via-coverage extension, NWELL/BOUNDARY extents — Phase 2 to be evicted by M2 / M5), Phase 3 updates params + device metadata.
- **M1c.** Removed the legacy 125-line `apply_edits_to_layout_data` function from `pipeline/run_mvp.py`; the pipeline now calls `WritebackDecoder(grid, config).apply(...)` once.

**Files touched.** `core/diff.py`, `core/solver.py`, `pipeline/run_mvp.py`; new `core/decoder.py`, `tests/unit/test_decoder.py` (5 tests).

**Acceptance.** Pytest 38/38. Pipeline buffer-resize JSON / CDL / `resize_report.txt` byte-equal under fixed `PYTHONHASHSEED`; GDS polygons identical (30/30 (layer, datatype, points) tuples match).

**Discovery.** M1's "decoder consumes EditOp stream" goal is partial — the solver emits EditOps for FIN/OD/LI but not POLY/NWELL/BOUNDARY; the decoder's Phase 2 fills the gap and is the seam where M2 (POLY) and M5 (NWELL/BOUNDARY) will plug in.

---

## 2026-04-25 — M0: initial MVP + roadmap creation

**Branch:** `claude/check-stream-env-vars-N5suX`

Initial English roadmap created from a Chinese architecture-analysis source. Verification snapshot generated against branch state on this date. All seven milestones marked Not started.

The starting state of the MVP:
- Single-cell inverter buffer fixture (NMOS 5fin + PMOS 7fin).
- End-to-end pipeline from CDL diff to GDS output with byte-golden reference.
- Two competing `EditOp` definitions (`core/diff.py` and `core/solver.py`).
- Per-layer hardcoded geometry recomputation in `apply_edits_to_layout_data`.
- CSP engine consulted as sanity check but not driving resize.
- Net-primary parser; only A-tier (LI / M1) in CSP.
- SKILL emission was a `printf` placeholder; Calibre dummy JSON only.
- 33 tests passing.

This is the byte-golden baseline that M1 through M5 preserve.
