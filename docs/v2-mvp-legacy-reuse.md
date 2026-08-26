# Layauto v2 MVP legacy reuse whitelist

> Status: implementation policy for coding agents.  
> Review basis: `main@b847535d8190160031f794191a2a684a888122b6` (2026-08-25).  
> Architecture source of truth: [`architecture.md`](architecture.md). This document narrows the code-reuse choices allowed for the first v2 MVP; it does not redefine the target architecture.

## 1. Decision

The first v2 MVP may reuse legacy **evidence-format knowledge, parser algorithms, IO mechanics, configuration data seeds, and parser test vectors only**. No legacy planning, state ownership, constraint/CSP, mutation, transaction, decoder, or pipeline logic is approved for code reuse.

`legacy_mvp/` is reference material, never a runtime dependency:

- `layauto_v2/**` must not import `legacy_mvp`, add it to `sys.path`, or call it through a subprocess.
- Approved code must be moved into the matching v2 module and changed to the v2 interface; do not create a compatibility façade around legacy state.
- The tables below are an allowlist. An unlisted file or symbol is `REJECT` by default.
- An exception requires an explicit review and an update to this file before implementation.

## 2. Meaning of each disposition

| Disposition | Coding-agent rule |
|---|---|
| `REUSE` | The named test data may be copied unchanged. No production Python module is approved for unchanged reuse in this review. |
| `ADAPT` | Port only the named symbol or algorithm into the stated v2 module. Change its API, validation, result types, and tests as required below. Never import the legacy module at runtime. |
| `REWRITE` | Use the named behavior, file format, or test case as a reference only. Implement from the v2 contract; do not copy the legacy implementation wholesale. |
| `REJECT` | Do not use in the v2 MVP. It remains archaeology only. |

## 3. Effective first-MVP profile

The broader architecture supports later extensions. The first coding slice is deliberately narrower:

- One cell and one existing MOS device per run.
- Exactly one typed `nfin` shrink intent; any second delta, grow, add/remove, topology change, rename, or routing intent fails before Stage 5.
- The physical edit is an OD active-coverage shrink. FIN is a static backdrop.
- All non-OD drawn geometry and all top-level pins are frozen in this slice. If LI/VIA0/M1/cut repair is required, the candidate is rejected; the MVP does not silently perform routing repair.
- Candidate generation is deterministic and template/policy based, using the gap-side OD edge. No general MILP, global router, or legacy CSP search is part of this slice.
- Failure is atomic and structured; a failed run leaves the pre-intent state unchanged.

Minimum post-commit invariants are: target `Device.nfin` is committed; active-fin attribution agrees with `FIN ∩ OD ∩ device attribution`; FIN and every frozen layer are unchanged; top-level pins are unchanged; exported artifacts are derived only from the committed snapshot.

## 4. Production-code whitelist

### 4.1 CDL input and intent extraction

| Legacy location | Disposition | v2 destination | Required change |
|---|---|---|---|
| `legacy_mvp/io_adapters/cdl_parser.py::_parse_value` | `ADAPT` | `layauto_v2/importers/cdl.py` | Use full-token parsing, explicit suffix rules, deterministic numeric representation, and structured format errors. Do not silently return an arbitrary string where a numeric parameter is required. |
| `legacy_mvp/io_adapters/cdl_parser.py::parse_cdl` | `ADAPT` | `layauto_v2/importers/cdl.py` | Preserve tokenization ideas only. Add continuation/comment handling, duplicate and malformed-row checks, explicit subckt selection, source locations, and typed normalized evidence. Do not hard-code one MOS-only grammar as the general contract. |
| `legacy_mvp/io_adapters/cdl_parser.py::diff_cdl` | `REWRITE` | Stage-2 intent normalization, principally `layauto_v2/domain/intent.py` | Produce exhaustive typed deltas. The legacy function silently ignores device add/remove, topology/model/port changes, and missing devices; that behavior is forbidden. Capability coverage must reject every non-MVP delta before mutation. |
| `legacy_mvp/io_adapters/cdl_parser.py::get_device_param` | `REJECT` | — | Replace ad-hoc lookup with typed `CircuitIR` queries and explicit missing/duplicate-identity errors. |

