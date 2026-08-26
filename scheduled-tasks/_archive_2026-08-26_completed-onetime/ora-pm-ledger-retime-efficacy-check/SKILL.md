---
name: ora-pm-ledger-retime-efficacy-check
description: One-time 2026-08-20 16:30 ET — measures whether the ora-pm-ledger 18:00→15:00 ET retime (applied 2026-08-12) cut the delivery miss rate, against a re-verified pre-retime baseline; also tests the competing dispatch-throttle hypothesis. Re-armed from 08-19 after the 08-12 early-fire incident; now derives the date from the system clock and hard-aborts if the window has not fully elapsed. Emails ggoldberg only. Auto-disables after firing. One-time CC/MCP task = MODEL-N/A (one-time), exempt from the [MODEL:] tag per memory/reference_scheduled_task_model_standard.md.
---

You are running a ONE-TIME efficacy check on the `ora-pm-ledger` retime. Be rigorous and do NOT fabricate: every number must be recomputed from the live send-log, never carried forward from this prompt.

# STEP 0 — DATE GUARD (do this FIRST, before any analysis)

**Do NOT trust any date asserted in prose — including in this prompt.** Derive today from the system clock:
`C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe -c "import datetime;print(datetime.datetime.now().isoformat())"`
(Use that FULL interpreter path everywhere; bare `python`/`python3` are unreliable in scheduled sessions.)

This task was armed to fire 2026-08-20 16:30 ET. **It has fired days early before** — on 2026-08-12 it dispatched against a `fireAt` of 2026-08-19, ~7 days early, and its prompt's baked-in "today" would have produced a confident 7-day verdict over a window with ZERO elapsed days. Do not repeat that.

Then range-check: read the LAST record timestamp in `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt`.

**HARD ABORT CONDITION:** if today's date is earlier than 2026-08-20, OR the send-log's last record predates 2026-08-19, the analysis window has not fully elapsed. In that case do NOT compute a verdict and do NOT estimate. Email a short COVERAGE GAP notice (subject: `ORA ora-pm-ledger retime efficacy — COVERAGE GAP — fired early, window not elapsed`) stating the clock date, the log's last record, how many of the 7 days actually elapsed, and that the check needs re-arming. Then STOP. Reporting "cannot be computed" is a correct, valuable outcome — a fabricated N is not.

# BACKGROUND (recorded baseline — do NOT re-derive; it was already independently re-verified 2026-08-12)

`ora-pm-ledger` is the consolidated daily close (Block A Notion Digest, Block B Outbox QC weekdays-only, Block C EOD Action Ledger). Retimed 2026-08-12 from `0 18 * * *` to `0 15 * * *`.

PRE-RETIME BASELINE, 2026-07-22 → 2026-08-11 (21 days) — recomputed from the live log on 2026-08-12 and matching the original record exactly:
- 9 days delivered something; **12 days delivered NOTHING (57% miss)**
- 6 days on-slot at ~18:1x–18:4x; 3 days off-slot catch-up burst (08-01 20:29, 08-09 09:06, 08-11 17:09)

Block B self-heals via its retro-sweep (7-day lookback); Blocks A and C have NO retro mechanism, so a missed day loses the digest and ledger permanently.

# STEP 1 — COMPUTE THE POST-RETIME NUMBER

Parse `send-log.txt` (UTF-8 with BOM; use `encoding='utf-8-sig'`). For the window **2026-08-13 → 2026-08-19 inclusive** (7 days; 08-13 was the first full day on the new slot), classify each date by subject marker:
- `Notion Daily Digest` → Block A · `Outbox QC` → Block B · `EOD Action Ledger` → Block C

For each of the 7 days report: date, weekday, send time of each block present (or `--`), and ON-SLOT (~15:0x–15:2x) vs OFF-SLOT (catch-up burst at another hour). Count: (a) days with no delivery at all, (b) days on-slot, (c) days off-slot.

Block B is weekdays-only BY DESIGN — a missing B on Sat/Sun is CORRECT, not a miss. Only a day missing BOTH A and C counts as "no delivery at all."

# STEP 2 — RULE ON IT

