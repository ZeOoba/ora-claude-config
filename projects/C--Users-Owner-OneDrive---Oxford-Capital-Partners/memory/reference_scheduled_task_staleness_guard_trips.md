---
name: reference_scheduled_task_staleness_guard_trips
description: "Standing pattern log for fail-loud master-data staleness/freshness guards tripping false-positive across the scheduled-task fleet. Case 1 (2026-07-12, ora-owner-outreach-queue-refresh) logged as the first documented occurrence — check new trips against this before re-diagnosing from scratch."
metadata:
  node_type: memory
  type: reference
  originSessionId: local_d974d26b-0ebe-48de-844c-1c7dcdbaea04
---

**Purpose:** several scheduled tasks now carry a fail-loud guard that halts (rather than silently
proceeding) when a master data file looks stale — by design, per the `ora-task-integrity-guard`
Step 0.5 fix (2026-07-09). This is a durable pattern log for that guard *class*, distinct from
[[project_owner_outreach_stale_guard_watch]] (a scoped, self-archiving tracking note for one
specific task's recurrence check). Log every future trip here, even a confirmed one-off, so the
next incident is checked against real cases instead of re-investigated cold.

## Failure class

A fail-loud staleness/freshness guard reads a master file's mtime (or an equivalent freshness
signal) and halts on a threshold breach. Two distinct causes produce the same symptom:
1. **Genuine staleness** — the underlying data actually is out of date (the guard is working as
   intended).
2. **False positive** — something touched the file's mtime (or freshness signal) without a
   substantive data update — e.g. a verify-only read/fact-check pass, a sync-timing artifact, or
   a partial/in-progress write — and the guard can't yet tell the two apart.

## Case log

### Case 1 — 2026-07-12, `ora-owner-outreach-queue-refresh` (LAMS)
- **Trip:** STEP-1 master-staleness guard fired 17:16 ET (a day early — task's normal cadence is
  Monday ~10:00 AM ET; 2026-07-12 was a Sunday), fail-loud alerted.
- **Self-correction:** re-ran clean 17:24 ET, ~8 min later, same day, before that evening's
  punch-list review session started.
- **Root cause (confirmed, not just suspected):** the guard correctly read a stale P1-scoring
  vintage signal on the off-market Investment Candidates master file — but the file's mtime had
  changed because of an **in-progress verify-only fact-check pass**, not an actual rescore. The
  guard has no way yet to distinguish "file touched by a read/verify operation" from "file touched
  by a real data update."
- **Handling:** bypassed for that single run only, per Gabriel's own in-session instruction — not
  treated as standing authorization to bypass silently in future weeks (see the draft Preferences
  line in the 2026-07-12 Punch-List Review, Notion page `39b6ecd8`).
- **Precedent this resembles:** same failure *class* as the `ora-task-integrity-guard`
  stale-baseline bug fixed 2026-07-09 (a retry-before-fail-loud Step 0.5 fix was added there) —
  worth considering an analogous fix in `owner_outreach_weekly.py` if this recurs.
- **Open question (unresolved, needs Gabriel):** relax `--strict-age` to WARN-only going forward,
  or keep requiring a manual bypass each time a mid-refresh verify pass touches the file? Carried
  in [[project_owner_outreach_stale_guard_watch]].
- Source: 2026-07-12 Punch-List Review, Notion Ops Hub page `39b6ecd8` (item 5) +
  [[project_owner_outreach_stale_guard_watch]].

### Case 2 — 2026-07-13, `ora-owner-outreach-queue-refresh` (LAMS) — **TRUE POSITIVE, not a false one**
- **Trip:** same task, same STEP-1 guard, at its normal Monday ~10:00 AM ET fire. This was the
  recurrence Case 1 was explicitly watching for — so the reflex read was "confirmed pattern, go fix
  `owner_outreach_weekly.py`." **That reflex was wrong.**
- **Root cause (from the run's own summary email, 10:11 AM ET):**
  *"Master vintage: 2026-06-10 (33d) — file-modified 2026-07-12 (1d) — STALE=YES."* The master's
  **content** vintage is genuinely 33 days old; the **file** was touched a day earlier without the
  underlying data being refreshed. Case 1 was the guard being *fooled by* that content-vs-mtime gap;
  Case 2 is the guard correctly *seeing through* it. **Opposite root causes, identical symptom.**
- **Handling:** unattended-path STALE guard held Notion page creation and the ledger commit
  (`--commit`). Nothing was actually withheld — NET-NEW was 0 that week regardless.
- **Correct response:** none in code. A retry-before-fail-loud fix (the one Case 1 suggested) would
  have taught the guard to swallow a true positive. The real action is a **data** action: refresh the
  off-market master, or consciously relax its age threshold.
- **Open (as of 2026-07-14):** the run's QUESTIONS FOR GABRIEL email is unanswered. Until the master
  is refreshed, the 2026-07-20 run will hold the writes again — the queue silently stops promoting to
  Notion. Carried in [[project_owner_outreach_stale_guard_watch]].

> **Naming caveat:** this file is titled "false positives," but Case 2 is a **true** positive. Read it
> as a log of *staleness-guard trips* generally. The whole value is in telling the two apart.

## How to apply on the next trip (any task, not just Owner-Outreach)

0. **First, ask which signal the guard actually read** — *content vintage* or *file mtime*? Cases 1
   and 2 are the same task, same guard, same alert shape, and have opposite root causes and opposite
   correct responses. A trip is not evidence of a false positive just because the last one was, and a
   *recurrence* is not evidence of a bug. Read the run's own stdout/summary email before concluding.

1. Before treating a fail-loud staleness/freshness alert as a genuine data-quality failure, check
   whether the master file's mtime changed because of a **verify-only or read-adjacent operation**
   (fact-check, spot-check, audit pass) rather than a real rescore/data update.
2. Check the task's own completion history (Notion Ops Hub row, `ggoldberg@oxfordra.net` summary
   email, or a same-day `event_log.md` entry) for a self-correction shortly after the trip — that's
   evidence for false-positive, not proof by itself.
3. Log the outcome here as a new dated case, whether it turns out to be a one-off or a confirmed
   recurrence. Two or more cases on the same task's guard = treat as a confirmed recurring pattern,
   not a fluke, and escalate to a code fix (retry-before-fail-loud, analogous to the
   `ora-task-integrity-guard` Step 0.5 precedent) rather than repeatedly hand-bypassing.
4. If a task-specific tracking note (like [[project_owner_outreach_stale_guard_watch]]) exists and
   is still open, update it too rather than only logging here.