### 4.2 GDS and bbox IO

| Legacy location | Disposition | v2 destination | Required change |
|---|---|---|---|
| `legacy_mvp/io_adapters/gds_io.py::{read_gds,_read_gds_gdstk,gds_to_bbox_by_layer}` | `ADAPT` | `layauto_v2/importers/gds.py` | Require explicit top-cell/hierarchy policy; preserve unknown layers, purpose/datatype, polygons or an explicit bbox approximation flag, source identity, DBU/unit, and deterministic order. Remove integer rounding in library user units and legacy layer-map globals. |
| `legacy_mvp/io_adapters/gds_io.py::{write_gds,_write_gds_gdstk,_write_gds_manual}` | `REWRITE` | `layauto_v2/export/gds.py` | Serialize an immutable snapshot. Cell identity, DBU, hierarchy, layer-purpose mapping, and unknown-shape preservation come from evidence/config, not `nmos_nfin`/`pmos_nfin` fields or hard-coded inverter names. Do not keep the manual writer as a production fallback. |
| `legacy_mvp/io_adapters/gds_io.py::compare_gds` | `REWRITE` | `layauto_v2/validation/golden.py` | Compare canonicalized geometry with multiplicity, polygon/hierarchy/unit policy, and structured mismatches. A set of rectangle bboxes is not sufficient. |
| `legacy_mvp/io_adapters/parser.py::parse_bbox_by_layer` | `REWRITE` | `layauto_v2/importers/gds.py` | Implement a versioned, validated bbox-evidence schema. Do not import `parser.py`: importing it also pulls legacy `core`, grid, and state classes. Ignore legacy `net`/`desc` convenience fields as identity truth. |

### 4.3 Calibre/LVS evidence

| Legacy location | Disposition | v2 destination | Required change |
|---|---|---|---|
| `legacy_mvp/io_adapters/calibre_query.py::{parse_ixref,parse_nxref}` | `ADAPT` | `layauto_v2/importers/calibre.py` | Keep strict header/body parsing and S/D-swap capture. Return typed evidence with schema version, raw-capture reference/hash, parser version, line-localized errors, and duplicate/identity consistency checks. |
| `legacy_mvp/io_adapters/calibre_query.py::{parse_net_names,join_net_xref}` | `ADAPT` | `layauto_v2/importers/calibre.py` | Require `END OF RESPONSE`; reject duplicate or ambiguous indices/names; validate cell/count consistency; retain layout, LVS, and schematic identities separately. |
| `legacy_mvp/io_adapters/calibre_query.py::{parse_device_info,parse_net_shapes}` and `_looks_like_*` helpers | `ADAPT` | `layauto_v2/importers/calibre.py` | Preserve raw vertices, precision/unit, opaque metadata, layer-block diagnostics, and terminator checks in memory/evidence provenance. Treat “last metadata line is the seed layer” and count-line heuristics as an explicit dialect, not a universal Calibre fact. Reject zero precision and malformed/ambiguous blocks. |
| `legacy_mvp/io_adapters/calibre_query.py::{_extract_net_names_block,_extract_device_info_block,_extract_net_shapes_block}` | `ADAPT` | Calibre tool-adapter portion of `layauto_v2/importers/calibre.py` | Return bounded raw captures plus diagnostics; never turn missing openers/terminators into a pass. |
| `legacy_mvp/io_adapters/calibre_query.py::{run_calibre_*,extract_*}` | `REWRITE` | Calibre tool-adapter portion of `layauto_v2/importers/calibre.py` | Separate runner, parser, and bundle assembly. Use a run-owned working directory, configurable command dialect, structured `ToolResult`, timeout/license/format-drift categories, redacted command/provenance, and atomic raw-capture publication. Do not delete a user-supplied pre-existing output to prove freshness. |
| `legacy_mvp/io_adapters/calibre_query.py::{run_dummy_*,write_*_yaml}` | `REWRITE` | fixture loader plus normalized-evidence serializer | Dummy mode reads the same raw schema as production and is explicit in run policy. Normalized output must carry schema version, units/precision, raw reference/hash, parser version, and issues. It may store bbox-only geometry only when the raw capture is retained and linked. |

