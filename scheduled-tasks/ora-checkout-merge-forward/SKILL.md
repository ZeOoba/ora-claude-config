---
name: ora-checkout-merge-forward
description: Daily 4:45 PM ET (CC/MCP fleet, filesystem/git tool) — safe merge-forward of the primary ~/.claude checkout's current branch with origin/main via maintenance/checkout-merge-forward.py (OI-249 candidate a, Gabriel-selected 2026-09-09). Never leaves a stuck/conflicted state: lands a clean merge when the tree allows it, no-ops when uncommitted local changes overlap (the ordinary case), auto-aborts on a real textual conflict. Silent on MERGED/NOOP_CLEAN/BLOCKED_STAGED/BLOCKED_DIRTY_OVERLAP; emails ggoldberg only on BLOCKED_CONFLICT or ERROR. Paired with cross-repo-wip-scan.py's weekly BRANCH_DRIFT detection (ora-weekly-hygiene Block I) -- that alarms on drift, this is the corrector. [MODEL: claude-sonnet-5 | set 2026-09-09]
---

You are running the daily checkout merge-forward sync, on the Claude Code (CC/MCP) fleet. You start fresh with no memory of prior runs.

WHY THIS TASK EXISTS: the primary `~/.claude` checkout sat on `feat/model-canary-probe-step25` for weeks, was merged into `main` once (2026-08-23) without its own HEAD ever moving back, and re-diverged to 40+ commits behind with ~100 dirty files -- found three separate times by accident during unrelated triage/audit passes (open-items-tracker.md#OI-249). `cross-repo-wip-scan.py` (wired into `ora-weekly-hygiene` Block I) now DETECTS that drift weekly. This task is the paired CORRECTOR: it keeps the checkout's current branch merged forward with `origin/main` on a daily cadence so drift never has the chance to compound again, without ever requiring the checkout to be clean first.

STEP 0 -- CLAIM (mandatory, this is a repo-maintenance sweep on the shared `~/.claude` checkout per register-scheduled-task step 3c): run
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/hooks/lib/claim_work.py" claim sched-repo-housekeeping "daily checkout-merge-forward sync run" --paths maintenance/checkout-merge-forward.py
If the claim is refused because a live (non-`sched-`) holder is genuinely active on an overlapping path, STOP and report BLOCKED_CLAIMED in the run log -- do not `--force` a live human/session's claim; a `sched-` claim from a PRIOR stuck run of this same task is fine to `--force`/`--steal` per the claim tool's own routine-takeover guidance for that namespace.

STEP 1 -- run the sync script:
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/checkout-merge-forward.py" --json
Capture its exit code and full JSON output (`status`, `detail`, `commits_merged`, `sha`). Do NOT reimplement or second-guess this script's logic -- it is authoritative, and it already guarantees the checkout is left either freshly merged or in exactly the state it was found in.

STEP 2 -- RELEASE the claim regardless of outcome:
  "C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe" "C:/Users/Owner/.claude/hooks/lib/claim_work.py" release sched-repo-housekeeping

STEP 3 -- outcome handling (read `status` from STEP 1's JSON):
  - `NOOP_CLEAN` -- already in sync. Routine, no alarm.
  - `MERGED` -- landed `commits_merged` commit(s) forward, new HEAD is `sha`. Routine, no alarm (this is the intended, desired outcome). Append one line to event_log.md via the sole writer: `"C:/Users/Owner/AppData/Local/Programs/Python313/python.exe" "C:/Users/Owner/.claude/maintenance/append-event-log.py"` with a short entry noting the date, commits_merged count, and sha -- do NOT Edit-anchor event_log.md directly.
  - `BLOCKED_STAGED` or `BLOCKED_DIRTY_OVERLAP` -- git refused safely before writing anything; this is the ORDINARY case on this checkout (it carries a large multi-session WIP backlog most days). Routine, no alarm.
  - `BLOCKED_CLAIMED` (from STEP 0) -- another session is genuinely active on this path. Routine, no alarm -- just try again tomorrow.
  - `BLOCKED_CONFLICT` -- a real textual conflict was found and the script already ran `git merge --abort` to fully restore the pre-merge state (verify: this status implies the tree is untouched, never left mid-merge). This DOES need a human to look at why origin/main and this branch have diverging edits to the same lines. ALARM.
  - `ERROR` -- the script itself could not run cleanly (not a git repo, fetch failed, index unreadable, or a commit failed unexpectedly after a clean merge stage). ALARM -- this is a tooling problem, investigate the probe, never treat as "clean".

STEP 4 -- ALARM (BLOCKED_CONFLICT or ERROR only): send a best-effort email via the SOLE send path -- Outlook COM:
  C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Checkout Merge-Forward — [status] [YYYY-MM-DD]" -BodyFile "<temp html>" -BodyFormat html
  TO ggoldberg@oxfordra.net ONLY -- never cc egoldberg@oxfordra.net, never ze@. Body: the exit code, full `detail` text, and (for BLOCKED_CONFLICT) which file(s) the conflict output named. On a non-zero send exit: retry ONCE, then do not suppress the alarm -- leave it for the next run's log to still show unresolved. Exit-code doctrine: exit 2 (COM failure)/4 (timeout) -> retry once then flag loudly; exit 1 (usage)/3 (stuck wizard) -> do not retry, flag immediately.

STEP 5 -- write the run outcome (best-effort, non-fatal) to `C:\Users\Owner\.claude\maintenance\_state\checkout-merge-forward-last-run.json`: `{"lastRun": "<ISO timestamp>", "status": "<status>", "commitsMerged": <N or null>, "sha": "<sha or null>"}`. This exists so a future session (or cross-repo-wip-scan.py's own BRANCH_DRIFT report) can see when this corrector last ran without re-invoking it.

NEVER: run `git add -A`, `git commit -a`, `git reset --hard`, `git rebase`, or any force-push on this checkout. Never touch any path outside what STEP 1's script itself touches. Never fabricate a MERGED/commits_merged result you did not read verbatim from the script's own JSON output.

Full design rationale, safety model, and 28-test suite: `maintenance/checkout-merge-forward.py` (module docstring) and `maintenance/_tests/test_checkout_merge_forward.py`. Sibling: `maintenance/cross-repo-wip-scan.py` (the weekly detector, `ora-weekly-hygiene` Block I) -- do not duplicate its branch-drift detection logic here; this task only acts, it does not independently re-detect.