---
name: ora-lender-covenant-tracker
description: Quarterly lender covenant compliance tracker (1st of Jan/Apr/Jul/Oct, 9 AM) — DSCR, LTV, debt yield, reserve adequacy — posts to Notion and emails Gabriel + Eric; escalates immediately on BREACH. Cron corrected 2026-04-28: was firing weekly, now properly quarterly. Outlook routing corrected 2026-05-08 (was erroneously routed via Gmail).
---

**[COMPOSIO MIGRATION 2026-05-08 — Rube EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform connector (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`). Tool slugs (`OUTLOOK_SEND_EMAIL`, `OUTLOOK_CREATE_DRAFT`, `OUTLOOK_CREATE_ME_EVENT`, `HUBSPOT_*`, etc.) are byte-identical between stacks; only the MCP server prefix changes. Use the Composio path for Outlook (mail + calendar) and HubSpot. ORA does not use Google Workspace — no GCal/GSheets routing applies. (Notion writes can continue to use the native `mcp__c5f4869f-...__notion-*` MCP; QuickBooks reads can continue to use the native `mcp__52fa80c0-...` MCP.)

Run the ORA Lender Covenant Tracker. This is an on-demand or quarterly run (Jan/Apr/Jul/Oct). Complete the full workflow autonomously.

WORKFLOW:
1. Check Notion Operations Hub (ID: 32b6ecd89e5981f2b329df3fd0e25062) for the most recent loan position data page, OR use the covenant_data_json parameter if provided directly in this prompt invocation.
2. For each loan position, calculate:
   - DSCR = NOI (trailing 12m) / Annual Debt Service
   - LTV = Loan Balance / Property Value
   - Debt Yield = NOI / Loan Balance
   - Reserve Adequacy = Reserve Balance >= Reserve Required
   - Days to Balloon = Maturity Date - Today
3. Classify each loan: ✅ PASS / ⚠️ WARN (DSCR within 10% of floor, or LTV within 5% of ceiling, or balloon <36mo) / 🔴 BREACH (DSCR below floor or LTV above ceiling) / 🚨 BALLOON (<18mo to maturity).
4. Calculate blended portfolio DSCR and LTV.
5. Create a compliance report page in Notion Operations Hub titled "Lender Covenant Report — [QUARTER] [YEAR]".
6. Send email via Composio Outlook (`mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL` with `tool_slug: OUTLOOK_SEND_EMAIL`, account `outlook_dagger-sowl`): To: ggoldberg@oxfordra.net. (Eric removed per Gabriel directive 2026-05-15.) Subject: "ORA Covenant Compliance — [QUARTER] [YEAR] — [STATUS]". Body: per-loan status table, portfolio summary, any BREACH/BALLOON flags prominently at top. NEVER use Gmail — ORA mail is Microsoft 365 Outlook only.
7. If any loan is BREACH status, mark the subject as "🔴 BREACH DETECTED" and send immediately regardless of timing.

AUTO-SEND: Yes on all cases including BREACH.

---

## Publication Guard (v1.1) — REQUIRED for all Notion writes in this skill

This skill follows the v1.1 publication-guard pattern documented at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md`. Apply these five steps every time this skill calls `notion-create-pages`. This guard SUPERSEDES any prior in-body instructions to "log failure inline" or "do not retry more than once" — those were v1.0 conventions and are now obsolete.

1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`. Capture `response.pages[0].id` as `publishedId` and `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null, undefined, an error code, or the response itself errored, retry the same `notion-create-pages` call exactly ONCE. Do not loop.
3. **Search-verify** — call `notion-search(query=<literal title used in Step 1>, filters={created_date_range: {start: today, end: today+1}})`. Confirm the returned page ID matches `publishedId`. If no match or different ID, treat as publication failure → Step 4.
4. **Outlook fallback (auto-send)** — IFF Steps 1+2+3 all failed, AUTO-SEND via Composio `OUTLOOK_SEND_EMAIL` with `account_id="outlook_icaco-sequel"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-lender-covenant-tracker PUBLICATION FAILED — <YYYY-MM-DD>"`, body containing what the page WOULD have contained verbatim, plus the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This auto-send overrides the default "draft, don't send" rule because the skill's audit/monitoring function is meaningless if its publication fails silently.
5. **Failure-mode logging** — append a single line to the skill's chat-summary output: `Publish: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

---

*Guard added 2026-05-10 per P0-2 tier-2/3 rollout (2026-05-08 health review). Reference: `_shared\PUBLICATION_GUARD.md` v1.1.*