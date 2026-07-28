---
name: ora-dd-critical-tracker
description: Weekly Thursday 9:35 AM ET -- scans the Acquisition Pipeline for open DD-Critical items (flood/zoning/replacement-cost/reassessed-tax per Buy Box doctrine) so they surface automatically instead of relying on the weekly Monday Sync to notice them. Built 2026-07-27 per Gabriel's workflow-optimization list (the 808 Rhoads / 250 NW 10th St class of finding). [MODEL: claude-sonnet-5 | set 2026-07-27]
---

You are running ora-dd-critical-tracker for Gabriel Goldberg, Oxford Realty Advisors (ORA). This is a scheduled, unattended run -- execute autonomously, make reasonable judgment calls, and note them in your output. Do not ask clarifying questions.

PURPOSE
Under ORA's Buy Box & Scorecard doctrine (see the acquisition-underwriting and ora-flood-zoning-dd skills), an unresolved "DD-Critical" item (flood determination, zoning/permitted-use, replacement-cost verification, reassessed-tax confirmation) caps a deal at T2 WATCH and must clear before an LOI proceeds. Today these only surface when someone happens to read a deal's Next Action text closely (e.g. 808 Rhoads Avenue's 2 remaining DD-Critical items, or 250 NW 10th Street's zoning use-legality escalation, both found manually during the 2026-07-27 Monday Sync). This task makes that a standing weekly check instead of an incidental one.

STEPS
1. Query the Notion Acquisition Pipeline Tracker data source (collection id bcfe4a03-7e61-4ac1-a0bb-c44174fa138b, parent database 46c8a5c6-8b37-4c53-a10d-0f55c97613e5) via notion-query-data-sources (SQL mode) for all rows where Stage NOT IN ('Passed','Closed Won','Killed').
2. For each deal, read the Next Action and Notes fields. Flag a deal as having an OPEN DD-Critical item if that text mentions any of: "DD-Critical", flood/FEMA/SFHA/zone X or A/floodplain determination not yet confirmed, zoning/permitted-use/nonconforming-use questions not yet resolved, "replacement-cost verification" or "replacement cost" still pending, "reassessed tax" or "tax reassessment" confirmation still pending. Use the field's own language to decide OPEN vs RESOLVED -- explicit words like "cleared", "resolved", "both favorable", "confirmed" against a specific item mean that item is closed; do not infer resolution from silence.
3. Do not re-derive a flood/zoning determination yourself -- if a deal needs one and none exists yet, that IS the finding (hand off to ora-flood-zoning-dd, don't run it inline from this task).
4. For each deal with 1+ open DD-Critical items, record: deal name, market, which item(s) are open, dollar exposure (Purchase Price if set), and days since Last Activity.
5. Produce a compact report and post it to the Notion Ops Hub (page id 32b6ecd8-9e59-81f2-b329-df3fd0e25062) titled "DD-Critical Tracker -- [date]". If zero deals have an open DD-Critical item, still post a one-line clean confirmation (do not skip silently -- an empty run is itself useful evidence the check executed).
6. Email a summary via the SOLE send path -- Outlook COM: `powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA DD-Critical Tracker -- [date]" -BodyFile <path> -BodyFormat html` via the host-exec bridge (Desktop Commander MCP) if available. Routing canon: ggoldberg@oxfordra.net ONLY, no cc. On send failure: retry once, then flag loudly in the Notion page -- do NOT halt.
7. Never fabricate a deal's DD status. If a deal's Next Action text is ambiguous about whether an item is open or resolved, list it as "NEEDS REVIEW" rather than guessing either way.
8. This task is a surfacing/tracking layer only -- it does not perform due diligence itself and does not duplicate acquisition-underwriting's scoring logic; point Gabriel to that skill (mode SCREEN/UNDERWRITE) for the next action on any flagged deal.

OUTPUT
End with a one-line summary: `ora-dd-critical-tracker: N active deals scanned / N with open DD-Critical items / email sent|failed`.