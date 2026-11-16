# W016 independent review — resource checkpoint, incomplete implementation

Reviewer `/root/w016_review` did not implement the product. Base:
`efc881d461ce2c87370f6df402ac50ae43c094e8`. Initial investigation reviewed the
accepted W015 contract, W016 requirements and existing annotation/body/terminal
producer and consumer code. This is **not a final review or PM acceptance**;
the full implementation and required acceptance matrix are incomplete. The reviewed
checkpoint is bound to the source manifest and independent identity audit below.

## Findings retained during implementation

| ID | Severity / independently observed problem | Correction and independent recheck |
| --- | --- | --- |
| R01 | Must: the initial `LocalAnalysisReceipt` used `validate_annotation_graph`, whose native graph walk does not reject undeclared instance fields. With actual W015 candidate files, acquire succeeded, then adding `undeclared_mutable=[]` to `evidence.captures[0]` still allowed receipt authentication. Reparse/dataclass equality did not detect the extra mutable field. | Execution changed the evidence and receipt boundaries to `validate_terminal_graph`. The independent [probe](evidence/review/nested_storage_probe.py) with `--expect-rejected` now raises `ValueError: terminal record has missing or undeclared retained fields`; [output and source hashes](evidence/review/nested_storage.after.stdout.json). This particular counterexample is closed; broader new-type/storage tests remain for final review. |

The first R01 reproduction was an inline actual-file probe: `issues ()`, valid
receipt ref `992a6e05a4cdf865cc768b500323a98c27bd51947d93bfaf34060ecc8bccac7a`, then
`ACCEPTED nested mutable undeclared SourceFile field`. No product input was
changed. When the same probe was saved and rerun, execution had already applied
the correction: the old `expect accepted` assertion exited 1. Its actual
[output](evidence/review/nested_storage.during-correction.stdout.json) is retained;
it is not presented as a reproducible frozen pre-fix snapshot. The explicit
post-fix invocation exited 0.

## Compatibility evidence preparation

[Fixed-input preparation](evidence/review/prepare_parity_inputs.py) copies only
actual fixed captures and the existing failure replacement declarations for
normal, extraction mismatch and body enclosure. It does not import product
algorithms or use expected/spec answers. The two revisions consume identical
absolute site URIs and unchanged bytes.

[Parity probe](evidence/review/old_interface_parity.py) compares complete DTO
structural bytes and public wire bytes for W007, W008, W009, W010, W011, W013 and
W014. Each side also decodes its own wire and checks complete DTO equality.
Gzip snapshots support exact byte comparison; report files retain lengths,
SHA-256, source/tests/config/input identity and interpreter/dependencies. W006
readback uses fixed run identity and checks unchanged unsealed attempt,
checkpoint and absence of terminal publication. Large routes are serial.

The baseline normal-direct route completed successfully; the candidate comparison
and other routes were not run. No two-sided parity result, A1–A8 completion, final
matrix or production/EDA assurance is claimed.

## Resource gate review (intermediate scope)

Independently checked the retained [first report output](evidence/local-probe-report.stdout.txt)
and `reporting/analysis.py`: the diagnostic prototype emits 262,231 bytes for
44,873 captured bytes (5.843848×), with 2,021 structurally deduplicated graph
objects. The report phase is 0.038480844 seconds; process HWM is 26,112 KiB.
Capture rows hold URI/SHA/length, byte values hold SHA/length, and the encoder
uses shared graph references; no old complete Result chain was found in the
measured report. The measured roots are local source, drawn/effective/local
connectivity, channels and annotation, not a complete `analyze_cell` result.

This independently supports the W015/W016 >2× report-size escalation trigger.
The task explicitly calls for explaining composition and returning to PM;
pausing body/manual expansion and the final matrix is consistent with that
budget gate. It does **not** establish completion of A1–A8 or a production
performance failure. A safe reduction must retain inspectable source locations,
all annotation targets/fragments/coverage/conflict/unmatched/classification,
and the exact geometry/FIN evidence. The output should be broken down by object
kind and provenance/parsed-owner payload before accepting a smaller report.

The old-interface compatibility probe is a different workload: complete public
encode/decode at seven stages. Its baseline normal-direct route exceeded 120
seconds while progressing successfully through W011 (W011 wire 54,048,729
bytes; encode/decode/DTO inspection 42.211304 seconds; HWM 328,100 KiB).
This is **not** a same-scope reference for new build+report and no 2× time/HWM
comparison is made. No other large route is being launched before PM review.

