# Layauto correctness audit (2026-05-13)

> **Scope.** Input-side correctness review of everything touching electrical schematics, GDS layout, layer map, and Calibre query fixtures/formats. The resize **output** path (`core/solver.py`, `core/decoder.py`, `core/drc_derivator.py`, `output/buffer_resized.*`) was deliberately excluded from this round and is the obvious next audit.
>
> **Status.** Documentation-only. No code, fixture, golden, or test was changed. Every "Recommendation" below is *deferred* — they are listed so they can be tracked, prioritised, and shipped later. See `backlog.md` "Correctness issues found in audit (2026-05-13)" for the working list.
>
> **Reference values** (from `tech/drc_rules.yaml`, resolved through `tech/config_loader.py`):
>
> | | Pitch | Width | Spacing |
> |---|---|---|---|
> | FIN  | 25 (`FIN.P.1`)  | 7  (`FIN.W.1`)  | — |
> | POLY | 54 (`POLY.P.1`) | 20 (`POLY.W.1`) | — |
> | LI   | 27 (`LI.P.1`)   | 17 (`LI.W.1`)   | 17 (`LI.S.1`) |
> | M1   | 36 (`M1.P.1`)   | 20 (`M1.W.1`)   | 16 (`M1.S.1`) |
> | VIA0 | — | 17×17 (`V0.SZ.1`) | 20 (`V0.S.1`) |
>
> | Extension / enclosure | nm |
> |---|---|
> | OD past FIN (`OD.X.FIN`) | 10 |
> | POLY past OD (`POLY.X.OD`) | 15 |
> | NWELL past topmost PMOS fin (`NWELL.X.FIN`) | 30 |
> | BOUNDARY past topmost PMOS fin (`BOUNDARY.X.FIN`) | 40 |
> | VIA0 enclosed by LI (`V0.E.LI`) | x≥1, y≥5 |
> | VIA0 enclosed by M1 (`V0.E.M1`) | x≥5, y≥1 |
>
> GDS DBU = 1 nm (both `dummy/gds_writer.py:11,129` and the gdstk path `io_adapters/gds_io.py:146` `unit=1e-9, precision=1e-12`). Fixture cell `INV_N5_P7`: NMOS fins at y∈{40,65,90,115,140}, PMOS fins at y∈{240,265,290,315,340,365,390}, cell 108 × 430 nm.

---

## A. Schematic / netlist

### A1 — "buffer" is a misnomer; the fixture is a single CMOS inverter

The repo brands itself "Buffer Fin Resize MVP" but the fixture circuit is one inverter, not a buffer. A CMOS *buffer* is non-inverting (two cascaded inverter stages, 4 transistors); a single-stage inverter computes `OUT = ¬IN`. The fixture has exactly two transistors with both gates tied to `IN` and both drains tied to `OUT` (`dummy/gen_buffer_layout.py:292-318`):

```python
{'name': 'MN0', 'type': 'nmos', 'pins': {'G':'IN','D':'OUT','S':'VSS','B':'VSS'}, ...}
{'name': 'MP0', 'type': 'pmos', 'pins': {'G':'IN','D':'OUT','S':'VDD','B':'VDD'}, ...}
```

The CDL confirms it (`dummy/fixtures/buffer_original.cdl`):

```
.SUBCKT INV_N5_P7 VDD VSS IN OUT
MN0 OUT IN VSS VSS nmos_finfet nfin=5 l=20n
MP0 OUT IN VDD VDD pmos_finfet nfin=7 l=20n
.ENDS INV_N5_P7
```

The cell name `INV_N{n}_P{p}` (`gen_buffer_layout.py:351,471`; also used in `io_adapters/gds_io.py:150,218`), the function `generate_inverter_layout()`, and the module docstring already say "inverter" — they are correct. The mislabels are:

| What | Where | Says |
|---|---|---|
| File names | `dummy/fixtures/buffer_{original,target}.{gds,cdl,json}`, `dummy/gen_buffer_layout.py`, `output/buffer_resized.*` | "buffer" |
| GDS library name | `dummy/gen_buffer_layout.py:347`, `io_adapters/gds_io.py:214` | `BUFFER_LIB` |
| README headline | `README.md:1` | "Buffer Fin Resize MVP" |
| Architecture overview | `docs/architecture.md:9` | "inverter buffer GDS" *(self-contradictory: inverter ≠ buffer)* |
| Changelog M0 | `docs/changelog.md:329` | "Single-cell inverter buffer fixture" *(same)* |

