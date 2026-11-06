# W010 public-contract and capture-boundary review

Reviewer: `/root/code_review/boundary_review`, not involved in the plan, product,
or formal test implementation. Scope: A1/A6/A7, with the new neutral contracts,
captured result and wire, and their consumed W009/W008/semantic/publication chain.
Reviewed base `9758a157115cc22d91ce095ac2002209b9f210d3` to frozen product
`0f5029df935bc0acd106aad1bc2be81304d4f442`. Product and formal tests were not changed.

## Code inspection

No mandatory finding was identified in this specialist scope.

- `LocalConnectivityDraft` rebuilds the complete neutral effective aggregate,
  operator binding, nodes, same-layer and connector edges, independent side
  audits, and all components. Exact tuple comparison rejects missing, extra,
  duplicated, regrouped, foreign-bound or false-audit content. Isolated nodes
  participate in the component rebuild.
- Neutral values establish representation consistency. The captured result
  separately authenticates its complete original W009 object graph before a
  codec can copy values, decodes its full retained receipt, and compares the
  restored input. A successful captured graph is then rebuilt with the actual
  captured rules payload and `tech.sources[6]`, which matches GeometryInput's
  fixed owner ordering. A different neutral rules origin cannot be certified
  as that capture.
- New constructor collections accept only native list/tuple, take one snapshot,
  and validate the stored snapshot. Original object graphs are checked using
  exact type identity for native values and registered DTOs before encoding.
  Mutable equal objects, subclasses, metaclass equality and mutable Fraction
  components therefore cannot be folded into an apparently safe value first.
  No normal public-API writable caller alias was found. Private mutation that
  bypasses native/frozen value contracts is not treated as an API finding.
- The new codec has closed fields/tags and canonical reconstruction checks. It
  does not broadly translate constructor failures. The consumed captured
  publication records and semantic receipt/readback constructors are in the
  existing explicit passthrough paths; geometry/effective children are decoded
  before enclosing constructor checks. The local expected-policy catch also
  leaves its handler before reconstructing the error result, preserving a
  later unexpected failure's existing context.
- New domain/state code has no file, repository, pipeline, parser or legacy
  runtime dependency. The full captured input/body evidence remains retained;
  graph records do not carry verified device/net attribution. Coverage declares
  local connector sides only and preserves deferred external-body, full-rule,
  coordinate, extraction, lifecycle and publication obligations.

Read: root AGENTS, README, collaboration/environment instructions, W010 A1–A8,
the relevant architecture clauses, the four new runtime files, consumed closed
graph/value and nested codecs, and relevant formal W010/W009 boundary cases.
The inherited task reading also supplied the actual owner and upstream scope
contracts; this specialist conclusion does not substitute for the main review's
geometry, performance or engineering-evidence audit.

## Independent dynamic checks

The independent [probe](boundary-probe.py) uses the public reader and run-entry
APIs, without importing formal test helpers. The official invocation is:

```sh
PYTHONPATH=/workspace/Layauto /workspace/.venvs/w010-dev312/bin/python -B docs/tasks/W010/review/boundary-probe.py > docs/tasks/W010/review/boundary-probe.stdout.txt 2> docs/tasks/W010/review/boundary-probe.stderr.txt
```

The single invocation exited **0**, on Python **3.12.14**, in **1041.084 seconds**.
The [result](boundary-probe-result.json) has `status="passed"` and
`failures=[]`; [stdout](boundary-probe.stdout.txt) records its summary and
[stderr](boundary-probe.stderr.txt) is empty.

- Actual W005 direct and W006 readback composition produced equal graphs. The
  captured compositions ran with file-access entrypoints blocked, and retained
  the unsealed attempt unchanged.
- **166** selected malformed public-record field replacements explicitly raised
  `ValueError`. All eight new public record kinds also roundtripped. This is a
  finite field/tag sample, not an exhaustive proof of all malformed bytes.
- **220/220** injected constructor failures retained the same exception object,
  existing cause, existing context and suppression flag. The matrix covered
  **96 direct** and **124 readback** outer paths across local, effective,
  geometry, semantic and captured publication constructors. TypeError, KeyError,
  KeyboardInterrupt and SystemExit each had **55** cases. Both values of the
  suppression flag were exercised; every row is retained in the JSON.
- **4** caller-list collection copies remained unchanged after their input lists
  were cleared; **8** mutable-text subclass inputs were rejected.
- The result's four new runtime source hashes still equal the reviewed files.
  The observed HEAD remains the frozen product head above.

The [receipt](boundary-receipt.json) binds the command, observed exit/result,
source hashes and probe/output/report artifact hashes. The script wrote one
final checkpoint rather than intermediate progress, so its case/phase was not
observable while running. No duplicate run or shortened replacement matrix was
started, and no probe or output was rewritten after completion.

**Specialist conclusion: no mandatory finding in this A1/A6/A7 scope.** This is
independent review evidence for the main reviewer, not PM acceptance or a claim
of complete Stage2/M1, external-body, production or full mandatory-rule success.