### 4.4 Configuration and layer mapping

| Legacy location | Disposition | v2 destination | Required change |
|---|---|---|---|
| `legacy_mvp/tech/config_loader.py::load_site_config` path-resolution idea | `ADAPT` | `layauto_v2/importers/config.py` | Keep resolution relative to the declaring file, but use immutable typed schemas, validate unknown/missing keys and paths by mode, and never default silently to dummy evidence. Do not mutate the parsed YAML with `setdefault`. |
| `legacy_mvp/tech/config_loader.py::{TechConfig,load_tech_config,get_tech_config,load_tech_config_from_site}` | `REWRITE` | `layauto_v2/importers/config.py` plus typed config records | Remove global mutable caching and the legacy compatibility-property API. Validate schema versions, rule/layer uniqueness, units, `ortho`, axes, via `connects`, edit/derivation policies, and cross-file references before Stage 2. |
| `legacy_mvp/tech/layermap_parser.py::parse_layermap` | `ADAPT` (deferred unless the MVP fixture needs an override) | `layauto_v2/importers/config.py` | Add dialect selection, duplicate detection, quoted/purpose handling, source locations, and hard errors instead of silently skipping malformed rows. |
| `legacy_mvp/tech/layer_map.py` | `REWRITE` | loader in `layauto_v2/importers/config.py`; immutable lookup/overlay records in `layauto_v2/annotation/layer_map.py` | Do not load YAML at import time or preserve module-level globals. The legacy A/B/C comments and `derived` flag do not encode the v2 edit/derivation policies completely. |

### 4.5 Export-only helpers

| Legacy location | Disposition | v2 destination | Required change |
|---|---|---|---|
| `legacy_mvp/io_adapters/writer_cdl.py` | `REWRITE` | `layauto_v2/export/cdl.py` | Serialize committed semantic IR for the selected cell; do not hard-code inverter instances, ports, model names, or both MOS parameters. |
| `legacy_mvp/io_adapters/writer_skill_script.py` | `REJECT` | Fresh implementation in `layauto_v2/export/skill.py` when needed | It consumes legacy `EditOp`, hard-codes an inverter, and its locate/resize helpers only print. It cannot be an MVP success path. |

There is no approved unchanged production-code `REUSE` entry. This is intentional: even the useful parser code needs v2 schemas, provenance, and error semantics.

## 5. Configuration and fixture-data whitelist

