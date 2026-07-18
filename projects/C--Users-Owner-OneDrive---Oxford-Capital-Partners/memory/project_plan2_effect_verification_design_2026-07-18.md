---
name: project-plan2-effect-verification-design-2026-07-18
description: "Design memo (not yet implemented) for Plan 2 of the 2026-07-18 setup-improvement effort — an output_contract: schema + a 10-task roster to close the 'dispatch != effect' gap in automation-health-monitor. Awaiting Gabriel's approval on schema/roster/values/gaps before any live SKILL.md is retrofitted."
metadata: 
  node_type: memory
  type: project
  originSessionId: 5900e68d-2914-4c15-9f60-65efc5d0a2c2
---

# Plan 2 — Effect-Verification Layer: Design Memo (2026-07-18)

Design-only pass, no live SKILL.md touched. Full memo (schema YAML, all 10 tasks' proposed contract values, integration sketch) captured in this session's transcript — condensed decision points below; expand from there if a retrofit session needs the full detail.

## What it solves
`automation-health-monitor` checks "did it fire" (`lastRunAt`), never "did it produce its declared output." This exact gap caused the northridge/brockton summary email to silently never send while the task showed complete. A new `output_contract:` SKILL.md frontmatter block (superset of the one already live on `ora-deal-aging-sla`) lets each task declare its expected artifact (Notion page, sent email, file, Outlook draft, registry mutation), a freshness window, and count semantics — checked additively alongside the existing hand-maintained producer-consumer table, never replacing it in this pass.

## Key design point: primary signal vs. conditional alarm
Two candidates (`ora-task-integrity-guard`, `ora-doctrine-integrity-guard`) are silent-by-design on a clean run — checking their alarm email as "the output" would false-alarm every healthy day. Both write an internal state file every run regardless of outcome; that's the correct contract target (`is_primary_health_signal: true`).

## Roster (10, ranked by real silent-failure history)
`ora-am-brief` · `ora-pm-ledger` · `ora-master-workbook-ingest` · `ora-weekly-hygiene` · `ora-deal-command-board` · `ora-deal-aging-sla` (already has a minimal contract) · `ora-broker-touch-cadence` · `ora-task-integrity-guard` (already suffered a real 7-day silent outage 07-09→07-16) · `ora-doctrine-integrity-guard` (Hard Invariant 4-adjacent) · `ora-cowork-heartbeat` (LAMS — sourced from automation-health-monitor's table, not an independently-read SKILL.md; needs re-verification at retrofit time).

## Gaps found (flagged, not fixed this pass)
1. **`ora-deal-command-board` has no guaranteed durable output today** — renders in-session via `show_widget`, Ops Hub posting is optional in its own SKILL.md. Contract unenforceable until that posting becomes mandatory.
2. **`ora-deal-aging-sla`'s "post one row" is ambiguous** — new dated child page vs. append to an existing page's body; the latter is much harder to freshness-check. Recommend standardizing every completion-posting task on the child-page pattern.
3. **`ora-weekly-hygiene` has 10 blocks; only 3 are contract-checkable as currently written** — the rest have no durable artifact beyond an unpersisted chat-log line.

## Approval checklist (Gabriel)
- [ ] Schema — approve as-is or amend field names/types
- [ ] Roster — approve the 10, or swap in `ora-financial-code-integrity-sweep` / `ora-sofr-direct-prefetch` (considered, not included)
- [ ] Per-task values — page IDs/cron expressions sourced from each SKILL.md as of 2026-07-18, not independently re-verified against live Notion; spot-check before retrofit
- [ ] Gaps 1-3 — fix as part of the retrofit, or track separately in `open-items-tracker.md`
- [ ] Integration sketch — confirm additive-only approach (legacy table stays; new check runs parallel) before implementation

## Status
PLANNED. No live SKILL.md edited. `automation-health-monitor` untouched. Retrofit is a separate follow-up session, one task at a time, after this checklist is cleared.
