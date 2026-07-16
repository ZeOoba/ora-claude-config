---
name: ora-inbox-pre-brief
description: ORA Inbox Pre-Brief — weekdays 6:30 AM ET. Sweeps overnight Outlook (last 14 hours), classifies messages by counterparty class against Notion DBs, scores urgency, posts triage brief to Notion Ops Hub 32b6ecd8-9e59-81f2-b329-df3fd0e25062, emails Gabriel + Eric. Pairs with Claude for Outlook add-in. v1.3 (2026-05-14) — replaces truncated `32b6ecd8` parent-id references with full UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062` (Notion API rejects short IDs); pins canonical Windows path for Claude_Workspace state files; cuts Composio Rube fallback wording (Rube EOL 2026-05-15) and pins native Composio OUTLOOK_SEND_EMAIL tool slug `mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL` (or direct OUTLOOK_SEND_EMAIL via Composio executor). v1.2 (2026-05-12) — adds Step 0.5 rate prefetch beacon read for chain-level upstream signal surfacing (co-consumer with ora-daily-brief-6am). v1.1 (2026-05-12) — adds heartbeat write-first guard against silent dispatcher misses.
---

## CANONICAL PATHS (added v1.3, 2026-05-14)

`Claude_Workspace` in this skill refers to the SharePoint-synced local folder:
`C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace`

State files:
- Heartbeat log: `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log`
- Treasury beacon: `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\_state\treasury-yields.json`
- Heartbeat-block-id map: `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\_state\heartbeat-blocks.json`

If the canonical `_state` folder does not exist at run time, create it before the heartbeat write — do not silently fall back to the session outputs folder. The session outputs folder is ephemeral and is purged between sessions; writes there are non-durable for watchdog purposes.

Canonical Notion parent UUID for all Ops Hub operations in this skill:
`32b6ecd8-9e59-81f2-b329-df3fd0e25062`

Never pass the truncated 8-character form `32b6ecd8` to the Notion MCP — it rejects with `validation_error: parent.page_id should be a valid uuid`.

You are the ORA Inbox Pre-Brief task. Run weekdays at 6:30 AM ET to triage overnight Outlook activity BEFORE Gabriel opens his inbox. Output goes to Notion Ops Hub and an email to Gabriel + Eric.

## STEP 0 — HEARTBEAT WRITE-FIRST GUARD (added v1.1, 2026-05-12)

**Purpose:** Defeat the silent-miss failure mode where the scheduler dispatches the task but the skill errors before `lastRunAt` is recorded, leaving `ora-automation-health-monitor` unable to distinguish a missed fire from a logging gap. (Root cause of 2026-05-11 silent miss surfaced in Daily Brief 2026-05-12 §4a.)

**Before doing ANY other work in this skill**, write a heartbeat entry that is durable independent of the rest of the skill's success path:

1. **State-file mirror (primary signal).** Append a single line `pre-brief-heartbeat: <ISO 8601 UTC> :: status=ENTERED :: run_id=<uuid>` to the canonical absolute path `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log` (one line per run, rotated weekly by `ora-claude-workspace-hygiene`). This file is the canonical watchdog signal. If the `_state` subfolder does not exist, create it; do not fall back to the session outputs folder.
2. **Notion mirror (secondary signal).** Update the dedicated heartbeat block on the Ops Hub page (parent UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — block ID stored in `Claude_Workspace/_state/heartbeat-blocks.json` under key `ora-inbox-pre-brief.heartbeat_block_id`. Idempotent overwrite (no page sprawl).
3. **Only after the state-file write succeeds** proceed to Step 1. If the Notion mirror fails, log a `HEARTBEAT_NOTION_MIRROR_FAILED` warning and continue — the state-file is sufficient.
4. **On any subsequent failure**, update the heartbeat line in place to `:: status=ENTERED → FAILED :: stage=<step-N> :: error=<message>` before exiting. The watchdog interprets `ENTERED` with no terminal status as in-flight; absence of any line for the day is a true silent miss.

This guard transforms a silent dispatcher-side miss into a detectable signal: a missed fire now means no heartbeat line at all, while a mid-skill error means heartbeat present + terminal `FAILED` status. The `ora-automation-health-monitor` v1.2 logic should be updated in tandem to read the heartbeat log when `lastRunAt` is null (tracked separately under `health-monitor-v1.3-heartbeat-aware`).

## STEP 0.5 — RATE PREFETCH BEACON READ (added v1.2, 2026-05-12)

**Purpose:** Surface a rate-prefetch outage in the Activity Summary so Gabriel sees the same upstream-failure signal whether he opens the Daily Brief, the Inbox Pre-Brief, or the Notion Ops Hub first. Co-consumer with `ora-daily-brief-6am` v1.1+.

1. After the heartbeat write (Step 0) and before Inbox Sweep (Step 1), read the canonical absolute path `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\_state\treasury-yields.json`. Parse JSON. Do not block the run on any failure here — beacon read is opportunistic context, not a gating dependency. If file is missing or unreadable, capture `status=MISSING_FILE | UNREADABLE` and proceed to Step 1.

2. Capture a `rate_beacon` object for use in Step 6:
   - `status`: one of `OK | SOURCE_DEGRADED | STALE_DATA | FAILED | MISSING_FILE | UNREADABLE`
   - `fetched_at_iso`: from JSON, or null
   - `errors`: `prefetch_errors[]` from JSON, or empty
   - `age_min`: `now_utc - fetched_at_iso`, or null

3. If `rate_beacon.status != "OK"`, in Step 6 ("TRIAGE OUTPUT"), prepend a single line at the very top of the brief — ABOVE the header — in the form:
   ```
   ⚠ UPSTREAM SIGNAL — ora-treasury-yield-prefetch status={status}; last fetched {fetched_at_iso}. Daily Brief Section 3 will show banner. No inbox-triage action required.
   ```
   This is informational only — does NOT change urgency scoring or inbox classification.

## OBJECTIVE

Classify, prioritize, and surface overnight inbox activity so Gabriel knows what is real and what is noise BEFORE opening Outlook. Eliminates discovery time inside the Claude for Outlook pane.

## TIMEFRAME

Sweep messages received in Gabriel's Outlook inbox between 4:30 PM ET prior business day and 6:30 AM ET today. On Monday runs, sweep from 4:30 PM ET previous Friday (covers full weekend).

## STEP 1 — INBOX SWEEP

Use the Outlook MCP (`mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_email_search`) to retrieve all messages in Gabriel's Inbox folder where receivedDateTime falls in the timeframe window.

Exclude:
- Newsletters and marketing blasts (sender domains containing common marketing platforms: mailchimp, hubspot.com/email, sendgrid, constantcontact, mktomail, etc.)
- Out-of-office auto-replies
- Calendar invitations and acceptances (these route through calendar logic separately)
- Internal Eric ↔ Gabriel ↔ Ze ↔ ORA-internal-only threads (no external counterparty)

## STEP 2 — COUNTERPARTY CLASSIFICATION

For each remaining message, classify the sender into one of seven counterparty classes by:

1. Cross-referencing sender email against Notion databases:
   - Tenant DB 8dbbaec0
   - Acquisition Pipeline bcfe4a03
   - Deal Sourcing Log 9a6ae219
   - Broker Relationships 48e43778
   - Vendor & Advisor Directory
   - Loan Portfolio Tracker
   - LP Database
   - Key Contacts (counsel, accountants, regulatory)

2. If no Notion match, use sender domain heuristics and signature parsing.

3. If still ambiguous, classify as "Unknown — review required."

Classes: Tenant / Broker / Vendor / Lender / Counsel / LP / Government / Unknown

## STEP 3 — URGENCY SCORING

Score each message 1–5:

5 — IMMEDIATE (respond before 9:00 AM)
- Lender covenant question or breach notice
- LP query touching capital call, distribution, or NAV
- Counsel deadline within 48 hours
- Regulatory deadline within 48 hours
- Tenant default notice or material complaint
- Active deal milestone (LOI deadline, PSA execution, closing)

4 — HIGH (respond today)
- Broker submitting a new deal in target market
- Active deal correspondence (counsel, seller, buyer)
- Tenant renewal-related (within 180 days of expiration)
- Vendor scope confirmation needed for active project
- Lender routine ask not on deadline

3 — STANDARD (respond within 2 business days)
- Routine tenant communications (maintenance, billing questions)
- Vendor invoices and routine updates
- Broker check-ins without active submission
- LP routine queries

2 — LOW (respond within 5 business days)
- Vendor pitches without prior engagement
- Industry contacts without active matter
- Information-only updates from counsel or accountants

1 — INFO ONLY (no response required, archive after read)
- CC'd on others' threads where Gabriel is not principal recipient
- Acknowledgments and confirmations

## STEP 4 — DEAL / MATTER LINKAGE

For each message, link to active deal or matter:
- Acquisition Pipeline record (if related to active acquisition)
- Tenant record (if tenant-related)
- Loan record (if lender-related)
- Vendor work order or contract (if vendor-related)
- LP fund (if LP-related)
- Counsel matter (if counsel-related)

If link cannot be made, flag for manual triage.

## STEP 5 — WATCH-OUT FLAGS

Surface RED FLAGS at the top of the brief:
- Any message scoring 5 (IMMEDIATE)
- Any sender flagged in Notion as "active dispute" or "litigation hold"
- Any message with attachments matching pattern: "PSA", "LOI", "Term Sheet", "Default", "Notice of", "Demand"
- Any sender domain mismatch with known contact (potential phishing or impersonation)
- Any message thread with > 5 messages in trailing 48 hours (heating up)

## STEP 6 — TRIAGE OUTPUT

Build the brief in this structure:

```
ORA INBOX PRE-BRIEF — [YYYY-MM-DD]
Window: [start datetime] → [end datetime] ET
Total messages swept: [n]
Excluded as noise: [n]
For triage: [n]

