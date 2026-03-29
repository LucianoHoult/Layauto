# Production Environment Integration Notes

## Components to Adapt

### 1. tech/tech_params.py
Replace all dummy values with real PDK parameters.
Critical: LI_PITCH must be set so that both S/D and gate contact
X positions fall on grid points.

### 2. io_adapters/parser.py
Adapt to actual Calibre SVDB query output format.
The key fields needed per device: instance name, type, nfin, pin-to-net map, bbox.
The key fields needed per net: shapes list with layer + bbox.

### 3. scripts/virtuoso_apply_edit.il
Implement the SKILL helper functions for actual shape find/modify/delete.
The edit operations list from solver.py provides bbox coordinates.

### 4. scripts/calibre_run_drc.sh / calibre_run_lvs.sh
Standard Calibre batch scripts. Run after applying edits to verify.

## Known Format Risks
- Calibre SVDB query may return coordinates in microns, not nm
- Pin names may be case-sensitive
- Net names may include hierarchy separators
- Fin Y positions may not be explicitly available (derive from OD + fin pitch)

## Testing Checklist (First Production Run)
1. [ ] Calibre query scripts produce valid JSON
2. [ ] Parser correctly maps to LayoutModel (compare with manual inspection)
3. [ ] Grid visualization matches Virtuoso layout view
4. [ ] CSP loads without violations
5. [ ] Resize produces correct edit list
6. [ ] SKILL script executes without errors
7. [ ] Post-edit DRC is clean
8. [ ] Post-edit LVS matches updated schematic