`docs/backlog.md:205` itself distinguishes "inverter / 2-stage buffer / latch" as separate future-work fixtures — confirming the project's own model: the current single-stage thing is the inverter, and a real buffer would be the next step up.

**Recommendation (deferred):** rename "buffer"→"inverter"/"INV" everywhere (file names, `BUFFER_LIB`, README, `architecture.md` §1, comments) and keep the circuit as one inverter — matches the fin-resize MVP's actual scope. If a real 2-stage buffer is ever wanted, add it as a new fixture rather than retrofitting this one.

### A2 — boundary dummy-poly gates straddle the OD; not represented in the netlist

`gen_buffer_layout.py:182-187` places three POLY gates per cell at x∈{0, 54, 108}:

```python
for i, gx in enumerate(gate_x):                 # gate_x = [0, 54, 108]
    net = 'IN' if i == 1 else ''
    desc = 'active_gate' if i == 1 else f'dummy_gate_{i}'
    add_shape('POLY', gx - pw, poly_y_bot, gx + pw, poly_y_top, net=net, desc=desc)
```

The POLY width is 20 nm, so `dummy_L` lands at x∈[-10, 10] and `dummy_R` at x∈[98, 118] — both straddle the cell edge. The OD spans x∈[0, 108] (`bbox_by_layer.json` `OD[0]={…0,30,108,150}`, `OD[1]={…0,230,108,400}`), so `POLY ∩ OD` is non-empty at the cell edges (x∈[0,10] and x∈[98,108]) — i.e. there are parasitic edge transistors. The dummy-gate POLY shapes have `net=''` (floating gate), and the CDL contains only `MN0`/`MP0`. This is the standard SDB-style layout, but real cells either tie boundary poly to a rail or have LVS recognise edge dummy devices; here neither happens. A real LVS run would flag floating gates and/or device-count mismatch.

**Recommendation (deferred):** tie dummy POLY to VSS/VDD via a contact, or recess the OD from the cell edge, or add edge dummy devices to the CDL. Lowest-impact fix is to add an LVS "ignore boundary parasitic" rule in the future tech bundle.

### A3 — minor netlist / parameter-modeling notes

- `w = nfin × FIN_PITCH` (=125 nm for 5 fins; `gen_buffer_layout.py:398`, `:618`; surfaces in `calibre_device_query.json` and the `1.25e-07` line of `device_info_M0.txt`) is a **layout-extent proxy**, not the FinFET electrical width (≈ `nfin · (2·H_fin + W_fin)`). Acceptable for a layout-side fixture; flag in case a future user reads it as electrical W.
- `l = 20n` (= POLY_WIDTH = physical gate length). For a 7 nm node this is realistic. ✓
- Model names `nmos_finfet`/`pmos_finfet` are placeholders; `nfin=` is non-standard SPICE but normal in FinFET CDLs. ✓
- Pin ordering is internally consistent: `.SUBCKT INV_N5_P7 VDD VSS IN OUT` + `MN0 OUT IN VSS VSS …` parses as D/G/S/B = OUT/IN/VSS/VSS, which matches the device `pins` dict in `gen_buffer_layout.py:298`. ✓

### A4 — `buffer_target.gds` and `buffer_resized.gds` are different layouts of the same netlist (informational)

`buffer_target.*` is `generate_inverter_layout(4, 6)` re-run from scratch: NMOS fins shrink to {40,65,90,115}, the NP-gap-anchor moves down, and PMOS fins relocate to y∈{215,240,265,290,315,340} with cell height 380 nm. The pipeline's resize keeps PMOS fins in place and removes only the topmost: NMOS y∈{40,65,90,115}, PMOS y∈{240,265,290,315,340,365}, cell height 405 nm (matches `docs/changelog.md:189` "NWELL `y2 = 395`, BOUNDARY `y2 = 405`"). The end-of-pipeline comparison (`output/resize_comparison.png`) is *visual*, not byte-equal, so this is "by design" — but it is confusing that there are two distinct "after" layouts of the same target netlist. Worth a sentence in `architecture.md` § 11 or `README.md` clarifying that `buffer_target.gds` is a "what a fresh layout of the target netlist would look like" reference, not the expected resize output.

---

## B. GDS geometry & layer map

### B1 — odd shape widths + `int()` truncation → shapes 0.5 nm off their nominal centre