═══ RED FLAGS — ACT BEFORE 9:00 AM ═══
[List score-5 items with one-line context. Empty section if none.]

═══ HIGH — RESPOND TODAY ═══
[Group by counterparty class. For each: sender name, subject, one-line context, link to Notion record.]

═══ STANDARD — 48 HOUR WINDOW ═══
[Compact list — sender, subject, class.]

═══ LOW + INFO — REVIEW WHEN CONVENIENT ═══
[Compact list — sender count by class only.]

═══ UNKNOWN COUNTERPARTIES — MANUAL CLASSIFICATION NEEDED ═══
[List sender + subject; recommend Notion record creation if pattern recurs.]

═══ ACTIVITY SUMMARY ═══
[1-2 sentence narrative of the day's signal: what's heating up, what's quiet, what's anomalous.]
```

## STEP 7 — NOTION POST

Post the brief to Notion Ops Hub (parent page UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062` — pass the full UUID, NOT the truncated `32b6ecd8` form which fails Notion's validation) as a new page under "Daily Pre-Briefs" subpage:
- Title: "Inbox Pre-Brief — YYYY-MM-DD"
- Tags: pre-brief, inbox, [day-of-week]
- Set retention: auto-archive after 14 days

Tool: `mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__notion-create-pages` with `parent: { type: "page_id", page_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062" }`.

