# Layauto architecture

> **Scope of this document.** What the project is, how it's structured, and the principles that drive the structure. For history (what was built when), see [`changelog.md`](changelog.md). For open work (what is not built yet), see [`backlog.md`](backlog.md).

## 1. Project overview

Layauto is an **incremental layout-automation framework** for FinFET cells. Today's MVP performs one narrow task end-to-end:

> Given an existing inverter buffer GDS (NMOS / PMOS with `nfin = 5 / 7`) and a CDL netlist that asks for `nfin = 4 / 6`, produce a new GDS with the requested fin counts, preserving DRC correctness, while reusing every shape that doesn't need to change.

That narrow task exercises the full pipeline (CDL parse → CSP load → resize solve → writeback → GDS emit) and a subset of the cross-cutting machinery (CSP-based DRC propagation, transactional rollback, derived-shape synthesis). Everything bigger — multi-cell, device add/remove, full routing — sits behind clean seams the design has reserved (see [`backlog.md`](backlog.md)).

**What's in scope.** Single-cell, per-cell modifications. Cell boundary fixed. M1 routing positions don't change. DRC subset: LI/M1 spacing, VIA0 enclosure.

**What's not in scope (today).** Multi-cell routing, cell-height changes, M2 and above metal layers, buffer insertion/deletion, multi-patterning constraints, full from-scratch placement/routing.

## 2. Pipeline flow

Entry point: `pipeline/run_mvp.py::run_full_pipeline(site_config_path)`.

| Stage | What it does | Implementation |
|-------|--------------|----------------|
| 1. Diff CDL | Parses original + modified `.cdl`; finds parameter-level differences (today: `nfin`) and emits `(inst, param, old, new)` tuples that drive macro dispatch. | `io_adapters/cdl_parser.py::parse_cdl` + `diff_cdl` |
| 1.5. LVS extract (iXref) | Either spawns `calibre -query <svdb_dir>` and streams `INSTANCE XREF WRITE` over stdin (`mode=calibre`) or copies a pre-staged `dummy/fixtures/iXref.temp` (`mode=dummy`, default). Parses the SVDB ixf format into `{cell, devices, header_lines}` and writes `output/ixref.yaml` as a saved-for-later middle file. Not consumed by Stage 2 yet. | `io_adapters/calibre_query.py::extract_ixref` |
| 2. Build `LayoutModel` + `MultiLayerGrid` | Parses Calibre device + net JSONs and the bbox-by-layer dump; constructs the geometric `shape_pool` first, then applies LVS as an annotation overlay; builds a per-layer `MultiLayerGrid` (A-tier track grids + B-tier cell grids). | `io_adapters/parser.py::build_layout_model` |
| 3. Set up CSP engine | Registers DRC constraint templates, initialises per-cell domains for every CSP-modelled layer (LI / M1 + the B-tier OD / VIA0). | `core/solver.py::LayoutSolver.setup_engine` |
| 4. Load existing layout into CSP | Walks every `TrackSegment` and B-tier cell from stage 2; stamps each cell as `FIXED` so propagation runs against existing geometry. Then projects unannotated shapes as `BLOCKAGE`. | `core/solver.py::load_existing_layout`, `load_b_tier_cells_into_engine`, `project_unannotated_blockages` |
| 5. Solve resize | Dispatches each CDL diff entry through `pick_macro` (`core/macros/pick_macro.py`); the L3 `device_resize` macro brackets its work in `engine.checkpoint` / `commit_with_full_delta` and routes geometry through L2 atomics. | `core/macros/pick_macro.py` → `core/solver.py::resize_device` → `core/atomic_ops.py` |
| 6. Emit output | C1 derivator emits NWELL / BOUNDARY edits; `WritebackDecoder` consumes the combined L1 stream and produces the modified layout dict; GDS / CDL / JSON / report files are written. | `core/drc_derivator.py::DRCDerivator` → `core/decoder.py::WritebackDecoder.apply` → `io_adapters/gds_io.py::write_gds` |

Two important properties:

