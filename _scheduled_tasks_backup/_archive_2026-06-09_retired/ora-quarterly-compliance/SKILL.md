---
name: ora-quarterly-compliance
description: ORA Quarterly Compliance — single sequential session (cron `0 9 1 1,4,7,10 *`, 1st of Jan/Apr/Jul/Oct) folding four quarterly tasks into one fire, resolving the 09:00/09:30 same-time collision. Runs four blocks IN ORDER — A) Lender Covenant Tracker → B) Insurance Renewal Tracker (property + tenant COI) → C) Tax Appeal Calendar → D) CRE-Data MCP Recheck. Each block keeps its own Notion target, email send path, recipients, publication guard, and escalation. v1.0 2026-06-03 (Phase 3 Stage 2 fleet merge of ora-lender-covenant-tracker + ora-insurance-renewal-tracker + ora-tax-appeal-calendar + ora-cre-data-mcp-recheck).
---

# ora-quarterly-compliance — Oxford Realty Advisors Quarterly Compliance (merged)

You are `ora-quarterly-compliance`. You replace four previously-separate quarterly tasks that all fired on the 1st of Jan/Apr/Jul/Oct (two at 09:00, two at 09:30 — a same-time collision) with **one sequential session**. Run the four blocks **in order A→B→C→D**. There is no hard data dependency between blocks, but the order runs the BREACH-critical financial check first and the lightweight MCP-registry recheck last. Each block keeps its own Notion target, email send path, recipient list, and publication guard **exactly as before** — do not cross-wire them or merge their emails.

## CADENCE

Fires **quarterly: `0 9 1 1,4,7,10 *`** (1st of Jan/Apr/Jul/Oct, 09:00 ET). All four blocks run every quarterly fire — no day-of-week or weekend branching. (Blocks C/D were previously timed 09:30; folding them into the 09:00 session eliminates the collision.) Also valid as an on-demand run if invoked directly.

## SHARED MCP ROUTING (canonical — normalized 2026-06-03)

Applies to ALL four blocks. The prior `8a611864` Composio wrapper is NOT a connected server; Rube (`d6315173`) is retired — **never reference either. ORA mail is Microsoft 365 Outlook only — NEVER use Gmail/Google Workspace.**
- **Outlook email:** `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (PRIMARY) → `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (`tool_slug: OUTLOOK_SEND_EMAIL`, account `me`) (fallback). Per-block recipients/subjects are specified in each block and MUST be preserved.
- **HubSpot:** native `mcp__a3e380ce-…__*`. **Notion:** native `mcp__c5f4869f-…__notion-*`. **QuickBooks:** Desktop only (no live MCP) — read TTM NOI / P&L from the Master Workbook or SharePoint export, not a live QB pull.
- **MCP registry (Block D):** `mcp__mcp-registry__search_mcp_registry`.

## SHARED PUBLICATION GUARD (v1.1) — REQUIRED for every `notion-create-pages` call in any block

Reference: `…\Documents\Claude\Scheduled\_shared\PUBLICATION_GUARD.md` v1.1. This SUPERSEDES any "log failure inline / do not retry" v1.0 wording. Apply these five steps each time a block writes to Notion:
1. **Capture** — invoke `notion-create-pages(parent=…, pages=[…])`; capture `response.pages[0].id` as `publishedId`, `.url` as `publishedUrl`.
2. **Retry once** — if `publishedId` is null/undefined/error or the response errored, retry the same call exactly ONCE. Do not loop.
3. **Search-verify** — `notion-search(query=<literal title used>, filters={created_date_range:{start: today, end: today+1}})`; confirm the returned ID matches `publishedId`. No match → publication failure → step 4.
4. **Outlook fallback (auto-send)** — IFF steps 1+2+3 all failed, AUTO-SEND via `mcp__composio-ora__OUTLOOK_SEND_EMAIL` `account_id="me"`, `to="ggoldberg@oxfordra.net"`, `subject="❌ ora-quarterly-compliance/<block> PUBLICATION FAILED — <YYYY-MM-DD>"`, body = what the page WOULD have contained verbatim + the Notion API error verbatim, body_tag `"AUTO-SENT — meta-failure path, no human-in-loop available"`. This overrides the default "draft, don't send" rule because the audit function is meaningless if publication fails silently.
5. **Failure-mode logging** — append one line to the chat-summary: `Publish[<block>]: [✅ direct | ✅ retry | ❌ fallback-sent | ❌❌ total-blackout]`.

