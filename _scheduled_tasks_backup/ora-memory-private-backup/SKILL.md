---
name: ora-memory-private-backup
description: Every 2h (10:47-22:47): mirror the local-only memory folder to the PRIVATE repo ZeOoba/ora-memory-private, commit if changed, push; refuses on public repo or mass memory loss. [MODEL: UNVERIFIABLE | checked 2026-11-20]
---

CONNECTOR SCOPE: no connectors. Do not call Notion, Microsoft 365, HubSpot, Netlify, Context7, Claude Code Remote, or any other connector, even if they are available in this session. This task works only through local shell commands and the Outlook COM send script; if the shell is unavailable, stop and report rather than reach for a connector.

PURPOSE: The ORA memory folder (C:\Users\Owner\.claude\projects\C--Users-Owner-OneDrive---Oxford-Capital-Partners\memory) is LOCAL-ONLY since 2026-11-20 (PR 476): it is git-ignored in the public ora-claude-config repo because it holds figures, contacts and tenant records. Its only off-box copy is the PRIVATE GitHub repo ZeOoba/ora-memory-private (local clone C:\Users\Owner\ora-memory-private). This task keeps that copy current.

GUARD: none beyond the script's own safety checks; run every fire.

STEPS:
1. Compute the run date once: `date '+%A %Y-%m-%d'`. Reuse its date part (YYYY-MM-DD) everywhere below.
2. Run exactly this, with a 300000 ms timeout, and capture all output and the exit code:
   `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:/Users/Owner/ora-memory-private/sync-memory.py`
   Do not run any other git command, do not edit any file, do not retry it more than once. The script itself: refuses (exit 2) unless the repo is PRIVATE, refuses (exit 2) if the live memory folder looks wiped (fewer than 80% of the backup's files, or MEMORY.md / event_log.md / open-items-tracker.md gone), otherwise mirrors, commits if changed and pushes (exit 0), or exits 3 on a git/push failure.
3. Exit 0: done. Print the script's single result line as the run summary. No email.
4. Exit 3 (or the script could not start): retry the same command ONCE after 60 seconds. If it still fails, go to step 5.
5. Exit 2 (REFUSED), or exit 3 twice: send ONE email via the Outlook COM script, the SOLE send path, to ggoldberg@oxfordra.net ONLY (no cc):
   `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 -To ggoldberg@oxfordra.net -Subject "ORA memory backup FAILED YYYY-MM-DD" -Body "<the script's output lines, then: 'The live memory folder may need checking before the next backup. Nothing was overwritten in the private repo; its git history keeps every earlier snapshot.'>" -BodyFormat text -DedupTaskId ora-memory-private-backup -DedupPeriodKey YYYY-MM-DD`
   On send exit 2 or 4: retry once; if it still fails, say so loudly in the run summary. Do not halt for it. On exit 5 or 6 (or any code other than 0, 2 or 4) do NOT retry: flag it loudly in the run summary and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
6. Never fabricate: report only what the script printed. If anything is unclear, end the summary with a QUESTIONS FOR GABRIEL list.

Never print file contents, figures, names or phone numbers from the memory folder in the summary or email; the script output contains only counts and git shortstats.