- **Incremental, not from-scratch.** Stage 2 reads existing layout; stage 4 stamps every existing cell as `FIXED`; stage 6's decoder deep-copies + patches per-layer rather than re-laying out. Each run rebuilds the *output* from scratch but never touches the input.
- **Atomic at the file level.** GDS write is a single `lib.write_gds(filename)` — either a complete file is produced or none. In-memory edits during writeback are not atomic, but they happen on a deep-copy of the input, so a mid-failure leaves the source untouched.

## 3. Architectural principles

These four are the load-bearing design decisions. Every milestone in [`changelog.md`](changelog.md) and every open item in [`backlog.md`](backlog.md) is justified by one of them.

### A. Three sources of truth, with annotation inversion

- **GDS `shape_pool` is geometric truth.** Every drawn rectangle becomes a `ShapeRecord` with full bbox.
- **CDL `Device` / `Net` is semantic truth.** What the circuit means.
- **LVS is annotation, and it is incomplete.** It binds geometry to semantics, but coverage is never guaranteed (filler, ESD, dummies, hand-edits often unannotated).

Practical consequence: the parser is **shape-pool-primary**. `build_shape_pool(bbox_data)` is the geometric pass; `apply_lvs_overlay(pool, net_data, devices)` stamps `net_id` / `device_id` / `pin_role` onto matching records by `(layer, bbox)` key. Unannotated shapes stay in the pool and project into CSP as `BLOCKAGE` occupants — they obstruct edits but carry no net identity.

### B. Tier-based layer dispatch

Layers are not equivalent; physical role determines abstraction. Four tiers, declared in `tech/layer_map.yaml`:

| Tier | Layers | Data structure | CSP participation |
|------|--------|----------------|-------------------|
| **A** — 1D track | FIN, POLY, LI, M1 | `TrackSegment` | Yes (track grid) |
| **B** — 2D cell | OD, VIA0, CPO, M0_CUT, FIN_CUT | `CellOccupancy(track_a, track_b)` with `owner_device_id` + `shared_with[]` (OD); `OccupantType.CUT` for cutters | Yes (cell grid) |
| **C1** — derived marking | NWELL, VT, PP, NP, BOUNDARY, DNW | No grid; pure-function derivation from A/B-tier state + `Device` metadata | No — `DRCDerivator` output |
| **C2** — editable annotation | DIODE, ESD, TEXT marker | No grid, no derivation; `ShapeRecord` direct edit | No |

Two specific B-tier behaviours:

- **Diffusion sharing.** OD cells use `owner_device_id` as primary key. Devices that share S/D add themselves to the cell's `shared_with[]` list. SKILL / GDS still emits a single OD shape; the sharing is a metadata-side relationship the macros consult.
- **CUT semantics.** A `CUT` occupant in `csp_engine` blocks `union` of net-equivalence classes across the cut location. Adding a POLY_CUT mid-span breaks one net into two; removing it re-merges them.

### C. Four-layer atomic-edit architecture

```
L4 Pipeline   :  diff_cdl → pick_macro → apply → writeback
L3 Macro      :  device_resize | add_cut / remove_cut | share_diffusion / split_diffusion |
                 (deferred — M6d) device_add | device_remove | net_reroute | buffer_insert
L2 Atomic op  :  add/remove/modify_segment | extend_od | extend_poly |
                 add/remove_fin_strip | mark_shared_diffusion |
                 add/remove_cut_cell | update_device_metadata
L1 Shape rec  :  ShapeAdd | ShapeRemove | ShapeModify   (the only EditOp)
```

**Strict responsibility split** — three sources of truth maintained independently:

- **L2 ops** *only* submit cell-level proposals to the CSP engine. They do not produce L1 records, do not mutate `LayoutModel` non-cell state, and do not decide feasibility.
- **CSP engine** receives proposals → runs DRC propagation + net-equivalence incremental update → returns feasibility + `CommitDelta(cells, unions)` → commits or restores.
- **Decoder** subscribes to CSP commit deltas → derives L1 `EditOp`s and updates the `LayoutModel` indexes. The decoder is the *sole* holder of `MultiLayerGrid.segment_to_physical`.
- **`shape_pool`** consumes L1 `EditOp`s to update geometric truth.

