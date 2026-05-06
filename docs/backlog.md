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

**Files to create / replace.**
- **New** `io_adapters/skill_emitter.py` — replaces the `printf` placeholder in `writer_skill_script.py`. Walks `shape_pool` + `EditOp` records; every emitted edit gets a provenance comment.
- **New** `io_adapters/calibre_runner.py` — replaces dummy Calibre JSON for real LVS/DRC.
- `pipeline/run_mvp.py` — append DRC/LVS calls; feed results back to L3 macro provenance.

**Acceptance.** Real PDK environment: buffer resize → SKILL load → DRC clean → LVS match. Inject a violating edit → DRC fail localizes to the responsible L2 op.

**Risks.** PDK redaction may block end-to-end validation. Keep an injection harness that mocks DRC violations.

**Dependencies.** M1–M6 all complete.

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

`io_adapters/parser.py::parse_calibre_*` assumes the dummy generator's exact JSON shape. Known production drift:
- Coordinates may be microns, not nm.
- Pin names may be case-sensitive.
- Net names may include hierarchy separators.
- `fin_y_positions` may not be explicit (derive from OD + fin pitch).

Worth adding a `format:` block to `site_config.yaml` for common drifts (`{units: nm|um, fin_y_field: fin_y_positions | derive}`). Code-side adapters needed for schemas that diverge harder.

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
