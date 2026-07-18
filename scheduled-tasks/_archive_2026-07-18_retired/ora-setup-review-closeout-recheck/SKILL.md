---
name: ora-setup-review-closeout-recheck
description: One-time re-check of the setup-review-closeout chip's DONE-gate after the 2026-07-17 16:01 ET northridge/brockton fire — closes chip if all 3 watches fired clean, else ABORTED with reason.
---

STATE AS OF 2026-07-16 (session that authored this task) — re-verify every claim below against live ground truth before acting; treat every line as a hypothesis, not a fact (rules.md §13).

CONTEXT: chip `setup-review-closeout` (see `C:\Users\Owner\.claude\chip-claims.log`, CLAIMED 2026-07-16T14:38:27-04:00 by Code/c3a1e79e, no DONE/ABORTED line yet) is a follow-up to `~/.claude/handoffs/2026-07-16_setup-review-closeout.md`. Its DONE-gate had 6 items; 3 were confirmed clean same-day (governor-drift-probe.py exit 0, memory-integrity-probe.py exit 0, doctrine-integrity-probe.py clean). The remaining 3 were blocked on scheduled watches that hadn't fired yet as of 2026-07-16: (1) 12:45 ET `ora-task-integrity-guard` STEP-1.5 (registry-membership-probe.py + emit-fleet-heartbeat.py + push-fleet-heartbeat.ps1), (2) 11:05 ET `automation-health-monitor` v1.8 beacon (LAMS/Cowork fleet), (3) 16:01 ET `ora-uw-northridge-brockton-full` itself (the one-time acquisition-underwriting re-run on 2900 Northridge Dr NW + 4331 Brockton Dr SE that originally motivated the whole setup-review chain).

Baseline captured 2026-07-16 (for diffing — confirm these actually advanced, don't just check "exists"):
- `~/.claude/maintenance/_state/registry-membership.log` latest line was `2026-07-16T13:50:00`
- fleet-heartbeat.json `ts` was `2026-07-16T17:50:00Z`
- `push-fleet-heartbeat.log` latest line was `2026-07-16T17:50:02Z OK - heartbeat pushed`

STEP 0 — CONCURRENT-WRITER CHECK (mandatory before any write): call `list_sessions` and scan for another running session with an overlapping title (chip name, "setup-review", "closeout", "northridge"). If a live sibling is actively working the same chip, STOP — do not duplicate the close-out; leave this task's own run as an ABORTED note in event_log.md citing the sibling session, and do not touch chip-claims.log.

STEP 1 — VERIFY each of the 3 pending items actually fired since the baseline (query live state, do not trust this prompt's numbers as current):
  a. `list_scheduled_tasks` → confirm `ora-task-integrity-guard` has a `lastRunAt` on 2026-07-17 at/after 12:45 ET, AND that today's run did not raise a STEP-3 alarm (check its most recent Notion Ops Hub post / email, per its own v1.5 doctrine: probe [ACTION] lines and probe/emitter failures are STEP-3 alarms, never silent).
  b. Confirm `automation-health-monitor`'s v1.8 beacon fired on the LAMS/Cowork fleet at/after 11:05 ET on 2026-07-17 with no alarm.
  c. Confirm `ora-uw-northridge-brockton-full` fired at/after 16:01 ET on 2026-07-17 (this task's own `lastRunAt` via `list_scheduled_tasks`), and that it ran against the CURRENT installed skill versions (acquisition-underwriting, ora-flood-zoning-dd) — not a stale cached version. If you can determine which skill version it actually invoked, note it; if not, note that as an open item rather than assuming.
  d. Cross-check `~/.claude/maintenance/_state/registry-membership.log`, the fleet-heartbeat.json `ts`, and `push-fleet-heartbeat.log` all show a NEWER timestamp than the 2026-07-16 baseline above.

STEP 2 — OUTCOME:
  - If all of (a)-(d) confirm clean (fired, no alarms, timestamps advanced): append ONE closing entry to `memory/event_log.md` via `python ~/.claude/maintenance/append-event-log.py` (NEVER Edit-anchor the header — rules.md §9) stating the DONE-gate is now 6/6 clear with the specific evidence found (timestamps, lastRunAt values). Then append the chip's close line to `C:\Users\Owner\.claude\chip-claims.log`: `<ISO-8601 local> | DONE | setup-review-closeout | Code/<this-session-id>`.
  - If ANY of (a)-(d) did not fire, or any watch raised a real alarm, or the northridge task ran against a stale skill version: do NOT mark DONE. Append an event_log.md entry (same script) stating exactly which item(s) are still open or alarmed, with evidence. Append `<ISO-8601 local> | ABORTED <one-line reason> | setup-review-closeout | Code/<this-session-id>` to chip-claims.log instead of DONE — never fabricate a clean result to close the chip early.

This is a one-time task (fireAt, not cron) — it auto-disables after this run. No further action needed to retire it. No email — this is internal bookkeeping only; if a watch actually alarmed, that watch's own email path already notified Gabriel, this task's job is only to close (or correctly leave open) the chip's paper trail.