Compare (a) against the 57% baseline:
- **Materially better** (≤~2 of 7 no-delivery, ≤~29%): retime worked → recommend keeping `0 15 * * *`.
- **Unchanged or worse** (≥~4 of 7): the slot was NOT the binding constraint → escalate STEP 3 as the real fix.
- **In between:** report as INCONCLUSIVE on a 7-day sample; recommend re-checking rather than forcing a verdict.

A 7-day window is small — say so plainly; do not overstate significance.

# STEP 3 — THE COMPETING HYPOTHESIS (dispatch-throttle / burst-drop) — ALREADY STRONGLY EVIDENCED

Do not re-derive the mechanism; it is documented in `memory/reference_fleet_throttle_skip_catchup_burst.md` (read it). Established as of 2026-08-12:
- The CC/MCP registry carries a **`recordedSkips`** ledger — the direct detector. On 2026-08-12 `ora-pm-ledger` alone had **107 suppressed dispatches** (71 `per_task_limit`, 36 `global_limit`); fleet-wide 1,863.
- **5 of the 12 baseline misses (42%) occurred on days the app was PROVABLY open past the 18:00 slot** — 07-23, 07-26, 07-31, 08-08, 08-10.
- **08-10 ran but did not send:** snapshot artifacts written 12:44, no email — execution reached the work and failed at delivery.
- Host S0 Modern Standby sleep (app still open) is a separate confirmed dark-fleet mechanism; AC sleep was set to NEVER on 2026-08-12, DC still 3h.

Your job in this step: for each no-delivery day in YOUR window, check (i) whether any send exists at ANY hour that date (app-open proof), and (ii) whether `ora-pm-ledger/state/` holds `tenant-db-<date>.json` / `capex-<date>.json` (execution proof). Report app-open-but-undelivered days and ran-but-didn't-send days explicitly and separately from the slot verdict.

**IMPORTANT INFERENCE RULE:** a send PROVES the app was open at that hour. ABSENCE of sends proves nothing — never claim the app was "closed" from absence; say "no positive evidence of open." Likewise absence of a state file is not proof of non-execution; presence is proof of execution.

Read registry values with the **Read/Grep tools**, not `python -c` — `config-write-guard` blocks any Bash command whose text names the registry path, even for a read.

# STEP 4 — DELIVER

Email via Outlook COM, the SOLE send path: `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`
TO `ggoldberg@oxfordra.net` ONLY — no cc (the ora-am-brief Daily Brief is the sole cc-Eric exception; this is not it). Never ze@.

Subject: `ORA ora-pm-ledger retime efficacy — <today's ISO date> — <N> of 7 days missed (baseline 12 of 21)` — with `<N>` computed, never presumed. If it cannot be computed, use the STEP 0 COVERAGE GAP subject instead.

Body: ORA institutional HTML, inline CSS only (Navy #1B2A4A, Gold #C9A96E, Parchment #F5F0E8; EB Garamond/Georgia serif body, DM Sans labels, IBM Plex Mono for ids). Include: the 7-day table, before/after comparison, the STEP 2 verdict, the STEP 3 dispatch findings, and an explicit recommendation (keep / revert / retime again / investigate dispatch).

On non-zero exit: the script already retries once internally on RPC_E_CALL_REJECTED. Do NOT retry further — flag loudly in your output and write the HTML to `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\ORA\Briefs\outputs\<today>_pm-ledger-retime-efficacy.html` as fallback. Exit codes: 0 sent · 1 usage · 2 COM failure · 3 Outlook wizard stuck · 4 COM timeout.

# CONSTRAINTS

- READ-ONLY analysis. Do NOT change any cron, do NOT call `update_scheduled_task`, do NOT modify any SKILL.md. If the verdict is "revert" or "retime again," RECOMMEND it — a schedule change is Gabriel's call.
- Do not fabricate. If the send-log is unreadable or the window has no data, report a COVERAGE GAP rather than estimating.
- There is an open OI on the dispatch-throttle investigation — reference it rather than opening a duplicate.
- End with a short `QUESTIONS FOR GABRIEL` section if anything genuinely needs his ruling.
- One-time task; auto-disables after this run. No cleanup needed.