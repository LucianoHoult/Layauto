# W008 integration evidence, 2026-11-03

PR #62 merged reviewed head `eb15a666010cf7f5fa82c97880a4d0e8f023fa8f`
into main as `16159c7edb2d085ab4987bff27ec11c5b5f53294`.
The merge tree equals the reviewed head tree; the 235-entry product manifest
matches. The parent [integration receipt](../integration-receipt.json) records
the final disposition and distinguishes new checks from adopted evidence.

- `premerge-audit.json` and `premerge_audit.py`: direct read-only verification
  of the new independent review's scope, hashes and command receipts. This did
  not repeat product tests or the prior archive/installation audit.
- `github-merge.json`, `github-pr.json`, `github-checks.json`: GitHub connector
  results. Empty status/workflow lists do not represent CI success.
- `merge-identity.json`: actual Git parents, tree equality and manifest checks.
- `run_combination.py`, `combination-check.json`: targeted tests run on the
  actual merge commit in the existing PM Python 3.12 environment. This is not
  a fresh package installation or another full 730-test run.

Absolute paths and HEAD assertions describe the original execution. To replay,
copy scripts to a temporary directory, use a separate checkout at their recorded
HEAD, and adjust local paths/Python environment. Keep the preserved outputs
unchanged. Full test, typing, build and installation evidence from the identical
reviewed product remains in the original W008 verification/PM/review records.

Task-document hashes in earlier receipts identify the task at their respective
commits. Subsequent PM status and integration additions change that document;
historical execution/reviewer text and original evidence are preserved.
