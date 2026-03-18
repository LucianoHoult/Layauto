# DRAM_PathFinder

DRAM_PathFinder is a modular Python framework for pre-layout DRAM timing evaluation using logic CDL netlists. It performs configurable pruning/linearization, distributed RC injection, and PWL stimulus generation.

## Directory Structure

```text
DRAM_PathFinder/
├── README.md
├── main.py
├── configs/
│   ├── tech_rc.json
│   ├── array_topo.json
│   └── stimulus.json
├── inputs/
│   └── dummy_4x4_array.cdl
├── core/
│   ├── config_parser.py
│   ├── cdl_parser.py
│   ├── netlist_engine.py
│   └── pwl_builder.py
├── utils/
│   ├── logger_setup.py
│   └── file_io.py
├── tests/
│   ├── test_netlist_engine.py
│   └── test_pwl_builder.py
└── runs/
```

## How to Run

From the `DRAM_PathFinder` directory:

```bash
python main.py
```

Each run creates a timestamped folder:

```text
runs/run_YYYYMMDD_HHMMSS/
```

Artifacts generated per run:
- `modified_netlist.sp`
- `stimulus.sp`
- `testbench.sp`

The sample CDL now includes a placeholder `PERIPHERY` subcircuit so the bundled example remains self-contained, and the generated testbench links `ACT_CMD`/`READ_CMD` stimuli onto the extracted `DRV_*` RC ladder drivers for runnable activation/read timing experiments.
- `run.log`

## How to Test

```bash
pytest -q
```

## Implementation Notes

- CDL line continuations (`+`) are merged before regex parsing.
- Cell instance extraction is driven by the configurable regex in `array_topo.json`.
- Active-cross non-target cells are linearized into dummy capacitors and removed as active devices.
- Target cell WL/BL nodes are rewired to distributed RC segment nodes, not left on global nets.
