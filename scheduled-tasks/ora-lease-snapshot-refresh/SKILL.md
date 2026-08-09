---
name: ora-lease-snapshot-refresh
description: Weekday 3x/day (7:40am/1:40pm/7:40pm ET) regeneration of oxford-command-center's data/snapshots/portfolio.json via scripts/lease-snapshot-drift-check.ts, independent of interactive server uptime -- keeps the snapshot within its 6h staleness threshold and reports lease drift (new/removed/date-changed) with an anomaly floor that refuses to write on a suspicious parse. Closes the 2026-07-24 lease-date integrity incident (PR #232). Retimed 07:00/13:00/19:00 -> 07:40/13:40/19:40 ET on 2026-07-27 (thin-the-AM-window pass): this was the single highest throttle-skip contributor (18 skips) in that morning's catch-up-burst event, sitting in a 3-task, 12-minute cluster with ora-task-integrity-guard (07:05, fixed by deliberate 2026-07-24 ruling) and ora-aaos-expire-leases (also retimed same pass). Uniform +40min offset preserves the 6h symmetric cadence across all three daily fires. As of 2026-07-27, data/snapshots/portfolio.json is git-tracked (Gabriel directive) -- this task now commits its own regenerated snapshot locally on main after a successful write (Exit 0/2 only), but ONLY when lease data actually moved -- a material-change gate ignores the meta.generatedAt timestamp the script rewrites on every run and restores the file rather than committing timestamp-only churn (Gabriel ruling 2026-07-27). As of 2026-08-09 it ALSO pushes that commit to origin/main, fast-forward only, under the guards in the Auto-push section (Gabriel directive 2026-08-09, superseding the prior do-not-push default). 2026-08-03 phantom-lease incident (parse.ts:476) CLOSED -- suspension lifted same day after PR #250 (parser fix) + PR #252 (checkSnapshot wired into both CLI writers as defense-in-depth) both merged and independently verified, including a live A/B proof against the production workbook. See the "CLOSED" banner below STEPS for detail. [MODEL: claude-sonnet-5 | set 2026-07-24]. v1.4 (2026-08-05, Gabriel-directed, ORA-wide once/day cadence policy): collapsed 3x/day weekday -> 1x/day weekday (07:40 ET). Staleness window between refreshes widens from 6h to up to ~24h; the PR #232 parser fix itself is unaffected, only refresh frequency changed. v1.5 (2026-08-09, Gabriel directive): auto-push added -- after a successful Auto-commit the task now pushes to origin/main, fast-forward only, and refuses to push (surfacing a QUESTION FOR GABRIEL instead) if origin/main has moved or if any commit ahead is not this task's own Auto-refresh commit. No force variant, ever. Exit-code routing unchanged.
---

You are running the scheduled task `ora-lease-snapshot-refresh` for Oxford Realty Advisors. This regenerates `data/snapshots/portfolio.json` in the `oxford-command-center` repo (`C:\Users\Owner\oxford-command-center`) via `scripts/lease-snapshot-drift-check.ts`, on a cadence independent of whether the interactive Command Center dev/prod server happens to be running (that dependency was the root cause of a 2026-07-24 lease-date integrity incident — the Command Center's alerts engine and its own portfolio snapshot disagreed about the portfolio's largest near-term lease expiration because the snapshot had gone stale). Full context: `CHANGELOG.md`'s "Stable lease ids + overlay-write hardening (2026-07-24)" entry and `docs/superpowers/plans/2026-07-24-lease-id-integrity-fix-plan.md` Task 3, both in that repo.

## Steps