`gen_buffer_layout.py:80-85`:

```python
def add_shape(layer, x1, y1, x2, y2, net='', desc=''):
    shapes[layer].append({'x1': int(x1), 'y1': int(y1),
                          'x2': int(x2), 'y2': int(y2), ...})
```

Combined with `hw = FIN_WIDTH/2 = 3.5`, `liw = LI_WIDTH/2 = 8.5`, `vw = vh = VIA0_WIDTH/2 = 8.5`, this asymmetrically truncates every odd-width shape: a center at integer y produces `int(y − 8.5)` low and `int(y + 8.5)` high, shifting the shape 0.5 nm down (or left). Examples from `bbox_by_layer.json`:

| Shape | Centre | Bbox | Width | Centre check |
|---|---|---|---|---|
| `FIN` (y=40) | 40 | `[0,36,108,43]` | 7 ✓ | (36+43)/2 = 39.5 ❌ |
| `LI` drain (x=81) | 81 | `[72,…,89,…]` | 17 ✓ | 80.5 ❌ |
| `VIA0` gate (x=54, y=162) | 54, 162 | `[45,153,62,170]` | 17×17 ✓ | (53.5, 161.5) ❌ |

Real tool output is always on the DBU grid; this asymmetric off-by-half is a clear "tell" that the coordinates were emitted by a quick generator script, not parsed from a real layout. It also induces the asymmetric M1 enclosure documented in C5.

