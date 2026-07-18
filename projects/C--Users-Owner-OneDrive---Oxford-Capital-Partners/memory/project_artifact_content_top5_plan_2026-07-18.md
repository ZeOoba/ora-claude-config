---
name: project-artifact-content-top5-plan-2026-07-18
description: "Fable-ranked top-5 highest-impact OPEN items found inside 3 artifacts' substantive content (not doc-accuracy — that pass is separate/done): northridge/brockton run closeout, ora-pm PortalDashboard /100 bug, LOI-throughput line, ora-cowork-heartbeat write failure, 511/275/monthly-close verification. Execution-ready plans in file. Status: PLANNED, not yet executed as of 2026-07-18."
metadata: 
  node_type: memory
  type: project
  originSessionId: 5900e68d-2914-4c15-9f60-65efc5d0a2c2
---

# Top-5 Highest-Impact Open Items — Artifact Content Review, 2026-07-18

Companion to the 2026-07-18 artifact **accuracy** remediation (see event_log.md same date) — that pass fixed factual errors IN the 3 artifacts (schematic-working, review-v02-working.md, Claude Code Setup Audit) and republished them. This pass is different: it reads the now-corrected artifacts' *substantive content* — open items, recommendations, unimplemented action plans — cross-checks each against live ground truth (registries, event_log, git, send-log), and ranks the 5 highest-impact items still genuinely open. Produced via a Fable-model pass per Gabriel's request, re-verified against live sources (not the artifacts' own claims).

**Governing constraint found during verification:** Gabriel ruled 2026-07-17 (ops_decision_log) that Tier 3/4 hygiene items from the setup-review plan are **dropped, not deferred** — explicitly do not pick these up. Setup-audit cadence is also frozen ~60 days (until ~2026-09-15).

## Top 5, ranked by real consequence

1. **Close the loop on `ora-uw-northridge-brockton-full`** — the run fired 2026-07-18, built real deliverables (IC memos, underwriting workbooks, comparison note for 2900 Northridge Dr NW + 4331 Brockton Dr SE), but the summary email never sent and nothing has been QC'd or logged to Notion. Real deal work-product, currently undelivered.
2. **ora-pm PortalDashboard divide-by-100 bug** — a live, tenant-facing financial display defect (tenants likely see 1/100th of balance owed) in production; the other 2 criticals from the 07-16 audit are fixed, this one has no fix commit. Direct cash-collection/tenant-trust consequence.
3. **Build the LOI-throughput line into `ora-friday-closeout`** — the one item Gabriel explicitly carried forward from the whole setup-review plan; everything else in its cohort is already built.
4. **Root-cause `ora-cowork-heartbeat`'s failing unattended writes** — twice-confirmed live failure (2 ACTION REQUIRED alarms), partially blinds the LAMS fleet's dead-man liveness signal.
5. **Verify 511/275 deal re-screens + monthly-close skill currency before 08-01** — both "launched but never confirmed," against a documented Workflow silent-failure class; cheap to check now, expensive if silently dead into the August close cycle.

## Execution-ready plans, Gabriel-decision gates, and what NOT to pick up

Full plans (verified starting state, numbered steps, done-when criteria, exact file paths) captured in this session's Fable output — condensed below; expand from the source agent transcript if a fresh execution session needs the complete step list.

**Gabriel-decision items (not auto-executable):** (1) close the TERMINAL setup-review-closeout chip; (2) approve retiring 5 spent one-time registry entries; (3) ora-pm git-history purge for declassified E. Fulton terms; (4) one supervised "Run now" click (or a Cowork-surface session) to fix `ora-cowork-heartbeat`'s missing tool grant — Code cannot write the LAMS registry; (5) any outbound broker contact following the 511 re-screen (Hard Invariant 1).

**Explicitly excluded — already done or out of scope, do not re-pick-up:** Tier 3/4 hygiene (dropped by ruling); any new setup audit (frozen to ~09-15); broker touch cadence, deal-command-board, parcel-data-recovery, OneDrive Business/Personal split, B3 burn-in, deal-recon guardrail, governor-drift FP fix, GitHub MCP disambiguation — all verified live/done even though some artifact cards still read stale.

**Key paths:** deliverables `Business\Investment Candidates -- 2026\outputs\`; send log `~/.claude/scheduled-tasks/_shared/send-log.txt`; ora-pm repo `C:\Users\Owner\ora-pm`; ora-pm audit `Claude_Workspace\02_Outputs\2026-07-16_ora-pm_AuditReport_v01.md`; fleet reporter `~/.claude/maintenance/fleet-status.py`.
