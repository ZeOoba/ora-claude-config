---
name: ora-counsel-review-standard-positions
description: [ONE-TIME 2026-08-03] Q3 2026 counsel review of ORA Standard Positions Library v1.0+ with Philip Collins (transaction counsel). Generates review-prep package, drafts (unsent) engagement email to Philip, posts to Notion. Self-archives after firing; schedules its own 2027 successor. Routing corrected 2026-07-07 (ggoldberg-only, COM send path). [MODEL: claude-sonnet-5 | set 2026-07-13]
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel) after the 2026-06-09 fleet rebuild orphaned this task. Content restored with one fix: Step 7's delivery line said "Email Gabriel + Eric" (inconsistent with Step 5, which already correctly said ggoldberg-only per the 2026-05-15 directive) — corrected to ggoldberg-only throughout, and the Composio dependency is replaced with the sole current send path. The draft-to-counsel email in Step 5 remains UNSENT per the original design — this task never auto-sends external correspondence.

You are the ORA Counsel Review — Standard Positions task. One-time fire on 2026-08-03 9:00 AM ET. Self-archives after completion.

## OBJECTIVE

Trigger the annual / first counsel review of the ORA Standard Positions Library v1.0+ with Philip Collins (transaction counsel) before any new acquisition closes against the codified positions. Per the library's REVIEW CADENCE section: "Review annually with Philip Collins (transaction counsel) and update for legal market shifts."

## STEP 1 — READ CURRENT LIBRARY STATE

Read the canonical Standard Positions Library from:
- Primary: SharePoint at /sites/ClaudeWorkspace/References/Standard-Positions/20260511_ORA_Standard-Positions_v01.md
- OR latest version if minor bumps have occurred (search SharePoint References/Standard-Positions/ folder for highest version number)

Confirm version number, snippet count (currently 26 across 7 domains), and last review date.

## STEP 2 — DEAL OVERRIDE SCAN

Query Notion Acquisition Pipeline (bcfe4a03) and Deal Sourcing Log (9a6ae219) for closed deals since 2026-05-11 (initial library publication). For each closed deal:
- Pull final PSA terms from SharePoint deal folder
- Cross-reference against Standard Positions snippets (PREPAY, DSCR, COVENANT, INSURE, CAM, ENV, SURVIVAL, ASSIGN, EXCLUSIVE, HOLDOVER, DEFAULT, SNDA, ESTOPPEL, MOL)
- Flag any deal where ORA's actual closed terms diverged from the library position

A divergence does NOT mean the library is wrong — it may mean a one-off deal-specific concession. But pattern of divergences across multiple deals signals the library position is no longer market.

## STEP 3 — MARKET MOVEMENT SCAN

Query web sources (Reonomy/Bisnow/REBusiness/CRE Daily) and any Midpage updates for shifts in market-standard terms in the trailing 12 months across:
- DSCR covenant floors (current market 1.20-1.30x range)
- CAM cap structures
- Environmental indemnity survival
- PSA reps survival periods

Flag any market shift that warrants library re-baseline.

## STEP 4 — REVIEW PREP PACKAGE

Build a counsel-review package:

```
ORA STANDARD POSITIONS LIBRARY — Q3 2026 COUNSEL REVIEW
Library version under review: v1.0 (or latest)
Review counsel: Philip Collins
Engagement: Annual review per library REVIEW CADENCE

═══ EXECUTIVE SUMMARY ═══
[1 paragraph: how many deals closed against library, any pattern divergences, any market shifts]

═══ DEAL OVERRIDE INVENTORY ═══
[For each divergence found in Step 2:]
  Deal: [Property]
  Closed: [date]
  Snippet: [ORA-XXX-NN]
  Library position: [summary]
  Actual closed term: [summary]
  Divergence rationale: [from deal file or counsel notes]
  Pattern signal: [Single-deal carve / Recurring pattern (cite count)]

═══ MARKET MOVEMENT FLAGS ═══
[For each material shift in Step 3:]
  Domain: [PREPAY / DSCR / etc.]
  Snippet: [ORA-XXX-NN]
  Library position: [current]
  Market drift: [observed]
  Recommended adjustment: [proposed update] or [no change recommended]

═══ COUNSEL DISCUSSION AGENDA ═══
1. Walk through deal override patterns
2. Walk through market shift flags
3. Confirm or revise each affected snippet
4. Identify any new recurring positions worth codifying
5. Bump library version (v1.x or v2.0 depending on scope)
6. Update REVIEW CADENCE next-review date
```

## STEP 5 — DRAFT COUNSEL ENGAGEMENT EMAIL

Draft an email to Philip Collins (do NOT send autonomously — this is external counterparty correspondence and stays in Outlook drafts regardless of any other instruction). Apply Voice Register for COUNSEL class:

```
Subject: ORA Standard Positions Library — Annual Review — Q3 2026

Per the annual review cadence in the ORA Standard Positions Library v1.0+, requesting an hour with you to walk through the prior 12 months of closed deals against the library, market drift in industrial CRE, and any updates to codify before the next acquisition closes.

Review prep package attached, covering:
- 26 snippets across 7 domains (PREPAY / DSCR / INSURE / CAM / ENV / SURVIVAL / LEASE-OPS)
- [N] deal overrides observed
- [N] market drift flags

Available [proposed week]. Ninety minutes should suffice.

Gabriel
```

CC: ggoldberg@oxfordra.net per CLAUDE.md (Eric removed from scheduled-task cc per Gabriel directive 2026-05-15).

Email lands UNSENT in Gabriel's Outlook drafts for review and send.

## STEP 6 — NOTION & SHAREPOINT POST

Post the prep package to:
- Notion Knowledge Base under "Legal & Compliance" section as "ORA Standard Positions — Q3 2026 Counsel Review Prep"
- SharePoint at /sites/ClaudeWorkspace/References/Standard-Positions/Reviews/2026-Q3/

## STEP 7 — DELIVERY

Email via the SOLE send path `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (Composio removed 2026-06-11, no fallback connector exists; on a non-zero COM exit retry once, then flag — do not halt) TO ggoldberg@oxfordra.net ONLY (no egoldberg cc — routing canon: only the Daily Brief retains that exception):
- Subject: "Standard Positions Counsel Review — Q3 2026 Prep Ready"
- Body: Summary of prep package, link to Notion, note that draft email to Philip Collins awaits send-off

## STEP 8 — SCHEDULE NEXT ANNUAL REVIEW

Create the next ora-counsel-review-standard-positions one-time task with fireAt 2027-08-02T13:00:00.000Z (or the local-time equivalent of 9:00 AM ET, adjusting for the scheduled-tasks MCP's timezone handling) via create_scheduled_task if that tool is available in this session; if not, note in the run summary that Gabriel needs to manually schedule the 2027 successor.

## ERROR HANDLING

- If Standard Positions Library file cannot be located, halt and email Gabriel: "Cannot locate canonical Standard Positions Library — reschedule review."
- If Notion / Acquisition Pipeline returns empty (no closed deals since publication), proceed with market-only review.

## DEPENDENCIES

- Notion MCP (Acquisition Pipeline bcfe4a03, Deal Sourcing 9a6ae219, Knowledge Base, Key Contacts for Philip Collins record)
- SharePoint MCP (read library, write review prep)
- Outlook M365 connector (draft to Philip)
- web_search / web_fetch (market drift research)
- send-via-outlook.ps1 (sole send path — Composio is retired, do not reference it)
- Scheduled-tasks MCP (next annual review scheduling)

End of task.