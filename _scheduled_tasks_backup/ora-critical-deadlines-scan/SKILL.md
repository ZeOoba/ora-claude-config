---
name: ora-critical-deadlines-scan
description: Weekly Thursday 9:05 AM ET — scans the Notion Ops Hub Critical Deadlines Tracker for entries due within 60 days or already passed with Status still Active/Upcoming; flags to Gabriel. Closes the gap found 2026-07-26 (no existing task monitored this database; King Energy Northwood's 7/5/2026 ITC/NTP deadline sat unconfirmed with no alert). [MODEL: claude-sonnet-5 | set 2026-07-26]
output_contract:
  version: 1
  blocks:
    - id: block-critical-deadlines-ops-hub-post
      artifact:
        type: notion_page
        title_pattern: "Critical Deadlines Scan — {DATE}"
        parent_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062"
      freshness_window_hours: 180
      expected_on:
        cron: "5 9 * * 4"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Verified against the live 2026-07-30 post (leading alarm-clock emoji; matched on text). Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
    - id: block-critical-deadlines-mail
      artifact:
        type: sent_mail
        mailbox: "ggoldberg@oxfordra.net"
        subject_pattern: "Critical Deadlines Scan — {DATE}"
        recipient: "ggoldberg@oxfordra.net"
      freshness_window_hours: 180
      expected_on:
        cron: "5 9 * * 4"
      on_missing_severity: warn
      is_primary_health_signal: false
      notes: "SEVERITY IS warn, NOT alarm, DELIBERATELY: the exact sent subject string has not yet been observed in Sent Items -- only the SKILL.md -Subject argument, whose date placeholder does not fix a format (a sibling task emits a plain hyphen where this one is assumed to emit an em dash). Promote to alarm once a real send is observed to match. The verified Notion block above carries the alarm. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
---

You are running the weekly ORA Critical Deadlines scan. This task is self-contained — you have no memory of prior runs.

DATA SOURCE: Notion database "⏰ Critical Deadlines Tracker", data source collection://c89df6f2-1d18-4341-9e57-6a15a696b14a (under Oxford Real Assets — Operations Hub, page 32b6ecd8-9e59-81f2-b329-df3fd0e25062). Use notion-query-data-sources (SQL mode) to pull all rows.

STEPS:
1. Query all rows where Status is "Active" or "Upcoming".
2. For each row, compare "date:Date:start" to today's date. Bucket into:
   - PASSED-UNCONFIRMED: date is in the past AND Status is not "Addressed" or "Passed" — these are the highest priority, they mean a deadline blew past with nobody marking it resolved (this exact failure mode let King Energy's 7/5/2026 Northwood ITC/NTP deadline go unconfirmed).
   - DUE SOON: date is within the next 60 days.
   - ON WATCH: everything else Active/Upcoming, for awareness only.
3. Never fabricate a resolution — if a deadline's outcome (e.g., was NTP actually reached) isn't confirmable from Notion/SharePoint/Outlook search, report it as PASSED-UNCONFIRMED, not as resolved. Do not guess dates or outcomes.
4. Post a status block to the Notion Ops Hub (same page tree as the tracker) with the three buckets, plainly formatted, dated.
5. Email a summary to ggoldberg@oxfordra.net ONLY (never cc egoldberg — that exception is reserved for the Daily Brief alone). Subject: "Critical Deadlines Scan — [today's date]". Lead with PASSED-UNCONFIRMED items if any exist; otherwise lead with DUE SOON. If there is no working send path available on this surface, save the summary as an Outlook draft or a dated file instead of failing silently, and say so in the Notion post.
6. If you find a PASSED-UNCONFIRMED item, do not attempt to resolve it yourself (e.g., do not draft or send anything to an external counterparty) — flag it clearly for Gabriel with a one-line suggested next step (e.g., "confirm with [counterparty] directly").

Do not modify Category, Owner select options, or any other schema — this task reads and reports, it does not rescore or auto-close deadlines. Only mark a row "Addressed"/"Passed" if you have direct evidence (an email, a Notion note, a document) that it was actually resolved — cite that evidence in the update.