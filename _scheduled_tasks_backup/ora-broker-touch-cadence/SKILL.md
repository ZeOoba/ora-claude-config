---
name: ora-broker-touch-cadence
description: Monthly (2nd, 1:40 PM ET) broker relationship touch cadence — reads the Notion Broker Relationships DB, checks Outlook for recent contact, DRAFTS (never sends) personal pocket-listing check-ins to up to 5 brokers via Outlook COM .Save(); summary to ggoldberg only. Draft-only by design (Hard Invariant 1). Serves acquisition velocity (priority #1); Gabriel-ratified G4b 2026-07-16. v1.0. [MODEL: UNVERIFIABLE | checked 2026-07-16]
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

# THE BODY MUST BE A SINGLE-QUOTED HERE-STRING (@'...'@). A double-quoted string
# SILENTLY DESTROYS EVERY DOLLAR FIGURE: PowerShell reads "$7.50" as the undefined
# variable $7 followed by ".50". Proven by repro 2026-08-27:
#   "clear $7.50/SF NNN ... $80.87/SF list ... $50,000 deposit"
#   -> "clear .50/SF NNN ... .87/SF list ... ,000 deposit"
# This defect shipped three corrupted counterparty drafts on 2026-08-13 that then
# sat unsent for 14 days. It bites this task hard: broker check-ins are numbers-forward
# and name the buy-box ($10M / 50K SF). Never interpolate. Never use @"..."@ either.
$body = @'
<body text — pasted verbatim, no escaping required>
'@

$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To      = '<broker email>'
$mail.Subject = '<subject>'
$mail.Body    = $body
$mail.Save()
# NEVER call $mail.Send() — drafts stay parked in the Outlook Drafts folder for Gabriel's own review and send.

# MANDATORY POST-SAVE FIGURE CHECK — a draft that fails this is NOT parked.
if ($body -match '\$\d' -and $mail.Body -notmatch '\$\d') {
  Write-Output 'FIGURE_CORRUPTION — dollar figures did not survive the save. Report the draft as defective in the STEP 5 Ops Hub row; do NOT tell Gabriel it is ready to send.'
} elseif ($mail.Body -match '(?<![\w$])[.,]\d{2}/SF') {
  Write-Output ('FIGURE_CORRUPTION_SUSPECTED — orphaned decimal before /SF: ' + $Matches[0])
} else {
  Write-Output ('PARKED_OK EntryID=' + $mail.EntryID)
}

STEP 5 — Completion reporting.
Post one row to the Notion Ops Hub (parent page 32b6ecd8-9e59-81f2-b329-df3fd0e25062) listing who was drafted, their market, and why (stale-touch trigger + any Outlook thread context used). Then email a one-paragraph summary to ggoldberg@oxfordra.net ONLY (no cc — routing canon; the ora-am-brief Daily Brief is the sole cc-egoldberg exception and does not apply here) via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — this summary is the ONLY send this task ever performs; the broker drafts themselves are never sent. On a COM failure for either the drafts or the summary send: retry once, then flag loudly in the Notion Ops Hub row if the retry also fails — do not halt the run.

HARD GUARDRAILS (verbatim, non-negotiable):
- Never call .Send() on a broker draft. An actual outbound send to a broker (counterparty) requires Gabriel's explicit in-turn confirmation per Hard Invariant 1 — this task is structurally incapable of doing that send itself.
- Never fabricate relationship history, thread context, or broker detail. If no real context exists for a broker, the draft says less — it never invents rapport, deals, or prior conversations that didn't happen.
- Never name any active confidential deal in a broker draft or the Notion/summary output. The confidential-deal roster lives in C:\Users\Owner\.claude\hooks\confidential-terms.json (and session context) — if a broker's context brushes against deal specifics, keep the draft generic.
- Routing canon: the completion summary goes to ggoldberg@oxfordra.net ONLY. No cc to egoldberg or anyone else.
- HubSpot is not consulted for broker last-contact truth (rules.md §3b) — Outlook search is authoritative for that check.

This task is registered on the CC/MCP fleet deliberately: it needs native shell access for the Outlook COM draft-creation pattern in Step 4.