---
name: project-automation-audit-interim-2026-09-09
description: Interim ora-setup-audit pass (not a numbered Automation Audit revision) — 5 easy/high-value same-day fixes found by verifying R23 residuals live plus one fresh doctrine-probe WARN, with a same-day execution plan Gabriel approved.
metadata:
  type: project
---

Interim pass, 2026-09-09, scoped to Gabriel's ask: "5 highest-value items fixable today + an execution plan." Not a full 4-thread audit and NOT published as an Automation Audit revision — findings below still need folding into the next full numbered pass (would be Rev 24) against [[project_automation_audit_rev23_2026-09-06]].

**Method:** verified R23's still-open items live (3 days later) rather than re-deriving from scratch, plus one fresh `doctrine-integrity-probe.py` run surfaced a new self-flagged WARN.

**Five findings, ranked, all confirmed live via direct read (not carried from R23 prose):**

1. **NEW — CLAUDE.md workspace-pointer stale.** `doctrine-integrity-probe.py` WARN: "last verified 2026-08-09 (31 days ago > 30)". Crossed threshold 2026-09-08. Fix = re-verify pointer target + bump verified-date. Touches CLAUDE.md → blast-radius, needs Gabriel's in-turn nod even though it's a metadata bump.
2. **`non_fleet_task_sweep` is a dead detector, not a stalled one.** Source `.py` is gone entirely (no archive copy found — can't undo, but can stop it lying) — only `__pycache__/non_fleet_task_sweep.cpython-313.pyc` (2026-08-04) and a matching 36-day-stale `.log` remain. This will re-trip as a false "stopped writer" alarm every future audit pass until archived. Fix = move both to `/archive/` (HI6), note retirement. Low blast radius (Claude-system path).
3. **Two LAMS spec folders confirmed orphaned** — `ora-heartbeat-fix-verify-0718am` (Jul), `ora-routine-pause-resume-lams-08-21` (Aug) — grepped the live LAMS registry (`local-agent-mode-sessions/a6ad2c61-c3c8-4a48-98a5-e40c1db22ad3/583f08bc-.../scheduled-tasks.json`) for both ids: zero hits. Confirms R23-14's "dark LAMS specs" finding, not previously actioned. Fix = archive both folders (HI6). Low blast radius.
4. **`reference-backup-coverage-probe.py` (OI-153, built 2026-08-14) is wired into ZERO scheduled task, hook, or the doctrine probe.** Its embedded cousin — doctrine-integrity-probe.py's own "Backup-coverage sweep" (line ~1971) — checks something narrower ("opt-in review candidates", currently 0) and does NOT import or call this script. The standalone probe's "26-day-stale log" isn't a stopped producer, it never started. Fix = either register it onto an existing daily/weekly guard via `register-scheduled-task` (supervised MCP tool, not JSON splice), or explicitly mark it manual/on-demand and drop it from staleness watch. Touches the scheduled-task registry → needs the single-writer check immediately before executing (registry-membership.log was last 09-07 at time of this pass — re-check freshness before acting).
5. **Highest-value unresolved R23-9 trigger collision: `investor-relations` vs CLAUDE.md's ratified "LP mail → communication-intelligence / legal-intelligence" canon.** Of the 5 collisions R23-9 left unarbitrated, this is the only one touching an external, LP-facing send path — real routing-ambiguity risk, not just catalog noise. Fix = trim `investor-relations`' SKILL.md description to explicitly defer LP correspondence to the canon skills, keep its own scope to LP reporting/analytics. ora-skills repo confirmed clean/synced (`0fd7ad7`, no conflicting uncommitted work) at time of this pass — safe to claim.

**Why:** Gabriel asked for a same-day punch list, not a full audit cycle; spending the full 4-5-thread investigation would have blown the EOD deadline the request itself set.

**How to apply:** Items 2–3 are archive-only/reversible (HI6) and were treated as pre-authorized once flagged; items 1, 4, 5 cross a named blast-radius surface (CLAUDE.md / scheduled-task registry / skill routing description) and were gated on Gabriel's go-ahead before editing. The full R23-9 collision list (5 pairs total) and the R23-8 cross-link doc gap are NOT included here — deliberately deferred to the next full numbered revision to keep this pass inside the EOD scope. Do not re-report items 2–4 as "new" in Rev 24 — they're R23 carryovers being closed, not fresh finds.
