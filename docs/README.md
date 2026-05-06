# Layauto docs

This directory tracks **what the project is**, **what has been done**, and **what is not done yet**, split across three living documents plus this index.

| File | Owns | Update cadence |
|------|------|----------------|
| [`architecture.md`](architecture.md) | Project description: principles, tiers, four-layer atomic-edit architecture, pipeline flow, data model, configuration bundle, layer stack, DRC rule encoding, key-file index. | Updated when an architectural decision changes. Rare. |
| [`changelog.md`](changelog.md) | Time-ordered record of every shipped change. One block per milestone (M1–M6b plus the config consolidation), with date, branch, summary, files touched, and acceptance evidence. | Append-only. Add an entry when a milestone or sub-milestone ships. |
| [`backlog.md`](backlog.md) | Things not implemented but worth considering. Open milestones (M6c routing, M6d routing-dependent macros, M7 SKILL/Calibre closure), residual deferred items lifted from completed milestones, performance follow-ups, production-integration TODOs. | Add when a deferral is identified; remove when shipped (and the entry moves to `changelog.md`). |

## Where to start

- **New contributor?** Read `architecture.md` end-to-end, then skim `changelog.md` to see what's actually shipped, then `backlog.md` for what to pick up.
- **Picking the next task?** Open `backlog.md`. The "Next milestone" section at the top is the recommended starting point.
- **Debugging a behaviour?** `architecture.md` § "Pipeline flow" + § "Key file index" point you at the right module. `changelog.md` shows what each module-level change was meant to do.
- **Updating a design?** Edit `architecture.md`. If the change is large enough to mark a sub-milestone, append to `changelog.md` once shipped.
