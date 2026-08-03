---
name: project_intelligence_platform_roadmap_ratified_2026-07-29
description: "RATIFIED master roadmap for the new Oxford Intelligence Platform initiative (facts/documents/edges layer on the existing warehouse) — merged to main 2026-07-29; Phase 0 kickoff is the next open action."
metadata:
  node_type: memory
  type: project
  originSessionId: f93fd8a8-7997-4b39-bf67-904099b7fd24
  modified: 2026-07-29T04:30:05.361Z
---

Full architecture review (critique + design) and the resulting master implementation roadmap were produced 2026-07-28/29 in a Code session, then reviewed and merged by Gabriel same day.

- **PR:** [ZeOoba/oxford-command-center#246](https://github.com/ZeOoba/oxford-command-center/pull/246) — **MERGED** 2026-07-29T04:15:10Z, merge commit `b1390b88`, verified via `gh pr view --json state,mergedAt,mergeCommit`.
- Docs now live on `main`: `docs/roadmap/intelligence-platform/{README,00-master-roadmap,01-agent-roadmap,02-standards-testing-quality}.md` + `docs/adr/` (new ADR convention for this repo — 5 initial ADRs on the hardest-to-reverse calls: workbook-wins precedence, relational not graph-DB storage, natural-key entity identity, schema-level confidentiality tiering, deterministic-compute/LLM-narrate boundary).
- Working branch/worktree (`docs/intelligence-platform-roadmap`) deleted post-merge; local `main` fast-forwarded to `b1390b88`.

**Why:** [[procurement-stance-deepen-not-migrate]] and the fact that ~70% of "Priority 1" (Financial Intelligence warehouse) is already built and merged made the original from-scratch "Bloomberg Terminal" vision brief unrealistic as written — the roadmap extends the existing `oxford-command-center` warehouse (SQLite facts/documents/edges tables) rather than standing up new infra (no graph DB, no vector DB, no bespoke OCR pipeline). Only Phase 0 (foundation: schema, backup, confidentiality tiering, ADR bootstrap) and Phase 1 (decision/outcome-tracking loop — the highest-value gap) are ticketed; later phases are deliberately purpose-only, with task-graph detail deferred to just-in-time `writing-plans` at kickoff. Reason cited in the roadmap itself: `docs/superpowers/specs/2026-06-13-ora-intelligence-platform-master-plan.md`'s pre-baked gap list went stale within five weeks — a 2-year pre-ticketed plan would repeat that at larger scale.

**Next open action — Phase 0 kickoff, deliberately held until on/after Mon 2026-08-03 (Gabriel, 2026-07-29: "let's start Phase 0 after Friday" — Fri 2026-07-31 is the last day before; treated as the next business day, adjust if he meant the weekend literally):** no `architecture/status.json` entry exists for this initiative yet — the first Phase 0 task creates it. The Phase 0 task graph is already fully specified in `00-master-roadmap.md` (IDs `IP-0.1`–`IP-0.10`); a future session should start directly from there rather than re-planning. **How to apply:** before starting any Intelligence Platform work, read `docs/roadmap/intelligence-platform/README.md` on `main` first (don't re-derive it). Do not start `IP-0.x` work before the held date without Gabriel re-confirming — this delay was an explicit instruction, not idle time.
