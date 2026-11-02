# W004 synthetic no_change fixture (W003 paths retained)

This is a synthetic input and expected output specimen, with **no Layauto
product run, production model validation, Calibre/LVS or Virtuoso execution**.
The active revision implements W004 D1=A, D2 and D3. Historical W003 reviews
and manual decisions retain their original version; PM owns their closure.

`spec.json` is the construction recipe. `oracle.json` is the separately authored
coordinate/terminal/component/rule answer. `independent-design-answer.json`
records a second investigator's integer/Fraction design calculation made before
generation; its suggested full-cell island overlay was replaced by the explicit
standalone `special/cut_islands` specimen and its own answer. None is a product
truth input. `sources.json` maps each actual dimension, design choice, rule,
condition, owner and missing production/PCell source.

The normal input is one flat `INV_M1_SYNTH`, 160 × 200 nominal nm, with 40 local
BOUNDARY rectangles. All 18 FIN stripes remain, with width 2, pitch 10 and lower
edge offset 24 nm; 5 N and 7 P crossings qualify. Six stripes are preserved but
unqualified. Each crossing has area 4 × 2 = 8 nm². CDL has ordered D G S B,
NF=M=1; **L=4n is channel length**, W=2n is toy fin width. Source, target and
expected CDL retain all pins, globals (empty), models, terminals and parameters.

## Local geometry and external body support

| Domain | Exact normal answer |
| --- | --- |
| Local physical graph | 14 effective conductor regions, 8 connector edges, 6 components |
| VSS | ON.S, LN, MN |
| VDD | OP.S, LP, MP |
| Y | ON.D, OP.D, LY, MY |
| A | G, MA |
| Local body | BN alone; BP alone; no local BTAP and no local body-to-rail edge |
| Read-only context | 6 external shapes; two separately proven B-to-rail associations |

`body/context.json` binds actual source GDS bytes, top, FRAME and exact local
BN/BP/MN/MP identities, local coordinate frame, nominal unit, selected profile
and operator. Its own bytes are bound by the query closure and F1 request.
`body/context-template.json` is a construction input, never a runtime input.
External geometry is not exported or included in the local physical graph.

```text
MN0.B -> BN --90 nm boundary edge-- BN.ext --TN.ext-- MN.ext --10 nm edge-- MN -> VSS
MP0.B -> BP --100 nm boundary edge-- BP.ext --TP.ext-- MP.ext --10 nm edge-- MP -> VDD
```

Type and each unique geometry match are checked before comparing the semantic
rail. External tap minimum enclosure is 8 nm in body, 2 nm in rail, against
T05's 1 nm requirement. Local active/body enclosure minima are 20/10 nm against
T04's 10 nm. `production_matched_body_evidence=false`, LVS `not_run` persist;
this is not a baseline-LVS frozen-body exemption or production abutment proof.

T05 evaluates 8 local connectors and 2 external taps in separate scopes. T08
compares D/G/S via local components and B via the proved context association.
T06 checks 3 local LI pairs, minimum 50 nm, requirement 2 nm. T07 checks 6 M1
pairs, minimum 5 nm, requirement 5 nm. FIN gap 8 nm and body gap 10 nm are
measured geometry, not invented minimum rules. All mandatory rules remain
required before no_change closure. Unknown support rejects; no label builds
an edge. MARK is preserved as an unannotated nonconductor.

`special/cut_islands` separately retains LB/CUTB and R08/R09, plus a remote A
conductor. LB minus CUTB yields [130,20,139,24] and [141,20,150,24], 2 nm apart.
The two fragments share the hand-selected 32×16 bucket [128,16,160,32] and
label A, yet remain separate from each other and A_REMOTE: 3 components, no
edges. This index demonstration is not a complete runtime coordinate model.

## Unique technology owners and inputs

`tech.json` only identifies the bundle and six owner files. `tech/drawn.json`
owns stream/lifecycle/connection mapping; `derived.json` owns annotation mapping
and tolerance; `physical.json` owns FIN/models/extraction/operators/body profile;
`formats.json` owns units and format capability; `coordinate.json` is explicitly
an incomplete example reference; `rules.json` owns mandatory rule conditions
and thresholds. The fixture helpers actually consume these files; duplicate
owner keys reject. Models are referenced from CDL syntax, not copied into it.

Site, export/validation policies and limitations retain their entrances.
Site outputs.core/directory must agree exactly with export policy names/path;
conflicts reject with no priority, override or default. MR-040 mechanism changes
remain deferred. Spec/oracle/expected and body template are construction or
comparison inputs; source GDS/CDL, selected body context, raw/header and selected
tech/config/policy are the input evidence closure.

