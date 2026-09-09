# Layauto

Layauto v2 is an incremental FinFET layout automation framework. The active
architecture is documented in [`docs/architecture.md`](docs/architecture.md),
and new implementation work should live under [`layauto_v2/`](layauto_v2/).

## Development setup

Use Python 3.10+ and a dedicated virtual environment. See
[`docs/environment/local-setup.md`](docs/environment/local-setup.md) for the configured macOS environment,
installation, validation, and Git commands. For iPhone access to this Mac and
browser-based cloud development, see
[`docs/environment/remote-development.md`](docs/environment/remote-development.md).

## Development workflow

Start with [`AGENTS.md`](AGENTS.md) and the
[`collaboration rules`](docs/collaboration/rules.md). The
[`current work entry`](docs/current-work.md) records where to resume;
[`docs/README.md`](docs/README.md) explains document ownership and reading routes.
The [v2 roadmap](docs/roadmap.md) maps first-release requirements to milestones,
dependencies, and acceptance; its planning review is tracked in
[W001](docs/tasks/W001-v2-global-plan.md). Product architecture, collaboration rules,
environment setup, and task results have separate owners. Read the architecture
sections relevant to the task.

## Active development

| Path | Purpose |
|------|---------|
| [`layauto_v2/`](layauto_v2/) | v2 package skeleton and future implementation home. It is intentionally empty of legacy MVP logic today. |
| [`docs/architecture.md`](docs/architecture.md) | Active v2 architecture source: stage boundaries, fact sources, state ownership, planning, constraints, transactions, export, validation, and module boundaries. |

## Legacy MVP archive

The previous MVP implementation has been moved as-is to
[`legacy_mvp/`](legacy_mvp/). It is retained only as a legacy/reference
implementation and regression seed. Root-level legacy imports are intentionally
not maintained. For archive tests and demonstrations, follow the
[environment instructions](docs/environment/local-setup.md#测试入口与历史基线)
to use the configured Python and protect tracked legacy outputs.

Do not treat `legacy_mvp/` as the v2 implementation baseline. Code may be
reused only after it is moved into the v2 responsibility boundary described in
`docs/architecture.md`.
