W012 A1 environment/tool handoff to root

Ready interpreters:
  /workspace/w012-a1-env/dev310/bin/python  CPython3.10.22
  /workspace/w012-a1-env/dev312/bin/python  CPython3.12.14

Existing /workspace/.venvs/layauto was not modified. No layauto product package was installed in either dedicated dev environment; root/frozen source cwd supplies runtime imports during checks. Core/dev dependency versions are based on the recorded W011 environment, installed from normal pip sources with inherited proxy/CA. No gdstk/klayout extras were needed.

Tools ready for root to copy into new W012/A1 attachments:
  tools/prepare_final.py
  tools/installed_smoke.py

Runner updates versus untouched W011 historical source:
  --baseline-test-count defaults1605 (parameterized check), default baseline collection uses W011 verification/collection-312.stdout.txt.
  Full original baseline ID retention and actual --expected-tests are checked for both interpreters.
  Runtime manifest requires100 files; new tests can increase total source/test/config count.
  Existing dual collect/fullpytest/strictmypy/pipcheck/build/cleaninstall/source-external -I -B smoke/package-source hash checks remain intact.

Smoke updates:
  Captured31 SourceFiles hash and completed-source resolution, body identity, complete18 FIN evaluation identity/source/width sets, fixed14nodes/8edges/6components/16T05 audits/pass, checkpoint unchanged and no terminal.
  Complete Result encode/decode/digest/source/local/body/crossing checks inherited unchanged.
  Installation smoke mismatch URI remains random (existing method); use only correctness, never same-condition performance comparison.

Evidence:
  evidence/receipt.json; evidence/manifest.json; requirements-310.txt; requirements-312.txt; run_command.py; all per-command stdout/stderr/json and pip install reports.
  Preserved initial read-only UV cache failure, sandbox UV install and pip-proxy failures, successful escalated retries. No current blocker.

No heavy product commands ran in this task. Tools were checked by --help/AST and baseline collection1605-count availability only. Root must freeze/review the final tool copies then run against new source.

Network condition: final runner build isolation and clean installations need approved network access (or complete offline package preparation). In this executor ordinary sandbox cannot connect to inherited proxy; successful setup commands used require_escalated with normal inherited network/CA. No proxy settings or credentials were overridden.
