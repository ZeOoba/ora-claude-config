---
name: ora-full-gate-weekly
description: Weekly Monday 11:30 ET (OI-254) - runs the FULL `npm run gate` for oxford-command-center from a throwaway origin/main worktree on this machine (Master Workbook + Property Financials mounted), so reconcile:noi-crosscheck, warehouse:verify and warehouse:drift run on a schedule (they are absent from gate:ci). Silent when clean; emails ggoldberg only on a non-zero stage, stale or unreachable input. Pause-aware. Read-only. [MODEL: claude-sonnet-5-5 | set 2026-10-13]
---

ORA weekly full-gate run (OI-254). CI's `gate:ci` omits reconcile:noi-crosscheck, warehouse:verify and warehouse:drift (they need the Master Workbook and the 32-file Property Financials set, which never leave Oxford machines); the self-hosted workflow has zero runs and no matching runner. This task is the watcher until PR-blocking CI is decided (Gabriel declined PR-blocking 2026-10-13: do NOT provision a runner or add a schedule: trigger).

READ-ONLY BY CONSTRUCTION. Never commit, push, stage, or edit any tracked file, the workbook, or the live warehouse DB. Work only in a throwaway detached worktree of origin/main under the temp dir; NEVER touch the shared checkout C:\Users\Owner\oxford-command-center (it carries other sessions' WIP). Remove the worktree on every exit path.

Compute the run date once: `date '+%A %Y-%m-%d'`; reuse that value in every subject and body (date part in date slots, weekday only where one is named).

STEP 0 - DOUBLE-FIRE ENTRY GUARD:
  python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-full-gate-weekly --block main --run-id <run_id> --ttl-min 60
  Exit 10 -> already completed today: log BLOCK_MAIN_ALREADY_COMPLETE_TODAY, report a normal skip, stop. Exit 11 -> another fire is live: stand down identically. Exit 0 -> continue. Only the run holding the claim calls complete/fail. Contract: _shared\README-DOUBLE-FIRE-GUARD.md.

STEP 1 - PAUSE-AWARE GUARD (before running anything):
  a. Read C:\Users\Owner\.claude\maintenance\_state\fleet-pause-windows.json and call list_scheduled_tasks. If any window for the CC/MCP fleet is open (open:true), or ora-master-workbook-ingest is enabled:false, the fleet is paused: log SKIPPED_FLEET_PAUSED, call block-sentinel complete with no email, stop. A pause is NOT red.
  b. Input freshness: the Master Workbook mtime (read-only; locate it the way scripts/reconcile-noi-crosscheck.ts / extract-workbook.ts resolve WORKBOOK_PATH) must be <=7 days old (CLAUDE.md STALE canon). If older, do not call the gate a failure: report class STALE_INPUT (own subject tag, see STEP 4).
  c. Input reachability: if the workbook or FINANCIALS_DIR is unreadable (OneDrive offline), wait 10 minutes and retry once; if still unreadable, report class INPUT_UNAVAILABLE (distinct from a gate FAIL).

STEP 2 - RUN (stdin closed, capture exit code + output per stage):
  cd C:\Users\Owner\oxford-command-center; git fetch origin; record origin/main SHA.
  git worktree add --detach <tmp>\ora-full-gate-<run_id> origin/main ; cd into it; npm ci.
  Set WAREHOUSE_DB=C:\Users\Owner\oxford-command-center\data\warehouse\finance.sqlite (the live warehouse; a fresh worktree has none, so without this the stages resolve a nonexistent DB). If that file is absent, report warehouse:drift as NOT-EXERCISED, never as a pass. WORKBOOK_PATH and FINANCIALS_DIR use the machine/script defaults.
  Run each stage as its own command so the email names the failing stage: npm run governance ; typecheck ; lint ; check:dev-css ; check:schema-drift ; test ; reconcile:snapshot ; reconcile ; reconcile:noi-crosscheck ; warehouse:verify ; warehouse:drift. Continue past a failing stage and run the remaining ones so one failure does not mask another. Quote each stage's exit code. Never fabricate a count or a pass; a missing script is MISSING (itself a finding).

STEP 3 - AGING: read/write C:\Users\Owner\.claude\maintenance\_state\full-gate-weekly.json {lastCleanAt, consecutiveFailures, failingStages} (the ONLY file this task may write). If the same stage failed on 2+ consecutive runs say so in the subject.

STEP 4 - REPORT:
  CLEAN (every stage exit 0, none NOT-EXERCISED except an absent optional warehouse DB reported in the log): write state, send NOTHING, `block-sentinel.py complete --task ora-full-gate-weekly --block main --run-id <run_id>` (no --email-sent-at).
  ANY non-zero stage, STALE_INPUT, or INPUT_UNAVAILABLE:
    PRE-SEND SENT-ITEMS PROBE: powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: full gate FAILING - <date>>". Exit 10 -> do NOT send, log MAIN_EMAIL_ALREADY_IN_SENT_ITEMS, still call complete. Exit 1 -> fail open, send anyway and note the probe gap.
    Send ONE email to ggoldberg@oxfordra.net ONLY (no cc, never ze@) via: powershell -NoProfile -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1
    Subject: "[ACTION] full gate FAILING - <date> -- <first failing stage>" (or "full gate STALE INPUT - <date>" / "full gate INPUT UNAVAILABLE - <date>"); any repeat tag appended at the very end, never between the stem and the date.
    Body: failing stages with exit code and first ~25 lines of each stage's output, origin/main SHA, workbook mtime, new vs repeating, and which stages were NOT-EXERCISED.
    Non-zero send exit: retry ONCE, then flag loudly, call block-sentinel fail --error "send failed" and do NOT call complete (a complete after a fail records emailSentAt=None and suppresses the rest of the day), and DO NOT halt worktree cleanup. The automation-health-monitor producer-beacon check catches a silent send.
    On a successful send: block-sentinel.py complete ... --email-sent-at <ISO8601>.
  Always remove the worktree (git worktree remove --force). If the run aborts early call: block-sentinel.py fail --task ora-full-gate-weekly --block main --run-id <run_id> --error "<what broke>".

Escalation: any data gap you cannot resolve goes in the email under QUESTIONS FOR GABRIEL; never fabricate. Event-log entries only via python ~/.claude/maintenance/append-event-log.py with header `## YYYY-MM-DD - <title>`.