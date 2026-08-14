---
name: ora-monday-sync
description: Monday week-ahead operations sync — retimed 2026-07-21 (Gabriel-directed) from 7:30 AM to 10:35 AM ET after 2 consecutive Monday/Tuesday mornings of Desktop-app-closed catch-up bursts pushed this task 3h+ late; new slot sits inside the window the app has reliably been open. [MODEL: claude-sonnet-5 | set 2026-07-08]
output_contract:
  version: 1
  blocks:
    - id: block-monday-sync-ops-hub-post
      artifact:
        type: notion_page
        title_pattern: "Monday Sync — {DATE}"
        parent_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062"
      freshness_window_hours: 180
      expected_on:
        cron: "35 10 * * 1"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Title verified against the live 2026-08-03 Ops Hub post. The Notion post is the signal, NOT the email: the sent subject format is UNSTABLE across runs -- 'ORA Monday Sync - 2026-07-27' uses a plain hyphen while 'ORA Monday Sync — 2026-08-03' uses an em dash, so any single mail pattern would intermittently miss. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron."
---

You are running the ORA Monday Sync for Gabriel Goldberg, Oxford Realty Advisors. Purpose: one week-ahead operational picture before the week starts.

0. **DOUBLE-FIRE ENTRY GUARD (added 2026-08-09).** This task sent **three times** on 2026-07-13 — 12:36:40, 12:42:47, 12:43:32 — three "ORA Monday Sync" emails and three Ops Hub posts for the same date. The 2026-07-21 retime (see the description above) moved the slot into a window the app is reliably open, which reduces how often a burst catches this task but cannot prevent a duplicate once one does; the guard is the actual fix, and it belongs here at the task's entry rather than in the cron. Run this **before step 1**:

   ```
   python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-monday-sync --block main --run-id <run_id> --ttl-min 30
   ```

   **Exit 10** → this Monday's sync already ran: log `BLOCK_MAIN_ALREADY_COMPLETE_TODAY`, **do not re-post or re-email**, and report a NORMAL skip (not a miss) citing the earlier run's Notion page. **Exit 11** → another fire is live; stand down identically. **Exit 0** → proceed to step 1. **Any other exit** (2 = malformed command, 9009/127 = interpreter missing) is a tooling failure, not a decision — fail open, run normally, and surface the code in the completion row.

   Only the run holding the claim may close it; a run that stood down calls neither `complete` nor `fail`. Full contract: `C:\Users\Owner\.claude\scheduled-tasks\_shared\README-DOUBLE-FIRE-GUARD.md`. Note the helper lives under `~/.claude` (CC fleet tree) but is invoked by absolute path, so it works from this LAMS task unchanged.

1. Outlook calendar (ggoldberg@oxfordra.net): list this week's meetings/deadlines.
2. Notion Acquisition Pipeline (bcfe4a03): active deals by stage, items with dates falling this week (DD deadlines, LOI/PSA dates).
3. Notion Operations Hub (32b6ecd8): open/flagged items from last week's completion rows, including any SEND FAILED flags — surface those first.
4. If today is the first Monday after the 1st of the month: check the Monthly Close database for the current month; if no rows exist, flag MONTHLY CLOSE NOT STARTED at the top.
5. Produce a compact sync: top 3 priorities, calendar, deal deadlines, carried-over items, automation health notes. Institutional register.
6. Post to Notion Operations Hub titled "Monday Sync — [date]".
6b. **Pre-send Sent-Items probe (Layer 2, immediately before step 7's send).** Write `ORA Monday Sync - [date]` to a temp .txt and run `powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\outlook-sent-probe.ps1" -SubjectFile <that file>`. **Exit 10** → do NOT send; log `MAIN_EMAIL_ALREADY_IN_SENT_ITEMS` and record a NORMAL skip. **Exit 1** → fail open: send, and note the probe gap in the completion row. This layer is independent of step 0's state file, which lives on OneDrive and can be lost to a sync conflict — on 2026-07-13 all three sends landed within seven minutes, which is exactly the window where only the mail store itself is authoritative.

7. Send via the SOLE send path — Outlook COM, via the host-exec bridge (Desktop Commander MCP) if available. Build the subject from codepoints in the invoking shell rather than passing a literal em dash across the Bash→PowerShell boundary — send-via-outlook.ps1's own header warns this mangles silently (exit 0, wrong subject, no error): `$dash = [char]0x2014; $subj = "ORA Monday Sync $dash [date]"`. Then: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject $subj -Body [sync] -BodyFormat html (send-via-outlook.ps1 has no -Html switch — BodyFormat defaults to html but pass it explicitly). Routing canon: ggoldberg@oxfordra.net ONLY, no cc. On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. Never send outside oxfordra.net.

8. **Close the entry guard.** Once the Notion post and the send both resolve:

   ```
   python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-monday-sync --block main --run-id <run_id> --notion-page-id <step 6 page id> --email-sent-at <ISO8601>
   ```

   If the run aborted, call `fail --task ora-monday-sync --block main --run-id <run_id> --error "<what broke>"` instead — that releases the claim immediately so a legitimate retry does not wait out the TTL. Leaving the claim `IN_PROGRESS` after the outputs shipped is the state to avoid: the next fire past the TTL reads it as a crashed run and regenerates everything.