| Legacy location | Disposition | Allowed use and limits |
|---|---|---|
| `legacy_mvp/dummy/fixtures/{iXref.temp,nXref.temp,net_names.txt,device_info_M0.txt,device_info_M1.txt,net_shapes_*.txt}` | `REUSE` | Exact synthetic parser test vectors for the dialect they encode. Label them `synthetic_generated`; they are not proof of real-Calibre compatibility or correct effective-region semantics. |
| `legacy_mvp/dummy/fixtures/{ixref.yaml,net_xref.yaml,device_info.yaml,net_shapes.yaml}` | `ADAPT` | Expected-value seeds only. Regenerate under the v2 schema; do not copy as canonical normalized evidence because schema/provenance/unit metadata are incomplete. |
| `legacy_mvp/dummy/fixtures/{buffer_original.cdl,buffer_original.gds,bbox_by_layer.json}` | `ADAPT` | Legacy regression seed for Stage-1 parsers. The bbox JSON must be regenerated from GDS and must not supply net/device identity. Known rounding, spacing, enclosure, dummy-gate, and naming limitations remain explicit. |
| `legacy_mvp/dummy/fixtures/{buffer_target.cdl,buffer_target.gds,buffer_target.json}` | `REWRITE` | Do not use as the first-MVP acceptance target: it changes both MOS devices and the subckt identity, and its FIN geometry follows legacy semantics. Create a one-device, shrink-only target with the cell-identity policy made explicit and all frozen layers unchanged. |
| `legacy_mvp/tech/drc_rules.yaml` | `ADAPT` | Dummy rule-data seed only. Add schema version/units and coverage metadata; do not present the limited academic/dummy values as a production deck. |
| `legacy_mvp/tech/layer_map.yaml` | `ADAPT` | Schema/data seed only. Add `purpose`, `ortho`/axes, explicit `edit_policy` and `derivation_policy`, and cross-file validation. FIN must be static/no-direct-edit; C1 markings must be post-commit-derived. |
| `legacy_mvp/tech/calibre_layer_map.yaml` | `ADAPT` | Dialect seed only. Resolve `V0`/`VIA0`, `GATE`/`POLY`, `ACTIVE`/`OD`, top-level schema, aliases, carries, and every `[VERIFY]` entry before production use. |
| `legacy_mvp/tech/site_config.yaml` | `REWRITE` | Use only as a list of required path categories. Remove legacy JSON inputs, Stage 1.5 naming, implicit dummy default, and target-golden-as-truth semantics. |
| `legacy_mvp/dummy/gen_buffer_layout.py` | `REJECT` as a correctness oracle | It may explain how old fixtures were produced, but its per-device FIN generation, rounding, dual-device target, and DRC gaps must not define the v2 fixture. |
| `legacy_mvp/dummy/gds_writer.py` | `REJECT` for v2 | Rectangle-only, write-only fixture utility; use the v2 GDS adapter or a captured tool artifact instead. |

## 6. Test reuse

The useful test asset is the **case**, not the legacy module graph.

Port selected positive and negative cases from `legacy_mvp/tests/unit/test_calibre_query.py` for:

- header/anchor/terminator validation;
- S/D swap and renamed/renumbered identity;
- malformed counts, rows, vertices, and truncated captures;
- multiple shapes/layers and unit conversion;
- missing binary, timeout, non-zero exit, missing output, and response-block extraction.

Change or drop these legacy expectations:

- `test_parse_net_names_no_terminator_uses_count`: v2 must return an evidence-format failure.
- tests that only assert normalized YAML drops metadata/vertices: replace them with checks for the chosen normalized schema **and** a valid raw-capture/hash/provenance backlink.
- `test_pipeline_legacy_site_config_without_calibre_block`: v2 must not preserve implicit legacy/dummy compatibility.
- parser/tier, solver, macro, decoder, occupancy, and round-trip tests that assert legacy state ownership or FIN editing are not portable.

Raw fixture parity is necessary but not sufficient. Add separate tests for a real or sanitized Calibre capture when one becomes available; until then, mark the dialect check `synthetic`, never `signoff-pass`.

## 7. Explicit default-deny areas

The following are outside the whitelist even if a small helper appears locally useful:

- `legacy_mvp/core/**`: data model, grid, CSP engine, solver, atomic/macro operations, decoder, diff, DRC derivator, and legacy rule predicates.
- `legacy_mvp/pipeline/**`: orchestration, writeback, debug, and verification flow.
- `legacy_mvp/io_adapters/parser.py` except the format knowledge explicitly marked `REWRITE` above.
- `legacy_mvp/scripts/**`: current Calibre scripts are TODO/placeholders or unstructured command wrappers.
- `legacy_mvp/visualization/**`, `legacy_mvp/output/**`, and legacy generated targets.
- Any `legacy_mvp/tests/**` assertion whose expected behavior depends on `EditOp`, mutable grid/engine ownership, stored `Net.segments`/`Net.vias`/`Device.fin_track_indices`, Stage-6 writeback, or direct FIN edits.