Nominal 1 nm is the versioned `w004-toy-unit-choice/2`, retained from the authored
W003 toy choice; GCD does not create a unit or process rule. GDS UNITS preserve
REAL8 bytes and exact rational decode, nominal scale, delta and half-mantissa-ULP
bound. Both fields bind independently. Original signed XY remain integers with
no snap. Output tick representability/range is a separate check. Source writer
uses Fraction; expected writer uses KLayout. KLayout geometry serialization is
independent, but its UNITS payload is normalized by the same nearest56 encoder;
`expected/unit-provenance.json` preserves originals and reconstruction hashes.
The verifier independently exact-decodes units and reads geometry using KLayout.

## Single Calibre-like synthetic dialect

`query/dialect.json` identifies **calibre_like_synthetic/2** and hashes the legacy
format descriptions used as sources. Nine raw inputs provide four capabilities:

| Capability | Raw inputs | Normalized |
| --- | --- | --- |
| instance xref | iXref.temp | instance_xref.yaml |
| net xref | nXref.temp + net_names.txt | net_xref.yaml |
| device regions | device_info_Q17.txt, device_info_Q93.txt | device_regions.yaml |
| net regions | net_shapes_n_a/n_y/n_lo/n_hi.txt | net_regions.yaml |

Xref `# SVDB: End of header.` ends only the header. Xrefs have no EOF marker;
all rows are consumed and mapped. NET NAMES has an explicit count and
`END OF RESPONSE`; Device_Info/Net_Shapes have metadata count, polygon vertex
count and the same response terminator. `query/requests.json` explicitly binds
response objects, rather than deriving identity from filenames. Net index is
the **one-based ordinal** of NET NAMES, opaque outside this query run; nXref
joins by layout net name. Normalized records are 2/4/2/8 respectively.

Geometry raw vertices are **(y,x), integer/20000 µm**. Thus `400 1160` is
`y=20 nm, x=58 nm`, precisely. Full vertices and named rational bbox values are
retained; exact quality follows a lossless four-corner rectangle proof plus
registry, not a nonexistent raw quality token. Each normalized field carries
its raw/manifest sources, line/token or JSON pointer, lexeme, bytes hash and
conversion/derivation. Metadata and section tuples remain opaque where legacy
meaning was not verified. NET NAMES opener 20000 is not a geometry unit source.
This selected synthetic subtype is not a verified production Calibre dialect.
No legacy runtime, float rounding, bbox downgrade or intermediate toy raw path
is used. Normalized files are comparison caches, never sole inputs.

## Checks, failures and reproduction

D3 check identity/input/proof/status/original obligation mapping is in
`validation_policy.json.check_obligations` and the human/machine reports.
Local GDS/CDL/JSON semantic readback, production independent downstream
open/syntax and Virtuoso/SKILL dry-run are separate. Original `virtuoso_readback`
remains deferred with explicitly unresolved scope; it is not silently renamed
away. Calibre old/new names have an explicit mapping. All real-tool checks
remain deferred/coverage none/requires_review; runtime and return code null.

`failures/cases.json` retains C01–C22 plus seven body witnesses. Apply every
replacement and removal to an independent normal copy. Nonbinding cases have
current source/raw/context/closure/cache hashes, including actual malformed raw.
Only C06/C07/C21 deliberately retain the named hash/top/cache defect. C22 tests
missing required body operator; absence of local BTAP itself is valid.
The helper detects input/geometry witnesses; future typed product failure,
zero ECO and no normal publication remain unexecuted runtime obligations.

From a Python ≥3.10 environment with KLayout 0.30.12 and matplotlib:

```sh
python -B tests/support/w003_generate.py --output /tmp/w004-regenerated
python -B tests/support/w003_verify.py --fixture tests/fixtures/w003_m1 --regenerated /tmp/w004-regenerated
python -B tests/support/w003_record_examples.py
python -B tests/support/w003_plot.py --fixture tests/fixtures/w003_m1 --output /tmp/w004-layout.png
```

Generation only writes the selected fixture directory. Record `--write` authors
samples, never runs a pipeline. Verification actually materializes all overlays;
`--work` preserves them in a chosen empty directory. Byte regeneration is checked
separately from correctness. The W004 execution record identifies tested snapshot,
commands, environment, output, independent review and unrun obligations. Normal
and eight failure record combinations remain expected samples, not production
results. PM alone may accept W004, close W003 and dispatch M1 parser work.
