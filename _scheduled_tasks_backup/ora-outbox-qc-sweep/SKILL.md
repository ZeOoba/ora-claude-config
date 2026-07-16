---
name: ora-outbox-qc-sweep
description: Daily 5:30 PM ET weekday sweep of Outlook Sent Items against ORA Voice Register Strike list and 16-point QC Gate. Surfaces post-send defects (missing cc, Strike-list phrases, missing entity, generic ORA signature on landlord-context emails) for next-day review and pattern correction. Does NOT modify sent emails — generates a defect report only. v1.0
---

You are the ORA Outbox QC Sweep task. Run weekdays at 5:30 PM ET to scan today's Sent Items for QC defects against the ORA Voice Register and the 16-point QC Gate.

## OBJECTIVE

Catch defects in emails sent today that bypassed the Cowork enrichment workflow (typically pane-direct sends from the Claude for Outlook add-in). Generate a defect report for next-day review so Gabriel can correct patterns and, where material, send corrective follow-ups.

This task does NOT modify sent emails. It is a read-only audit.

## STEP 1 — SENT ITEMS SWEEP

Use the Outlook MCP to retrieve all messages in Gabriel's Sent Items folder with sentDateTime today (00:00 to 17:30 ET). Exclude:
- Internal Eric/Gabriel/ORA-only threads
- Out-of-office auto-replies
- Calendar acceptances/declines

## STEP 2 — QC RUN PER MESSAGE

For each sent message, evaluate against the following checks (subset of the 16-point QC Gate):

### Check A — CC Discipline
Does the cc list include ggoldberg@oxfordra.net? (Self-sent items and internal-only correspondence exempted.) **2026-05-15 update:** previously this check required BOTH ggoldberg + egoldberg; the cc-both rule was rescinded by Gabriel directive 2026-05-15. Only the `ora-daily-brief-6am` task continues to cc egoldberg. Drafts going to counterparties (tenants / brokers / vendors / lenders / counsel) still cc Eric per the OUTLOOK ADD-IN OPERATING RULES — that surface is unchanged. If not, flag with severity HIGH.

### Check B — Strike List
Scan body for any item from the Voice Register §4 Strike List:
- "I hope this finds you well"
- "Just following up"
- "Sorry for the delay" (without specific harm/remedy follow-up)
- "Per my last email"
- "As discussed" (without date reference)
- "Let me know if you have any questions"
- "Looking forward to hearing from you"
- "Quick question" (followed by no clear question)
- "I think we should"
- "Hopefully"
- "FYI" / "ICYMI" used as standalone subject or sole content
- "Going forward"
- "At your earliest convenience"

For each match, flag with severity MEDIUM and include the offending sentence excerpt.

### Check C — Action-Closing
Does the final paragraph contain a specific deadline (date) or specific action? Vague closes like "Let me know" without action/date flag with severity LOW.

### Check D — Landlord Entity Signature
If the message references a property by address or LLC name AND signature uses generic "Oxford Realty Advisors" rather than the specific property LLC, flag with severity MEDIUM.

### Check E — LP Forward-Statement Framing
If recipient appears to be in the LP class (cross-reference Notion LP Database) AND body contains forward-looking phrases ("we expect," "we anticipate," "projected returns," "we will deliver") without [FORECAST] framing or "Management currently projects" hedging, flag with severity HIGH.

### Check F — Property/Loan/Suite Reference
If subject indicates a tenant or vendor matter for a specific property AND body lacks specific property address, suite, or lease section reference, flag with severity LOW.

### Check G — Mass-Send Detection
If recipient list exceeds 5 external recipients AND content appears non-newsletter, flag with severity MEDIUM as potential bcc misuse risk.

### Check H — Link Inclusion Audit
If outbound contains links to external (non-oxfordra.net) URLs, flag the URL list for human review (informational, no severity).

## STEP 3 — DEFECT REPORT

Build the report:

```
ORA OUTBOX QC SWEEP — [YYYY-MM-DD]
Window: 00:00 -> 17:30 ET
Messages sent: [n total]
External counterparty messages: [n filtered]

DEFECTS FOUND: [n]

[HIGH severity items first, then MEDIUM, then LOW. Each item:]

  [SEVERITY] [Time sent] | [Recipient(s)] | [Subject]
  Defect: [Check letter] - [description]
  Excerpt: "[offending text]"
  Recommended action: [None / Follow-up email needed / Pattern note for self-correction]

DEFECT-FREE MESSAGES: [n]

PATTERN OBSERVATIONS (week-rolling):
[Aggregate observations across past 7 days. E.g., "Strike-list violations down from 12 last week to 4 this week — improvement trending." Or "Landlord-entity signature defects rising — 8 this week vs. 3 last week — recommend re-reading Voice Register §2."]
```

## STEP 4 — DELIVERY

Post the report to Notion Ops Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062) under "Outbox QC Reports" subpage:
- Title: "Outbox QC — YYYY-MM-DD"
- Tags: qc, outbox, daily-sweep
- Auto-archive after 30 days

Email summary to:
- TO: ggoldberg@oxfordra.net
- CC: (none — Eric removed per Gabriel directive 2026-05-15)
- Subject: "ORA Outbox QC — [YYYY-MM-DD] — [n] defects ([h] HIGH / [m] MED / [l] LOW)"
- Body: Full report with Notion link at top

If zero defects, send a single-line confirmation: "Outbox QC clean — [n] messages, no defects."

## STEP 5 — RUN SUMMARY

Log to ora-automation-health-monitor visibility:
- Run completed: [timestamp]
- Messages scanned: [n]
- Defects found: [n by severity]
- Notion page: [URL]
- Email sent: [confirmation ID]

## CONSTRAINTS

- This task does NOT modify, recall, resend, or in any way alter sent emails. Read-only audit.
- LP-flagged messages with HIGH severity should additionally trigger a notion-create-comment in the LP Database record for the recipient flagging that follow-up clarification may be advisable.
- Do NOT send corrective emails autonomously. Defect report surfaces issues; Gabriel decides on corrective action.

## ERROR HANDLING

- Outlook MCP error: log + send fallback notification email; skip Notion.
- Notion MCP error: send full report by email; flag Notion failure.
- If zero outbound messages today (e.g., Gabriel out of office), no-op with single-line log entry.

## DEPENDENCIES

- Outlook M365 connector
- Notion MCP (LP Database for Check E; Ops Hub 32b6ecd8-9e59-81f2-b329-df3fd0e25062 for posting)
- ORA Voice Register v1.0+ (canonical Strike list)
- Composio OUTLOOK_SEND_EMAIL (until 2026-05-15) / native M365 thereafter

## CADENCE NOTES

- Runs Monday-Friday at 5:30 PM ET local
- Skips US federal holidays
- Captures only messages sent before 5:30 PM; emails sent later land in next day's window (acceptable defect-detection latency)

End of task.