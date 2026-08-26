# Layauto docs

This directory is centered on the active Layauto v2 architecture. Historical MVP
planning, backlog, audit, and flow documents have either been absorbed into the
architecture or archived.

## Active docs

| File | Owns |
|------|------|
| [`architecture.md`](architecture.md) | Active v2 architecture source: project scope, Stage 1-6 boundaries, fact sources, layout-state ownership, annotation, physical edit semantics, planning, constraints, transactions, export/validation, module organization, configuration boundaries, and absorbed backlog/audit highlights. |

## Archived docs

| File | Status |
|------|--------|
| [`archive/changelog.md`](archive/changelog.md) | Historical MVP/v1 shipped-change log. Kept for archaeology only; it is not a v2 planning source. |

## Where to start

- Read [`architecture.md`](architecture.md) end-to-end for the current v2 plan.
- New v2 implementation should live under `layauto_v2/`.
- The previous MVP implementation is archived under `legacy_mvp/` and should not
  be used as the active architecture baseline.
- If a new architectural issue is found, add it to the relevant section of
  `architecture.md` following its backlog/audit placement rules rather than
  recreating standalone backlog, audit, or legacy-flow documents.
