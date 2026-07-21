# Layauto legacy MVP archive

This directory contains the previous Buffer Fin Resize MVP implementation moved
as-is out of the active repository root. It is retained for reference,
regression archaeology, and selective code reuse only.

## Running the archived MVP

Run legacy commands from this directory with `PYTHONPATH=.:..` so the
archived top-level packages (`core`, `io_adapters`, `pipeline`, `visualization`,
and `dummy`) and the archived `tech/` bundle remain on Python's import path:

```bash
cd legacy_mvp
PYTHONPATH=.:.. python3 pipeline/run_mvp.py
PYTHONPATH=.:.. pytest tests
```

Root-level compatibility shims are intentionally not provided. New v2 work
belongs under `../layauto_v2/` and must follow `../docs/architecture.md`.