The first two compatibility attempts failed in the reviewer probe's structural
comparison, not the product DTO equality: FrozenMap is a dataclass whose
`_entries` insertion order can change legitimately on closed decode. The final
probe handles FrozenMap before generic dataclasses and sorts map keys; all
actual DTO fields, types and values remain compared. Original
[initial script](evidence/review/old_interface_parity.initial.py), first and
second stdout/stderr are retained. No old golden or product behavior was changed
to accommodate those probe failures.


## Frozen checkpoint conclusion

The reviewed checkpoint has 293 source/test/config files in the execution
[source manifest](evidence/source-identity.json). Independent byte checks found
zero mismatches; manifest SHA-256 is
`e567c32d18761d27eb66da2c61032017731b95e5779c09da9c16388e982975b5`.
The [independent audit](evidence/review/frozen-source-audit.json) binds that
uncommitted checkpoint to base `efc881d461ce2c87370f6df402ac50ae43c094e8`.
This checkpoint is reviewable but is not a completed W016 delivery.

R02 (must, static review) found that new `AnalysisAnnotationBinding` was outside
old `validate_members`' reconstruction registry. A forged new binding's
scope/version/validity could therefore avoid semantic reconstruction at the new
draft boundary. Execution added explicit binding reconstruction and revalidation
on `to_value`. The independent [actual-file probe](evidence/review/annotation_binding_storage_probe.py)
now rejects forged scope, validity and schema version, and rejects mutated scope
on `to_value`; all four assertions pass, exit 0, stderr empty. The
[full output](evidence/review/annotation-binding.after.stdout.txt) binds the tested
runtime files. This specific finding is closed; it is not a full A5 adversarial
matrix.

The reduced [diagnostic view](evidence/local-diagnostic.json) independently
measures 235,613 bytes, SHA-256
`958b5c97685f49c511720e6f019a61fb09295551b0df39669f8b96624b2da554`,
1,869 objects and 23 capture descriptors totaling 44,873 bytes (5.250663×).
This matches [composition](evidence/report-composition.json). Removed owner
payload repetition and indexed SourceRefs reduce size but do not clear the gate.
Provenance operands (25,747 bytes), drawn records (13,756), classifications
(11,518), FIN evaluations (10,230) and derived provenance (9,581) are material
remaining groups. The measured six roots exclude terminals, body/manual and
request/facet status aggregation. The resource pause remains justified.

Baseline normal-direct completed all seven stages' full DTO and public wire
roundtrips. Its sole retained compressed snapshot set is
[baseline-normal-direct](evidence/review/baseline-normal-direct/report.json)
(about 5.1 MiB, moved from `/tmp`, not duplicated). W014 wire is 23,449,288
bytes, SHA-256 `4d47883ea1e597b6c9fc60b7093aef0287c301fbd67136d1b7d7340f1476bb96`;
W014 inspection took 51.783226 seconds and process HWM was 328,100 KiB.
The report retains original absolute output paths as execution facts; snapshots
now resolve relative to its current directory. This is baseline preparation,
**not candidate parity**. No readback/mismatch/wrong-body or candidate route was
started after the gate.

- Independently run: actual-file nested-storage and annotation-binding probes;
  baseline direct W005/W007–W014 DTO/wire roundtrips; final 293-file identity
  audit; report length/hash/capture totals/composition check; source/interface
  review of the new reader/receipt, source-only kernels and annotation/body
  extraction boundaries.
- Adopted by identity: execution's targeted 58-test and mypy evidence on this
  checkpoint. No complete product matrix is adopted or claimed.
- Not covered/completed: public `analyze_cell`, full source-to-result status and
  error aggregation, terminals/body/manual integration, actual temporary-input
  A1–A6 matrix, complete new/old mutual rejection and two-sided DTO/wire parity,
  all three resource cases, Python 3.10/3.12 full tests/build/clean installs,
  production PDK/dialects/EDA and isolated-host verification.
- Recheck triggers: any changed source/tests/config/dependencies invalidates
  relevant checkpoint checks; source changes require targeted revalidation and
  a fresh required final matrix when implementation completes. PM must resolve
  the report budget/scope checkpoint before expansion; resuming source work
  alone is not permission to drop required diagnostic facts.

**Conclusion: resource-checkpoint review complete; full implementation review
and W016 acceptance remain incomplete.** Two identified defensive-boundary
findings have specific independent corrections verified. No merge, publication,
production or user acceptance is asserted.
