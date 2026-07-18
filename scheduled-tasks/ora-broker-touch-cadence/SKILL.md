---
name: ora-broker-touch-cadence
description: Monthly (2nd, 1:40 PM ET) broker relationship touch cadence — reads the Notion Broker Relationships DB, checks Outlook for recent contact, DRAFTS (never sends) personal pocket-listing check-ins to up to 5 brokers via Outlook COM .Save(); summary to ggoldberg only. Draft-only by design (Hard Invariant 1). Serves acquisition velocity (priority #1); Gabriel-ratified G4b 2026-07-16. v1.0. [MODEL: UNVERIFIABLE | checked 2026-07-16]
output_contract:
  version: 1
  blocks:
    - id: block-completion-row
      artifact:
        type: notion_page
        page_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        cron: "40 13 2 * *"
      skip_condition: "GUARD CONDITION (STEP 2): if the Broker Relationships DB is unreachable or zero brokers have a 30+ day stale touch, the task posts a shorter guard-exit row and exits early rather than running STEP 3-5 — but a row still posts to Ops Hub in both the normal and guard-exit paths, so absence of any write is still the alarm condition, not brevity of the write."
      on_missing_severity: warn
      is_primary_health_signal: true
      notes: "This task posts an APPENDED row to the shared Ops Hub root page (STEP 5 / GUARD CONDITION), not a distinct dated child page — no per-run page ID exists to check more precisely. Checking this page's last_edited_time is therefore a coarse signal shared with every other task that writes to Ops Hub the same day (2026-08-02, its first scheduled fire, and monthly on the 2nd thereafter); treat freshness here as 'something wrote to Ops Hub that day,' not standalone proof this specific task ran — cross-check lastRunAt via list_scheduled_tasks for confirmation. ID itself (32b6ecd8-9e59-81f2-b329-df3fd0e25062) is verified, not guessed."
---

ORA Broker Relationship Touch Cadence (v1.0, Gabriel-ratified G4b 2026-07-16)

AUTOMATION-BUDGET JUSTIFICATION: Serves ORA priority #1 (acquisition velocity) — opens the pocket-listing/relationship deal-flow channel that every existing sourcing task (ora-deal-sourcing-scan, ora-entry-market-scan) deliberately avoids, since those are on-market/public-listing scans only. Gabriel-ratified as ruling G4b on 2026-07-16. DRAFT-ONLY BY DESIGN — this task never sends an external communication; it exists specifically to stay inside Hard Invariant 1 while still opening the relationship channel.

GUARD CONDITION: If the Notion Broker Relationships DB is unreachable, or zero brokers qualify (see Step 2), post a Notion Ops Hub row stating so and exit silently — do not halt, do not fabricate a broker list.

STEP 1 — Pull broker roster.
Read the Notion Broker Relationships DB (data source id 48e43778b1f24b168f3c0bf18f8642e9). Pull active brokers with their market/cluster and last-logged-touch date if tracked there.

STEP 2 — Select up to 5 stale-touch brokers.
Select up to the top 5 brokers across ORA's target clusters (Columbus, Cincinnati, Indianapolis, Kansas City, plus entry markets: Louisville, Delmarva, Grand Rapids, Des Moines) who have no logged touch in 30+ days per the Notion DB.
HubSpot is NOT a broker CRM at ORA (rules.md §3b) — do not consult it for broker last-contact truth. Outlook is the source of truth for broker last-contact: for each candidate broker, use mcp outlook_email_search to check recent correspondence (last 30 days) before drafting. Skip anyone Gabriel emailed in the last 30 days, even if the Notion DB shows no logged touch — Outlook truth overrides a stale/missing Notion field.

STEP 3 — Draft personal check-ins.
For each selected broker, DRAFT a short, personal check-in email: institutional-direct tone, references their market and any live thread context found in Outlook search, asks specifically about off-market/pocket industrial or flex listings in ORA's buy-box (sub-$10M, sub-50K SF, Class B/C industrial/flex). No form-letter feel. 4-6 sentences max. Sign per the Property→LLC Signature Roster convention only if the correspondence is property-specific; otherwise sign as Gabriel Goldberg, Oxford Realty Advisors, per Voice Register (broker mail is relationship correspondence, not landlord-to-tenant mail, so the personal/firm signature applies, not a property LLC).

STEP 4 — Park drafts in Outlook. NEVER send.
Create each broker draft as an Outlook DRAFT via COM — never via .Send(). Use exactly this pattern (spelled out verbatim so an unattended run never improvises):

$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To = "<broker email>"
$mail.Subject = "<subject>"
$mail.Body = "<body text>"
$mail.Save()
# NEVER call $mail.Send() — drafts stay parked in the Outlook Drafts folder for Gabriel's own review and send.

STEP 5 — Completion reporting.
Post one row to the Notion Ops Hub (parent page 32b6ecd8-9e59-81f2-b329-df3fd0e25062) listing who was drafted, their market, and why (stale-touch trigger + any Outlook thread context used). Then email a one-paragraph summary to ggoldberg@oxfordra.net ONLY (no cc — routing canon; the ora-am-brief Daily Brief is the sole cc-egoldberg exception and does not apply here) via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — this summary is the ONLY send this task ever performs; the broker drafts themselves are never sent. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub row if the retry also fails — do not halt the run.

HARD GUARDRAILS (verbatim, non-negotiable):
- Never call .Send() on a broker draft. An actual outbound send to a broker (counterparty) requires Gabriel's explicit in-turn confirmation per Hard Invariant 1 — this task is structurally incapable of doing that send itself.
- Never fabricate relationship history, thread context, or broker detail. If no real context exists for a broker, the draft says less — it never invents rapport, deals, or prior conversations that didn't happen.
- Never name any active confidential deal in a broker draft or the Notion/summary output. The confidential-deal roster lives in C:\Users\Owner\.claude\hooks\confidential-terms.json (and session context) — if a broker's context brushes against deal specifics, keep the draft generic.
- Routing canon: the completion summary goes to ggoldberg@oxfordra.net ONLY. No cc to egoldberg or anyone else.
- HubSpot is not consulted for broker last-contact truth (rules.md §3b) — Outlook search is authoritative for that check.

This task is registered on the CC/MCP fleet deliberately: it needs native shell access for the Outlook COM draft-creation pattern in Step 4.