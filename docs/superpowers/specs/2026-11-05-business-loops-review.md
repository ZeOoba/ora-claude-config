# Business loops review: does the automation learn? (2026-11-05)

- **Lane:** L5 research, then L3 build for three fixes (this branch, `feat/business-loops-2026-11-05`)
- **Scope:** `~/.claude` (ora-claude-config) as it serves ORA's priorities: acquisition velocity, then operational optimization, institutional quality, comms/brand, knowledge capture.
- **Out of scope:** maintenance-reduction bundles 1–6 (`2026-11-05-maintenance-reduction-bundle-1-design.md`), which are being run by another session. Nothing here re-proposes them.
- **Method:** three read-only surveys (memory loop, fleet business data flows, alarm-to-action loop), followed by direct reads of the task specs, the Notion Deal Sourcing Log schema, the outreach logs, the OCC calibration tables (opened read-only), the guard state and the Outlook send log. Every number below cites its source. Re-measure before relying on any of them.

## 1. Headline

The system captures predictions well and almost never closes the loop to outcomes. In each of the four places where it scores something, the outcome side is either empty or deferred to an event that does not exist:

| Loop | Prediction side | Outcome side | Evidence |
|---|---|---|---|
| Scan tier → review decision | `Verdict`, `Buy Box Score` written weekly | The "December back-test" that three doctrines defer to has no procedure and no run | `ora-passed-deal-tracker` §Calibration use; `ora-deal-sourcing-scan` v2.9 header; deal-decision-ledger FORT note. `annual-cycle/SKILL.md` has no back-test step, and its year-in-review moved to February in v1.2 (2026-10-30). |
| Off-market letters → owner response | 277 T1 letters in 5 releases (`mail-log.csv`, 08-21 to 10-30) | 0 responses captured. `outreach-responses.csv` is absent, and the Notion queue holds 1 suppressed row of 480 (Parked). | `_oo_scorecard_block.md` 2026-11-02, `_oo_suppression.json` |
| T2 calls | 16 owners on call sheets (`call-log.csv`) | 0 outcomes. The sheets carry no phone numbers, because skip-trace was ruled out of scope. | funnel design §A1; scorecard row "outcomes logged: 0" |
| OCC Score-vs-Outcome log | 68 property verdicts (one 07-12 snapshot, plus 07-08 and 09-27) | 0 outcomes. That is expected until FY2026 closes. 0 `acquisition-score` verdicts have ever been emitted, although the enum and a UI panel exist. | `finance.sqlite`, read-only: `calibration_verdict` = 68, `calibration_outcome` = 0 |

The funnel is also empty at the bottom. In the trailing 90 days to 2026-11-02 there were 151 scan-triaged rows, 16 full SCREENs, 2 T1 PURSUE and **0 LOIs**, against a target of 3 (BELOW PACE). A hand back-test on 2026-10-30 found that 0 of 8 decided T1 rows held T1. Doctrine v2.9 followed the same day. Nothing is scheduled to test whether v2.9 worked.

### First back-test readout (live export, 2026-11-05)

Source: seven read-only Notion SQL exports of the Deal Sourcing Log. They are the engine's documented queries: five verdict partitions, T1 rows, and `P(exec)` rows. The log holds 661 rows, of which 26 are excluded from calibration.

| Tier (era) | Logged | Reached LOI | Won | Rejected | Dead, no decision | Never reviewed |
|---|---|---|---|---|---|---|
| T1 PURSUE (pre-v2.9) | 6 | 1 | 0 | 0 | 4 | 1 |
| T2 WATCH (pre-v2.9) | 306 | 4 | 1 | 5 | 8 | 289 |
| PASS (pre-v2.9) | 86 | 1 | 0 | 20 | 19 | 46 |
| No verdict (pre-v2.9 broker intake) | 198 | 1 | 0 | 17 | 11 | 168 |
| v2.9 onward (29 PASS, 5 T2) | 34 | 0 | 0 | 1 | 0 | 33 |

