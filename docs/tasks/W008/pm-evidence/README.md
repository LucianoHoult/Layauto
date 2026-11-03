# W008 PM checks, 2026-11-03

These are the preserved outputs of the PM receipt checks on
`baad5347627db194649430cf6b0f5ebf0aa1165e`. Product and test bytes equal delivery
`aced62b0adda35fe7bcd8284a7354badc5b03649`; the intervening commit only adds
U06 clarification in current-work and roadmap. The parent [PM receipt](../pm-receipt.json)
separates directly executed checks from adopted execution evidence.

The original 84-entry evidence manifest includes the delivery-time W008 task
document. Its recorded hash remains recoverable at `aced62b`; the subsequent PM
status/receipt additions intentionally change that document. Its A1–A8 and
execution/reviewer text are unchanged. The other 83 evidence entries and all
235 source/test/config entries still match. The historical manifest is retained.

- `environment.json`, `pytest.json`, `mypy.json`: actual Linux Python 3.12
  checks using an existing environment, not a clean installation.
- `cr01-check.json` and `input-check/cr01_check.py`: run the unchanged original
  CR-01 reproducer and require its repaired, located rejection with nine
  completed facts retained. The historical reproducer itself asserts the old
  success and therefore is not a standalone passing regression on fixed code.
- `geometry-check/`: delegated, read-only mathematical and aggregate checks;
  16 bounded probes. Large integer DTO checks do not expand GDS input capability.
- `evidence-audit/`: delegated standard-library/Git/package-byte audit;
  32 consistency checks. Recorded Mac test, build and installation executions
  are adopted; the original Mac installation directories were not accessed here.

Scripts and original receipts were copied without changing their bytes. Their
absolute paths describe the actual run. To reproduce elsewhere, copy the scripts
to a temporary directory and supply the checkout path or set the documented
working directory/PYTHONPATH. The evidence audit intentionally checks the exact
`baad534` historical HEAD; use a separate checkout at that commit. It writes its
results beside the script, so do not run the preserved copy in place and overwrite
this historical evidence. The geometry probe expects the repository as cwd;
the CR-01 wrapper takes the repository as its sole argument.

No product, fixture, expected answer, or original execution/review evidence was
changed by these checks. No main merge, next task, full physical-state conclusion
or production validation is implied.
