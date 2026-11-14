---
name: ora-passed-deal-tracker-spec-sync-1113
description: One-time (2026-11-13 18:15 ET, after Friday's ora-checkout-merge-forward) CC/MCP task: sync origin/main's ora-passed-deal-tracker SKILL.md (#402/#411/#413/#416) to the live fleet path via propagate-task-spec.py, only if every .claude script the spec names exists in the live checkout and the shared-checkout preflight is CLEAR; otherwise HOLD and email ggoldberg why. Gabriel in-turn 2026-11-06 "Sync after catch-up". Tracker next fires 11-15 06:30. [MODEL: UNVERIFIABLE | set 2026-11-06]
---

CONNECTOR SCOPE: no connectors. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7, Claude Code Remote, or any other connector, even if they are available in this session. Work only through Bash, the local filesystem and the Outlook COM send script. If Bash or the filesystem is unavailable, stop and report that in the run summary.

# One-time: sync the ora-passed-deal-tracker live spec after the checkout catch-up

Background (authorized by Gabriel in-turn 2026-11-06, "Sync after catch-up"): ora-claude-config PRs #402, #411, #413 and #416 changed `scheduled-tasks/ora-passed-deal-tracker/SKILL.md` on origin/main. The live copy the scheduler runs (`C:/Users/Owner/.claude/scheduled-tasks/ora-passed-deal-tracker/SKILL.md`, in the ~/.claude checkout on branch live/primary-checkout) was held back because main's Step 5b runs `C:/Users/Owner/.claude/maintenance/funnel-backtest.py`, which the live checkout did not yet have. The weekly `ora-checkout-merge-forward` (Fridays 16:45) is expected to bring it in. ora-passed-deal-tracker next fires 2026-11-15 06:30. This task syncs the spec only when it is safe, and otherwise holds and tells Gabriel.

Rules: never fabricate a result; quote command output verbatim. Never edit the live SKILL.md by hand and never use Bash redirection onto it; the ONLY write path is `propagate-task-spec.py`. Never run git merge, reset, checkout, stash, commit or push in ~/.claude. Never create or use any override token. PY = `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe` (bare `python` may not be on PATH). Run gates unpiped: `cmd > file 2>&1; echo "EXIT: $?"`, then read the file.

Progress marker after each side-effect step (N of 3):
`C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\task-progress-marker.py write --fleet cc --task-id ora-passed-deal-tracker-spec-sync-1113 --step N --of 3 --note "<short state>"`

## Step 0 — run date
Run `date '+%A %Y-%m-%d'` once. Use its date part (YYYY-MM-DD) in every subject, header and file name below.

## Step 1 — checks (no writes)
Work in `C:/Users/Owner/.claude`. Make a temp dir `T=C:/Users/Owner/AppData/Local/Temp/ora-tracker-sync-YYYY-MM-DD`.
a. `git fetch origin main -q`. On failure: outcome HOLD (reason: fetch failed, quote the error).
b. Already in sync? Compare `git hash-object --path scheduled-tasks/ora-passed-deal-tracker/SKILL.md scheduled-tasks/ora-passed-deal-tracker/SKILL.md` with `git rev-parse origin/main:scheduled-tasks/ora-passed-deal-tracker/SKILL.md`. Equal → outcome ALREADY-SYNCED; skip to Step 3.
c. Export the source: `mkdir -p $T/src/ora-passed-deal-tracker && git show origin/main:scheduled-tasks/ora-passed-deal-tracker/SKILL.md > $T/src/ora-passed-deal-tracker/SKILL.md`.
d. Dependency check: list every `C:/Users/Owner/.claude/...` path ending in .py/.ps1/.json that the exported spec names (`tr -d '\r' < file | grep -oE 'C:/Users/Owner/\.claude/[A-Za-z0-9_./-]+\.(py|ps1|json)' | sort -u`) and test each with `[ -e path ]`. Any missing → outcome HOLD (reason: list the missing paths). Also record `maintenance/_state/checkout-merge-forward-last-run.json` verbatim for the report.
e. Preflight: `$PY maintenance/preflight-shared-checkout.py --repo . --paths scheduled-tasks/ora-passed-deal-tracker/SKILL.md --since $(git rev-parse HEAD) > $T/preflight.txt 2>&1; echo "EXIT: $?"`. Non-zero → outcome HOLD (reason: preflight verdict, quote its RESULT_JSON line).
f. Dry run: `$PY maintenance/propagate-task-spec.py --pair "$T/src/ora-passed-deal-tracker/SKILL.md" "C:/Users/Owner/.claude/scheduled-tasks/ora-passed-deal-tracker/SKILL.md" --tag YYYY-MM-DD-tracker-sync --max-replaced 80 --max-added 250 > $T/dry.txt 2>&1; echo "EXIT: $?"`. Non-zero or any "refused" → outcome HOLD (quote dry.txt).

## Step 2 — apply (only if every Step 1 check passed)
Re-run Step 1f's command with `--apply` appended (output to `$T/apply.txt`). Then marker step 1.
Verify: the live `git hash-object --path ...` value must equal `git rev-parse origin/main:scheduled-tasks/ora-passed-deal-tracker/SKILL.md`. Equal → outcome SYNCED. Not equal → outcome FAILED (quote both hashes and apply.txt; the backup `SKILL.md.bak-YYYY-MM-DD-tracker-sync` sits beside the live file). Never retry the apply.

## Step 3 — event log (all outcomes)
Write an entry file `$T/el.md` with header `## YYYY-MM-DD — ora-passed-deal-tracker live spec sync: <OUTCOME>` and 2-5 lines: outcome, the live and origin/main blob hashes, the reason (for HOLD/FAILED), the merge-forward last-run status. For SYNCED include the literal line `- **LIVE task spec change:** ora-passed-deal-tracker SKILL.md propagated via propagate-task-spec.py (#402/#411/#413/#416).` Append ONLY via `$PY C:/Users/Owner/.claude/maintenance/append-event-log.py --entry-file <Windows path of el.md>` (use a C:/ path, not /c/). Exit 1 = malformed header: match the newest existing heading's form once. Then marker step 2.

## Step 4 — email (all outcomes)
Send via Outlook COM, the SOLE send path, TO ggoldberg@oxfordra.net ONLY (no cc):
`C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Passed-Deal Tracker Spec Sync — <OUTCOME> YYYY-MM-DD" -BodyFile "<temp html>" -BodyFormat html`
Body: outcome in one line; for SYNCED the hashes and "live for the 11-15 06:30 run"; for HOLD/FAILED the exact reason, quoted evidence, and a QUESTIONS FOR GABRIEL section with one question: "Sync the tracker spec by hand before the 11-15 06:30 run, or let it run on the old spec this month?" Retry only on exit 2 or 4, once; never resend after any other exit (send state unknown). If the retry fails, say so loudly in the run summary; do not halt. Then marker step 3.

## Step 5 — run summary
One line: outcome · live blob · main blob · event-log append exit · send exit.