- **The log cannot calibrate yet.** Three of the four 2026-10-27 T1 rows no longer read T1, because the 10-30 review overwrote their `Verdict`. Their prediction survives only in the memory ledger. Four of the six remaining T1 rows read `Status = Dead` with no `Go / No-Go`, so a quality pass cannot be told from a withdrawn listing. The scan already keeps `Ask at First Sighting` write-once. The same convention for `Verdict` and `Buy Box Score` (decision D-5) is the precondition for every rate below meaning anything.
- [SPECULATIVE] **LOIs come from T2, not T1.** Four of the seven rows that ever reached LOI were T2 WATCH, including the only WON, and 289 T2 rows were never reviewed. On this sample, the tier label does not predict where ORA bids. If the pattern holds, the T2 pile needs a periodic human triage slot, or the tiering is mis-ranking. The sample is too small to tell which, and the engine reports it again each run.
- **v2.9 has produced no T1 rows in its first 34.** Its new buckets (T1-PENDING-PRICE and T1-PENDING-VERIFY) are written as T2 WATCH by design, so the next test of v2.9 is whether those rows get verified and promoted.
- **`P(exec)` has 3 resolved outcomes** (0.35 not executed, 0.9 not executed, 0.9 won; Brier 0.31). That is far too few to judge. It is reported so the count is visible as it grows.
- **7 of the 9 go decisions carry no `Scorecard Done`.** Either LOIs advance without a full SCREEN scorecard, or the box goes unticked. Both readings undermine the SCREEN-pace metric in the weekly funnel scorecard.
- **Source mix:** 53% of logged rows have Source `Other` or blank. Four of the 7 rows that reached LOI have a blank source, because they predate the v2.10 source mapping.

## 2. Findings, ranked by business impact

1. **The calibration event is a phantom (acquisition velocity).** See the table above. Doctrine changes therefore happen one miss at a time (v2.8, v2.9 and v2.10 in five weeks), never from accumulated evidence. *Fixed in part here:* `maintenance/funnel-backtest.py`. Wiring it to a run date is decision D-3.
2. **24 business and data tasks were dark for 5+ weeks with no alarm (operations).** The 09-28 CC resume stalled and left 35 tasks off. The 10-30 triage found 24 still stranded, and Gabriel deferred them: 13 reports, 5 data producers and 6 self-maintenance tasks. The stranded reports include `deal-command-board`, `deal-aging-sla` (it also watches unshipped LOIs), `vacancy-aging-report`, `loan-balance-check` (which missed 10-21), `monthly-portfolio-briefing` (which missed 10-01 and 11-01) and `calibration-snapshot` (which missed the Q4 snapshot on 10-01). Eight guard and integrity tasks were re-enabled the same day.
   - **Root cause.** `pause-resume-guard` detected the stall at 2026-09-29 00:27Z, which is the only way its state entry gets created. No alarm reached the Outlook send log; the last guard alarm there is 09-12. The same day, the resume task was archived as `_archive_2026-09-29_completed-onetime`. Its `filePath` stopped resolving, the check `continue`d, and the alarm state cleared.
   - **The general gap.** Every check judges an EVENT (a resume inside a 72-hour window, or a fleet ratio at or below 10%). None judges the STATE "disabled with no recorded intent".
   - **The guard's alerts may never be delivered at all** (found by the REFUTE pass; not yet resolved).
     - Since 2026-09-02, `send-log.txt` holds one guard email, on 09-12 at 17:35. That is not a scheduled run time, so it was a manual test.
     - Live state shows the 09-28 incomplete-resume alarm and a LAMS fleet-ratio alarm both tripped and both `alarmed: false`, so every 6-hour run retries a send that never lands.
     - No `[ALERT SEND FAILED]` fallback note reached the Ops Hub.
     - The identical invocation dry-runs cleanly from an interactive shell (`-WhatIf`, exit 0).
     - The 13:20 run today was killed 12 seconds in (`0xC000013A`). The task runs `python.exe` with a visible console in the interactive session.
     - This branch makes every send attempt observable (`_sendLog` in the guard state). Running the guard hidden, as `ClaudeFleetMirror` already runs via `run-hidden.vbs`, is follow-up F-10.
   - *Fixed here:* a stranded-task digest in the guard, plus a held-off register with review dates. Seeding that register is decision D-4.
