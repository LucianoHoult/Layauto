# Layauto

Layauto v2 is an incremental FinFET layout automation framework. The active
architecture is documented in [`docs/architecture.md`](docs/architecture.md),
and new implementation work should live under [`layauto_v2/`](layauto_v2/).

## Active development

| Path | Purpose |
|------|---------|
| [`layauto_v2/`](layauto_v2/) | v2 package skeleton and future implementation home. It is intentionally empty of legacy MVP logic today. |
| [`docs/architecture.md`](docs/architecture.md) | Active v2 architecture source: stage boundaries, fact sources, state ownership, planning, constraints, transactions, export, validation, and module boundaries. |

## Legacy MVP archive

The previous MVP implementation has been moved as-is to
[`legacy_mvp/`](legacy_mvp/). It is retained only as a legacy/reference
implementation and regression seed. Root-level legacy imports are intentionally
not maintained; if the old flow needs to be run, execute it from inside the
archive directory:

```bash
cd legacy_mvp
PYTHONPATH=.:.. python3 pipeline/run_mvp.py
PYTHONPATH=.:.. pytest tests
```

Do not treat `legacy_mvp/` as the v2 implementation baseline. Code may be
reused only after it is moved into the v2 responsibility boundary described in
`docs/architecture.md`.