1. Run, from the `oxford-command-center` repo root: `npx tsx scripts/lease-snapshot-drift-check.ts`
2. Read the exit code AND the full stdout/stderr output — the exit code alone doesn't carry the detail a human needs.
3. On Exit 0 or Exit 2 only, commit the regenerated snapshot per "Auto-commit" below.
4. If step 3 produced a commit, push it per "Auto-push" below (fast-forward only, this task's own commits only).

## ✅ 2026-08-03 phantom-lease incident — CLOSED, suspension LIFTED 2026-08-03 20:2x UTC (Gabriel ruling)

This task was suspended (write, then write-and-commit) 2026-08-03 after `parse.ts:476`'s `propertyKey` guard stringified a Date instead of rejecting it, ingesting the rent roll's derived "VACANCY & UPCOMING AVAILABILITY" block as 10 phantom leases (138 → 148 leases, annual rent +$312,540). Full diagnosis: `memory/reference_parseleases_vacancy_block_phantom_leases_2026-08-03.md`.

Both halves of the lifting condition are now done and independently verified, not merely merged:
1. **Parser fix** — [PR #250](https://github.com/ZeOoba/oxford-command-center/pull/250) (`d35931a`).
2. **checkSnapshot wired into both CLI writers as defense-in-depth** — [PR #252](https://github.com/ZeOoba/oxford-command-center/pull/252) (`1185638`). `evaluateReconciliationGate()` refuses the write on any error-severity flag from `checkSnapshot()` + `snapshot.dataQuality`. Live A/B proof against the real production workbook (fix reverted vs. present, in an isolated worktree) confirmed both writers now refuse with the exact incident numbers instead of writing corrupt data.

First live resume, run by hand 2026-08-03 20:2x UTC on synced `main`: clean write, 138 leases, $5,576,537, 0 flags, both gates passed. Committed (`fa9ed8b`, "Auto-refresh: lease snapshot (138 leases, no drift)") — the material-change gate found a genuine non-timestamp diff (5 days of accumulated portfolio movement: loan amortization, rent/NOI changes — not corruption) and correctly did not restore/discard it. **Normal cadence resumes at the next scheduled fire; STEPS above apply as written, no special handling needed.**

## Auto-commit (`data/snapshots/portfolio.json` is git-tracked)

`data/snapshots/portfolio.json` was un-ignored and committed to `main` on 2026-07-27 (Gabriel directive) — it is no longer a gitignored scratch file, so every successful regeneration should land in history, not just sit unversioned on disk.

- **Material-change gate (Gabriel ruling 2026-07-27 — supersedes the old bare `git status` check).** The script rewrites `meta.generatedAt` on *every* run, so `git status` on this file is **never** empty and a bare status check commits on every fire — ~15 timestamp-only commits/week that bury the commits representing real lease movement. Decide with a diff that ignores that one field. From the `oxford-command-center` repo root:

  ```bash
  MATERIAL=$(git diff -U0 -- data/snapshots/portfolio.json | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[+-][[:space:]]*"generatedAt":')
  ```

  Branch on `$MATERIAL`'s **contents**, never on an exit code — `grep` exits 1 when it matches nothing, so `&&`-chaining this reports the opposite of the truth.
  - **`$MATERIAL` empty** → only the timestamp moved. Do NOT commit. Run `git restore data/snapshots/portfolio.json` so the shared checkout isn't left permanently dirty, then skip the rest of this section. The only content discarded is the timestamp the script wrote seconds earlier, which the next run regenerates; lease data is by definition identical to `HEAD` in this branch. If the `restore` itself fails, treat that as a guard-condition failure and surface it rather than leaving the tree dirty and silent.
  - **`$MATERIAL` non-empty** → real portfolio data moved. Continue to the sanity check and commit below, and quote the `+`/`-` lines in the run report — that is the actual change, and on an Exit 0 it is the *only* place it surfaces (the drift reporter only speaks up for new/removed/date-changed leases, so a rent or SF correction lands here as an Exit 0 with a material diff).
- Before touching git at all, run a repo-sanity check: `git status --short` (no path filter) and `git log -1`. If the repo is mid-merge/mid-rebase (a `MERGE_HEAD` or `rebase-merge`/`rebase-apply` directory present), on a detached HEAD, or not on `main`, do NOT commit — treat it exactly like a guard-condition failure below (report the anomaly, escalate with a QUESTION FOR GABRIEL, leave the working tree alone). This protects against colliding with a human's or another session's in-progress work in this shared checkout.
- If other files besides `data/snapshots/portfolio.json` are also dirty, that is pre-existing WIP that is not this task's to touch — never `git add -A` / `git add .`. Stage ONLY the one file: `git add data/snapshots/portfolio.json`.
- Commit with a message summarizing the script's own printed counts, e.g. `Auto-refresh: lease snapshot (138 leases, no drift)` for Exit 0, or `Auto-refresh: lease snapshot (139 leases; drift: +2 new / -1 removed / 3 date-changed)` for Exit 2 — pull the actual numbers from stdout, never fabricate them.
- A commit failure (hook rejection, lock file, anything non-clean) is a guard-condition failure, not a silent skip — surface it the same way as the exit-code alarms below rather than swallowing it.

## Auto-push (Gabriel directive 2026-08-09 — supersedes the prior "commit locally, never push" default)

Through 2026-08-08 this task committed on `main` and stopped, because an unattended push to the shared remote was a standing decision Gabriel had not made. He made it on 2026-08-09 (after a manual push of `8e4f51e`): **once a commit has been made per Auto-commit above, push it.** No commit → nothing to push; this whole section is skipped.

`git push` publishes *every* local commit on `main`, not just this task's — so the guards below exist to make sure that's only ever this task's own commit.

- **Fetch before deciding — never push blind.** `git fetch origin`, then read the divergence:

  ```bash
  git rev-list --left-right --count origin/main...HEAD   # output: "<behind>	<ahead>"
  git log origin/main..HEAD --oneline
  ```
- **Push only on a clean fast-forward.** Behind-count must be `0`. If it is non-zero, `origin/main` has moved since the last local commit — do **NOT** push, and do **NOT** merge, rebase, reset, pull, or `--force`/`--force-with-lease` to make it pushable. The commit stays local and safe; report the divergence as a guard-condition failure with a QUESTION FOR GABRIEL and let a human reconcile the shared checkout.
- **Push only this task's own commits.** Every commit listed by `git log origin/main..HEAD` must be an `Auto-refresh: lease snapshot ...` commit from this task. If anything else is ahead — a human's or another session's work deliberately left unpushed — do **NOT** push; pushing would publish their work as a side effect of a snapshot refresh. Surface it instead, same as above.
- Both guards satisfied → `git push origin main`. Report the pushed range (`<old>..<new>`) in the run report.
- A push failure (rejected, auth, network, pre-push hook) is a guard-condition failure, not a silent skip — surface it. Do not retry with any force variant, and do not retry more than once for a plainly transient network error.
- Still **no** Notion post and **no** email for an Exit 0 push — the exit-code routing below is unchanged by this section.

## Exit code handling (differentiated 0/1/2/3 — do not treat them the same)

- **Exit 0 (clean, no drift):** nothing to report to Notion/email. Still runs the Auto-commit step above, but expect the *usual* Exit 0 outcome to be **no commit and a restored, clean tree** — the material-change gate suppresses the timestamp-only churn. An Exit 0 that *does* commit means a non-date field (rent, SF, tenant attribute) moved without tripping the drift reporter; that is the informative case and belongs in the run report. Do not post to Notion, do not email regardless of whether a commit happened.
- **Exit 2 (wrote portfolio.json, found drift worth a look — new/removed/date-changed leases):** this is routine, not an alarm. Post a brief status note to the Notion Operations Hub (page `32b6ecd8-9e59-81f2-b329-df3fd0e25062`, or search for "Operations Hub" if that ID has moved — verify before trusting a hardcoded ID) summarizing the new/removed/date-changed lease counts from the script's own printed output. No email for this case. Also runs the Auto-commit step above.
- **Exit 1 (refused to write — anomaly floor tripped, or corrupt overlay/previous-snapshot):** `portfolio.json` is UNCHANGED, real financial/portfolio data is stale until a human investigates. This is an alarm: post to Notion Operations Hub AND email `ggoldberg@oxfordra.net` ONLY (no cc — routing canon, see CLAUDE.md Email & scheduler section) via the Outlook COM send path (`C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` — the SOLE send path). Quote the script's own refusal message verbatim in both the Notion note and the email so the specific cause (overlay corruption, previous-snapshot corruption, 0-lease parse, >25% lease removal) is immediately visible, not just "it refused." Do NOT retry automatically and do NOT pass `--force` — this needs a human decision, not an automated override.
- **Exit 3 (unexpected crash — parseWorkbook failure, missing worksheet, workbook locked mid-sync):** same alarm treatment as exit 1 (Notion + email, ggoldberg only, quote the error). On a COM send failure specifically: retry the send once, then flag loudly in the Notion completion row if it still fails — do not silently drop the alert.

## Guard conditions

- If the script itself is missing (e.g. this task fires before a future revert of the branch that added it), report that clearly as a setup/environment problem in the Notion note and email — do not fabricate a "no drift" result.
- Never fabricate lease counts, drift details, or a "clean" result if the script's actual output is ambiguous or unparseable — if you can't tell what happened from the output, say so explicitly and escalate with a QUESTION FOR GABRIEL rather than guessing.

## Pointers, not duplication

- Do not re-implement the drift-check's own logic (id comparison, staleness thresholds, anomaly floor) — that all lives in the script itself and in `server/config.ts`'s `isSnapshotStale`. This task's only job is to run the script, read its output, and route the result (silent / Notion-only / Notion+email) per the exit code.
- **Corrected 2026-07-26 — the line below was stale.** `ora-cc-snapshot-refresh` (weekly Monday `npm run extract`) now shares BOTH the anomaly floor AND the drift report with this task (`evaluateAnomalyFloor`/`formatDriftReport`, exported from `scripts/lease-snapshot-drift-check.ts` and imported by `scripts/extract-workbook.ts`) — see event_log.md, "orphaned-task-forensics: portfolio.json snapshot regression" and its follow-ups, 2026-07-26. A manual off-schedule `npm run extract` run corrupted two tenants' lease-end dates on 2026-07-25 specifically because that path had neither protection at the time. `ora-cc-snapshot-refresh` remains the lower-frequency (weekly) backstop by CADENCE — this task is still the primary, more-frequent (3x/weekday) refresh path — but it is no longer the only one with data-integrity protection. Do not repeat the old "no anomaly floor, no drift reporting" framing.