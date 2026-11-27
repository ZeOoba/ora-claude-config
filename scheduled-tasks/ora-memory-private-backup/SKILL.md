---
name: ora-memory-private-backup
description: Every 2h (10:47-22:47): mirror the local-only memory folder to the PRIVATE repo ZeOoba/ora-memory-private, commit if changed, push; refuses on public repo or mass memory loss. [MODEL: UNVERIFIABLE | checked 2026-11-20]
---

CONNECTOR SCOPE: no connectors. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7, Claude Code Remote, or any other connector, even if they are available in this session. This task works only through local shell commands and the Outlook COM send script; if the shell is unavailable, stop and report rather than reach for a connector.

PURPOSE: The ORA memory folder (C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory) is LOCAL-ONLY since 2026-11-20 (PR 476): it is git-ignored in the public ora-claude-config repo because it holds figures, contacts and tenant records. Its only off-box copy is the PRIVATE GitHub repo ZeOoba/ora-memory-private (local clone C:\Users\Owner\ora-memory-private). This task keeps that copy current.

GUARD (double-fire, added 2026-11-25; see scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md): one run per cron slot. A catch-up burst after the app reopens must not run the sync or send the failure email twice for the same slot.

STEPS:
0. Before anything else, compute RUN_ID once with `date +%s`, then claim the slot (one line, as written):
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-memory-private-backup --slot-times 10:47,12:47,14:47,16:47,18:47,20:47,22:47 --run-id <run_id> --ttl-min 20
   Take `<block>` and `<etDate>` VERBATIM from the claim output's `block` and `etDate` fields and reuse them for complete and fail. Never recompute them and never do timezone math in the shell: Git Bash on this machine returns UTC, which puts the 20:47 and 22:47 ET runs on the next day.
   - Exit 0 → proceed to step 1.
   - Exit 10 → this slot's run already completed. End silently: no sync, no email. This is a normal skip, not a miss.
   - Exit 11 → another run holds this slot. Stand down the same way.
   - Exit 2, or no `block` in the output → the guard is broken. Do not guess a slot, and call neither complete nor fail. Set the run date and `<block>` by the step 1 fallback rule, then send the step 5 email with subject `ORA memory backup guard failure YYYY-MM-DD` and the claim output as the body, then stop.
   - Any other exit code → tooling failure: fail open. Run steps 1–6 without a claim, call neither complete nor fail, and quote the code in the run summary.
   ONLY the run that got exit 0 calls `complete` or `fail`; a run that stood down calls neither.
1. Run date = `<etDate>` from the claim output (YYYY-MM-DD, ET). Use it everywhere below as YYYY-MM-DD. FALLBACK RULE: when the claim output has no `etDate` or no `block` (exit 2, any other non-zero exit, or an exit 0 that came back without them), set the run date from PowerShell `Get-Date -Format yyyy-MM-dd` (ET on this host; never Git Bash `date`, which returns UTC). Set `<block>` to `failopen-` followed by PowerShell `Get-Date -Format HHmm`. Then two fail-open sends on one day get different dedup keys, and neither suppresses the other. Say in the summary that the fallback was used. A fallback `<block>` is only for the dedup key: never pass it to complete or fail.
2. Run exactly this, with a 300000 ms timeout, and capture all output and the exit code:
   `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/ora-memory-private/sync-memory.py`
   Do not run any other git command, do not edit any file, do not retry it more than once. The script itself: refuses (exit 2) unless the repo is PRIVATE, refuses (exit 2) if the live memory folder looks wiped (fewer than 80% of the backup's files, or MEMORY.md / event_log.md / open-items-tracker.md gone), otherwise mirrors, commits if changed and pushes (exit 0), or exits 3 on a git/push failure.
3. Exit 0: done. Print the script's single result line as the run summary. No email. Go to step 7.
4. Exit 3, or the script could not start (including Python printing `can't open file`, which exits 2 but is NOT a REFUSED): retry the same command ONCE after 60 seconds. Retry exits 0 → step 3. Anything else → step 5.
4b. CATCH-ALL: any other outcome not covered by steps 3, 4 and 5 (exit 1 including a Python traceback, any other non-zero code, a timeout, or no exit code captured) is a failure. Do not retry it; go straight to step 5. Never end such a run silently.
5. Exit 2 (REFUSED), exit 3 or could-not-start twice, or any step 4b failure: send ONE email via the Outlook COM script, the SOLE send path, to ggoldberg@oxfordra.net ONLY (no cc):
   `powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/Owner/.claude/scheduled-tasks/_shared/send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "ORA memory backup FAILED YYYY-MM-DD" -Body "<first line: the exit code, or 'timeout' / 'no exit code'; then the script's output lines (or 'no output'); for a REFUSED exit 2 only, then: 'The live memory folder may need checking before the next backup. Nothing was overwritten in the private repo; its git history keeps every earlier snapshot.'>" -BodyFormat text -DedupTaskId ora-memory-private-backup -DedupPeriodKey YYYY-MM-DD-<block>`
   This is contract mode (rules.md §2). Run the send command once only, whatever its exit code: the script handles transient COM failures itself, and an exit 6 means the message MAY have gone out. On any non-zero exit, flag it loudly in the run summary with the script's output line. Do not halt for it.
6. Never fabricate: report only what the script printed. If anything is unclear, end the summary with a QUESTIONS FOR GABRIEL list.
7. Close the claim (only if step 0 returned exit 0 with a `block` in its output). When the run ends normally, including after a step 5 failure email:
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-memory-private-backup --block <block> --run-id <run_id>
   If the run aborts before reaching a normal end:
   python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-memory-private-backup --block <block> --run-id <run_id> --error "<what broke>"

Never print file contents, figures, names or phone numbers from the memory folder in the summary or email; the script output contains only counts and git shortstats.