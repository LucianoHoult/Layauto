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
| [`layauto_v2/`](layauto_v2/) | v2 input reading and process-local pre-context run audit; later runtime stages remain skeletons. |
| [`docs/architecture.md`](docs/architecture.md) | Active v2 architecture source: stage boundaries, fact sources, state ownership, planning, constraints, transactions, export, validation, and module boundaries. |

## Input reading component

The W005 component reads the declared synthetic GDS/CDL/query/config subset from
actual files and returns immutable evidence or located input errors:

```python
from pathlib import Path
from layauto_v2.importers import read_inputs

result = read_inputs(Path("tests/fixtures/w003_m1/site_config.yaml"))
if result.status == "success":
    assert result.value is not None
    geometry = result.value["gds"]
else:
    issues = result.issues
    completed_evidence = result.completed
```

Paths resolve from the site file directory. Each file is read once per call;
`result.sources` preserves those bytes and their SHA-256. GDS XY/REAL8, CDL
lexemes, and query polygons retain exact values and provenance. Optional
normalized query caches are compared against freshly parsed raw captures.
The importer does not load expected/spec/oracle answers or call EDA tools.

`read_inputs` is the supported component boundary; lower-level parsers consume
already validated profiles. Expected input failures return `status="error"`;
unexpected exceptions and process interrupts propagate. An optional
`tool_run_id` only links an external execution record. This API does not create
RunAttempt/RunRecord, layout state, body connectivity, no-change decisions, or
exports. Its success is not production admission or W005 PM acceptance.

The implemented `layauto-input/1` bootstrap ceilings are 1,000,000 bytes per
text document and 32 nested containers (root depth 1), with profile limits able
to tighten them. The record ceiling is 1000: GDS counts all stream records;
CDL counts non-comment logical lines; query limits xref/name rows, requests,
and polygon records in each capability. Original LF/whitespace counts toward
text size. Only the declared schema/dialect versions are accepted.

Install `.[dev]` for engineering checks, then run:

```sh
python -m pytest tests/unit tests/contracts -q
python -m mypy
python -m build
```

The strict checker targets the input component and its neutral domain/tech
contracts with Python 3.10 syntax. Execution, independent reviews and supported
interpreter/build evidence are linked from [W005](docs/tasks/W005-input-reading-binding.md).

## Pre-context run entry

The internal W006 entry creates a run identity before reading or parsing any
input. It drives the same reader with actual fixture captures and retains the
bytes, execution facts, parse evidence and failures in a process-local repository:

```python
from pathlib import Path
from layauto_v2.domain.publication import RunRequest, InputsReady
from layauto_v2.pipeline import prepare_inputs
from layauto_v2.repository import PublicationRepository

repository = PublicationRepository()
# The caller retains this exact request, run id and key across retries.
request = RunRequest(
    proposed_run_id="example-run-001",
    lineage_id="example-lineage",
    idempotency_key="create-001",
    site_path=str(Path("tests/fixtures/w003_m1/site_config.yaml").resolve()),
)
result = prepare_inputs(repository, request)
if isinstance(result, InputsReady):
    assert result.attempt.phase == "unsealed"
    parsed_inputs = result.value  # Handoff to a future Stage 2.
```

Callers may additionally supply `Selection(uri, declared_sha256)` in the
request's `raw_input_selections`, `raw_capture_selections` and
`config_policy_selections`. Relative selections use the site directory; the
site path itself must be absolute. Declared hashes remain frozen separately
from the actual acquisition hashes. Later discovered sources, including
optional normalized caches, are audited without rewriting the request.

`InputsReady` is not a completed run, baseline, no-change decision or successful
terminal result. A captured input failure normally produces a repository-owned
terminal `PipelineResult` with `deployment_disposition="reject"`, linked to its
failure RunRecord and audit chain. RunRecord construction failure has the sole
`run_record_freeze_failure` closure variant. `PublicationUnavailable` means
publication could not be confirmed; it retains available refs and in-memory
diagnostics without inventing a terminal pointer. Repository conflicts raise
`RepositoryConflict`; `KeyboardInterrupt` and `SystemExit` propagate after
best-effort recording.

Repository reads resolve typed content refs. A failed finalization resumes its
saved checkpoint on retry without reading changed files. Publication and replay
are atomic within one process only; there is no disk persistence or recovery
after process loss. Stage 2–6, real EDA and production admission remain outside
this entry. Requirements, review and validation are recorded in
[W006](docs/tasks/W006-precontext-run-audit.md).

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