L3 macros use `engine.checkpoint` / `restore` for transactional bracketing. `device_resize`, for example, expands a metadata delta into a sequence of `extend_od` + `extend_poly` + `add/remove_fin_strip` calls inside a single transaction.

**Non-CSP side-channels** (parallel to the main path):
- C1 derived markings → `drc_derivator` subscribes to commit deltas, emits L1 directly.
- C2 editable annotations → L3 may emit L1 directly without entering CSP.
- Pure metadata updates (e.g., non-geometric device parameters) → write `Device` fields only; no L1, no CSP.

**Decoder rejection of derived-shape edits.** Since M6a, the decoder rejects any incoming `EditOp` whose `(layer, old_bbox)` matches a `ShapeRecord` with `is_derived=True`, *unless* the op carries the M5 derivator's `desc='derived_<layer>_y2_shift'` prefix. This makes the M5 `is_derived` seam load-bearing and prevents L3 macros from accidentally stomping on derived markings.

### D. Annotation depth and incompleteness

- Annotation atomicity equals edit atomicity, dispatched per tier:
  - **A** — rectangle-level → copies into `TrackSegment` fields.
  - **B** — rectangle-level → rasterizes to cells; `pin_role` inferred from gate position; shared S/D segments tagged via `shared_with`.
  - **C1** — no annotation; derivator generates from rules.
  - **C2** — rectangle-level annotation attached to `ShapeRecord`; never enters CSP.
- Every atomic carries identity (`net_id` / `device_id` / `pin_role`). Every `ShapeEditRecord` carries a **provenance backlink** pointing to the L3 macro / L2 op / derivator rule that produced it. Used for: blast-radius computation, conflict localization, DRC/LVS feedback closure.
- **Four conservative rules for unannotated shapes** (LVS incompleteness):
  1. Unannotated shapes enter CSP as `BLOCKAGE`.
  2. On CSP commit, the engine exports an "affected cell neighborhood" delta; derivator and decoder re-evaluate unannotated shapes inside it. (Subscription model is push-ready; today the derivator runs full recompute — see [`backlog.md`](backlog.md) § "Derivator subscription model".)
  3. At parse time, run geometric-overlap cross-check; tag suspicious shapes `SUSPECT_CONNECTED_TO_*`. (`ShapeRecord.suspect_tags` exists as the seam; cross-check is not yet implemented — see [`backlog.md`](backlog.md).)
  4. Default conservatively: don't traverse, don't silently delete, don't auto-merge, treat collisions as real conflicts.

## 4. Module map

```
Layauto/
├── pipeline/              # End-to-end orchestration
│   └── run_mvp.py            # Entry point; reads tech/site_config.yaml
├── core/                  # IO-independent engine
│   ├── data_model.py         # ShapeRecord, TrackSegment, CellOccupancy, Device, Net, LayoutModel
│   ├── grid.py               # LayerGrid + MultiLayerGrid (track grids + B-tier cell grids)
│   ├── csp_engine.py         # ConstraintEngine: propose/commit/restore + union-find
│   ├── drc_constraints.py    # DRC constraint templates (per-layer)
│   ├── atomic_ops.py         # L2 atomics (the only callers of CSP propose/release)
│   ├── solver.py             # Resize solver, CSP loader, L3 device_resize macro
│   ├── decoder.py            # WritebackDecoder: L1 EditOp -> shape dict mutation
│   ├── drc_derivator.py      # C1 derived markings (NWELL, BOUNDARY, ...) → L1
│   ├── diff.py               # EditOp dataclass + diff_cdl
│   └── macros/               # L3 macro family
│       ├── cut_ops.py            # add_cut / remove_cut
│       ├── share_diffusion.py    # share_diffusion
│       ├── split_diffusion.py    # split_diffusion
│       └── pick_macro.py         # MacroCall + dispatch table
├── io_adapters/           # IO-side (swap for production)
│   ├── parser.py             # Calibre JSON -> LayoutModel (shape-pool-primary)
│   ├── cdl_parser.py         # CDL parse + diff
│   ├── gds_io.py             # GDS write (gdstk + manual fallback) + read-back
│   ├── writer_cdl.py         # CDL emission
│   └── writer_skill_script.py  # SKILL emitter (placeholder; M7)
├── tech/                  # Tech bundle (composable YAMLs)
│   ├── site_config.yaml      # Top-level run-config (paths only)
│   ├── drc_rules.yaml        # Unified DRC rule deck
│   ├── layer_map.yaml        # Per-layer records (gds, tier, role, ...)
│   ├── config_loader.py      # Loads YAMLs into TechConfig
│   ├── layer_map.py          # YAML-loaded constants (LAYER_MAP, LAYER_TIER, ...)
│   ├── layermap_parser.py    # Optional foundry .layermap override parser
│   └── drc_rule_deck.py      # Programmatic rule-table builder
├── visualization/         # Layout viewers (matplotlib)
├── dummy/                 # Dummy fixture generation (not used in production)
│   ├── gen_buffer_layout.py    # Generates Calibre + bbox + GDS fixtures
│   └── fixtures/               # Generated artifacts
├── scripts/               # Production environment shell hooks (M7 placeholders)
│   ├── calibre_query_extract.sh
│   ├── calibre_run_drc.sh
│   ├── calibre_run_lvs.sh
│   └── virtuoso_apply_edit.il
├── tests/
│   ├── unit/
│   └── integration/
└── output/                # Pipeline outputs
```

