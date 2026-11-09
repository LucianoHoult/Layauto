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
| [`layauto_v2/`](layauto_v2/) | v2 input reading, pre-context audit, semantic normalization, exact drawn-base geometry/occupancy and effective-region drafts; later physical stages remain skeletons. |
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

The strict checker targets input reading, pre-context audit, semantic normalization
drawn-base/effective geometry, local connectivity and channel identity/FIN measurements
with their neutral contracts and Python 3.10 syntax. Execution, independent reviews and supported
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

## Semantic normalization component

W007 consumes already captured W005 evidence. It produces an immutable source
semantic draft, a separate immutable target, complete typed target differences,
and query identity links with annotation seeds:

```python
from layauto_v2.normalization import from_parse_result, normalize

parsed = read_inputs(Path("tests/fixtures/w003_m1/site_config.yaml"))
if parsed.status == "success":
    normalized = normalize(from_parse_result(parsed))
```

The adapter validates the captured evidence and source bindings; normalization
performs no file IO. W006 callers can pass `InputsReady` and the already read
checkpoint, parse, tool and evidence records to `from_inputs_ready`. The
component does not access the repository or advance the attempt.

Device and net identities come from the CDL and explicit query cross-references.
All model-declared parameter axes, exact values, units and field sources are
retained. Target differences remain obligations for a future planner, including
unsupported length or structural changes. Equal source and target semantics do
not establish extraction equality, body connectivity, no-change closure or run
success. Annotation seeds retain query polygons and provenance for a future
spatial overlay; they are not layout geometry or physical connectivity.

The internal DTO/wire contracts are versioned and immutable. Validation and
independent reviews are recorded in
[W007](docs/tasks/W007-semantic-identity-normalization.md). This slice does not
construct or publish a baseline, invoke EDA tools or implement Stage 6.

## Drawn geometry and base occupancy component

W008 authenticates geometry and selected policy fields against the same captured
bytes, then retains every local GDS record and constructs exact base occupancy:

```python
from layauto_v2.normalization import geometry_from_parse_result, build_geometry

if parsed.status == "success":
    geometry = build_geometry(geometry_from_parse_result(parsed))
    if geometry.status == "success":
        layout = geometry.value.layout
        partition = geometry.value.partition
        fragments = geometry.value.fragments
```

`geometry_from_inputs_ready` takes the same five caller-read arguments as the
semantic adapter. `geometry_from_normalization_input` composes with an existing
W007 input. All three adapters revalidate captured GDS, owner documents and
header/body associations without file IO or repository access. First acquisitions
retain the selected URI spelling; later header/body references may retain
W005's historical alias resolution. Invalid
receipts raise `GeometryInputError` (a `ValueError`) with a located issue and
prior parse facts; prior W005/W006/W007 receipt errors keep their boundaries.
The builder returns a located component error for an unsupported geometry
comparator; unexpected exceptions and process interrupts propagate unchanged.

The immutable `BaseOccupancy -> BasePartition -> LayoutDraft` chain has one
drawn owner. Every source BOUNDARY remains distinct, including duplicate or
unannotated records and C1/C2. Original XY, stream positions, source bytes,
REAL8 scale evidence and layer policy are retained. Exact nominal physical
coordinates convert reversibly to canonical integer DBU. The layout's
`semantic_digest` compares top plus the physical rectangle multiset, while
content refs also bind provenance, units, policies and record identity.

`drawn-layer-edges/1` sorts each projected layer's drawn rectangle bounds into
finite half-open cells. Each occupied cell retains all exact record fragments;
coverage reconstructs every projected rectangle. Coordinate services own no
occupancy. This internal partition specifies indexing only: it supplies no
manufacturing grid, legal routing/movement space or full Stage 2 coordinate
binding. VIA/CONTACT/CUT keep only their own drawn occupancy. External body
context stays separate, and semantic targets/query seeds are unchanged.

The geometry wire codec is closed, versioned and exact. Neutral state DTOs
validate evidence consistency; a successful `GeometryResult` additionally binds
them to the authenticated captures. These are drafts, not committed snapshots,
physical connectivity, annotation coverage, body/extraction assurance, baseline,
no-change or run completion. Validation and independent review are linked from
[W008](docs/tasks/W008-geometry-base-occupancy.md).

## Effective geometry and spatial terminals

W009 consumes a successful W008 result without file or repository IO:

```python
from layauto_v2.normalization import build_effective_geometry

if geometry.status == "success":
    effective = build_effective_geometry(geometry)
    if effective.status == "success":
        draft = effective.value
        # Each LI record has a CUT result (possibly empty). Each OD record
        # has channel, S and D regions under the selected toy profile.
        record_results = draft.records
```

