# W012 A1 before-source package reconstruction

These are **new packages rebuilt during this A1 execution session** from Git commit `7f7c1304bdafd941791421cef64864fb1616303c`. They are not the original W011 wheel/sdist blobs and are not performance samples.

The source was acquired by `git archive` for exactly `layauto_v2/`, `pyproject.toml`, and `README.md`, then extracted only into `/workspace/w012-a1-before-package/source`. The measured `/workspace/w012-a1-before` and main checkout sources were not written. The 102 selected source files match `performance/frozen-identity.json -> sources.before`; each of the 100 runtime members in **both actual package files** matches those before-source hashes and the original W011 runtime manifest.

Build used the already prepared independent CPython 3.12.14 environment, `build==1.6.1`, `setuptools==79.0.1`, with `--no-isolation`. This records an explicit reconstruction environment and avoided network/dependency work during the active final test matrices. No product installation, smoke, test matrix or benchmark was run. Byte-compiling-disabled warnings are retained in the raw build output; package construction and all member checks passed.

Actual accessible artifacts:

- `dist/layauto-0.2.0-py3-none-any.whl`, SHA256 `ffff7cd43c4680024fda7efdc9f1fc912e2273b0405c9fb1645f2cb8e9212441`
- `dist/layauto-0.2.0.tar.gz`, SHA256 `afb9db801fd45801a8e0ec69485ee65178b707ac21fde1b2ed5d44f067b98a94`

`package-identity.json` records both full member manifests, actual bytes/SHA, environment, command identities and the classification above. `before-source-identity.json` records the source/member comparison and the two upstream manifest hashes; `before-source.tar` preserves the actual Git archive command output. Commands, stdout/stderr, metadata discovery failure and reconstruction script are retained. `evidence-manifest.json` is finalized after all command output files closed.

To integrate this evidence, copy this directory except the working `source/` tree into new `W012/A1/before-package/` attachments. Do not replace any W011 archive or existing P1/P2 report. Source reconstruction is already accessible through the retained tar and fixed Git revision.
