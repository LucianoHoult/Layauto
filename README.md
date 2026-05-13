# Buffer Fin Resize MVP

Incremental layout automation framework for FinFET fin resizing,
using CSP-based DRC constraint propagation.

## Current Status (MVP)

| Stage | Description | Status |
|-------|-------------|--------|
| 0 | Dummy fixtures (GDS, CDL, Calibre JSON) | ✅ Complete |
| 1 | Data model & Grid system | ✅ Complete |
| 2 | IO parsing (Calibre query → LayoutModel) | ✅ Complete |
| 3 | CSP engine + DRC constraint templates | ✅ Complete |
| 4 | Load existing layout into CSP | ✅ Complete |
| 5 | Resize solver (nfin-1 for NMOS & PMOS) | ✅ Complete |
| 6 | GDS output + visual diff + SKILL template | ✅ Complete |
| 7 | Production environment integration | ⬜ Pending |

## Quick Start

```bash
# Generate dummy fixtures
python3 dummy/gen_buffer_layout.py

# Run complete pipeline (parse → CSP → resize → GDS → verify)
python3 pipeline/run_mvp.py

# Output files appear in output/
```

## Output Files

After running `pipeline/run_mvp.py`:

- `output/buffer_resized.gds` — Resized layout GDS
- `output/buffer_resized.json` — Resized layout data
- `output/buffer_resized.cdl` — Updated netlist
- `output/resize_comparison.png` — 3-way visual comparison
- `output/resize_diff.png` — Diff overlay showing changes
- `output/resize_report.txt` — Text report of edit operations

## Project Structure

```
buffer_fin_resize/
├── tech/               # Dummy process parameters
│   ├── tech_params.py  # Pitches, widths, spacings
│   └── layer_map.py    # GDS layer mapping
├── dummy/              # Dummy data generation
│   ├── gen_buffer_layout.py   # Generate GDS + Calibre JSONs
│   ├── gds_writer.py          # Minimal GDS-II writer (stdlib only)
│   └── fixtures/              # Generated dummy files
├── core/               # Core engine (IO-independent)
│   ├── data_model.py   # CellState, TrackSegment, Device, Net
│   ├── grid.py         # MultiLayerGrid, coord↔track conversion
│   ├── csp_engine.py   # CSP constraint propagation engine
│   ├── drc_constraints.py  # DRC rule templates
│   └── solver.py       # Resize solver + edit generation
├── io_adapters/        # IO layer (swap for production)
│   └── parser.py       # Calibre JSON → core data structures
├── visualization/      # Layout and CSP visualization
│   └── layout_viewer.py
├── pipeline/           # End-to-end flow
│   └── run_mvp.py      # Main pipeline script
├── scripts/            # Production environment scripts
│   └── virtuoso_apply_edit.il  # SKILL template
└── output/             # Pipeline outputs
```

## Architecture

```
Physical coords (nm)   ←→   Track-Segment layer   ←→   CSP grid layer
     GDS I/O                   Working repr              DRC enforcement
                               (TrackSegment)            (domain propagation)
```

- **Grid**: Each layer has a track grid defined by pitch. Along-track
  dimension uses orthogonal layer's tracks as anchor points.
- **CSP**: Each grid cell has a domain (set of legal states). Assigning
  a cell propagates constraints to neighbors, shrinking their domains.
  DRC rules are encoded as (Stencil, Trigger, Forbidden) templates.
- **Resize**: Release old cells → assign new cells → check CSP feasibility.
  If any domain becomes empty, the resize is infeasible.

## Dependencies

- Python 3.10+
- numpy, matplotlib, pyyaml (required)
- gdstk (optional — needed for GDS-reading paths; the bundled writer
  in `dummy/gds_writer.py` uses stdlib `struct` only)
- pytest, klayout (optional — for the test suite / local DRC)

### One-click install

A cross-platform checker and installer ships under `scripts/`:

```bash
# Linux / macOS
./scripts/install.sh           # check + install required deps
./scripts/install.sh --check   # report only, no install
./scripts/install.sh --all     # install required + optional

# Windows (cmd / PowerShell)
scripts\install.bat
scripts\install.bat --check
scripts\install.bat --all

# Or directly (any platform):
python scripts/check_deps.py --install
```

`scripts/check_deps.py` reports the installed vs. required versions
for every package and pip-installs anything missing. The Windows
wrapper sets `PYTHONUTF8=1` so subsequent script runs read YAML / JSON
fixtures as UTF-8 regardless of the system code page (avoids the
zh-CN `UnicodeDecodeError: 'gbk' codec can't decode` failure mode).

## Production Integration Notes

To connect to your actual PDK/environment:

1. **Replace `tech/tech_params.py`** with real process values
2. **Adapt `io_adapters/parser.py`** to match actual Calibre SVDB query format
3. **Add DRC rules** to `core/drc_constraints.py` (just add new constraint classes)
4. **Implement `scripts/virtuoso_apply_edit.il`** with actual SKILL operations
5. **Add `scripts/calibre_run_drc.sh`** for post-modification DRC verification

The `core/` directory requires NO changes for production — only `tech/`,
`io_adapters/`, and `scripts/` need adaptation.