3. **Owner responses have no low-friction capture path (acquisition velocity, compliance).** This is already tracked as [OI-240](../../../projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/open-items-tracker.md#OI-240) (MEDIUM, 2026-09-07). The 09-22 funnel build added call sheets and a conversion report, but capture is still at zero. The only capture path is a CLI script. T3 letters promise "tell me and I will stop", and only the response log honors that promise. The 08-21 cohort reaches T3 around 11-19. *Not fixed here:* the outreach scripts live in a business OneDrive folder, so changing them needs permission (Invariant 5). See decision D-2 and follow-up F-1.
4. **Every consumer of the shared OCC checkout reads month-old data (institutional quality).**
   - `C:/Users/Owner/oxford-command-center` has sat on branch `data/snapshot-2026-10-06` since about 10-08. It is 103 commits behind `origin/main`. Its 5 unique commits already landed on main as #445 (the rent-roll parser fix) and #453 (the AR remap).
   - So `data/snapshots/portfolio.json` there reads generatedAt 2026-10-06 and 139 leases, while main holds generatedAt 2026-10-26, asOf 10-23 and 140 leases, from three later refreshes.
   - Readers of that path get the stale copy: `ora-am-brief` (CC'd to Eric), `ora-recovery-billing-monthly`, `ora-noi-opportunity-digest`, `ora-renewal-hubspot-reconcile`, and the local app if it is served from that checkout.
   - `ora-cc-snapshot-refresh` documents the gap ("nothing advances the live checkout; known gap") but assigns it to no one.
   - The checkout is clean (0 dirty files). *Not fixed here:* moving another repo's shared checkout needs Gabriel's go-ahead. The fix is to advance it to `main`, then give the gap an owner (follow-up F-9).
   - **Correction:** a first draft of this branch treated the STALE reading as a false alarm and added a verification stamp. An adversarial REFUTE pass showed the STALE reading was correct and the stamp would not have changed it. The stamp was withdrawn before commit.
5. **RE-ENGAGE exists only in the monthly entry-market scan.** The weekly established-market scan never compares a re-listed pass against ORA's walk price, so the highest-odds re-engagements are not raised. The Notion fields `Walk Price`, `Re-Engagement Flag` and `Re-Engagement Tickler Date` already exist. Follow-up F-2.
6. **Open work cannot be seen (knowledge capture).**
   - `open-items-tracker.md` is 770 KB with 201 open rows. The median row is 949 B, 105 rows are more than 60 days old, there are no status, owner or due columns, and nothing ranks or ages the rows.
   - Eleven `feedback_*` files restate one lesson ("verify before acting") and carry no recurrence count.
   - `MEMORY.md` is 226 B over its WARN gate.
   - Follow-ups F-3 and F-4.
7. **Alarms carry no outcome (self-improvement of the monitoring layer).**
   - No alarm records whether it was acted on, and no per-probe precision is computed.
   - Guard telemetry holds only about 2.5 hours of history.
   - At least five probe outputs have no reader. `deal-stage-reconciler.py` is dead because its only caller is a stranded task.
   - `edge-mfg-scout` has written 5 weekly pending files to an accept-list that does not exist.
   - By count, 20 of the 43 live tasks are META (46%).
   - Follow-ups F-5 and F-7 (per bundle-1 D2).

## 3. What this branch changes

| Component | Files | Behavior |
|---|---|---|
| Sourcing back-test engine | `maintenance/funnel-backtest.py` and test (51 tests, including a sqlite3 replay of the export queries) | Takes seven read-only Notion exports of the Deal Sourcing Log: a grouped query run once per verdict partition (Notion SQL returns about 100 rows and cannot paginate), plus per-row T1 and P(exec) exports, all documented verbatim in the module. A truncated export is refused. It reproduced an independent cross-check of the live log exactly. It reports: scan tier against review decision by doctrine era, with Wilson CIs; funnel conversion; source yield; P(exec) Brier and reliability; loss-class mix; stalled T1 rows; and data quality. Report-only by hard rule. It never changes a weight, band, gate or Notion. |
| Stranded-task alarm | `maintenance/pause-resume-guard.py` and test (61 tests) | Alarms when a recurring task is disabled with no recorded intent. Recorded intent means retire-pending, held by a *bounded* pending resume (one firing between 24h ago and 21 days ahead), or under an active hold in `_state/held-off.json`. An expired hold strands again. One digest goes out on any newly stranded id, then weekly while anything stays stranded, and state advances only on confirmed delivery. A broken register surfaces tasks; it never hides them. An active fleet-wide `*` hold also holds that fleet's fleet-ratio alarm. Every send attempt is logged (`_sendLog`), and saves are atomic. When a digest fires in the same run as an existing alarm, the two share one email. Round 1 of the REFUTE pass blocked it; every defect is fixed, and round 1's own probes now pass. |
| Held-off register | `maintenance/_state/held-off.json` | Seeded with Gabriel's rulings only: the LAMS fleet wildcard (dark by the 10-30 ruling, review 2027-10-30); `ora-audit-log-sweep` and `ora-sofr-direct-prefetch` (held, review 2026-12-31); and the 22 deferred tasks (his 11-05 answer: keep off, review 2026-12-01). |
| Write-once predictions | Notion Deal Sourcing Log (2 new properties); `ora-deal-sourcing-scan` and `ora-entry-market-scan` specs | `Verdict at First Sighting` and `Score at First Sighting` are written on row creation only. Gabriel approved this on 2026-11-05. |
| Monthly back-test | `ora-passed-deal-tracker` spec | Runs the engine on the 15th and puts its block in the email, so calibration evidence arrives monthly instead of at a December meeting that did not exist. Approved 2026-11-05. |

**Deploy note.** These run from the live `~/.claude` checkout, so they take effect only after merge plus `ora-checkout-merge-forward` (Fri 16:45). The guard's first digest after deploy lists only what no hold covers.

## 4. Decisions that are Gabriel's (not made here)

- **D-1. Re-enable the stranded business set.** Recommended: `deal-aging-sla`, `deal-command-board`, `vacancy-aging-report`, `loan-balance-check`, `monthly-portfolio-briefing`, `calibration-snapshot` (plus one catch-up run for Q4), `renewal-hubspot-reconcile` and `tenant-hubspot-reconciliation`. This goes through `register-scheduled-task`, with its single-writer check.
- **D-2. Off-market T2 and response capture.** Either fund skip-trace for the top 8 owners a week, or drop T2 and run a letters-only ladder. Separately, approve letting Notion `Cadence Status` and `DNC` edits count as captured responses (F-1).
- **D-3. Back-test cadence.** Either fold a monthly calibration block into `ora-passed-deal-tracker`, which needs one Notion query a month, or register a one-time 2026-12-15 run. Any weight, band or gate change still needs Gabriel's in-turn sign-off.
- **D-4. Seed `held-off.json`.** This branch seeds only rulings already made on 10-30: the LAMS fleet wildcard, `ora-audit-log-sweep`, and `ora-sofr-direct-prefetch`, each with its source and a review date. Whatever D-1 leaves off needs Gabriel's review date. Until then, those tasks appear in the weekly digest, which is the intended effect.
- **D-5. Make predictions write-once in the Deal Sourcing Log.** Add `Verdict at First Sighting` and `Score at First Sighting`, written by the scan on creation only, the way `Ask at First Sighting` already is. Separately, record every quality pass as `Go / No-Go = Pass`, and reserve `Dead` for listings that are gone. The engine already accepts `verdict_first` and switches its tier basis automatically. This is a Notion schema change, so it needs Gabriel's go-ahead.

## 5. Follow-ups (each its own change)

- **F-1.** Response capture from the Notion queue into `outreach-responses.csv`, mirroring `pull_suppression.py`. Needs a business-folder write permission.
- **F-2.** Port RE-ENGAGE (ask within 5% of `Walk Price`) into the weekly scan, or make `Walk Gap` a Notion formula.
- **F-3.** Split the open-items tracker into an active file and an archive, with a closed status vocabulary and a weekly mover, modeled on `rollover-event-log.py`.
- **F-4.** Consolidate the "verify before acting" feedback family into 2–3 files that carry an `Occurrences:` count.
- **F-5.** Add one outcome field per alarm (fixed / noise / deferred / ignored) and a monthly per-probe precision rollup. Demote a probe after one bad month and retire it after a second.
- **F-6.** OCC: emit `acquisition-score` verdicts and resolve deal outcomes from the Sourcing Log's `LOI Outcome`. This is financial-decision code, so it is refute-Workflow-gated.
- **F-7.** Apply bundle-1 D2 to the readerless probe outputs (`deal-stage-reconciler` and its snapshot, the override-frequency and override-efficacy probes, the mcp-usage ledger). Either name a reader or retire each one.
- **F-8.** `register-scheduled-task`: write a hold on every deliberate DISABLE, and never archive a fired resume as "completed" while any id it listed is still disabled.
- **F-11.** Extend the write-once rule into `ora-skills`. Each change below is a separate PR under that repo's single-writer rule.
  - `deal-retirement` creates Sourcing Log rows without the first-sighting fields.
  - `acquisition-underwriting`, `verified-deal-recon` and `loi-generation` update rows with no never-write list.
  - Add the two fields to deal-retirement's create step, and to the never-write lists of the three updating skills.
  - Separately, have quality passes record `Go / No-Go = Pass` (D-5). The engine counts only explicit decisions toward T1 precision; a re-tiered T1 with no decision stays open and shows up in the stalled list.
- **F-10.** Make the pause-resume guard's alerts reach Gabriel.
  - Read the first scheduled runs' `_sendLog` entries after this branch deploys.
  - If they confirm the console-kill or scheduled-context failure, re-register the `ORA Fleet Pause-Resume Guard` Windows task to run hidden (`pythonw.exe`, or `run-hidden.vbs` as `ClaudeFleetMirror` does).
  - That edits a Windows Task Scheduler definition, so it needs Gabriel's go-ahead.
  - Until delivery is proven, treat this guard's emails, including the new stranded digest, as unverified.
- **F-9.** Give the shared OCC checkout's freshness an owner. Either advance it to `main` after every snapshot merge (a step in `ora-cc-snapshot-refresh` or `ora-checkout-merge-forward`'s OCC twin), or have consumers read `origin/main:data/snapshots/portfolio.json`. Either way, `generatedAt` keeps meaning what consumers assume it means.

## 6. Checked and fine

- Weekly sourcing chain order: scan (Tue 10:45), then `done.json`, then construction-verify (14:15).
- Monday ingest order: ingest, then snapshot-refresh, then acq-sync.
- Outreach suppression is fail-closed and script-owned.
- Sourcing Log dedupe and `Exclude from Calibration` are honored by the passed-deal tracker.
- The pause-resume guard is scheduled every 6 hours (Windows task, interactive logon, `StartWhenAvailable` and `WakeToRun` on). Two caveats: its 13:20 run on 11-05 was killed at 12 s (`0xC000013A`), and its alert delivery is unverified (see finding 2 and F-10).
- Guard latency and block rate are low (about 22 blocks in roughly 28k fires in the available window).
