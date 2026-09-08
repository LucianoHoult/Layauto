# Working on Layauto

## Start and resume

- Read `README.md`, then `docs/collaboration/rules.md` for the requested role
  (PM, execution, or review). Use `docs/current-work.md` to locate current work;
  an explicitly named task or review scope takes precedence over that pointer.
- Inspect the repository, branch, HEAD, staged/unstaged changes, and untracked
  files before trusting a handoff. Preserve pre-existing changes. A short prompt
  does not authorize committing, pushing, or merging beyond the user's scope.
- Before changing a path, find and read its applicable ancestor/local
  `AGENTS.md` files. Do not assume starting at the root loaded all descendants.
- Read the task's architecture references and affected producer/consumer
  contracts. `docs/README.md` provides a starting route. Summaries and old
  proposals do not replace the normative architecture.

## Project boundaries

- `docs/architecture.md` is the active v2 product architecture. New runtime work
  belongs in `layauto_v2/`; `legacy_mvp/` is archived reference code, not the v2
  baseline or a runtime dependency.
- Keep collaboration rules, product contracts, environment instructions, and
  task results in their documented owners. Update the source and its links
  together rather than creating a second active definition.
- Follow the role, evidence, and escalation rules in
  `docs/collaboration/rules.md`. Ordinary authorized work should continue without
  asking the user to approve every internal step.

## Environment and outputs

- Read `docs/environment/local-setup.md` before installing or running project
  checks. On this Mac use `$HOME/.virtualenvs/layauto/bin/python`; the system
  `/usr/bin/python3` is too old. Other hosts need their own Python 3.10+ environment.
- Keep environments outside iCloud. Root pytest excludes the legacy archive;
  use the documented legacy invocation when those tests are relevant.
- Some legacy outputs and bytecode are tracked. Disable bytecode/cache writes
  for legacy checks and use separate output paths for demonstrations.
- Read `docs/environment/remote-development.md` when changing hosts or using
  cloud tasks. Ensure the selected checkout actually contains the task records,
  code, and evidence needed for the handoff.
