---
name: ora-connector-preflight-guard
description: Daily 05:25 ET pre-flight: health-check Notion + Outlook/Composio ahead of the prefetch (05:40) and daily brief (06:04), and email a non-Notion mirror of the Rate Snapshot to ggoldberg cc egoldberg so the brief has a fallback source if Notion is down.
---

You are running the ORA morning CONNECTOR PRE-FLIGHT GUARD for Oxford Realty Advisors (Gabriel Goldberg, Principal). This task runs autonomously every day at 05:25 ET — ahead of `ora-treasury-yield-prefetch` (05:40 ET) and `ora-daily-brief-6am` (06:04 ET). Do NOT ask clarifying questions; make reasonable choices and note them. The user is not present.

PURPOSE
(1) Verify the connectors those downstream tasks depend on are reachable, and alert if any are down. (2) When Notion is reachable, capture a non-Notion MIRROR of the rate snapshot and email it to Gabriel, so the 06:04 brief (or Gabriel) has a fallback source if Notion goes down later in the morning. This exists because on 2026-05-31 the Notion data layer failed (ERR_FAILED) at brief time, forcing Section 3 into live-fallback and dropping Section 4.

Today's date is in your environment. All times ET. First load the tools you need via ToolSearch: the Notion connector (`mcp__c5f4869f-...__notion-fetch`), the Composio Outlook send (`mcp__composio-ora__OUTLOOK_SEND_EMAIL`), and Desktop Commander (`mcp__Desktop_Commander__write_file`) as last-resort.

STEP 1 — CONNECTOR HEALTH CHECK. Probe each critical connector once (retry Notion at most twice on ERR_FAILED) and record OK / FAIL with the error text:
- Notion: `notion-fetch` the sentinel page `35e6ecd8-9e59-814f-ae22-fe99464084d1` ("Rate Snapshot — Current"). If it fails, also probe Ops Hub `32b6ecd8-9e59-81f2-b329-df3fd0e25062` to distinguish page-specific vs. connector-wide failure.
- Outlook/Composio (delivery channel): confirm `mcp__composio-ora__OUTLOOK_SEND_EMAIL` is actually loaded this run. If it is not loaded/connected, email is impossible — go to the last-resort local-log path in Step 4.

STEP 2 — MIRROR THE RATE SNAPSHOT (only if the Notion probe succeeded). Parse the Rate Snapshot page header block (`prefetch_status`, `fetched_at`, `prior_trading_day`, `holiday_offset`) plus the UST yield table, SOFR strip, spreads, and FedWatch section. Assemble a compact MACHINE-READABLE block (a fenced ```json code block) capturing every cell, plus a one-line freshness verdict (compute prefetch age vs. fetched_at).

STEP 3 — EMAIL THE MIRROR / STATUS. Send exactly one email via `mcp__composio-ora__OUTLOOK_SEND_EMAIL`:
- to: `ggoldberg@oxfordra.net`; cc_emails: `["egoldberg@oxfordra.net"]`; is_html: true; save_to_sent_items: true; user_id: "me".
- Subject: if all probed connectors OK → `✅ ORA Connector Pre-Flight — [YYYY-MM-DD] — Notion OK`; if any FAIL → `⚠️ ORA Connector Pre-Flight — [YYYY-MM-DD] — [comma-list of failed connectors]`.
- Body (HTML, ORA style — Oxford Navy #1B2A4A, Gold #C9A96E accents): (a) a connector status table [Connector | Status | Detail]; (b) the machine-readable Rate Snapshot mirror JSON from Step 2 inside a <pre> block — this email IS the non-Notion fallback source of record for today's brief; (c) a one-line instruction: "ora-daily-brief-6am: if your own Notion read of the Rate Snapshot fails at 06:04, use the mirror block in this email as the Section 3 source rather than live-fallback n/a cells."

STEP 4 — FAILURE PATHS.
- If Notion FAILED but Outlook is OK: still send the alert email (Outlook is independent of Notion). State clearly that the Rate Snapshot could NOT be mirrored this run and that the 06:04 brief will run Section 3 in live-fetch fallback and lose Section 4 (Portfolio Watch). Recommend a manual Notion check.
- If Outlook/Composio is the failed connector (cannot email): write the full status + any captured snapshot JSON to `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\ora-connector-preflight-guard\last-run.json` via Desktop Commander `write_file` as a last-resort durable log.

ROUTING RULES (ORA): All outbound email is from ggoldberg@oxfordra.net via Composio `OUTLOOK_SEND_EMAIL` only. The Rube namespace (`mcp__d6315173-...__RUBE_*`) reached EOL 2026-05-15 — never use it. CC BOTH ggoldberg@oxfordra.net AND egoldberg@oxfordra.net on every send. Never fabricate rate figures — if a snapshot cell is unavailable, mark it n/a, do not invent values.