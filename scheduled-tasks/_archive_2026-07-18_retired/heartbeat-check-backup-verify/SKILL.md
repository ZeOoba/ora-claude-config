---
name: heartbeat-check-backup-verify
description: Backup verification: confirm heartbeat-beacon-recovery-check actually ran and sent its email; alert directly if not.
---

Background: a one-time scheduled task called `heartbeat-beacon-recovery-check` was set to fire at 10:00 AM ET on 2026-07-17. Its job: check whether the Cowork Heartbeat Notion beacon (page id 35c6ecd8-9e59-81d5-8d2c-d08002458b78) recovered after a 2026-07-16 write-failure investigation, log the result to event_log.md, and email Gabriel (ggoldberg@oxfordra.net) a one-line verdict. There is a real, concrete risk that task's first unattended run stalls on a tool-approval prompt (the same failure class investigated for `ora-cowork-heartbeat` itself that day — its registry entry lacked an approvedPermissions grant) and never completes or sends anything. This task is a backup check, firing 15 minutes later, to catch that silent-failure case.

Do this:
1. Check `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt` (tail is fine) for a line containing "Cowork Heartbeat beacon" with a timestamp on 2026-07-17 around 10:00-10:15 AM ET. If found, the primary task's email sent successfully — STOP HERE, do nothing further (no action needed, do not send any email, do not log anything — the primary task already covered it).
2. If NOT found in the send log, also check `~/.claude/projects/C--Users-Owner-OneDrive---Oxford-Capital-Partners/memory/event_log.md` for a "## 2026-07-17 — ora-cowork-heartbeat beacon recovery check" entry near the top (it's newest-first). If that entry exists but no email was sent, the task partially completed — note this distinction.
3. If NEITHER the send-log line NOR the event_log entry exist: the primary task silently failed to run or complete. In that case:
   a. Independently do the check the primary task was supposed to do: use the Notion MCP `fetch` tool on page id 35c6ecd8-9e59-81d5-8d2c-d08002458b78, read the "Last heartbeat: <timestamp>" line, and compare against the known-stale baseline `2026-07-15T21:57:21Z` (later = recovered, unchanged = still stuck).
   b. Check `list_scheduled_tasks` for the `heartbeat-beacon-recovery-check` task's current state (enabled/disabled, lastRunAt) to report what evidence exists about whether it fired at all.
   c. Send an email via `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (-To ggoldberg@oxfordra.net only, no cc, -BodyFormat text) with subject "Cowork Heartbeat beacon — backup check (primary task did not complete)". Body: state plainly that the primary 10:00 AM check task appears to have not run or not finished (cite what you found in step 3b), then report the beacon state you found independently in step 3a as the substantive answer Gabriel actually needs. Keep it under 6 sentences.
   d. Log one line to event_log.md via `python C:\Users\Owner\.claude\maintenance\append-event-log.py --entry-file <path>` under heading "## 2026-07-17 — Backup check: heartbeat-beacon-recovery-check did not complete, ran independently" summarizing the same finding.

Do not touch anything else. This is a one-time read-only diagnostic; it auto-disables after this single run.