The component explicitly checks the captured physical/drawn operator versions
and consumed semantics. CUT acts only on its declared LI target. Exact integer
set subtraction preserves holes, disconnected results, duplicate drawn records
and every contributing CUT source. Each region has canonical disjoint rectangle
pieces and typed content references. Raw drawn records and base occupancy stay
available through `draft.base`; effective pieces are derived regions.

The selected profile recognizes one positive-area POLY stripe per OD active.
The channel must span the active's height and leave complete left S and right D
regions. Identical stripe records retain all sources; ambiguous stripes or an
unsupported split return located issues and prior captured facts. These spatial
roles do not establish canonical device/net identity or an S-to-D conductor edge.
Other geometry, W007 semantic/query evidence and external body context remain
available in the original receipt.

`normalization.effective_codec` supplies closed, versioned canonical wire and
digests for neutral region DTOs, drafts and capture-bound results. Neutral
constructors validate representation and aggregate coverage; successful results
also bind the complete W008 input and captured physical owner. A neutral value
alone is not a captured-input receipt. No manufacturing lattice, region occupancy
projection, contact graph, FIN/body extraction, annotation overlay, baseline or
run terminal is produced. Requirements, reviews and engineering evidence are
linked from [W009](docs/tasks/W009-effective-geometry-terminals.md).

## Local contact graph and enclosure audit

W010 consumes a successful W009 result and its authenticated captured rule owner:

```python
from layauto_v2.normalization import build_local_connectivity

if effective.status == "success":
    local = build_local_connectivity(effective)
    if local.status == "success":
        graph = local.value
        physical_edges = graph.edges
        local_enclosure_status = graph.local_enclosure_status
```

Each independent OD S/D region, cut LI region and original POLY/M1/local BODY
record remains a separate node. Same-layer positive area or positive length
shared edges connect; point contact does not. Declared connectors require one
positive-area region on each side before component grouping or enclosure checks.
Duplicate records retain their identities. Every node, including isolated BODY
regions, belongs to a complete local component.

Physical connector edges and their per-side T05 enclosure audits are separate.
A successful graph can carry `local_enclosure_status="violation"`; this does not
establish mandatory rule success. Enclosure checks the exact region set using
rational margins, including holes and multiple pieces. Typed references bind
sources, geometry, scope, units and operators; the versioned canonical wire in
`normalization.local_connectivity_codec` reconstructs complete graphs and audits.

The pure component preserves the complete input, drawn occupancy, semantic/query
evidence, readback attempt and separate external body evidence. Unsupported
operators or ambiguous connector endpoints return located component issues;
unexpected exceptions and interrupts propagate unchanged. It does not create
external body edges, verified net/device labels, a complete coordinate model,
all mandatory checks, a baseline or a run terminal. Scope, reviews and engineering
evidence are recorded in [W010](docs/tasks/W010-local-contact-connectivity.md).

## Channel identity and FIN measurements

W011 combines the same captured W007 identities with W009 channels and W010's
local graph:

```python
from layauto_v2.normalization import build_channel_identity

if local.status == "success":
    channels = build_channel_identity(local)
    draft = channels.value
    if draft is not None:
        measurements = draft.measurements
        source_differences = draft.differences
```

Query seeds supply exact localization evidence. Each seed retains its complete
candidate intersections and coverage; a unique partial seed can locate a channel
without claiming full region annotation. Source devices and recognized channels
must form a complete one-to-one association. Shared POLY nodes remain shared.

FIN qualification and counts come from drawn geometry: positive-area crossing,
full channel X span, and full active Y containment. Every FIN record and decision
is retained. Partial crossings or unexplained duplicate/overlapping FIN records
produce located issues and unknown affected counts. Exact channel length and
per-crossing FIN widths are compared with source CDL axes; all decidable
mismatches remain visible. Target intent and its complete differences stay separate.

A successful component result can contain source parameter mismatches. An error
can retain a diagnostic draft in `value`; its issues and unknown counts must be
checked before consuming measurements. Owner/admission errors can have no draft.
The complete source receipt, local topology, T05 audits, body evidence and
unsealed readback attempt remain available. Neither result is complete device,
net, model, body, mandatory-rule or run assurance.

The closed, versioned `normalization.channel_identity_codec` reconstructs complete
observations and capture bindings. Scope, reviews and verification are recorded in
[W011](docs/tasks/W011-channel-identity-fin-count.md).

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
