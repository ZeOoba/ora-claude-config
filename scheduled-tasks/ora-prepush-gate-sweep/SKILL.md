---
name: ora-prepush-gate-sweep
description: Weekly Thursday 11:00 ET — runs the three pre-push gates against ~/.claude WITHOUT pushing, so a broken gate or a stale live-state test is found on a schedule instead of at someone's next push. Silent when clean; emails ggoldberg only on a failure. Read-only: never pushes, never commits, never mints an override token. [MODEL: claude-sonnet-5 | set 2026-09-17]
---

ORA weekly pre-push gate sweep. Registered 2026-09-17 (Gabriel-directed) after three separate defects surfaced in one day ONLY because someone happened to push: a stale hardcoded baseline in test_check_open_items_duplicate_ids.py that blocked every session's pushes, and eos-review-gate silently failing OPEN because hooks/lib/git_probe_common.py was missing on the branch. Both had been broken for days with nothing watching. This task is the watcher.

READ-ONLY BY CONSTRUCTION. Never push, never commit, never stage, never edit a file, and NEVER mint an override token of any kind. If a gate blocks, that is the finding -- report it, do not clear it.

STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-18; run before STEP 1). Same overnight-offline catch-up-burst exposure documented fleet-wide (README-DOUBLE-FIRE-GUARD.md) -- a second fire in the same window would re-run the gates twice and, on a failure day, send a duplicate FAIL email. Run this first:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-prepush-gate-sweep --block main --run-id <run_id> --ttl-min 30
```

- **Exit 10** -> today's sweep already completed. Log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, do not re-run the gates, and report it as a NORMAL skip citing the earlier run's result.
- **Exit 11** -> another fire is live. Stand down identically.
- **Exit 0** -> proceed to STEP 1.

**Only the run that holds the claim may call `complete` or `fail`.** A run that stood down (exit 10 or 11) calls neither. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`. Do not "fix" a double-fire by retiming this task's cron -- the burst is documented fleet-wide behavior; the guard belongs here.

STEP 1 — Run the three gates from C:\Users\Owner\.claude, each with stdin closed, capturing exit code and output. They read the LIVE tree, which is the point:
  python hooks/git-prepush-doctrine-gate.py < NUL
  python hooks/git-prepush-hook-tests-gate.py < NUL
  python hooks/git-prepush-confidential-scan.py < NUL
The confidential scan expects push refs on stdin; with stdin closed it scans nothing and exits 0. Report that as NOT-EXERCISED, never as a pass -- do not fabricate coverage it did not provide.

STEP 2 — Classify each result:
  - exit 0 with no FAIL lines: clean.
  - The hook-tests gate prints "hook-tests-gate: N pass, M fail, K env-skip (of T)". Quote that line verbatim. It retries a timed-out test once at a doubled budget and prints "timeout-retry (... not blocking)" -- that is NOT a failure; report it separately as load-related.
  - A genuine FAIL: capture the test name and the first ~15 lines of its output.
STEP 3 — Aging check. Read maintenance/_state/prepush-gate-sweep.json if it exists (a plain state file this task owns; writing it is allowed and is the ONLY write permitted here). It holds {"lastCleanAt": ISO, "consecutiveFailures": N, "failingTests": [...]}. Update it with this run's result. If the SAME test has now failed on 2+ consecutive sweeps, say so explicitly in the subject -- a gate broken for two weeks is a different problem from one broken today.

STEP 4 — Report.
  - CLEAN: write the state file, send NOTHING, and stop. Silence is the success signal. Close the STEP 0 claim with no `--email-sent-at` (a no-send completion is legitimate, same convention as `ora-open-sessions-board`'s 0-actionable-items path):
```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-prepush-gate-sweep --block main --run-id <run_id>
```
  - ANY genuine FAIL, or either of the first two gates exiting non-zero:

    **PRE-SEND SENT-ITEMS PROBE (mandatory, immediately before the send below).** Layer 2 of the STEP 0 guard, dated stem:
```
powershell -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1 -SubjectFile "<temp .txt containing exactly: pre-push gates FAILING - <today's date>>"
```
    The stem must sit at position 0 of the subject after `outlook-sent-probe.ps1` strips the leading `[ACTION]` tag (README-DOUBLE-FIRE-GUARD.md, Layer 2) -- so the date has to immediately follow "FAILING -" in the composed subject below, with any variable count/repeat suffix AFTER the date, never between the stem and the date.

    Exit 10 -> do NOT send, log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS`, and still call `block-sentinel.py complete` below so Layer 1 re-converges. Exit 1 -> fail open: send anyway, and note the probe gap in the email body.

    Send ONE email to ggoldberg@oxfordra.net ONLY, no cc, via:
```
powershell -NoProfile -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1"
```
    Subject: "[ACTION] pre-push gates FAILING - <today's date> -- <N> test(s)" (add " x<N> weeks" when STEP 3 shows a repeat, appended at the very end). The date must come immediately after "FAILING -", matching the probe's dated stem exactly -- do NOT put the test count or any other variable text between "FAILING" and the date. <today's date> is the run date computed once at run start with `date '+%A %Y-%m-%d'` (date part in every date slot; weekday only where one is named) and reused verbatim in every title, subject and body (probe stem included).
    Body: the verbatim gate summary line, each failing test with its captured output, whether it is new or repeating, and this reminder: a failing gate blocks EVERY session's pushes, not just the author's, so it is shared infrastructure, not one person's bug. On send exit 2 or 4, retry once, then stop. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the failure record named above, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.

    Close the STEP 0 claim now that the email has landed (or been skipped as an already-sent duplicate per the probe above):
```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-prepush-gate-sweep --block main --run-id <run_id> --email-sent-at <ISO8601>
```
Never fabricate a count -- report exactly what the gates printed. If a gate script is missing, report it as MISSING (a deleted gate is itself a finding), never as a pass.

If the run aborts before reaching either branch above, call `fail` instead so the claim does not strand at IN_PROGRESS for the full TTL:
```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-prepush-gate-sweep --block main --run-id <run_id> --error "<what broke>"
```