## 5. Data model

The five core dataclasses (all in `core/data_model.py`):

| Class | Holds | Notes |
|-------|-------|-------|
| `ShapeRecord` | `layer`, `bbox_nm`, `desc`, optional LVS overlay (`net_id` / `device_id` / `pin_role`), `provenance`, `is_derived`, `suspect_tags` | Geometric truth (M3). Lives in `LayoutModel.shape_pool`. `is_derived=True` is set by `DRCDerivator` and load-bearing for the M6a decoder rejection check. |
| `TrackSegment` | `layer`, `track_idx`, `start_anchor`, `end_anchor`, `net_id`, offsets, `bbox_nm` cache, `shape_record` backlink | A-tier wire on the track grid. `shape_record` is the M3 backlink to the geometric source. |
| `CellOccupancy` | `layer`, `track_a`, `track_b`, `occ_type` (`WIRE` / `VIA` / `DEVICE_DIFF` / `DEVICE_GATE` / `CUT` / `BLOCKAGE`), `net_id`, `owner_device_id`, `shared_with[]`, `shape_record` | B-tier 2D cell. `__post_init__` enforces `tier_of(layer) == 'B'`; `add_sharer` requires `occ_type == DEVICE_DIFF`. |
| `Device` | `inst_name`, `dev_type`, `nfin`, `nf`, `pins`, `bbox_nm`, `fin_track_indices`, `gate_track_idx` | Per-device topology metadata from the Calibre device query. |
| `Net` | `name`, `net_type`, `pins`, `segments[]`, `vias[]` | Logical net + its routed geometry. |
| `LayoutModel` | `devices[]`, `nets{}`, `shape_pool[]`, `cell_name`, `cell_width_nm`, `cell_height_nm` | Top-level container. `shape_pool` is the M3 truth source; `nets` is back-compat. |

`LayoutModel.annotation_coverage()` returns per-layer `{total, annotated, unannotated}` — emitted as `output/annotation_coverage.txt` after every pipeline run.

## 6. Configuration & tech bundle

The tech bundle is **composable** — three YAML files, none mandatory by itself, all reachable through one site-config pointer.

```
tech/
├── site_config.yaml   # ← edit per-experiment; paths only
│     │
│     ├─ tech.drc_rules         → tech/drc_rules.yaml
│     ├─ tech.layer_map         → tech/layer_map.yaml
│     ├─ tech.layermap_override → optional foundry .layermap (gds-pair only)
│     ├─ inputs.{original_cdl, modified_cdl, device_query, net_query,
│     │          bbox_by_layer, layout_json, target_json, target_gds}
│     └─ output.dir
│
├── drc_rules.yaml   # Unified rule-record format (see § 8 below)
└── layer_map.yaml   # Per-layer records (see § 7 below)
```

