# DRC Rules (MVP Subset)

## Mathematical Framework

Each DRC rule is encoded as a CSP constraint template:

$$C_r = (\text{Stencil}_r, \text{Trigger}_r, \text{Forbidden}_r)$$

- **Stencil**: relative grid offsets defining spatial scope
- **Trigger**: anchor cell states that activate the rule
- **Forbidden**: neighbor states disallowed when triggered

## Rules Implemented

### 1. LI Along-Track Spacing
- **Physical**: LI shapes on same track must have ≥ 17nm gap
- **CSP**: `SameLayerAlongTrackSpacing('LI', spacing_ortho=1)`
- **Stencil**: `[(LI, 0, -1), (LI, 0, +1)]`
- **Trigger**: Any WIRE state
- **Forbidden**: WIRE of different net
- **Use case**: VSS and VDD share LI track 1

### 2. M1 Cross-Track Spacing
- **Physical**: Adjacent M1 tracks center-to-center ≥ 36nm
- **CSP**: `SameLayerMinSpacing('M1', spacing_tracks=1)`
- **Stencil**: `[(M1, -1, 0), (M1, +1, 0)]`
- **Use case**: Prevent different-net M1 wires on adjacent tracks

### 3. M1 Along-Track Spacing
- **Physical**: M1 shapes on same track, different nets, ≥ 16nm gap
- **CSP**: `SameLayerAlongTrackSpacing('M1', spacing_ortho=1)`

## Rules NOT Yet Implemented (Post-MVP)
- Via0 enclosure by LI/M1 (checked by KLayout DRC instead)
- End-of-line spacing
- LI cross-track spacing (not relevant for resize — LI X positions fixed)
- Multi-patterning coloring constraints

## Adding New Rules
1. Create a subclass of `DRCConstraintTemplate` in `core/drc_constraints.py`
2. Define `trigger()` and `forbidden_states()` methods
3. Set `anchor_layer` to restrict firing to the correct layer
4. Register in `create_mvp_drc_rules()`