## NON-MUTATION GUARANTEE (I6)

Every block EMITS outputs only — Notion pages/cache, emails, and the insurance-calendar Cowork artifact. **Block D NEVER auto-installs an MCP connector** (surfaces for Gabriel's approval only). No block writes `settings.json`, `~/.claude/` config, or any memory file. Nothing here edits configuration or memory.

> **RECIPIENT POLICY (RESOLVED 2026-06-03):** per Gabriel's 2026-05-15 directive ("Eric removed from scheduled-task cc; only the Daily Brief retains egoldberg"), **ALL four blocks email ggoldberg@oxfordra.net ONLY.** The source SKILLs for Blocks B/C/D had never been updated and still said "Gabriel + Eric"; that egoldberg cc was **normalized away on 2026-06-03** at Gabriel's direction during this merge. No block in this task ccs egoldberg.

ORA context: ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, MD, IN, WI, MO, KS, TN.

---

# BLOCK A — LENDER COVENANT TRACKER

*(Folded verbatim-in-intent from `ora-lender-covenant-tracker`.)* DSCR / LTV / debt yield / reserve adequacy across the loan portfolio; escalates immediately on BREACH. Complete the full workflow autonomously.

1. Check Notion Operations Hub (ID `32b6ecd89e5981f2b329df3fd0e25062`) for the most recent loan position data page — OR use a `covenant_data_json` parameter if provided directly in the invocation.
2. For each loan position, calculate:
   - **DSCR** = NOI (trailing 12m) / Annual Debt Service
   - **LTV** = Loan Balance / Property Value
   - **Debt Yield** = NOI / Loan Balance
   - **Reserve Adequacy** = Reserve Balance ≥ Reserve Required
   - **Days to Balloon** = Maturity Date − Today
3. Classify each loan: ✅ PASS / ⚠️ WARN (DSCR within 10% of floor, or LTV within 5% of ceiling, or balloon <36mo) / 🔴 BREACH (DSCR below floor or LTV above ceiling) / 🚨 BALLOON (<18mo to maturity). *(Governor floors: DSCR ≥ 1.25×, LTV ≤ 40% per `CLAUDE.md`.)*
4. Calculate blended portfolio DSCR and LTV.
5. Create a Notion Operations Hub page titled "Lender Covenant Report — [QUARTER] [YEAR]" (apply the SHARED PUBLICATION GUARD).
6. **Email** via the canonical send path — **TO: ggoldberg@oxfordra.net** (Eric removed per 2026-05-15 directive). Subject: "ORA Covenant Compliance — [QUARTER] [YEAR] — [STATUS]". Body: per-loan status table, portfolio summary, any BREACH/BALLOON flags prominently at top.
7. If any loan is BREACH, mark the subject "🔴 BREACH DETECTED" and send immediately regardless of timing. **AUTO-SEND: yes in all cases, including BREACH.**

---

# BLOCK B — INSURANCE RENEWAL TRACKER  (property policies + tenant COI)

*(Folded verbatim-in-intent from `ora-insurance-renewal-tracker`.)* Covers BOTH property policies AND tenant COI compliance.

**PART 1 — Property Insurance:**
1. Pull all 27 ORA property policies from Notion Operations Hub / insurance database.
2. For each policy, compute days until expiration.
3. Bucket: 120d / 90d / 60d / 30d / expired.
4. Surface premium creep year-over-year.
5. Carrier exposure analysis.
6. Update the `ora-insurance-renewal-calendar` Cowork artifact.

**PART 2 — Tenant COI Compliance:**
1. Pull all active (non-vacant) tenants from HubSpot Contacts (canonical tenant roster). Query: `search_crm_objects`, objectType=contacts, `filterGroups:[{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}]`. Properties: firstname, lastname, company, email, address, monthly_rent, lease_end_date, square_feet, hs_object_id. Paginate `limit=200` until all retrieved.
2. For each tenant contact, check HubSpot notes/engagements for COI / certificate-of-insurance data. If a COI expiration date is recorded, compute days until expiration.
3. Bucket per tenant: Current / Expiring 60 Days / Expiring 30 Days / Expired / Not on File.
4. Verify COI names ORA entities as additional insured (where captured in HubSpot notes).
5. Compute portfolio metrics: count by status, % expired or expiring 30 days.

**Output:**
- **Email — TO: ggoldberg@oxfordra.net only** (Eric removed per the 2026-05-15 directive; normalized 2026-06-03) via the canonical send path, two sections — Section A: property policy renewal queue (carrier, premium delta, action queue); Section B: tenant COI compliance status (count by bucket, list of expired/expiring-30d tenants). Subject: "ORA Insurance Tracker Q[N] [YYYY] — Property + Tenant COI" (prefix **[ALERT]** if any tenant Expired or any property <30 days to expiration).
- Notion Operations Hub page archiving both sections (apply the SHARED PUBLICATION GUARD).
- Update the `ora-insurance-renewal-calendar` artifact.

Format: ORA Institutional Style Guide v1.0+.

---

# BLOCK C — TAX APPEAL CALENDAR

*(Folded verbatim-in-intent from `ora-tax-appeal-calendar`.)* Identify properties where assessed value materially exceeds income-approach valuation AND the county appeal deadline is within 90 days.

1. Invoke the `tax-appeal` skill in BATCH mode. For each of 27 ORA properties:
   a. Pull current assessed value from the Notion Property database (or prior tax bill in SharePoint).
   b. Pull TTM NOI from QuickBooks (P&L by class, last 12 months) — **QB Desktop only; read from Master Workbook / SharePoint export, not a live QB MCP pull.**
   c. Apply the market cap-rate floor by submarket per acquisition-underwriting guidance.
   d. Compute Implied Value = NOI / cap rate; Overassessment Ratio = Assessed / Implied.
2. Pull county-by-county appeal deadlines (cached in Notion Knowledge Base; refresh annually). For OH/MD/IN/WI/MO/KS/TN counties, note the next deadline.
3. **APPEAL CANDIDATE = (Overassessment Ratio ≥ 1.10) AND (deadline within 90 days).**
4. Build report in ORA Institutional Style: Property | County | Assessed | TTM NOI | Implied | Ratio | Deadline | Recommendation (FILE / WATCH / SKIP).
5. Save to Notion Operations Hub as "Tax Appeal Calendar — YYYY-MM" (apply the SHARED PUBLICATION GUARD).
6. **Email — TO: ggoldberg@oxfordra.net only** (Eric removed per the 2026-05-15 directive; normalized 2026-06-03) via the canonical send path. Subject: "ORA Tax Appeal Calendar — YYYY-MM (N candidates)". Body: top candidates with deadline urgency + link.
7. If any candidate has a deadline within 30 days, prefix the subject "[ACTION REQUIRED]".

**QC GATES:** all 27 properties evaluated; cap-rate floor sources cited; no appeal filed without Gabriel approval — analysis only.

---

# BLOCK D — CRE-DATA MCP RECHECK

*(Folded verbatim-in-intent from `ora-cre-data-mcp-recheck`.)* Detect whether any priority CRE-data MCP connector has shipped to the Anthropic registry since the last check, and notify only if so.

1. For each target connector, call `mcp__mcp-registry__search_mcp_registry` with relevant keywords. Targets: **Reonomy** (commercial property data), **Regrid** (parcel), **CoStar** (CRE marketplace + analytics), **CompStak** (lease comps), **Buildout** (CRE marketing), **ATTOM** (property + tax data).
2. Compare against the last-known availability cache in Notion Knowledge Base page "CRE-Data MCP Watch List". First run → baseline = none available.
3. For any newly-available connector, capture: name, vendor URL, tool list (≥10 most relevant), pricing if visible.
4. Update the Notion cache page with current availability state, dated (apply the SHARED PUBLICATION GUARD if creating a page; otherwise `notion-update-page`).
5. **If ≥1 new connector is available, email — TO: ggoldberg@oxfordra.net only** (Eric removed per the 2026-05-15 directive; normalized 2026-06-03) via the canonical send path. Subject: "[NEW] CRE-Data MCP Available: {connector}". Body: summary + recommended action (install vs wait).
6. If no change, log a one-liner to the Notion page and **skip the email**.

**QC GATES:** all 6 targets queried; cache page updated regardless of outcome; **NEVER auto-install a connector — surface for Gabriel approval only.**

---

# END-OF-SESSION RUN SUMMARY

After all four blocks complete, emit a one-line-per-block status (block · Notion publish result · email sent/skipped · any BREACH/ALERT/ACTION-REQUIRED flag) to the session log so `ora-health-guard` can confirm the merged quarterly session fired cleanly. Block A always emails; Block D emails only on a new-connector change. A missed whole-session run is independently surfaced by the health guard.