**Loading** (`tech/config_loader.py`):
- `load_tech_config()` — defaults to the two YAMLs next to it. Returns a `TechConfig` whose properties (`FIN_PITCH`, `LI_MIN_SPACING`, `VIA0_ENC_BY_LI_X`, `LAYER_MAP`, ...) resolve through the rule-id index and layer-record index.
- `load_site_config(path)` — returns a parsed dict with all path-valued fields resolved relative to the YAML.
- `load_tech_config_from_site(path)` — one-liner for the pipeline: reads the site config, loads the referenced tech YAMLs.

**`pipeline/run_mvp.py --config <site_config.yaml>`** is the production iteration loop:
1. Edit one YAML on the production box.
2. Run pipeline; observe phenomenon (logs / output PNGs / report text).
3. Send phenomenon back; updated code ships.
4. Drop in updated code, keep the same `site_config.yaml`, rerun.

**Things deliberately not in config** (extracted from input files):
- Device instance names (`MN0`, `MP0`) — from CDL `.SUBCKT` body.
- Device type — from CDL model name + Calibre `device_type`.
- nfin counts — from CDL diff; no fallback.
- Cell name — from input CDL `.SUBCKT` line; output cell name from output CDL.
- `num_gate_slots` / `np_gap_fins` — only used by the dummy fixture generator; live as inline constants in `dummy/gen_buffer_layout.py`.

**Deferred site-config sections** (see [`backlog.md`](backlog.md) § "Production integration"):
```yaml
# Not yet wired:
# calibre:  { svdb_dir, drc_rules, lvs_rules, ... }
# virtuoso: { lib_name, cell_name, view_name, ... }
```

## 7. Layer stack

### 7.1 Tiers and orientations (from `tech/layer_map.yaml`)

| Layer | GDS | Tier | Orientation | Role | Notes |
|-------|-----|------|-------------|------|-------|
| FIN   | (1, 0)  | A  | H | fin           | Pitch 25 nm |
| POLY  | (2, 0)  | A  | V | poly          | Contacted-poly pitch 54 nm |
| LI    | (3, 0)  | A  | V | interconnect  | Pitch 27 nm (half CPP) |
| M1    | (5, 0)  | A  | H | interconnect  | Pitch 36 nm |
| VIA0  | (4, 0)  | B  | — | via           | `connects: [LI, M1]` |
| OD    | (6, 0)  | B  | — | diffusion     | Owns `shared_with[]` for diffusion sharing |
| NWELL | (7, 0)  | C1 | — | well          | `derived: true` |
| BOUNDARY | (10, 0) | C1 | — | boundary    | `derived: true` |
| CPO / M0_CUT / FIN_CUT | — | B | — | cut | `role: cut`, GDS pair pending fixtures |
| VT / PP / NP / DNW | — | C1 | — | marker | `derived: true`, geometry pending |
| DIODE / ESD / TEXT | — | C2 | — | annotation | Direct-edit, never CSP |

V layers: pitch defines X spacing, tracks run along Y. H layers: pitch defines Y spacing, tracks run along X. LI pitch = half gate pitch so it can land on both S/D and gate-contact x positions.

### 7.2 Module-level constants

`tech/layer_map.py` loads `layer_map.yaml` at import time and exposes the same constants the pre-YAML hardcoded module exposed: `LAYER_MAP`, `GDS_TO_LAYER`, `LAYER_COLORS`, `LAYER_TIER`, `TIERS`, `A/B/C1/C2_TIER_LAYERS`, `CUT_LAYERS`. Plus helpers `tier_of(layer)`, `layers_in_tier(tier)`, `is_cut_layer(layer)`. All existing call sites work unchanged.

## 8. DRC rule encoding

`tech/drc_rules.yaml` uses an **ASAP7-inspired unified rule-record format**. Every rule is one record under `rules:` with the same five fields:

