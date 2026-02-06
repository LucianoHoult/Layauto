# Hierarchical Logic-Depth Circuit Visualizer

This repository implements **Phase 1 (MVP)** of a Google Maps-style circuit visualizer:
- Parse SPICE/CDL-like netlists into a graph model.
- Build an instance DAG for a top-level subcircuit.
- Calculate logic depth using `X_i = max(X_inputs) + 1`.

## Project Structure

```text
/project-root
├── /parser       # Netlist to graph conversion logic
├── /layout       # Logic-depth algorithm (Phase 1)
├── /web-ui       # Placeholder for upcoming React frontend phases
├── /test_cases   # Unit tests for requested topologies
└── /docs         # Additional documentation
```

## How to Input a Netlist

Use SPICE/CDL text with:
- `.SUBCKT <name> <ports...>`
- `X...` instance lines (`Xname <pins...> <cell_type>`)
- `.ENDS`

Example:

```spice
.SUBCKT top IN VDD VSS OUT
XINV0 IN n1 VDD VSS INV
XINV1 n1 OUT VDD VSS INV
.ENDS
```

## Logic Depth Calculation

1. Each instance contributes a directed edge from driver net to load net.
2. Primary input nets are anchored at depth 0.
3. Instance depth is computed in topological order:
   - `X_i = max(input_predecessor_depths) + 1`
4. If a feedback loop exists, the current MVP raises an error (to be handled in Phase 4).

## UI Navigation Shortcuts

Frontend implementation starts in Phase 3. Planned shortcuts:
- Mouse wheel: semantic zoom in/out.
- Left click net/pin: show fan-in/fan-out highlight paths.
- Drag canvas: pan.

## Run Tests

```bash
pytest -q
```

Covers:
- Simple inverter chain.
- NAND/NOR chain.
- Latch-style loop detection.
