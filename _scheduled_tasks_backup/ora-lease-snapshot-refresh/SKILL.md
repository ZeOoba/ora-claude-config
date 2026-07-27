---
name: ora-lease-snapshot-refresh
description: Weekday 3x/day (7am/1pm/7pm ET) regeneration of oxford-command-center's data/snapshots/portfolio.json via scripts/lease-snapshot-drift-check.ts, independent of interactive server uptime -- keeps the snapshot within its 6h staleness threshold and reports lease drift (new/removed/date-changed) with an anomaly floor that refuses to write on a suspicious parse. Closes the 2026-07-24 lease-date integrity incident (PR #232). [MODEL: claude-sonnet-5 | set 2026-07-24]
---

You are running the scheduled task `ora-lease-snapshot-refresh` for Oxford Realty Advisors. This regenerates `data/snapshots/portfolio.json` in the `oxford-command-center` repo (`C:\Users\Owner\oxford-command-center`) via `scripts/lease-snapshot-drift-check.ts`, on a cadence independent of whether the interactive Command Center dev/prod server happens to be running (that dependency was the root cause of a 2026-07-24 lease-date integrity incident — the Command Center's alerts engine and its own portfolio snapshot disagreed about the portfolio's largest near-term lease expiration because the snapshot had gone stale). Full context: `CHANGELOG.md`'s "Stable lease ids + overlay-write hardening (2026-07-24)" entry and `docs/superpowers/plans/2026-07-24-lease-id-integrity-fix-plan.md` Task 3, both in that repo.

## Steps

1. Run, from the `oxford-command-center` repo root: `npx tsx scripts/lease-snapshot-drift-check.ts`
2. Read the exit code AND the full stdout/stderr output — the exit code alone doesn't carry the detail a human needs.

## Exit code handling (differentiated 0/1/2/3 — do not treat them the same)

- **Exit 0 (clean, no drift):** nothing to report. Do not post to Notion, do not email. Silent success.
- **Exit 2 (wrote portfolio.json, found drift worth a look — new/removed/date-changed leases):** this is routine, not an alarm. Post a brief status note to the Notion Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`, or search for "Operations Hub" if that ID has moved — verify before trusting a hardcoded ID) summarizing the new/removed/date-changed lease counts from the script's own printed output. No email for this case.
- **Exit 1 (refused to write — anomaly floor tripped, or corrupt overlay/previous-snapshot):** `portfolio.json` is UNCHANGED, real financial/portfolio data is stale until a human investigates. This is an alarm: post to Notion Operations Hub AND email `ggoldberg@oxfordra.net` ONLY (no cc — routing canon, see CLAUDE.md Email & scheduler section) via the Outlook COM send path (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path). Quote the script's own refusal message verbatim in both the Notion note and the email so the specific cause (overlay corruption, previous-snapshot corruption, 0-lease parse, >25% lease removal) is immediately visible, not just "it refused." Do NOT retry automatically and do NOT pass `--force` — this needs a human decision, not an automated override.
- **Exit 3 (unexpected crash — parseWorkbook failure, missing worksheet, workbook locked mid-sync):** same alarm treatment as exit 1 (Notion + email, ggoldberg only, quote the error). On a COM send failure specifically: retry the send once, then flag loudly in the Notion completion row if it still fails — do not silently drop the alert.

## Guard conditions

- If the script itself is missing (e.g. this task fires before a future revert of the branch that added it), report that clearly as a setup/environment problem in the Notion note and email — do not fabricate a "no drift" result.
- Never fabricate lease counts, drift details, or a "clean" result if the script's actual output is ambiguous or unparseable — if you can't tell what happened from the output, say so explicitly and escalate with a QUESTION FOR GABRIEL rather than guessing.

## Pointers, not duplication

- Do not re-implement the drift-check's own logic (id comparison, staleness thresholds, anomaly floor) — that all lives in the script itself and in `server/config.ts`'s `isSnapshotStale`. This task's only job is to run the script, read its output, and route the result (silent / Notion-only / Notion+email) per the exit code.
- **Corrected 2026-07-26 — the line below was stale.** `ora-cc-snapshot-refresh` (weekly Monday `npm run extract`) now shares BOTH the anomaly floor AND the drift report with this task (`evaluateAnomalyFloor`/`formatDriftReport`, exported from `scripts/lease-snapshot-drift-check.ts` and imported by `scripts/extract-workbook.ts`) — see event_log.md, "orphaned-task-forensics: portfolio.json snapshot regression" and its follow-ups, 2026-07-26. A manual off-schedule `npm run extract` run corrupted two tenants' lease-end dates on 2026-07-25 specifically because that path had neither protection at the time. `ora-cc-snapshot-refresh` remains the lower-frequency (weekly) backstop by CADENCE — this task is still the primary, more-frequent (3x/weekday) refresh path — but it is no longer the only one with data-integrity protection. Do not repeat the old "no anomaly floor, no drift reporting" framing.
