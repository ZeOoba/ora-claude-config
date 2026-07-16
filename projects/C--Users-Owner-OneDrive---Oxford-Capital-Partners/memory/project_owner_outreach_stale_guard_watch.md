---
name: project_owner_outreach_stale_guard_watch
description: "CLOSED 2026-07-14 — the watched 2026-07-13 fire DID trip the staleness guard again, but CORRECTLY (real 33-day content staleness, not Case 1's mtime false positive). Gabriel ratified the 2026-06-10 vintage as current same-day; SKILL.md STEP 1 updated (v1.3) with a dated, per-vintage STANDING RATIFICATIONS clause so the guard won't re-ask on unchanged data but still halts on any new stale vintage."
metadata: 
  node_type: memory
  type: project
  originSessionId: ddf5f6ad-6d81-4a1f-bb37-89a7e4067efe
---

**CLOSED 2026-07-14.** This note was opened to watch `ora-owner-outreach-queue-refresh` (LAMS, Mondays ~10:00 AM ET) for a recurrence of the 2026-07-12 master-staleness guard **false positive** (Case 1 — a verify-only pass touched the master's mtime, the guard misread it, and it self-corrected ~8 min later). The watched fire has now happened, and the answer is **not** the binary this note anticipated.

## What actually happened at the 2026-07-13 fire

The guard **did trip again** — but it was **right this time.** From the run's own summary email (`ORA Owner-Outreach - Weekly - 2026-07-13`, sent 10:11 AM ET to ggoldberg@oxfordra.net):

> *Master vintage: 2026-06-10 (33d) — file-modified 2026-07-12 (1d) — STALE=YES*

The two dates disagree because they measure different things: the off-market master's **content** vintage is 2026-06-10 (33 days old), while the **file** was touched 2026-07-12 (1 day ago). The touch did not refresh the underlying data. Case 1 was the guard being fooled *by* that gap (trusting mtime); this trip is the guard correctly *seeing through* it and flagging genuinely stale content.

**No code fix is warranted.** The anticipated `owner_outreach_weekly.py` retry-before-fail-loud change would have been exactly the wrong response — it would have taught the guard to swallow a true positive.

## The live consequence — RESOLVED 2026-07-14

Per the unattended-path STALE guard, the run **held** Notion page creation and the ledger commit (`--commit`). Nothing was lost this week — NET-NEW was 0 regardless, so nothing that would have been pushed was withheld. The run emailed a **QUESTIONS FOR GABRIEL** block; Gabriel answered it the same day (interactive elicitation, 2026-07-14): **"Current — unblock next run"** — a one-time ratification of the 2026-06-10 vintage, not a rescreen and not a standing STALE_DAYS/threshold change. Logged in [[ops_decision_log]] (2026-07-14 entry).

**Durability gap, also closed 2026-07-14:** the guard (`owner_outreach_weekly.py` STEP 1 in the SKILL.md) had no mechanism to remember a one-time confirmation, so the 2026-07-20 fire would have re-tripped on the same unrefreshed data and re-asked the identical question. Fixed by adding a **STANDING RATIFICATIONS** clause directly to STEP 1 of `ora-owner-outreach-queue-refresh/SKILL.md` (v1.2 → v1.3): the guard now checks the reported master vintage against a dated, per-vintage ratification list before halting — proceeds without re-asking when the vintage still reads 2026-06-10, but the halt-and-ask fires again automatically the instant the reported vintage changes to anything else (a real refresh, even a still-stale one). `STALE_DAYS` and the default halt behavior are unchanged; nothing was silently widened. Edited directly (the file is plain OneDrive prose, not a git-tracked or registry-spliced asset — SKILL.md content is authoritative per [[reference_cc_scheduler_filepath_mechanism]] regardless of which surface writes it).

## Lesson (durable — why this file survives instead of being archived)

A fail-loud staleness guard that trips twice is not automatically crying wolf. **Check which signal it read** — content vintage vs. file mtime — before concluding false positive. Case 1 and this trip look identical from the outside (same task, same guard, same alert shape) and have opposite root causes and opposite correct responses. Logged as **Case 2** in [[reference_scheduled_task_staleness_guard_trips]], the durable home for this pattern class.

Related: [[reference_scheduled_task_staleness_guard_trips]] · [[event_log]]