```yaml
- id:        FIN.P.1                    # <LAYER>.<TYPE_CODE>.<NUM>
  type:      min_pitch                  # one of: min_pitch | min_width | min_spacing |
                                        #         min_enclosure | min_extension | exact_size
  layers:    [FIN]                      # 1 entry for single-layer; 2 for enclosure / extension
  value_nm:  25                         # scalar — OR — {x: ..., y: ...} for axis-keyed
  severity:  critical                   # critical | recommended | advisory

# axis-keyed value:
- id: V0.E.LI
  type: min_enclosure
  layers: [VIA0, LI]                    # [inner, outer]
  value_nm: {x: 1, y: 5}
  severity: critical

# extension with condition:
- id: NWELL.X.FIN
  type: min_extension
  layers: [NWELL, FIN]                  # [outer, anchor]
  value_nm: 30
  severity: critical
  condition: {fin_role: pmos}
  notes: "NWELL extends ≥30nm past topmost PMOS fin (consumed by drc_derivator)"
```

ID convention: `<LAYER>.<TYPE_CODE>.<NUM>` — type codes `P` (pitch), `W` (width), `S` (spacing), `E` (enclosure), `X` (extension), `SZ` (size). The flat list-of-records is parser-friendly so a foundry DRM PDF can be lifted into this format with a small extraction script.

