# Stage 5 (execute resize) — redesign proposal

> Scope: **only** Stage 5 of the flow (`docs/flow.md` §7), i.e. the L4→L3→L2→L1
> resize chain `pick_macro → resize_device → atomic_ops → EditOp`.
> This document records the current behaviour, the root-cause correctness
> problem, the recommended placement model, a staged plan, and the
> backlog impact. It does **not** change core code; it is the design
> contract a follow-up implementation PR executes against.
>
> Decision recorded here: adopt **Model A (fixed cell frame)**. Rationale
> and the rejected alternative (Model B, shrink-to-fit) are in §5.

---

## 1. Headline finding

The current Stage 5 resize is **electrically equivalent but
geometrically incoherent**: the output matches neither the architecture's
own stated scope ("cell boundary fixed / M1 routing positions don't
change / cell-height changes not in scope" — `architecture.md` §1) nor the
from-scratch `dummy/fixtures/buffer_target`. Measured on the live
fixture (NMOS 5→4, PMOS 7→6), **12 of 30 shapes (40%) diverge** from the
target, across FIN/OD/POLY/LI/VIA0/M1/NWELL/BOUNDARY. The pipeline only
*prints* a mismatch count (`pipeline/run_mvp.py:635`) and never fails — and
that printed count is over a **narrower layer set** than this measurement
(see §2).

The root cause is not a bug in a single helper — it is that **Stage 5 has
no coherent "layout placement model."** The fix is to establish the
correct model and rebuild the L3→L2→L1 chain around it.

---

## 2. Evidence

`output/buffer_resized.json` vs `dummy/fixtures/buffer_target.json`
(measured), plus the from-scratch reference:

| | NMOS fins | PMOS fins | cell_height | VDD rail |
|---|---|---|---|---|
| original (5,7) | [40,65,90,115,140] | [240,265,290,315,340,365,390] | 430 | 414 |
| **current resize out** | [40,65,90,115] ✓ | **[240,265,290,315,340,365]** | **405** | **414** |
| from-scratch target (4,6) | [40,65,90,115] | **[215,240,265,290,315,340]** | **380** | **378** |

All three differ. Per-layer mismatch (resized vs target), 12 shapes:
`FIN 1, OD 1, POLY 3, LI 3, VIA0 1, M1 1, NWELL 1, BOUNDARY 1`.

> **This 12-of-30 is an all-layer manual measurement** (every layer in the
> JSON, NWELL/BOUNDARY included) — it is **not** the pipeline's printed
> `mismatches`. That printed count compares a narrower set: the `compare_gds`
> path covers `FIN/OD/POLY/LI/VIA0/M1` (`pipeline/run_mvp.py:613`) and the
> JSON fallback only `FIN/OD/LI/VIA0/M1` (`:624`) — both **omit
> NWELL/BOUNDARY** (the fallback also omits POLY). So the exact frame-drift
> Model A must eliminate (NWELL/BOUNDARY/cell-height) is **invisible to
> today's pipeline metric**; step 6 must widen the gate, not just flip
> print→fail.

Config values grounding the geometry (from `tech/drc_rules.yaml`):
`FIN_PITCH=25, OD_EXTENSION_BEYOND_FIN=10, POLY_EXTENSION_BEYOND_OD=15,
NWELL_MARGIN_BEYOND_FIN=30, BOUNDARY_MARGIN_BEYOND_FIN=40,
VIA0_ENC_BY_LI_Y=5, LI_WIDTH=17`.

---

## 3. Current logic recap

| Layer | Entity | Behaviour |
|---|---|---|
| L4 | `core/macros/pick_macro.py` | `nfin` diff → `MacroCall('resize_device')` |
| L3 | `core/solver.py:resize_device:352` | one transaction, 5 sub-actions |
| L2 | `core/atomic_ops.py` | `remove_fin_strip` / `extend_od` / `modify_segment` / `extend_poly` |
| L1 | `core/diff.py:EditOp` | macro builds the final bbox directly |

"Top-down removal" strategy (`core/solver.py:391`):

```python
removed_fin_tracks   = old_fin_tracks[-delta:]   # always the topmost fins
remaining_fin_tracks = old_fin_tracks[:-delta]
```

Emits 7 EditOps: FIN remove ×2, OD modify ×2, LI modify ×2, POLY y2-shift ×1.

---

## 4. Root cause — three incompatible placement models

Walking the live use case (NMOS 5→4, PMOS 7→6):

1. **NMOS is on the bottom (hugs VSS); removing its top fin is correct** —
   NMOS anchored at the bottom, OD retracts toward the gap.
2. **PMOS is on the top (hugs VDD), but the code also removes PMOS's
   "top" fin (390), pushing PMOS away from VDD.** Physically PMOS should
   anchor to VDD and drop the **gap-side (bottom)** fin. This is an
   NMOS/PMOS asymmetry bug, rooted in `dev_type=='nmos'/'pmos'` hardcoding
   in `_emit_poly_modify_if_endpoint_changed` (`core/solver.py:689`) and
   the blanket `old[-delta:]` top-trim.
3. **The code edits "half the frame."** The decoder recomputes
   `cell_height=405` (`core/decoder.py:324`) and the derivator recomputes
   NWELL/BOUNDARY y2, **but M1 rails don't move and the N/P gap isn't
   closed**. The gap goes 100→125 (one fin pitch too wide), the cell is 25
   too tall, and VDD is one M1 pitch off. It is **neither "fixed frame"
   nor "shrink-to-fit"** — it lands in between and matches nothing.

> The two devices are treated as **independent, anchored to absolute Y,
> each trimming its top fin**, with no global model coordinating
> device / gap / rail / frame.

---

## 5. Recommended model — A: fixed frame + static fin + OD-driven + real CSP gating

**Model A:**

- **Frame is fixed**: cell row height, VSS/VDD rails, cell boundary, and
  the whole fin grid do not move. This *is* the architecture's stated
  scope, and it is the hard physical constraint of real standard cells
  (fixed row height so cells abut in a row).
- **Fin is a static backdrop** (= backlog **M8**): resize never deletes a
  fin; "one fewer fin" means OD covers one fewer fin track, and that track
  degrades to a field/dummy fin.
- **Each device anchors to its own rail, grows/shrinks OD from the gap
  side**: NMOS anchors VSS (drop top/gap-side), PMOS anchors VDD (drop
  bottom/gap-side). The anchor direction is **derived from geometry**
  (which rail the device is nearer), not hardcoded to nmos/pmos.
- **OD is the single primary edited layer, routed through the engine**:
  shrink → `propose_release`; grow → `propose_assign` (now the CSP
  actually checks OD–OD cross-gap spacing and VIA0 enclosure). LI/POLY
  endpoints are **derived from the OD extent + via reach**, not recomputed
  by arithmetic in the macro.

**The elegant consequence (verified against config values):** because
each device anchors its rail and the rail-side outermost fin stays put,
the shared POLY's two ends (set by NMOS-bottom and PMOS-top fins)
**don't move**; NWELL (PMOS-top + margin), BOUNDARY, cell_height, and M1
rails **all stay fixed**. So Model A's NMOS 5→4 / PMOS 7→6 resize only
edits **OD (gap-side retract) + the gap-side, non-via-anchored S/D LI
bars** — POLY / NWELL / BOUNDARY / M1 / FIN / cell frame are all reused.
This is *exactly* the project's "incremental, minimal-change, reuse
everything that need not change" thesis, and it edits **less** than today.

Under Model A the target(4,6) becomes NMOS `[40,65,90,115]`, PMOS
`[265,290,315,340,365,390]`, frame unchanged — so resize can reach
**PERFECT MATCH** (once the dummy target is regenerated under Model A;
it currently encodes Model B). Shrink is trivially DRC-safe (gap widens);
grow is where CSP earns its keep.

**Rejected alternative — Model B (shrink-to-fit):** cell shrinks with fin
count, rails/gap follow down (what `dummy/gen_buffer_layout.py` emits
today). It needs no fixture regen, but contradicts the architecture scope
and is physically unplaceable in a standard row (variable height). In a
real flow, drive variants are *different cells of equal height*, not a
height edit — so Model B's "area saving" is illusory. Model A wins on
"basic layout principles / correctness."

---

## 6. Secondary issues to fix during the rebuild

1. **CSP does not gate the resize at all** (most damaging to the project
   thesis). On shrink, `modify_segment` only calls `propose_release`,
   never `propose_assign` (`core/atomic_ops.py:160`), so feasibility never
   fires; OD goes through `extend_od` which **bypasses the engine
   entirely** (mutates `grid.b_tier_cells` + `shape_record` only —
   `core/atomic_ops.py:301`), leaving engine OD cells **stale** after a
   resize. The commit always prints "0 union events." "DRC correctness via
   CSP" is currently a no-op on the resize path.
2. **FIN is treated as editable** (`remove_fin_strip` deletes ShapeRecords
   and emits `remove_shape FIN`). Violates FinFET reality — fins are a
   fixed backdrop, only OD changes. This is backlog **M8**.
3. **Shrink-only** (`new_nfin >= nfin` rejected, `core/solver.py:377`).
   Real ECOs also grow nfin; grow is precisely where CSP must check
   spacing/enclosure.
4. **Geometry hand-computed by arithmetic in the macro** (OD/POLY bboxes
   from config extensions), duplicating the dummy generator's layout
   formula; plus magic numbers like `li_ext_y=5` (`core/solver.py:555`)
   that exist only to match the generator's overshoot — brittle.
5. **`apply_resize_to_model` keeps the first n (bottom) fins** via
   `fin_track_indices[:new_nfin]` (`core/solver.py:739`) — wrong for PMOS,
   and obsoleted once `fin_track_indices` becomes a derived property (M8).
6. **Anchor direction is implicit and dev_type-coupled**, so it won't
   generalise to arbitrary placements (multi-finger, multi-device along X).
   Derive the anchor from geometry instead.

---

## 7. Staged plan (each step independently committable)

| Step | Content | Touches |
|---|---|---|
| 0. decision + fixture | adopt Model A; regenerate `buffer_original/target` under "fixed frame + static fin" (one-time byte-golden churn) | dummy (Stage 5 prerequisite) |
| 1. static FIN | delete the FIN edit path (`_emit_fin_removes` / `remove_fin_strip` / decoder FIN branch); fin becomes a fixed backdrop = **bring M8 forward** | L2/L3/decoder |
| 2. anchor abstraction | introduce an explicit per-device rail anchor (geometry-derived); replace `old[-delta:]` + nmos/pmos hardcoding with "keep rail side, drop gap side" | L3 |
| 3. OD via CSP | route OD coverage changes through `propose_release/assign` so DRC gates them and the engine stays authoritative; derive LI/POLY endpoints from OD + via reach; drop magic numbers | L2/L3 |
| 4. fixed frame | stop editing cell_height / NWELL / BOUNDARY / POLY / M1 on shrink; derivator becomes a no-op for the in-scope shrink (fires only on grow / legitimate frame change) | L3/decoder/derivator |
| 5. grow support | allow `new_nfin > nfin`; OD extends toward the gap, CSP checks spacing/enclosure; surface infeasible cleanly | L3 |
| 6. validation gate | **widen** the target comparison to the full Model-A invariant set (`FIN/OD/POLY/LI/VIA0/M1` **+ NWELL/BOUNDARY + cell frame**), *then* turn it from a print into a **hard gate**. Today's metric omits NWELL/BOUNDARY (and POLY in the JSON fallback), so flipping print→fail alone could report PERFECT MATCH while the frame is still wrong | pipeline tail |

---

## 8. Backlog impact

- **Absorbs and front-loads M8** (static fin) — it is the foundation of
  Model A and should be step 1 of this rebuild rather than a standalone
  milestone.
- **Adds an architecture decision**: pin the resize placement model (A),
  resolving the contradiction where the scope says "fixed frame" but the
  target fixture uses shrink-to-fit.
- **Orthogonal to M9/M11** (representation normalization). The "OD through
  the engine / engine authoritative" piece of step 3 is a minimal slice of
  M11-U1 / M9's writeback loop and can land now without waiting for them.
- **M5 derivator** becomes mostly a no-op under Model A shrink
  (NWELL/BOUNDARY are frame-fixed); keep it for grow / legitimate frame
  changes.

---

## 9. Acceptance (for the eventual implementation PR)

- `nfin 5→4 / 7→6` resize emits **zero FIN EditOps**; output FIN layer is
  byte-identical to input.
- POLY / NWELL / BOUNDARY / M1 / cell frame are unchanged under shrink
  (reused, not re-emitted).
- The engine's OD cells reflect the post-resize coverage (no stale state);
  a grow case is rejected when it would violate OD spacing / VIA0
  enclosure, with a clean infeasible result.
- After regenerating the Model-A fixtures, the pipeline reports
  **PERFECT MATCH** and the comparison is a hard gate **covering the full
  Model-A invariant set** (`FIN/OD/POLY/LI/VIA0/M1` + NWELL/BOUNDARY + cell
  frame), not just the layers the comparison checks today.