**Recommendation (deferred):** change DBU to 0.5 nm (or 1 pm to match the gdstk path's `precision=1e-12`); or pick even widths; or at minimum use `round()` instead of `int()` and round to the grid consistently.

### B2 — GDS layer numbers are arbitrary placeholders (by design — note for clarity)

`tech/layer_map.yaml` declares FIN[1,0], POLY[2,0], LI[3,0], VIA0[4,0], M1[5,0], OD[6,0], NWELL[7,0], BOUNDARY[10,0]. These match no real PDK (ASAP7, SKY130, etc. all use very different numbers). This is *not* a bug — `tech/layer_map.yaml:5-8` explicitly says the schema is LEF/`.lyp`-style for foundry import, and `tech/config_loader.py:63-67` (`layermap_override`) plus `tech/layermap_parser.py` provide the seam to patch GDS pairs from a real `.layermap` file without touching `layer_map.yaml`. State explicitly in this audit so future readers do not mistake the placeholders for an integration claim.

### B3 — GDS ↔ `bbox_by_layer.json` ↔ Calibre fixtures are mutually consistent (positive finding)

`bbox_by_layer.json` is produced by writing the GDS then reading it back (`gen_buffer_layout.py:831-835` via `gds_to_bbox_by_layer`), and `device_info_*.txt` / `net_shapes_*.txt` are derived from the same `layout_data['shapes']` dict. Spot-check (precision=20000 → ×20 nm→units): `net_shapes_OUT.txt` LI shapes:

| Verts (Calibre `(y,x)`, units) | nm | Matches `bbox_by_layer.json` |
|---|---|---|
| (700,1440)…(700,1780) | x∈[72,89], y∈[35,203] | `LI[2]={x1:72,y1:35,x2:89,y2:203}` ✓ |
| (3860,1440)…(3860,1780) | x∈[72,89], y∈[193,395] | `LI[3]={x1:72,y1:193,x2:89,y2:395}` ✓ |
| VIA0 (3780,1440)… | x∈[72,89], y∈[189,206] | `VIA0[2]={x1:72,y1:189,x2:89,y2:206}` ✓ |
| M1 (3760,1420)… | x∈[71,91], y∈[188,208] | `M1[2]={x1:71,y1:188,x2:91,y2:208}` ✓ |

`device_info_M0.txt` verts (550,880)…(550,1280) → x∈[44,64] (= gate_x ± POLY_WIDTH/2 = 54 ± 10), y∈[27.5, 152.5] (= fin_ys[0] − 12.5 to fin_ys[-1] + 12.5). Algebraically derivable from `gen_buffer_layout.py:629-643`. ✓

**So the *inter-fixture* consistency the audit was asked to check is solid for these files** — everything flows from `generate_inverter_layout()`. The real input-side problems are the DRC self-inconsistency (Section C), the format fidelity vs real Calibre (Section D), and the regeneration drift on two fixtures (Section E).

---

## C. The dummy layout is **not DRC-clean against the project's own `drc_rules.yaml`**

The CSP engine only enforces LI/M1 same-track + adjacent-track spacing and B-tier OD/VIA0 spacing (`docs/architecture.md:272-285`); VIA0 enclosure is "currently checked by KLayout DRC" (which is optional and evidently not run on the fixture). The MVP's "DRC-correct by construction" premise is therefore false for the *input* fixture — only un-checked rules are hiding it.

### C1 — `LI.P.1` (27) < `LI.W.1` (17) + `LI.S.1` (17) = 34 → adjacent LI tracks at min width are physically illegal; the cell uses adjacent LI tracks → real `LI.S.1` violations

`gen_buffer_layout.py:115,119` places three LI bars on adjacent half-CPP tracks per cell:

```python
gate_x  = [0, 54, 108]                                # GATE_PITCH = 54
sd_li_x = [(gate_x[i]+gate_x[i+1])/2 for i in range(2)]   # = [27, 81]
# Plus a gate-contact LI at x = gate_x[1] = 54.
```

So LI tracks are at x=27, 54, 81 — adjacent tracks 27 nm apart on a layer with width 17 nm and min-spacing 17 nm. Edge-to-edge LI gap on adjacent tracks = 27 − 17 = 10 nm < 17 nm = `LI.S.1`. From `bbox_by_layer.json` LI:

| Pair | x-gap | Y-overlap | Verdict |
|---|---|---|---|
| `li_gate_contact [45,157,62,205]` vs `li_nmos_drain [72,35,89,203]` | 72−62 = **10** | [157,203] non-empty | violation (10 < 17) |
| `li_gate_contact [45,157,62,205]` vs `li_pmos_drain [72,193,89,395]` | 10 | [193,205] non-empty | violation |
| `li_gate_contact` vs `li_*_source` | 10 | empty (145<157, 235>205) | no fire (no Y-overlap) |

Two real DRC violations. Root cause: by collapsing ASAP7's separate LISD (S/D LI) and LIG (gate LI) into one "LI" layer, the half-CPP track pitch becomes over-constrained for min-width / min-spacing.

**Recommendation (deferred):** either (a) raise `LI.P.1` to 34, (b) split LI into LISD + LIG with their own pitches (closer to ASAP7), or (c) shrink `LI.W.1`/`LI.S.1` so `2W+S ≤ pitch` holds. Option (b) is the most realistic.

### C2 — VIA0 has 0 nm LI enclosure in X; `V0.E.LI.x` requires ≥1 nm — all 4 vias violate

`VIA0_WIDTH = LI_WIDTH = 17` (`drc_rules.yaml:50,54`), so for every via the VIA0 x-span equals the surrounding LI x-span exactly. From `bbox_by_layer.json`:

| Via | VIA0 x | LI x | LI shape | Enclosure (left/right) |
|---|---|---|---|---|
| via0_nmos_source | [18,35] | [18,35] | li_nmos_source | 0 / 0 |
| via0_pmos_source | [18,35] | [18,35] | li_pmos_source | 0 / 0 |
| via0_drain       | [72,89] | [72,89] | li_*_drain     | 0 / 0 |
| via0_gate        | [45,62] | [45,62] | li_gate_contact| 0 / 0 |

All four violate `V0.E.LI.x = 1`.

**Recommendation (deferred):** make `V0.SZ.1.x` smaller than `LI.W.1` (e.g. VIA0 = 15, LI = 17 → 1 nm enclosure on each side).

### C3 — LI does **not fully cover** VIA0 in Y on 3 of 4 vias (via overhangs LI by 3–4 nm) — hard "via not enclosed by metal-below" error

The "extend LI to reach via" code (`gen_buffer_layout.py:244-262`) extends LI to `m1_y ± VIA0_ENC_BY_LI_Y` but **omits the via half-height (`VIA0_HEIGHT/2 ≈ 8.5`)**. So the LI edge lands inside the via instead of past it:

```python
nmos_src_li['y1'] = int(m1_y_vss - VIA0_ENC_BY_LI_Y)             # = 18 − 5 = 13
pmos_src_li['y2'] = int(m1_y_vdd + VIA0_ENC_BY_LI_Y)             # = 414 + 5 = 419
gate_li['y1']    = int(min(gate_li['y1'], m1_y_in - VIA0_ENC_BY_LI_Y))   # = min(175,157) = 157
gate_li['y2']    = int(max(gate_li['y2'], m1_y_in + VIA0_ENC_BY_LI_Y))   # = 205 (no change)
```

But the via half-height is 8.5 nm, so the via top/bottom are at `m1_y ± 8.5`, *outside* the LI extension:

| Via | VIA0 y | LI y | Via overhang past LI |
|---|---|---|---|
| via0_nmos_source [9,26] | 9, 26 | li_nmos_source [13,145] | bottom 9 < 13 → **4 nm below LI** |
| via0_pmos_source [405,422] | 405, 422 | li_pmos_source [235,419] | top 422 > 419 → **3 nm above LI** |
| via0_gate [153,170] | 153, 170 | li_gate_contact [157,205] | bottom 153 < 157 → **4 nm below LI** |
| via0_drain [189,206] | 189, 206 | li_nmos_drain [35,203] ∪ li_pmos_drain [193,395] | covered only by the *union* of the two overlapping drain bars; each individual bar would fail |

Three hard "via not metal-covered" errors plus one borderline (covered only because two same-net LI shapes happen to overlap, which any DRC will accept but is fragile).

**Recommendation (deferred):** change the extend-LI-for-via expression to `m1_y ± (ceil(VIA0_HEIGHT/2) + VIA0_ENC_BY_LI_Y)` (= ±14 here), giving 5.5 nm Y-enclosure (rounds to 5 nm worst case).

### C4 — VIA0 under-enclosed by M1 in X on the 2 signal vias; `V0.E.M1.x` requires ≥5 nm

The M1 stubs are `2·m1_ext_x = 20 nm` wide (`gen_buffer_layout.py:265,278-287`); VIA0 is 17 nm; net X-enclosure ~1.5 nm:

| Via | VIA0 x | M1 x | Enclosure (left/right) vs ≥5 |
|---|---|---|---|
| via0_drain | [72,89] | m1_out [71,91] | 1 / 2 → **violation** |
| via0_gate  | [45,62] | m1_in  [44,64] | 1 / 2 → **violation** |
| via0_*_source | [18,35] | m1_vss/vdd [0,108] | 18 / 73 → ✓ |

Two violations on the signal stubs; the power vias are fine because they sit in full-width rails.

**Recommendation (deferred):** widen the signal M1 stubs to ≥ `VIA0_WIDTH + 2·VIA0_ENC_BY_M1_X` = 17 + 10 = 27 nm.

### C5 — asymmetric `V0.E.M1.y` enclosure (1 vs 2 nm) is a fragile by-product of B1's 0.5 nm shift

Because VIA0 (odd width, shifted 0.5 nm low) sits inside M1 (even width, not shifted), Y-enclosure is 1 nm on one side and 2 nm on the other for every via — e.g. m1_vss [...,8,...,28] vs via0_nmos_source [...,9,...,26]: bottom 1 nm, top 2 nm. The rule (`V0.E.M1.y = 1`) is satisfied today, but only because the truncation happens to round one side up to exactly the minimum. Any future change to widths or the rounding convention can flip a side to 0 nm. State this as a hidden coupling rather than a violation.

### C6 — what *is* DRC-clean (so this section reads fairly)

`M1.P.1`/`M1.W.1`/`M1.S.1` = 36/20/16 is self-consistent (`20 + 16 = 36`) ✓.
`POLY.X.OD`: poly y∈[15, 415] extends exactly 15 nm past OD edges (NMOS OD top 150 → poly extends 265 nm, well above 15; NMOS OD bottom 30 → poly extends 30−15 = 15 nm below) ✓.
`NWELL.X.FIN`: NWELL [..,210,..,420] vs topmost PMOS fin 390 → 30 nm ✓; bottom 210 vs bottommost PMOS fin 240 → 30 nm ✓.
`BOUNDARY.X.FIN`: BOUNDARY top 430 vs topmost PMOS fin 390 → 40 nm ✓.
NWELL covers PMOS OD ([230,400] ⊂ [210,420]) ✓ and clears NMOS OD (210 > 150) ✓.

---

## D. Calibre-query fixtures & formats

### D1 — `calibre_device_query.json` and `device_info_*.txt` disagree by 0.5 nm on the *same* device bbox

Two generators in `gen_buffer_layout.py` write "the device bbox" with different rounding conventions:

| Generator | y formula (NMOS) | Result | File |
|---|---|---|---|
| `generate_calibre_device_query` (`:400-405`) | `fin_ys[0] - GATE_PITCH//2`/`-FIN_PITCH//2` (integer floor) | y1=40−12=**28**, y2=140+12=**152** | `calibre_device_query.json` MN0 `{x1:27,y1:28,x2:81,y2:152}` |
| `generate_calibre_device_info` (`:629-643`) | `fin_ys[0] - fin_pitch_nm/2` (float) | y1=40−12.5=**27.5**, y2=140+12.5=**152.5** | `device_info_M0.txt` verts → y∈[27.5, 152.5] |

(They also disagree on x: device-query uses `gate_x ± GATE_PITCH//2 → [27, 81]` for the device-cell extent; device-info uses `gate_x ± POLY_WIDTH/2 → [44, 64]` for the gate seed shape — those are *different* representations and can legitimately differ, but the y-axis 0.5 nm gap is just inconsistent rounding.)

**Recommendation (deferred):** pick one rounding convention and apply both places; or use a 0.5 nm DBU.

### D2 — the `DEVICE INFO` "seed shape" is a synthetic rectangle, not `POLY ∩ OD`

The seed-shape bbox in `device_info_M0.txt` is x∈[44,64], y∈[27.5, 152.5] = `POLY_WIDTH × (fin_span ± half-fin-pitch)`. But the active OD is `bbox_by_layer.json` `OD[0]={...,30,...,150}`, so the "seed shape" overhangs OD by 2.5 nm on each side in Y. A real Calibre `DEVICE INFO` returns the device-recognition layer (`ngate`/`pgate`), defined as `poly AND active`, **clipped to OD** — so a real run would emit y∈[30,150], not [27.5, 152.5]. This synthetic bbox cannot come out of real Calibre. Same for `device_info_M1.txt` y∈[227.5, 402.5] vs `OD[1]={...,230,...,400}` (2.5 nm overhang each side).

**Recommendation (deferred):** clip the seed bbox to `POLY ∩ OD` in `generate_calibre_device_info`, matching what real Calibre would emit. This also enables D5's mapping table once added.

### D3 — `NET SHAPES` shapes are raw GDS geometry, not the "effective conducting region" the docs claim

`docs/architecture.md:421-422` (and §9 prose at `:454-463`) states: *"each shape's bbox represents the effective conducting region — cuts and extension margins are excluded"*. But `generate_calibre_net_shapes` (`gen_buffer_layout.py:706-731`) just dumps `layout_data['shapes'][layer]` filtered by net, with no trimming. Verified: `net_shapes_OUT.txt` LI verts → exactly `[72,35,89,203]` and `[72,193,89,395]` = the raw `LI` shapes from `bbox_by_layer.json`, including the via-reach extensions. There is a "trimming deferred to 1.6" caveat at `:422` and `changelog.md` 2026-05-07 entry, but §9's prose still reads as current behaviour.

**Recommendation (deferred):** either implement trimming (subtract cut shapes and extension margins) **or** soften the doc wording to "raw layer geometry; effective-region trimming deferred to 1.6". Option (b) is the smaller change and is what the changelog already plans.

### D4 — `device_info` hard-codes `poly_width_nm = 20` and `fin_pitch_nm = 25` instead of reading config

`gen_buffer_layout.py:617-618`:

```python
poly_width_nm = 20
fin_pitch_nm  = 25
```

If `tech/drc_rules.yaml` `POLY.W.1` or `FIN.P.1` change, the GDS shapes follow (they read `config.POLY_WIDTH` / `config.FIN_PITCH` at `:69,:64`) but `device_info_*.txt` silently stays on the old constants. Latent bug.

**Recommendation (deferred):** read `config.POLY_WIDTH` / `config.FIN_PITCH` (config is already an arg of the parent `generate_all_fixtures`; thread it through to `generate_calibre_device_info`).

### D5 — the LVS / HDB *formats* are modelled on a user-provided example, not verified against real Calibre

The SVDB ixf/nxf headers (`# SVDB: ... (File format 1)`, `# SVDB: End of header.`), the `Device_Info <precision>` / `Info:` / `0 0 <n> <date>` count-line / `p <idx> <nverts>` / `<y> <x>` integer-pair convention (LL→LR→UR→UL, `(y, x)` order — unusual; most tools use `(x, y)` and CCW), precision 20000 → 0.05 nm, and the per-layer count-line ambiguity the parser papers over (`io_adapters/calibre_query.py::parse_device_info`, see `changelog.md:51`) — all plausible but unconfirmed against a real `calibre -query` session. The repo itself acknowledges that `--lvs-mode calibre` is "untested with a real Calibre binary" (`changelog.md:119`).

**Recommendation (deferred):** validate against the actual `calibre -query` output before the first production run; treat the formats as provisional. This is a known/acknowledged gap, not a defect — listing here so it does not get forgotten.

### D6 — what *is* correct on the Calibre side (positive findings)

- `iXref.temp` content is internally consistent: cell `INV_N5_P7`, 4 pins, `0 M0 0 MN0`, `0 M1 0 MP0 X` (S/D-swap flag on PMOS for the parser test path).
- `nXref.temp` + `net_names.txt` round-trip: nets {IN, OUT, VSS, VDD}, layout names = source names (no internal-net renumbering for the inverter), 1-indexed in NET NAMES.
- `net_shapes_*.txt` shape contents match the raw GDS exactly when checked vert-by-vert (Section B3).

---

## E. Fixture provenance / regeneration drift

### E1 — `buffer_original.json` and `calibre_net_query.json` are **stale relative to `gen_buffer_layout.py`** (committed-vs-generator drift)

Running `python3 dummy/gen_buffer_layout.py` on a clean tree produces a diff in two committed fixtures:

```
$ python3 dummy/gen_buffer_layout.py     # then:
$ git status --short dummy/fixtures/
 M dummy/fixtures/buffer_original.gds
 M dummy/fixtures/buffer_original.json
 M dummy/fixtures/calibre_net_query.json
$ git diff --stat dummy/fixtures/
 dummy/fixtures/buffer_original.gds    | Bin 2164 -> 2166 bytes
 dummy/fixtures/buffer_original.json   |  68 +++++++++++++++++-----------------
 dummy/fixtures/calibre_net_query.json |  64 ++++++++++++++++----------------
```

Inspecting the diffs: every changed line is a **shape-ordering** change (e.g. in `buffer_original.json`, the committed file has the `VIA0` block before the `M1` block; the regenerated file has them swapped). **Coordinate values are identical** — only the iteration order changed. Root cause: the layer-ordering in `tech/layer_map.yaml` (which drives `shapes = {layer: [] for layer in LAYER_MAP}` at `gen_buffer_layout.py:78`) was changed in a refactor (M1 now sits before VIA0; OD is in the B-tier block after M1), but those two committed JSONs were never re-committed. The committed `buffer_original.gds` differs by 2 bytes in the binary — same root cause, plus a small encoding-detail difference between gdstk and the manual writer (the originally-committed GDS was written by gdstk; today's regen used the manual writer because gdstk is not installed in this environment, see E2).

This is the user's exact original suspicion confirmed in a milder form than expected: **the fixtures don't 100% match what the generator produces today.** The mismatch is purely cosmetic (ordering and a 2-byte binary delta) — but it means the long-standing "byte-golden" claim in `changelog.md` (e.g. M3: *"GDS polygon-set identical (30/30)"*) is true *for content* but no longer *for the literal fixture file*. Future "byte-golden" references should compare *normalised* (sorted) fixture content, or the fixtures should be re-committed and the generator's iteration order frozen.

**Recommendation (deferred):** (a) regenerate and re-commit `buffer_original.{gds,json}` and `calibre_net_query.json` (next time gdstk is available so the GDS encoding stays gdstk-consistent), and (b) add a CI check that `python3 dummy/gen_buffer_layout.py && git diff --exit-code dummy/fixtures/` is clean — that catches drift at PR time rather than letting it accumulate.

### E2 — `gen_buffer_layout.py` requires `gdstk` to fully regenerate, contradicting the "optional" claim

`README.md:90-91` says: *"gdstk (optional — needed for GDS-reading paths; the bundled writer in dummy/gds_writer.py uses stdlib struct only)"*. True for *writing*, but `generate_all_fixtures` (`gen_buffer_layout.py:831-835`) calls `gds_to_bbox_by_layer(orig_gds_path, ...)` to produce `bbox_by_layer.json` from a GDS read-back — and that path is gdstk-only (`io_adapters/gds_io.py:65-69` raises `ImportError` when `gdstk` is absent). The regen of the input fixtures therefore aborts mid-run without gdstk:

```
ImportError: gdstk is required for GDS reading. Install with: pip install gdstk
```

So gdstk is effectively *required* to regenerate the fixture set (just not to *consume* the pre-committed ones at run time, which is what the README is talking about).

**Recommendation (deferred):** either (a) update `README.md` to say "gdstk is required to regenerate `bbox_by_layer.json`", or (b) make the manual writer also able to read its own output for the round-trip (small task — the manual writer is < 200 lines), or (c) drop the GDS round-trip and emit `bbox_by_layer.json` directly from `layout_data['shapes']` (acceptable because `bbox_by_layer.json` claims to be the GDS truth source, and the manual GDS write is already lossless from `layout_data['shapes']`).

---

## Summary table

| ID | Area | Issue | Severity | User decision |
|----|------|-------|----------|---------------|
| A1 | schematic | "buffer" naming ≠ inverter circuit | naming/clarity | document only, no rename |
| A2 | schematic | boundary dummy-poly over OD, floating, not in CDL | medium (latent LVS) | documented |
| A3 | schematic | `w = nfin·pitch` proxy; placeholder model names | low | documented |
| A4 | schematic | `target.gds` ≠ `resized.gds` geometry | low / informational | documented |
| B1 | GDS | odd widths + `int()` → 0.5 nm off-centre | low–medium | documented |
| B2 | GDS | placeholder layer numbers | none (by design) | documented |
| B3 | GDS | GDS ↔ bbox ↔ Calibre fixtures consistent | — | positive finding |
| C1 | DRC | LI pitch < width + spacing → `LI.S.1` violations | high | documented |
| C2 | DRC | VIA0 0 nm LI enclosure (need 1) | high | documented |
| C3 | DRC | via overhangs LI in Y by 3–4 nm (missing half-height term) | high | documented |
| C4 | DRC | VIA0 under-enclosed by M1 in X (1–2 vs 5 nm) | high | documented |
| C5 | DRC | asymmetric `V0.E.M1.y` from B1 | low (fragile) | documented |
| C6 | DRC | M1 / POLY-X-OD / NWELL / BOUNDARY rules clean | — | positive finding |
| D1 | Calibre | `device_query` vs `device_info` bbox differ 0.5 nm | low | documented |
| D2 | Calibre | DEVICE INFO seed shape ≠ `POLY ∩ OD` | medium | documented |
| D3 | Calibre | NET SHAPES not trimmed (doc says "effective region") | low (doc/impl gap) | documented |
| D4 | Calibre | `device_info` hard-codes poly_width / fin_pitch | low (latent) | documented |
| D5 | Calibre | HDB / LVS formats unverified vs real Calibre | known gap | documented |
| D6 | Calibre | iXref / nXref / NET NAMES content correct | — | positive finding |
| E1 | provenance | committed `buffer_original.{gds,json}` and `calibre_net_query.json` are stale relative to the generator | medium | documented |
| E2 | tooling | `gen_buffer_layout.py` needs gdstk to fully regen, despite "optional" claim | low (doc) | documented |

## Out of scope (explicit follow-ups)

The user scoped this audit to **inputs + formats only**. The following remain unaudited and are the obvious next-pass targets:

1. **Resize output path** — `core/solver.py::resize_device`, `core/decoder.py::WritebackDecoder`, `core/drc_derivator.py::DRCDerivator`, and the produced `output/buffer_resized.gds`. Open questions: does the resized layout stay DRC-clean (most of C1–C4 will recur or worsen because the via-extension code is in `gen_buffer_layout.py` only — the resize path has its own LI/M1 reshaping logic in `_emit_*` helpers); do moved M1 rails still cover their vias; are derived `is_derived` NWELL / BOUNDARY extents right for both the original and target nfin counts (the M5 changelog cites `y2 = 395` / `y2 = 405` for the resized cell, which can be cross-checked); does `WritebackDecoder.apply` deep-copy semantics preserve all coordinate metadata.
2. **Real-Calibre format validation** (D5) — first run `calibre -query <real-svdb>` and compare against the parser's expectations.
3. **CSP DRC-rule completeness** — only the LI/M1 same/adjacent-track and B-tier OD/VIA0 spacing rules are CSP-enforced today (`docs/architecture.md:272-285`); enclosure / extension / EOL / multi-patterning rules are deferred. The C-section findings argue for adding at least `V0.E.LI` and `V0.E.M1` to the CSP front-line so the next dummy fixture cannot regress in the same way.
4. **The `--config` override flow** and `layermap_override` end-to-end (already in `backlog.md` "Test-coverage gaps").