`TechConfig` properties resolve through this rule index — `config.LI_MIN_SPACING` reads rule `LI.S.1`, `config.VIA0_ENC_BY_LI_X` reads rule `V0.E.LI` axis `x`, etc. Property names are unchanged from the pre-config-consolidation API (PR #19); rule-id resolution is internal.

### 8.1 CSP DRC subset (today)

Three rule families implemented in `core/drc_constraints.py`:

1. **Same-layer same-track spacing** (LI / M1) — `SameLayerAlongTrackSpacing(layer, spacing_ortho)`. Stencil `[(layer, 0, ±1)]`.
2. **Same-layer adjacent-track spacing** (M1) — `SameLayerMinSpacing(layer, spacing_tracks)`. Stencil `[(layer, ±1, 0)]`.
3. **B-tier same-layer spacing** (OD / VIA0) — same templates as above, with `trigger_types=(DEVICE_DIFF,)` for OD and `(VIA,)` for VIA0 (M4e).

Rules NOT yet in CSP (but in the YAML, used by the writeback path):
- VIA0 enclosure by LI / M1 — currently checked by KLayout DRC.
- End-of-line spacing.
- LI cross-track spacing — not relevant for resize.
- Multi-patterning coloring.

Adding a new CSP rule:
1. Subclass `DRCConstraintTemplate` in `core/drc_constraints.py`.
2. Define `trigger()` and `forbidden_states()` methods.
3. Set `anchor_layer` to scope the firing layer.
4. Register in `create_mvp_drc_rules()`.

## 9. Calibre data formats

The pipeline today consumes three JSON artifacts produced by `dummy/gen_buffer_layout.py`. In production these are produced by Calibre SVDB queries (see § 10).

### `calibre_device_query.json`

```json
[
  { "instance":   "MN0",
    "device_type": "NMOS",
    "parameters":  { "nfin": 5, "nf": 1, "l": 20, "w": 125 },
    "pins":        { "G": "IN", "D": "OUT", "S": "VSS", "B": "VSS" },
    "bbox":        { "x1": 27, "y1": 28, "x2": 81, "y2": 152 },
    "fin_y_positions": [40, 65, 90, 115, 140] }
]
```

Consumer: `io_adapters/parser.py::parse_calibre_device_query` → builds `Device`. Provides `nfin` / `gate_track_idx` / `fin_track_indices` topology metadata for resize.

### `calibre_net_query.json`

```json
{ "VSS": { "type":  "power",
           "pins":  [["MN0", "S"], ["MN0", "B"]],
           "shapes": [{ "layer": "LI", "x1": 18, "y1": 13, "x2": 35, "y2": 145, "desc": "li_nmos_source" }] } }
```

Consumer: `parse_calibre_net_query`. Each shape passes through `MultiLayerGrid.physical_to_segment_coords` to become a `TrackSegment` and attaches to `Net`. This is how the CSP solver learns about routed geometry.

### `bbox_by_layer.json`

```json
{ "FIN": [{ "x1": 0, "y1": 37, "x2": 108, "y2": 44, "net": "", "desc": "nmos_fin_0" }] }
```

Consumer: `parse_bbox_by_layer`. The geometric-truth pass (M3): every entry becomes a `ShapeRecord` with `net_id=None` until LVS overlay stamps it.

### `iXref.temp` and `ixref.yaml`

Calibre HDB ``INSTANCE XREF WRITE`` output (file format 1):

```
# SVDB: Instance Cross Reference (ixf) (File format 1)
# SVDB: Layout Primary INV_N5_P7
# SVDB: ...
# SVDB: End of header.
INV_N5_P7 4 INV_N5_P7 4
0 M0 0 MN0
0 M1 0 MP0 X
```

Header lines start with ``# SVDB:`` and terminate with ``# SVDB: End of header.``. The first body line is the cell summary (``<layout_cell> <layout_pin_count> <source_cell> <source_pin_count>``); subsequent lines are device rows (``<layout_idx> <layout_inst> <source_idx> <source_inst> [X]`` — trailing ``X`` flags an LVS-detected S/D swap on MOS devices).

Producer (production): `io_adapters/calibre_query.py::run_calibre_ixref` spawns ``calibre -query <svdb_dir>``, streams ``INSTANCE XREF WRITE <path>`` + ``EXIT`` over stdin, captures stdout/stderr, and raises informative errors on missing binary / non-zero exit / missing output file. Producer (dummy): the file is pre-staged at `dummy/fixtures/iXref.temp` (also reproducible from `dummy/gen_buffer_layout.py::generate_calibre_ixref` for parametric regen).

Consumer: `parse_ixref` returns ``{cell, devices, header_lines}``; ``write_ixref_yaml`` serializes the same structure as ``output/ixref.yaml`` (also committed at `dummy/fixtures/ixref.yaml` as a byte-golden reference). The middle file is reserved for future LVS feedback closure (M7) — net-equivalence overrides for swapped S/D, layout-vs-source device-identity reconciliation. Stage 2's `build_layout_model` does not consume it today.

## 10. Production integration model

The `core/` directory does not change for production. Integration touches three seams: tech bundle, IO adapters, and tooling scripts.

### 10.1 What's pure config (one-file edit)

The single editable file is `tech/site_config.yaml` (§ 6). It points at `drc_rules.yaml` + `layer_map.yaml` (which the foundry can supply directly), names the input artifacts, and names the output dir. Most production swaps land entirely in these YAMLs.

### 10.2 What's adapter (Python edit, not config)

- **`io_adapters/parser.py`** — actual Calibre SVDB query JSON may differ in keys / units (μm vs nm, hierarchical net names, missing `fin_y_positions`). The parser is the right place for format-tolerant fixes; format drift larger than key-renames will need a `format:` block in `site_config.yaml` (proposed in [`backlog.md`](backlog.md)).
- **`io_adapters/cdl_parser.py`** — production CDL may have line continuations, multi-line params, and per-foundry SPICE flavours.

### 10.3 What's tooling (deferred — M7)

- **`scripts/virtuoso_apply_edit.il`** — SKILL placeholder. Production needs real `_removeShapeByBBox` / `_resizeShapeByBBox` implementations bound to the foundry PDK. See [`backlog.md`](backlog.md) § M7.
- **`scripts/calibre_run_drc.sh` / `calibre_run_lvs.sh`** — production needs the actual `calibre` invocation lines uncommented and parameterised.
- **iXref query (Stage 1.5) — landed 2026-05-07.** `io_adapters/calibre_query.py::run_calibre_ixref` runs the `calibre -query <svdb_dir>` subprocess for real (full Popen + stdin scripting + timeout + missing-binary diagnostics). The dummy/real switch lives in `tech/site_config.yaml::calibre.mode` (CLI override: `--lvs-mode {dummy,calibre}`). Replaces the previous shell-script seam.

### 10.4 Known format risks for first production run

- Calibre coordinates may be microns, not nm.
- Pin names may be case-sensitive.
- Net names may include hierarchy separators.
- Fin Y positions may not be explicit (derive from OD + fin pitch).

Validation checklist: (1) Calibre query scripts produce valid JSON; (2) parser correctly maps to `LayoutModel` (compare to manual inspection); (3) grid visualization matches Virtuoso; (4) CSP loads without violations; (5) resize produces correct edit list; (6) SKILL executes; (7) post-edit DRC clean; (8) post-edit LVS matches.

## 11. Validation strategy

- **Golden-diff baseline.** The MVP buffer-resize output is the M0 baseline. Every subsequent milestone preserves byte-level identity for the buffer-resize case unless explicit sign-off is recorded in [`changelog.md`](changelog.md). See M2's "report evolves intentionally" precedent and M4d's 1 nm cosmetic FIN-bbox shift.
- **Conflict-injection harness.** Active from M2 (LI-vs-VIA collision), M3 (unannotated LI stub blocking a resize path), M4 (OD-share, LI fanning across multiple S/D cells, CPO cutting a net), M6 (diffusion share + split + cut sequencing); planned for M7 (DRC violation injection).
- **Performance instrumentation.** From M4e, `core/csp_engine.py::propagate_stats` records `{calls, cells_visited, time_ns}` per layer. `get_propagate_stats()` and `reset_propagate_stats()` are the query API.
- **Multi-device regression.** Planned from M6d — extend `dummy/gen_buffer_layout.py` to inverter / 2-stage buffer / latch.
- **Real-PDK closure.** First exit from dummy environment happens in M7.

## 12. Key file index

- `pipeline/run_mvp.py` — pipeline orchestration; `--config <site_config.yaml>`, `--lvs-mode {dummy,calibre}`.
- `io_adapters/calibre_query.py` — `parse_ixref`, `write_ixref_yaml`, `run_calibre_ixref`, `run_dummy_ixref`, `extract_ixref` (Stage 1.5).
- `core/solver.py` — `LayoutSolver`, `setup_engine`, `load_existing_layout`, `load_b_tier_cells_into_engine`, `project_unannotated_blockages`, `resize_device` (L3 macro).
- `core/data_model.py` — `ShapeRecord`, `TrackSegment`, `CellOccupancy`, `Device`, `Net`, `LayoutModel`.
- `core/grid.py` — `LayerGrid`, `MultiLayerGrid` (track grids + B-tier cell grids).
- `core/csp_engine.py` — `ConstraintEngine`: `propose_assign` / `propose_release` / `commit_with_full_delta` / `restore`, union-find (`union`, `net_of`, `connected_to`, `connected_cells`, `mark_cut`, `mark_blockage`), `propagate_stats`.
- `core/drc_constraints.py` — DRC constraint templates + `create_mvp_drc_rules`.
- `core/atomic_ops.py` — L2 atomics: `assign/release/modify_segment`, `add/remove_cut_cell`, `mark_shared_diffusion`, `extend_od`, `add/remove_fin_strip`, `extend_poly`.
- `core/decoder.py` — `WritebackDecoder.apply` (L1 → shape dict); `DerivedShapeEditError`.
- `core/drc_derivator.py` — `DRCDerivator.derive_c1` (NWELL / BOUNDARY).
- `core/diff.py` — `EditOp`; `diff_to_edit_ops`.
- `core/macros/` — L3 macro family (`cut_ops`, `share_diffusion`, `split_diffusion`, `pick_macro`).
- `io_adapters/parser.py` — `build_shape_pool`, `apply_lvs_overlay`, `project_b_tier_shapes`, `build_layout_model`.
- `io_adapters/cdl_parser.py` — `parse_cdl`, `diff_cdl`, `get_device_param`.
- `io_adapters/gds_io.py` — `write_gds`, `read_gds`, `compare_gds`, `gds_to_bbox_by_layer`.
- `io_adapters/writer_cdl.py` — `write_cdl`.
- `io_adapters/writer_skill_script.py` — SKILL emitter (placeholder).
- `tech/site_config.yaml`, `tech/drc_rules.yaml`, `tech/layer_map.yaml` — composable tech bundle.
- `tech/config_loader.py` — `TechConfig`, `load_tech_config`, `load_site_config`, `load_tech_config_from_site`.
- `tech/layer_map.py` — YAML-loaded constants (`LAYER_MAP`, `LAYER_TIER`, `tier_of`, ...).
- `dummy/gen_buffer_layout.py` — fixture generator (production-irrelevant).
