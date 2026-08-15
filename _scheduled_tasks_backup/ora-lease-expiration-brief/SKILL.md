---
name: ora-lease-expiration-brief
description: Weekly lease expiration and renewal pipeline brief — retimed 2026-07-21 (Gabriel-directed) from 8:30 AM to 10:45 AM ET, same root cause/fix as ora-monday-sync (see that task's description). [MODEL: claude-sonnet-5 | set 2026-07-08]
output_contract:
  version: 1
  blocks:
    - id: block-lease-expiration-ops-hub-post
      artifact:
        type: notion_page
        title_pattern: "Lease Expiration Brief — {DATE}"
        parent_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062"
      freshness_window_hours: 180
      expected_on:
        cron: "45 10 * * 1"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Verified against the live 2026-07-21 post. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
    - id: block-lease-expiration-mail
      artifact:
        type: sent_mail
        mailbox: "ggoldberg@oxfordra.net"
        subject_pattern: "ORA Lease Expiration Brief — {DATE}"
        recipient: "ggoldberg@oxfordra.net"
      freshness_window_hours: 180
      expected_on:
        cron: "45 10 * * 1"
      on_missing_severity: warn
      is_primary_health_signal: false
      notes: "SEVERITY IS warn, NOT alarm, DELIBERATELY: the exact sent subject string is not yet observed in Sent Items -- only the SKILL.md -Subject argument, whose date placeholder does not fix a format. Promote to alarm once a real send is confirmed to match. The verified Notion block above carries the alarm. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
---

You are running the ORA Lease Expiration Brief for Gabriel Goldberg, Oxford Realty Advisors (~600K SF shallow-bay industrial, ~140 tenants). Use the lease-renewal-pipeline skill if present on this surface; if absent, say so and proceed with the steps below — never improvise a missing skill's internal procedure beyond this prompt.

1. Recompute today's date and today+90 days as absolute ISO literals (`YYYY-MM-DD`), then refresh the "Renewal Watch — ≤90 Days" saved view (Tenant DB data source `b12f4cfd-a995-4755-8341-6435ae8173b4`, `view://3a56ecd8-9e59-819c-8333-000c3d9a8627`) via the Notion `update_view` tool: CLEAR FILTER; FILTER "Lease Expiration" >= "<today>" AND "Lease Expiration" <= "<today+90>" AND "Lease Status" != "Vacant" AND "Lease Status" != "Expired" AND "Row Retired" = false. Never filter on a FORMULA-output property (Months to Expiry, Months Remaining, Days to Expiration) or use a relative offset like "+90d" — both silently no-op in this MCP's view DSL (see `reference_notion_view_dsl_formula_filter_bug.md`); only absolute ISO literals on the native `Lease Expiration` date field filter correctly. If `update_view` is unavailable on this surface, flag it loudly in the brief and continue — do not halt the run over a stale view.
2. Query Notion Tenant Database (data source 8dbbaec0) for leases expiring within 30/90/180-day horizons; include tenant, property, SF, current rent $/SF NNN, expiration date.
3. Cross-check HubSpot (current tenants only) for any renewal-related activity in the last 7 days.
4. Produce the brief bucketed by horizon: URGENT ≤30d, ACTIVE 31–90d, WATCH 91–180d, with a recommended next action per URGENT/ACTIVE tenant and flags for missing data.
5. Post the full brief to Notion Operations Hub (32b6ecd8) titled "Lease Expiration Brief — [date]".
6. Send via the SOLE send path — Outlook COM, via the host-exec bridge (Desktop Commander MCP) if available. Build the subject from codepoints in the invoking shell rather than passing a literal em dash across the Bash→PowerShell boundary — send-via-outlook.ps1's own header warns this mangles silently (exit 0, wrong subject, no error): `$dash = [char]0x2014; $subj = "ORA Lease Expiration Brief $dash [date]"`. Then: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject $subj -Body [brief] -BodyFormat html (send-via-outlook.ps1 has no -Html switch — BodyFormat defaults to html but pass it explicitly). Routing canon: ggoldberg@oxfordra.net ONLY, no cc. On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. Never draft or send anything to tenants or any external party from this task.