---
name: reference-bounded-pause-voided-overlapping-efficacy-checks-2026-08-21
description: "A bounded fleet pause silently voids any one-time efficacy check whose measurement window it overlaps — the check measures a DISABLED task and reads the silence as a miss. Bit twice on 2026-08-21 (ora-pm-ledger, ora-psa-drift-watch). Before ruling on any retime/remediation efficacy, check the task's `enabled` history over the window, not just the send-log."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 22a20c12-8ae6-4d2e-ae7a-89acb1956634
  modified: 2026-08-24T22:20:23.807Z
---

**The trap.** An efficacy check counts "days the task delivered nothing" from
`_shared/send-log.txt`. A paused task delivers nothing. The two are
indistinguishable in the send log — so a pause that overlaps the window
manufactures fake misses and the check confidently reports a worse-or-unchanged
verdict against its baseline.

**How it happened.** `ora-pm-ledger`'s retime efficacy check was armed 2026-08-12
for 2026-08-20, measuring 08-13 → 08-19. On 2026-08-17 — five days later, with no
cross-reference between the two decisions — Gabriel ordered "pause all routines
until Friday 5 PM", disabling 35 of 40 CC/MCP tasks including `ora-pm-ledger`.
The resume task `ora-routine-pause-resume-08-21` step 4 *deliberately* left the
one-time tickler checks alone (correct in itself — they were never part of the
pause), so all of them fired on schedule against a dark fleet.

Result on 2026-08-21: 3 of 7 window days showed zero delivery, but **all three
were pause days**. On the 4 days the task was actually eligible it delivered
4 of 4, all on-slot. Literal verdict "43% miss, roughly unchanged from the 57%
baseline" would have been flatly wrong. `ora-psa-drift-watch`'s check hit the
identical wall the same afternoon ("DID NOT FIRE").

**The check that disambiguates** — do this BEFORE computing any verdict:
1. Registry `lastRunAt` / `lastScheduledFor` for the task. A `lastRunAt` that
   stops dead mid-window and never resumes is a pause signature, not a miss run.
2. `~/.claude/maintenance/_state/*FleetPause*RestoreLedger*.json` and any
   `ora-*-pause-resume-*` task folder — the resume task's SKILL.md names every
   paused id explicitly.
3. Execution artifacts (`<task>/state/*-<date>.json`). Present = ran; absent is
   NOT proof of non-execution, but absent *and* named in a pause ledger is
   conclusive enough.

**Second trap, same investigation.** `recordedSkips` is a **rolling** ledger
(~6 days retained), not cumulative. `ora-pm-ledger` held 107 skips on 08-12 and
4 on 08-21 — that is retention decay, not improvement. Never report a
skip-count decline as progress without first establishing the earliest retained
timestamp in the file. Fleet-wide `per_task_limit` read **zero** in the retained
window, but 5 of those 6 days sat inside the pause with 35 of 40 tasks disabled,
so contention was artificially suppressed — it does not close [[open-items-tracker]] OI-133 item (a).

**Doctrine gap — FIXED 2026-08-24.** `register-scheduled-task` v2.12 required a
bounded pause to register its own auto-resume but did NOT require enumerating
one-time checks whose window intersects the pause and either deferring their
`fireAt` past the resume or recording them as knowingly voided. Recommended to
Gabriel 2026-08-21 as question 2 of the pm-ledger efficacy report; ratified
2026-08-24 (yes, add the check). Shipped as v2.17's ONE-TIME EFFICACY-CHECK
CHECK, `ora-skills` commit `d9e3708`. Auto-synced to the LAMS skills-plugin
copy at commit time but landed in `PENDING_REIMPORT.md` — Gabriel still needs
to click Save skill in Cowork before the updated version is live there.

Related: [[reference_fleet_throttle_skip_catchup_burst]] ·
[[reference_rev10_efficacy_2026-08-20]] ·
[[reference_one_time_task_fired_days_early]] ·
[[feedback_verified_null_vs_inferred_null]]
