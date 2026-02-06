# Hierarchical Logic-Depth Circuit Visualizer

This repository now includes a transistor-aware Phase 1/2 foundation:
- Parse SPICE/CDL-like netlists (`.SUBCKT`, `X...`, `M...`) into hierarchical models.
- Group transistor-level structures into CCCs (Channel-Connected Components).
- Compute logic depth with loop handling and feedback-edge marking.
- Export frontend-ready JSON (`id/type/x/y/parent_module/pins/...`).

## Project Structure

```text
/project-root
├── /parser       # Netlist + hierarchical data model
├── /layout       # CCC + logic-depth + JSON export
├── /web-ui       # Placeholder for React frontend phases
├── /test_cases   # Topology/unit tests (including DRAM/hierarchy)
├── /test         # Extra regression tests
└── /docs         # Additional documentation
```

## How to Input a Netlist

Supported entries:
- `.SUBCKT <name> <ports...>` and `.ENDS`
- `Xname <pins...> <cell_or_subckt>` (case-insensitive)
- `Mname <d> <g> <s> <b> <model>` (transistor-level)

## Logic Depth Rules

1. Primary-input nets are depth 0 anchors (unless explicitly passing an empty set).
2. Default stage behavior increments depth per instance (or hierarchical internal latency).
3. For transistor-level nets, depth increments via **gate influence edges**.
4. Feedback loops are detected and broken by selecting/marking feedback edges for UI.
5. Transmission gates can be configured as transparent (`tg_transparent=True`) to avoid stage increment.

## Frontend JSON Output

`DepthResult.to_frontend_json(subckt)` returns:
- node list with `id`, `type`, `x`, `y`, `parent_module`
- `pins` with derived role (`Driver`/`Load`)
- `bounds`, `detail_level`, `is_collapsed`
- `feedback_edges` with `is_feedback=true`

## Run Tests

```bash
python -m pip install -r requirements.txt
pytest -q
```