## STEP 8 — EMAIL DELIVERY

Send the brief via native Composio `OUTLOOK_SEND_EMAIL` (executed through `mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL`). Do NOT use the deprecated Rube server (`mcp__d6315173-...`) — Rube reaches end-of-life 2026-05-15 per ora-cre-data-mcp-recheck and CLAUDE.md §Tool Hierarchy.

Arguments:
- `to`: `ggoldberg@oxfordra.net`
- `cc_emails`: `[]`  # Eric removed per Gabriel directive 2026-05-15 — only Daily Brief retains egoldberg cc
- `subject`: `ORA Inbox Pre-Brief — [YYYY-MM-DD] — [n] for triage, [n] RED`
- `is_html`: `true`
- `save_to_sent_items`: `true`
- `body`: Full brief content as HTML, with Notion page link at top.

If the email send returns HTTP 202 with no message-id payload, do NOT retry — Microsoft Graph accepts asynchronously and a retry creates a duplicate.

## STEP 9 — RUN SUMMARY

Log to ora-automation-health-monitor visibility:
- Run completed: [timestamp]
- Messages processed: [n]
- Notion page created: [URL]
- Email sent: [confirmation ID]
- Errors encountered: [list, or "none"]

## ERROR HANDLING

If Outlook MCP returns error or empty result set:
- Log error
- Send fallback email to Gabriel + Eric: "Pre-brief skipped today — Outlook MCP error: [details]"
- Do NOT post empty brief to Notion

If Notion MCP returns error:
- Log error
- Send brief by email anyway (Notion-link line replaced with: "Notion post failed, see body for full content")

## DEPENDENCIES

- Outlook M365 connector (read via `mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_email_search`)
- Notion MCP `mcp__c5f4869f-7d3a-4472-a66a-8e61315feb51__*` (read: 8 databases listed; write: Ops Hub `32b6ecd8-9e59-81f2-b329-df3fd0e25062`)
- Composio native `OUTLOOK_SEND_EMAIL` via `mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_MULTI_EXECUTE_TOOL`. Rube path (`mcp__d6315173-...`) is RETIRED — EOL 2026-05-15.
- ORA Voice Register v1.0+ (for tone of any drafts surfaced inline)
- SharePoint-synced Claude_Workspace at `C:\Users\Owner\OneDrive - Oxford Capital Partners (1)\Claude_Workspace\` (state files; create `_state` subfolder on first run if missing)

## CADENCE NOTES

- Runs Monday-Friday at 6:30 AM ET local
- Skips US federal holidays (check before sending — if today is a federal holiday, suppress run with no-op log entry)
- Does NOT run weekends; Monday run includes weekend window
- Pairs with ora-week-ahead-briefing (Friday 4:30 PM) and ora-daily-brief-6am (6:00 AM market intel) to give Gabriel a layered morning

End of task.