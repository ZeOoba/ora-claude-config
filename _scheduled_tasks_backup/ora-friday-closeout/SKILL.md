---
name: ora-friday-closeout
description: Friday 4:30 PM ET — week closeout ledger (Part A) + week-ahead synthesis (Part B). v2.1 (2026-07-18): Part A gained a report-only LOI Throughput line (Gabriel-carried-forward item from the 2026-07 setup-review plan). v2.0 (2026-07-16, Fleet Ledger v2 ruling C1): absorbed the retired CC task ora-week-ahead-briefing verbatim as Part B — one Friday session, one email, one Notion page; the CC twin was retired same day. [MODEL: claude-sonnet-5 | set 2026-07-08]
output_contract:
  version: 1
  blocks:
    - id: block-friday-closeout-mail
      artifact:
        type: sent_mail
        mailbox: "ggoldberg@oxfordra.net"
        subject_pattern: "ORA Friday Closeout & Week Ahead — {DATE}"
        recipient: "ggoldberg@oxfordra.net"
      freshness_window_hours: 180
      expected_on:
        cron: "30 16 * * 5"
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Sent unconditionally at step 2 via the COM path; no Notion artifact is written on every run, so the mail is the only every-run signal. Window is 180h = weekly cadence (168h) plus slack, mirroring the CC convention of 30h for a daily cron; a tighter window would false-alarm on any audit day after the fire, and a detector people learn to ignore is worse than none."
---

You are running the ORA Friday Closeout for Gabriel Goldberg, Oxford Realty Advisors. Purpose: close the week with an honest ledger of done vs open (Part A), then set up the coming week (Part B). One session, ONE email, ONE Notion page covering both parts.

## Part A — Week closeout ledger

1. Notion Operations Hub (32b6ecd8): review all completion rows/pages from the past 7 days — task runs, SEND FAILED flags, anomalies.
2. Notion Acquisition Pipeline (bcfe4a03): stage changes this week; deals with no movement in 14+ days.
3. LOI Throughput (report-only, added v2.1 2026-07-18):
   - LOIs generated/sent this week — source: `loi-generation` skill outputs in deal folders (search project/deal `outputs/` subfolders for `*LOI*` files dated within the past 7 days) plus any LOI-referencing row added to `memory/deal-decision-ledger.md` this week. Count generated vs. confirmed-sent (sent = an actual outbound send confirmed in event_log/send-log — never assume "generated" means "sent," per Hard Invariant 1).
   - Pipeline-stage conversions — Notion Acquisition Pipeline (bcfe4a03): count deals that moved into or out of an LOI-related stage (e.g. Screening→LOI Sent, LOI Sent→Under Contract) in the past 7 days.
   - Week-over-week trend — compare this week's LOI count to the prior week's (carry forward from the previous Friday Closeout Notion page); report the delta, not just the raw count.
   - This line is report-only: no new send action and no Notion write beyond the existing single completion page. If the Notion Acquisition Pipeline query is unavailable this run, state "LOI pipeline-stage data unavailable this run" in the line — do not guess or fabricate a count.
4. Compile: completed this week, open items carried forward (with owner: Gabriel vs automation), automation fleet health summary (which tasks ran/missed), LOI Throughput line, and next week's top 3.

## Part B — Week-ahead synthesis (absorbed 2026-07-16 from ora-week-ahead-briefing, ruled C1; that CC task is retired — do not expect or re-create it)

Sources to query for next Monday-through-Friday:
1. Outlook calendar — `mcp__c0ea3c01-...__outlook_calendar_search` — all meetings/events for the next 7 days for ggoldberg@oxfordra.net.
2. Scheduled-task fires — `mcp__scheduled-tasks__list_scheduled_tasks` in THIS runtime returns the LAMS/Cowork fleet; for the CC/MCP fleet read the generated roster block in `C:\Users\Owner\.claude\session-context.md` (regenerated daily by ora-task-integrity-guard STEP 1.5) via the host-exec bridge (Desktop Commander) if available. If the bridge is unavailable this run, list LAMS fires only and note "CC fires unavailable this run" — do not guess.
3. Notion Operations Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — open items with due dates inside the week ahead.
4. Notion Acquisition Pipeline (`bcfe4a03`) — deals with active milestones (LOI deadlines, DD expirations, closing dates) inside the week.
5. Notion Tenant Database (`8dbbaec0`) — lease expirations or renewal-decision dates falling inside the week.
6. HubSpot deal stages — `mcp__a3e380ce-...__search_crm_objects` — deals expected to advance or with action items due inside the week (current tenants scope per rules.md §3b).

Part B output sections:
- Day-by-day grid (Mon-Fri): meetings, scheduled-task fires, Notion deadlines, deal milestones.
- Watch list: items where Gabriel must act (drafts pending review, signatures needed, calls to return). Data gaps go to a "QUESTIONS FOR GABRIEL" note — never fabricate.

## Output & delivery (both parts, single email + single Notion page)

Structure: A. Executive summary (3-4 sentences: the week's posture + top 3 priorities) → B. Closeout ledger (Part A) → C. Week-ahead grid + watch list (Part B).
Format: ORA Institutional Style Guide v1.0+ — clean HTML, Oxford Navy headers, parchment background blocks.

1. Post to Notion Operations Hub (parent `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) titled "Friday Closeout & Week Ahead — [date]". Publication guard: capture `pages[0].id` as `publishedId`; retry the create exactly once if null/errored; verify via `notion-fetch` DIRECTLY on `publishedId` (never `notion-search` — index lag / same-title false negatives); if still failing, state the Notion failure + API error in the email body (no separate alert email). Append to run summary: `Publish: [✅ direct | ✅ retry | ❌ fallback-noted-in-email]`.
2. Send via the SOLE send path — Outlook COM: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Friday Closeout & Week Ahead — [date]" -BodyFile <temp.html> -BodyFormat html — via the host-exec bridge (Desktop Commander MCP) if available. Routing canon: ggoldberg@oxfordra.net ONLY, no cc (Daily Brief is the sole cc-Eric exception; this is not it). On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. Never send outside oxfordra.net.

HARD GUARDRAILS: never move money, execute trades, or send external communications without explicit in-turn confirmation; never modify financial models or the governor constants (DSCR 1.25 / LTV 40); never touch oxfordra.net; active confidential deals (roster: C:\Users\Owner\.claude\hooks\confidential-terms.json) never appear on any external surface; never fabricate.

RUN SUMMARY (always, last line): "ora-friday-closeout: [P] completions / [Q] open items / [N] calendar items / [M] task fires / [K] deadlines / [J] milestones / [L] LOIs (Δ vs prior week) / email [sent|FAILED] / Publish: [...]".