Concepts may still inform review, but no code from these locations may be copied into the MVP without first changing this allowlist.

## 8. Coding-agent procedure

For every proposed legacy-derived implementation:

1. Locate the exact path and symbol in Section 4 or 5. If absent, stop and request a whitelist update.
2. Record the disposition and v2 destination in the task/PR description.
3. Implement inside `layauto_v2/`; never add a legacy runtime dependency.
4. Add characterization tests using approved raw captures, then add v2-contract tests that do not depend on legacy outputs.
5. Return typed data and typed failures; no silent fallback, stdout-only success, or convenience-field truth.
6. Verify architecture boundaries before merge.

Minimum automated boundary checks:

- no import or runtime path reference from `layauto_v2/**` to `legacy_mvp/**`;
- no `sys.path` mutation in v2;
- importers do not construct occupancy, segments, vias, fin attribution, candidates, or transactions;
- exporters and validators accept immutable snapshots and cannot call mutable state APIs;
- normalized evidence includes schema/provenance/unit information and links to retained raw captures;
- missing/ambiguous Calibre terminators, identities, layer mappings, or units produce structured failures;
- a non-MVP CDL delta fails before any transaction opens;
- FIN, frozen-layer, pin, and pre/post rollback hashes enforce the first-MVP profile.

## 9. Architecture review findings and alignment

The v2 target architecture is directionally sound: its Stage 1/2 separation, GDS/CDL/Calibre fact split, single-state ownership goal, planning-before-commit rule, and read-only Stage 6 boundary are the right basis for this whitelist. This review applies the implementation-boundary clarifications to `architecture.md` and records the remaining design recommendations here:

| Status | Finding | Resolution / recommendation |
|---|---|---|
| Applied | The target architecture and the first implementation slice were interleaved; Sections 1.4, 7.3, and 7.4 allowed a broader resize/repair reading. | `architecture.md` now identifies the first-MVP profile explicitly: one device, one shrink intent, OD-only drawn edit, all other geometry/pins frozen, repair-required candidate fails, deterministic policy. Routing repair remains a later target capability. |
| Next fixture task | The committed legacy target changes `MN0` and `MP0`, changes the subckt name, and embodies legacy FIN behavior. | Create a new v2 fixture/target for one MOS shrink. Keep cell identity unchanged unless cell rename is separately modeled as a supported intent. |
| Applied | Architecture Sections 6.7, 9.2, 11.3, and 11.13 permitted broad categories such as geometry helpers, rule predicates, and trail ideas, which an agent could over-read as approval of `legacy_mvp/core/**`. | `architecture.md` now points to this concrete default-deny allowlist and states that this review approves no legacy core symbol. Future exceptions require symbol-level review. |
| Applied | `layauto_v2/legacy/` was shown as an optional package while the actual legacy tree is root-level `legacy_mvp/`. | `architecture.md` now states that the optional package is not instantiated for the first MVP. Root `legacy_mvp/` remains reference-only and non-importable from the v2 main path. |
| Recommended next | Typed failures are required throughout but no single MVP taxonomy is canonical. | Define at least `UNSUPPORTED_INTENT`, `INVALID_INTENT`, `EVIDENCE_INCOMPLETE`, `NO_CANDIDATE`, `CONSTRAINT_VIOLATION`, `TRANSACTION_ABORTED`, `EXPORT_FAILURE`, and `VALIDATION_FAILURE`, each with stage, stable code, object/evidence references, details, and state-unchanged status. |
| Recommended next | `layout_store` and `occupancy` are both described as authoritative working state, which can still be implemented as two independently mutable truths. | Define one aggregate `LayoutState` transaction owner and a publish-time invariant such as `project(layout_store, coordinate_system) == occupancy`; neither child store may commit independently. |

`architecture.md` remains authoritative for the long-term module and state boundaries; this file is the concrete default-deny source-selection policy for legacy-derived MVP work.
