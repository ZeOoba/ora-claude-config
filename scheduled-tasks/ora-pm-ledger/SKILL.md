---
name: ora-pm-ledger
description: ORA Evening Ledger — consolidated daily close. Runs three blocks in order at one cadence — A Notion Daily Digest (every day), B Outbox QC Sweep (weekdays only), C EOD Action Ledger (every day). Restored 2026-07-08 from three separately-archived block specs after the 2026-07-05 CC/MCP registry loss destroyed the original consolidated file; routing/send-path/paths corrected to current canon during restoration (see RESTORATION NOTE at bottom). CC canonical file inlined 2026-07-08 (second restoration same day) to remove a redirect-to-OneDrive pattern that had already broken twice. Re-enabled 2026-07-09 (Gabriel-approved, post-recovery-stabilization confirmation). [MODEL: UNVERIFIABLE | checked 2026-07-08]
---

# ORA EVENING LEDGER — Consolidated Daily Close (ora-pm-ledger)

## 0. RUN ORDER & PURPOSE

One task, one 18:00 ET fire (subject to the catch-up-burst scheduler doctrine —
if the Desktop app wasn't open at 18:00, this runs at next app-open and is
still "today's" run). Execute, branching by ET day-of-week:

1. **BLOCK A — Notion Daily Digest** (every day) — what changed in Notion today.
2. **BLOCK B — Outbox QC Sweep** (Monday–Friday only) — compliance audit of
   today's Sent Items against the Voice Register.
3. **BLOCK C — EOD Action Ledger** (every day) — day-closing orchestrator:
   inventories every open manual action Gabriel owes, auto-resolves what's
   safely reversible, and reports the rest.

Each block below is otherwise self-contained. A shared **§ GLOBAL — SEND
PATH, ROUTING, PYTHON** section at the end applies to all three and
overrides any older per-block instruction that conflicts with it.

## 0.5 PRE-FLIGHT DE-DUPE GUARD (run FIRST, before Block A)

This task is registered on BOTH fleets (CC/MCP + LAMS/Cowork). On 2026-07-09 both
fired the same day (a LAMS run ~16:27 ET delivered A/B/C; the CC 18:00 fire then
re-ran) — producing a full DUPLICATE set of emails and Notion pages, and the
duplicate Ops Hub pages double-count in the next morning's brief. Until the
redundant registration is retired, THIS guard makes a second same-day fire a no-op.
Run it before anything else:

1. **Check whether today's deliverables already exist for `{TODAY}` (ET):**
   - Sent Items for subjects `ORA Notion Daily Digest - {TODAY}`,
     `ORA Outbox QC - {TODAY}`, `ORA EOD Action Ledger - {TODAY}`.
   - Notion Ops Hub (`32b6ecd8…`) child pages `Outbox QC — {TODAY}` and
     `EOD Action Ledger — {TODAY}`.
   - The send-log `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-log.txt` (if this
     surface can reach it) for today's OK sends.
2. **Decide per block, not all-or-nothing.** For each applicable block (Block B is
   weekdays-only): if that block's email AND its durable copy already exist for
   `{TODAY}`, **SKIP it** — do not re-send, do not re-post. Run only the block(s)
   with no evidence of today's delivery.
3. **If all applicable blocks are already delivered:** no-op. Append ONE line to the
   day's `EOD Action Ledger — {TODAY}` Ops Hub page: "ora-pm-ledger {TODAY}: duplicate
   same-day fire suppressed by de-dupe guard — prior run already delivered A/B/C."
   Send NOTHING; do NOT write HTML fallbacks (those are for send FAILURES only).
4. Proceed to the surviving blocks only after this guard clears.

---

## BLOCK A — NOTION DAILY DIGEST (every day)

You are generating Gabriel Goldberg's end-of-day digest of everything that
moved in the Oxford Realty Advisors Notion workspace **today**. Today's date
(America/New_York) is available in your environment — call it `{TODAY}`
(ISO `YYYY-MM-DD`). This is an INTERNAL status report to Gabriel, not a
counterparty communication — sending it is permitted.

ORA context: ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27
properties across OH, MD, IN, WI, MO, KS, TN. Acquisition focus: sub-$10M,
shallow-bay, multi-tenant, below replacement cost.

### A.1 SOURCES — THE NOTION SURFACE TO SCAN

Priority sections (always reported first, even if empty, each with its own
heading). IDs below are as last verified 2026-06-11 (Ops Hub Databases
Maintenance Sweep entries) — **not re-verified during this 2026-07-08
restoration**; if a fetch errors, record a COVERAGE GAP, do not silently
drop the source, and flag the ID for a refresh.

| # | Section heading | Notion target | ID |
|---|---|---|---|
| A | **Deal Pipeline** | Acquisition Pipeline Tracker | `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b` |
| A | **Deal Pipeline** | Deal Sourcing Log | `9a6ae219-85a3-4621-899c-c757fd062f8b` (canonical pair: database `8d2ddc5177e84cd7b1c0c0f6ef943479` / data source `9a6ae219-85a3-4621-899c-c757fd062f8b`) |
| A | **Deal Pipeline** | Broker Relationships | `48e43778-b1f2-4b16-8f3c-0bf18f8642e9` |
| B | **Tenants & Operations** | Tenant Database — query via data source, NOT the wrapper ID (wrapper `8dbbaec0…` throws "Aggregation property not found"; root cause was a tool-routing quirk, not a broken rollup — fixed 2026-04-27) | `collection://b12f4cfd-a995-4755-8341-6435ae8173b4` |
| B | **Tenants & Operations** | Property Register | `19a61fc9-21ed-42d7-a0db-aa730d9a9683` |
| B | **Tenants & Operations** | CapEx & Maintenance Log | `5dfcc3ad-532e-4e5f-bf8d-512e2b69e317` |
| C | **Knowledge Base & Decisions** | 📚 Oxford Institutional Knowledge Base | `3386ecd8-9e59-8166-af49-da066dc7ca14` |
| D | **Operations Hub (everything else)** | Oxford Real Assets — Operations Hub | `32b6ecd8-9e59-81f2-b329-df3fd0e25062` |

Section **E — Everything Else Edited Today** is a workspace-wide catch-all
for anything created/edited today that does not belong to A–D.

### A.2 METHOD — HOW TO DETERMINE "CHANGED TODAY"

The Notion MCP exposes two reliable signals; use BOTH and merge, deduping by
page ID:

1. **Newly created today (precise):** `notion-search` with
   `query_type: "internal"` and
   `filters.created_date_range.start_date = {TODAY}`. Run it (a) workspace-wide
   for the catch-all, and (b) scoped to each priority data source via
   `data_source_url` (use the `collection://…` form for the Tenant DB; for the
   others, first `notion-fetch` the database ID to read its
   `<data-source url="collection://…">` tag, then search that data source).

2. **Edited today (best-effort):** `notion-search` returns each result's
   `timestamp` (last-edited). For each priority source, run a broad semantic
   search and KEEP any result whose `timestamp` date == `{TODAY}`. Also
   `notion-fetch` the Operations Hub page and scan its recent activity /
   child pages for `{TODAY}` last-edited stamps.

**Known limitation — state it honestly, do not hide it:** the available MCP
filters on *created* date precisely but cannot range-filter on *last-edited*
date server-side, so edits to older pages are caught only when they surface in
the semantic searches above. If you suspect coverage is partial for a source,
say so in that section ("edit-detection best-effort — newly-created items are
complete; edits to pre-existing pages may be incomplete"). Never imply
completeness you didn't achieve.

For every item captured, record: **title**, **what changed** (created vs.
edited; 1-line substance if discernible from the page), **last-edited time
(ET)**, and a **clickable Notion URL**.

If a source returns zero changes today, print "— no changes today" under its
heading (do not omit the heading). If NOTHING changed anywhere today, send the
email anyway with a single line: "No Notion activity recorded today."

### A.3 REPORT FORMAT — INSTITUTIONAL HTML EMAIL

Build one self-contained HTML document, ORA Institutional Style:
- Palette: Navy `#1B2A4A` (headings/rules), Gold `#C9A96E` (accents), Parchment
  `#F5F0E8` (section background). Body font stack
  `'EB Garamond', Georgia, serif`; labels/meta in
  `'DM Sans', Arial, sans-serif`; any IDs/code in `'IBM Plex Mono', monospace`.
- All CSS **inline** (email clients strip `<style>` and `<head>`). No external
  resources, no `<script>`, no inline event handlers.
- Structure:
  1. **Header** — "ORA Notion Daily Digest — {Weekday, Month D, YYYY}", run
     time ET, and a one-line **Scoreboard**: total items changed, split as
     `N created · M edited` and a per-section count (A/B/C/D/E).
  2. **Section A — Deal Pipeline**, **B — Tenants & Operations**,
     **C — Knowledge Base & Decisions**, **D — Operations Hub**,
     **E — Everything Else Edited Today**. Each item as a compact row:
     **Title** (linked) — what changed — `last-edited HH:MM ET`.
  3. **Section F — Portfolio Alerts** — time-sensitive flags computed from the
     live dashboard data (see A.4). Place this near the TOP (above Section A) so
     Gabriel sees action items first.
  4. **COVERAGE GAPS** — any source that errored or returned best-effort only.
  5. Footer: "Generated by ora-pm-ledger (Notion Digest block) · 18:00 ET" + a
     link to the Operations Hub + the dashboard (https://ora-command-center.pages.dev).

Keep it skimmable: tables or tight rows, not prose paragraphs.

### A.4 PORTFOLIO ALERTS (source of record: the Command Center alerts engine — put at TOP of email)

**DO NOT read the retired `C:\Users\Owner\oxford-perfection\ora-dashboard\data\*.json`
dashboard.** That whole tree was archived 2026-07-07 to
`C:\Users\Owner\archive\oxford-perfection_archived-20260707\` and its last data
refresh is 2026-06-22 (17+ days stale) — it is NOT the source of record and must
never be presented as current. (Repointed 2026-07-09; see RESTORATION NOTE.)

Portfolio Alerts are computed authoritatively by the **oxford-command-center
alerts engine** (`src/analytics/conditions.ts` + `src/brain/critical-dates.ts`),
which runs daily and produces that morning's **Command Center Daily Brief**
(posted to Notion ~06:15 ET — the same brief Block A already fetches, and whose
run-state is in `C:\Users\Owner\oxford-command-center\data\brief-health.json`).
Surface the Brief's already-computed flags rather than re-deriving them: the
warehouse's lease/debt tables are not yet populated, so re-derivation would
silently UNDER-report. List only alerts that FIRE, most-urgent first:
- **Lease expirations ≤90 days** — tenant · property · annual rent · days out. Source: the day's Command Center Daily Brief critical-dates section.
- **Insurance ≤30 days / expired** — count + total premium + next renewal date. Source: the Brief. MAY be verified/refined directly from the live warehouse `C:\Users\Owner\oxford-command-center\data\warehouse\finance.sqlite`, table `property_insurance_policies` (columns `expiration_date`, `premium_annual`, `policy_type`) — the one alert class fully populated in the warehouse.
- **Loan balloons ≤18 months** — loan · months · balance. Source: the Brief (warehouse `debt_positions` is currently EMPTY — do NOT read it as authoritative).
- **DSCR < 1.25× or LTV > 40%** — property · figure. Source: the Brief / warehouse `debt_scores` once populated.
- **Acquisition deadlines / stalled deals** — deal · market. Already covered by Block A's live Notion Acquisition Pipeline query — cross-reference it, do NOT re-derive.
Each alert = one line: number + threshold + "so what", with a link to the
dashboard (https://ora-command-center.pages.dev) for detail. If the day's
Command Center Daily Brief is unavailable on the run surface, record a COVERAGE
GAP for the affected alert classes — do NOT fabricate and do NOT fall back to the
retired JSON dashboard. If none fire, print "✅ No portfolio alerts."
**Exclude any E. Fulton item** (invariant 3 — confidential active deal;
internal principals' email is fine per A.5, but keep this section mechanically
source-driven and don't editorialize on it here — Block C's guardrails are the
place for deal-specific handling).

### A.5 QC GATE (run before send)
- Every reported item traces to a real Notion page returned this run — **no
  fabrication**. If unsure an item changed today, exclude it or label it.
- Recipient: TO ggoldberg@oxfordra.net ONLY (see GLOBAL § routing — this
  corrects the original spec's CC egoldberg@, rescinded 2026-05-15 / re-ratified
  2026-06-10).
- Subject carries today's date. HTML renders standalone (inline CSS, no script).
- Coverage gaps and best-effort edit-detection are disclosed, not hidden.
- Internal principals' report — confirm no send-to-counterparty content.
  (E. Fulton Street Portfolio may appear here — this is an internal email, not
  external/oxfordra.net material — but never forward it externally.)

### A.6 FAILURE HANDLING
If the run cannot complete (Notion connector down, etc.), still send whatever
was gathered, list the failure under COVERAGE GAPS, and never present a partial
run as complete. A missed run is independently surfaced by
`ora-automation-health-monitor` / the dead-man heartbeat chain.

---

## BLOCK B — OUTBOX QC SWEEP (Monday–Friday only)

You are the ORA Outbox QC Sweep block. Runs only on ET weekdays, as part of
this task's single 18:00 fire, to scan today's Sent Items for QC defects
against the ORA Voice Register and the 16-point QC Gate.

**No other skill or task performs this check — it has no replacement
elsewhere.** This is a read-only audit; it never modifies, recalls, resends,
or alters sent emails.

### B.1 OBJECTIVE

Catch defects in emails sent today that bypassed the Cowork enrichment
workflow (typically pane-direct sends from the Claude for Outlook add-in).
Generate a defect report for next-day review so Gabriel can correct patterns
and, where material, send corrective follow-ups himself.

### B.2 SENT ITEMS SWEEP

Use the Outlook MCP to retrieve all messages in Gabriel's Sent Items folder
with `sentDateTime` today, window 00:00 through this run's fire time (nominal
18:00 ET — messages sent after the sweep runs land in next day's window;
acceptable defect-detection latency). Exclude:
- Internal Eric/Gabriel/ORA-only threads
- Out-of-office auto-replies
- Calendar acceptances/declines

### B.3 QC RUN PER MESSAGE

For each sent message, evaluate against the following checks (subset of the
16-point QC Gate):

**Check A — CC Discipline.** Does the cc list include ggoldberg@oxfordra.net?
(Self-sent and internal-only correspondence exempted.) The old cc-both
(ggoldberg + egoldberg) rule was rescinded by Gabriel directive 2026-05-15,
re-ratified 2026-06-10 — only the `ora-am-brief` Daily Brief still cc's Eric.
Drafts to counterparties (tenant/broker/vendor/lender/counsel) still cc Eric
per the Outlook add-in operating rules — that surface is unchanged. If the
expected cc is missing, flag HIGH.

**Check B — Strike List.** Scan body for any Voice Register §4 Strike List
item: "I hope this finds you well" · "Just following up" · "Sorry for the
delay" (without specific harm/remedy) · "Per my last email" · "As discussed"
(no date reference) · "Let me know if you have any questions" · "Looking
forward to hearing from you" · "Quick question" (no clear question follows) ·
"I think we should" · "Hopefully" · "FYI"/"ICYMI" as standalone subject/sole
content · "Going forward" · "At your earliest convenience". Flag MEDIUM per
match, with excerpt.

**Check C — Action-Closing.** Does the final paragraph contain a specific
deadline (date) or specific action? Vague closes ("Let me know" with no
action/date) flag LOW.

**Check D — Landlord Entity Signature.** If the message references a property
by address or LLC name AND the signature uses generic "Oxford Realty
Advisors" or the personal "Gabriel Goldberg, VP Acquisitions" block rather
than the specific property LLC, flag MEDIUM.

**Check E — LP Forward-Statement Framing.** If the recipient is in the LP
class (cross-reference Notion LP Database) AND the body contains
forward-looking phrases ("we expect," "we anticipate," "projected returns,"
"we will deliver") without `[FORECAST]` framing or "Management currently
projects" hedging, flag HIGH.

**Check F — Property/Loan/Suite Reference.** If the subject indicates a
tenant/vendor matter for a specific property AND the body lacks a specific
property address, suite, or lease-section reference, flag LOW.

**Check G — Mass-Send Detection.** If recipients exceed 5 external addresses
AND content is non-newsletter, flag MEDIUM (potential bcc-misuse risk).

**Check H — Link Inclusion Audit.** If the outbound contains links to
external (non-oxfordra.net) URLs, list them for human review — informational,
no severity.

**Check I — Frozen-Date Subject (added 2026-07-09).** If the subject carries
a date token that reads as the message's own dateline — a trailing
"— YYYY-MM-DD" suffix, or a date inside an automated-report-style subject
(Brief / Report / Digest / Ledger / QC / Sweep / Board / Guard) — and that
date differs from `sentDateTime`'s date by MORE than 1 day, flag MEDIUM.
This check applies to ALL of today's sent mail including automated/internal
sends (do not apply the B.2 internal-thread exclusion to it). Rationale: the
Command Center Daily Brief went out 2026-07-08 and 2026-07-09 subject-titled
"— 2026-06-01" (a pinned config date) and no sweep caught it. False-positive
guard: dates that reference an event, deadline, meeting, or period label
("Closing 2026-08-15", "June rent roll", "Week of July 13") are NOT
datelines — do not flag those.

**Outside A–I (always run, report separately, awareness-only unless directed
otherwise):**
- **Confidentiality Watch** — does the message discuss an active confidential
  deal's terms/status with an external party? Note the channel (e.g.
  privileged counsel correspondence is typically legitimate) and flag for
  awareness per invariant 3 — never silently pass over it.
- **Posture Note** — does the message disclose negotiating posture (available
  cash, urgency, deal status) to a broker/seller/counterparty ahead of price
  discussion? Flag as an observation; it's Gabriel's call, not a QC defect.

### B.4 DEFECT REPORT

```
ORA OUTBOX QC SWEEP — [YYYY-MM-DD]
Window: 00:00 -> [run time] ET
Messages sent: [n total]
External counterparty messages: [n filtered]

DEFECTS FOUND: [n]

[HIGH severity items first, then MEDIUM, then LOW. Each item:]

  [SEVERITY] [Time sent] | [Recipient(s)] | [Subject]
  Defect: [Check letter] - [description]
  Excerpt: "[offending text]"
  Recommended action: [None / Follow-up email needed / Pattern note for self-correction]

[Confidentiality Watch / Posture Note items, same format, outside A-H]

DEFECT-FREE MESSAGES: [n]

PATTERN OBSERVATIONS (week-rolling):
[Aggregate observations across past 7 days of Outbox QC pages in the Ops Hub.]
```

### B.5 DELIVERY
- Post the report to Notion Ops Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`)
  as a child page titled "Outbox QC — YYYY-MM-DD". Tags: qc, outbox,
  daily-sweep. Auto-archive after 30 days.
- Email summary — see GLOBAL § routing/send-path (TO ggoldberg@ ONLY, COM-only
  send). Subject: "ORA Outbox QC — [YYYY-MM-DD] — [n] defects ([h] HIGH / [m]
  MED / [l] LOW)". Body: full report, Notion link at top.
- If zero defects: send a single-line confirmation — "Outbox QC clean — [n]
  messages, no defects."

### B.6 CONSTRAINTS
- Read-only audit. Never modify, recall, resend, or alter sent emails.
- LP-flagged HIGH-severity messages additionally trigger a
  `notion-create-comment` on the LP Database record for the recipient,
  flagging that follow-up clarification may be advisable.
- Do NOT send corrective emails autonomously — the defect report surfaces
  issues; Gabriel decides on corrective action.

### B.7 ERROR HANDLING
- Outlook MCP error: log + note in the Block C coverage gaps; skip Notion if
  Notion is also unreachable, otherwise still post what's known.
- Notion MCP error: still deliver the email report; flag the Notion failure.
- Zero outbound messages today (e.g., Gabriel out of office): no-op with a
  single-line log entry, still post/send the zero-defect confirmation.

### B.8 DEPENDENCIES
- Outlook M365 connector · Notion MCP (LP Database for Check E; Ops Hub for
  posting) · ORA Voice Register v1.0+ (canonical Strike list).

---

## BLOCK C — EOD ACTION LEDGER (every day)

## C.0 PURPOSE
At end of each day, produce ONE report listing every manual item Gabriel is
supposed to complete, having already auto-resolved everything that can be
safely resolved without his input. The report is a ledger of: what was owed,
what Claude finished, what is staged for one-click approval, and what
genuinely requires Gabriel's hand.

This block is the day's CLOSING bracket to the morning brief/pre-triage. It
runs last within this task's single 18:00 fire, after Block A (Digest) and
Block B (Outbox QC, weekdays) so it can fold their outputs in.

## C.1 HARD GUARDRAILS — NON-NEGOTIABLE
This task runs unsupervised. It MUST NOT, under any circumstance:
- Send any outbound communication to a counterparty (tenant, broker, vendor,
  lender, counsel, LP, government). Drafts only — never SEND.
- Run `netlify deploy --prod` or any production deploy. Preview only.
- Move money, execute a trade, initiate a transfer, or post a journal entry
  to QuickBooks of record.
- Delete, overwrite, or mutate any system-of-record irreversibly.
- Modify the live ORA Master Workbook. Read-only against DSOR.
Anything crossing these lines is downgraded to TIER 3 (flag-only) and
packaged for Gabriel's approval. Never narrate around a guardrail.

## C.2 INVENTORY — THE CANONICAL UNIVERSE OF "ITEMS OWED"
Pull open, assigned-to-Gabriel, or unactioned items from ALL four source
classes. Dedupe by entity + due-date; collapse the same obligation appearing
in two systems into one ledger line.

A. Notion Ops Hub (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — open tasks/action
   items assigned to GG. Also read Knowledge Base follow-ups and any
   "Awaiting GG" flags. Fold in today's Block A digest and Block B outbox QC
   output (if it ran).
B. Operational pipelines —
   - Monthly Checklist (the 31-item close workbook) — items not ticked.
   - Lease-renewal pipeline — expirations <120d w/o renewal action.
   - Acquisition Pipeline (`bcfe4a03…`) + Deal Sourcing (`9a6ae219…`) — deals
     whose "Next Step" is past-due or owner = GG.
   - HubSpot (current tenants / deal stages, MCP — current-tenant scope only)
     — stage-stalled or owner=GG deals, and tenant follow-ups surfaced this day.
C. Outlook — flagged mail, unanswered inbound >24h old, and any morning
   pre-brief output surfaced for GG.
D. Automated scans — newest `exception-detection` anomalies and any
   `automation-health-monitor` missed-task findings from today.

Freshness guard: if a Notion mirror is >7d behind workbook
`lastModifiedDateTime`, read live; never present stale figures as current.
Do NOT fabricate any item. **Mandated-source discipline:** the Monthly
Checklist, lease-renewal pipeline, and HubSpot (source class B) MUST each be
attempted every run; if any is unreachable on the current surface, record it
by name as a COVERAGE GAP — never silently omit it (the 2026-07-09 run omitted
these without flagging; that is the failure this rule closes). Any other
unreachable source is likewise recorded as a COVERAGE GAP, not dropped.

## C.3 TRIAGE — CLASSIFY EVERY ITEM
For each inventoried item assign exactly one tier:

- **TIER 1 — AUTO-RESOLVE (reversible):** Claude completes it fully now. Code
  fix on a branch + preview deploy; corrected/recalculated workbook; Notion
  record update on a mirror/staging field; document/redline produced; data
  pulled and reconciled. Nothing outbound, prod, or money.
- **TIER 2 — DRAFT & STAGE:** the deliverable is finished but the final act
  is outbound/irreversible. Produce the artifact (email draft, signed
  redline, ready PSA edit) and stage it; do NOT fire it. Provide the exact
  one-step action Gabriel must take.
- **TIER 3 — FLAG ONLY:** judgment, negotiation posture, money, or production
  change that Claude must not pre-empt. State precisely what is needed and
  why it was not auto-resolved.

## C.4 RESOLUTION — ROUTING
For each TIER 1 / TIER 2 item, route to the narrowest capable executor.

### C.4a Operational / document / data items → Cowork in-session
Use the most specific ORA skill: re-operations, lease-renewal-pipeline,
rent-roll-qc, document-assembly, communication-intelligence,
tenant-intelligence, maintenance-analytics, tax-appeal, etc. Skill-specific
logic overrides global preferences. Produce the artifact to `/mnt/user-data/outputs`
and, where known, mirror to SharePoint.

### C.4b Code / website / repo items → Claude Code via Desktop Commander
For any oxfordra.net or codebase item ("debug", "fix", "build error",
"regression", "broken", "investigate code"), delegate to Claude Code running
on THIS machine (it has repo + credential access the sandbox does not):

`start_process` (invoke by FULL PATH — `claude` is NOT on the PATH in
non-interactive/scheduled sessions; the binary lives at
`C:\Users\Owner\.local\bin\claude.exe`):
```
& "C:\Users\Owner\.local\bin\claude.exe" -p "<scoped task>.
Investigate exhaustively, fix on a new branch, run checks,
preview-deploy only (--deploy, never --prod). Return root cause,
change, and preview URL." --output-format stream-json
```
Set cwd to the repo root; generous timeout; `read_process_output` to stream.
If the run needs file access, pass `--add-dir` for the repo.

Claude Code must exhaust investigation autonomously (multi-pass repair per
the `code-debugging-optimizations` skill) and stop at preview — never prod.

FALLBACK: if the `claude` CLI is absent, not authenticated, or errors, do the
investigation IN-SESSION using `code-debugging-optimizations` against the
repo via Desktop Commander, branch + preview only, and note in the report
that the Claude Code leg degraded to Cowork.

### C.4c Logging
Append every resolved/staged item to Notion Ops Hub (`32b6ecd8…`) as an
activity entry so the morning brief sees today's closure. Mirror field
only — never the live workbook.

## C.5 THE EOD ACTION LEDGER — REPORT
Assemble one report, ORA Institutional Style (Navy/Gold/Parchment; EB
Garamond / DM Sans / IBM Plex Mono). Structure:

1. Header — "ORA EOD Action Ledger — {Weekday, YYYY-MM-DD}", run time ET.
2. Scoreboard — counts: items owed, auto-resolved (T1), staged (T2), flagged
   (T3), coverage gaps. One line.
3. TIER 1 — RESOLVED: each item, what was done, link to artifact / branch /
   preview URL / Notion entry.
4. TIER 2 — STAGED FOR ONE-CLICK: each item, the finished artifact, and the
   single action Gabriel must take to execute.
5. TIER 3 — NEEDS GABRIEL: each item, what decision/authority is needed, and
   the recommended option with rationale.
6. COVERAGE GAPS: any source unreachable this run.
7. Session-hygiene footer: <=5 bullets of workflow optimizations spotted.

### C.5 DELIVERY
- Post the ledger to Notion Ops Hub as a child page ("EOD Action Ledger —
  YYYY-MM-DD") and email — see GLOBAL § routing/send-path (TO ggoldberg@
  ONLY, COM-only send. This corrects the original spec, which routed via the
  now-retired Composio connector and cc'd Eric).
- Persist the ledger as a Cowork artifact ("ORA EOD Action Ledger") so it is
  reopenable.

## C.6 QC GATE (run before send)
- Every ledger line traces to a real source item (no fabrication).
- No TIER 1/2 action breached a C.1 guardrail.
- All counterparty comms are DRAFTS, recipients unverified-flagged.
- Code changes are on a branch w/ preview URL, never prod.
- Dollar figures sourced + dated inline.
- Markup renders; links resolve. Then send.

## C.7 FAILURE HANDLING
If the run cannot complete (connector down, CLI failure), still send a
partial ledger with whatever resolved, list COVERAGE GAPS explicitly, and
flag the failure to Gabriel. Never present a partial run as complete. A
missed run is itself surfaced by `automation-health-monitor`.

---

## GLOBAL — SEND PATH, ROUTING, PYTHON (applies to ALL three blocks; overrides any conflicting per-block text above)

- **Routing (2026-05-15 directive, re-ratified 2026-06-10):** ALL THREE
  blocks' emails (Notion Digest, Outbox QC, EOD Action Ledger) → TO
  `ggoldberg@oxfordra.net` ONLY. No CC egoldberg@ — the sole surviving
  Eric-cc exception firm-wide is the `ora-am-brief` Daily Brief. Counterparty
  mail (never sent by this task — draft-only) follows its own class routing
  under the Voice Register. Never ze@.
- **Send path (SOLE path — no fallback connector exists):** Outlook COM via
  `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1`.
  The Composio fallback referenced in the original archived block specs was
  removed 2026-06-11 (connector gone) — do not attempt it, do not reference
  Rube (shut down). On a non-zero exit from the script: it already performs
  one bounded internal retry on `RPC_E_CALL_REJECTED` (HRESULT 0x80010001);
  at the task level, do not retry beyond that — flag loudly (a note in the
  block's own Notion page + carry the failure forward into Block C's
  COVERAGE GAPS if C runs after) and continue to the next block. Do NOT
  halt the whole task on one block's send failure.
  - Exit codes: 0 = sent · 1 = usage error · 2 = COM failure (retry
    exhausted) · 3 = Outlook stuck on a startup/profile wizard (human must
    dismiss — do not attempt to work around this programmatically) · 4 = COM
    call timed out (>15s).
- **Fallback persistence (all three blocks, on any send failure):** write the
  block's HTML body to
  `C:\Users\Owner\OneDrive - Oxford Capital Partners\ORA\Briefs\outputs\{TODAY}_<block>.html`
  — filenames used in practice: `{TODAY}_notion-daily-digest.html`,
  `{TODAY}_outbox-qc.html`, `{TODAY}_eod-action-ledger.html`. **Use this
  exact no-`"(1)"`-suffix OneDrive path** — the parallel folder
  `OneDrive - Oxford Capital Partners (1)` referenced in the original
  archived Block A spec is a duplicate-sync artifact, not the canonical
  location. The Notion page for each block is the primary durable copy
  regardless of email outcome; the HTML file is the secondary fallback.
- **Python:** use the FULL path
  `C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe` for any
  python invocation — `python`/`python3` are not reliably on PATH in
  non-interactive/scheduled sessions.
- **Guardrails (all blocks):** do NOT modify `settings.json`, `~/.claude`
  config, hooks, or memory files. Never touch oxfordra.net. Block C's C.1 is
  the binding hard-guardrail list for its own auto-resolve authority; Blocks
  A and B are read/report-only and carry no resolution authority at all.

---

## RESTORATION NOTE (2026-07-08)

The consolidated `ora-pm-ledger` spec this file replaces was destroyed by the
2026-07-05 app reinstall/registry loss and, despite a 2026-07-07 pointer
claiming an "intact OneDrive spec," the file did not actually exist at this
path — both the `.claude\scheduled-tasks\ora-pm-ledger\SKILL.md` pointer and
this OneDrive location were empty/missing as of the 2026-07-07 evening run,
which operated instead directly off the three separately-archived block
specs in `_archive_2026-06-11_orphans\` (`ora-notion-daily-digest`,
`ora-outbox-qc-sweep`, `ora-eod-action-ledger`).

This file is a full reconstruction from those three archived originals,
merged into one consolidated spec and corrected against current ORA canon:
- Recipients unified to ggoldberg@-only across all three blocks (originals
  variously cc'd egoldberg@, which was rescinded 2026-05-15 / re-ratified
  2026-06-10).
- Send path unified to Outlook COM only; all Composio references removed
  (connector retired 2026-06-11).
- Fallback file paths corrected to the no-`"(1)"`-suffix OneDrive location.
- Python invocations pinned to the full interpreter path.
- Cadence collapsed from three separate historical cadences (17:00 / 17:30 /
  19:00) to the single live registry cadence, `0 18 * * *`.

**Not independently re-verified in this restoration:** the Notion database
IDs in Block A §A.1 (Broker Relationships, Property Register, CapEx &
Maintenance Log) are carried forward from the archived original as-is. If a
future run hits errors against these, treat it as a stale-ID problem to fix,
not a connector outage.

**RESOLVED 2026-07-09:** the §A.4 dashboard data path
(`C:\Users\Owner\oxford-perfection\ora-dashboard\data\`) was found archived
2026-07-07 and 17+ days stale; §A.4 has been repointed to the live
oxford-command-center alerts engine / Command Center Daily Brief, with insurance
verifiable directly from `oxford-command-center\data\warehouse\finance.sqlite`.
The retired JSON dashboard is explicitly forbidden as a source.

## RESTORATION NOTE 2 (2026-07-08, later same day)

The CC/MCP canonical file at this path (`~/.claude/scheduled-tasks/ora-pm-ledger/SKILL.md`)
had been reduced back to a thin pointer-stub redirecting to the OneDrive
location described above, which was itself found archived to
`Documents\Claude\Scheduled\_archive_2026-07-08_retired\ora-pm-ledger\SKILL.md`
during a systemic check of all CC/MCP tasks for the same fragile pattern that
had already broken `ora-master-workbook-ingest` and `ora-health-guard` the
same day. This file restores the full content above verbatim from that
archived copy and inlines it here to eliminate the redirect entirely — the
same fix applied to `ora-master-workbook-ingest` and `ora-weekly-hygiene`.
Do not reintroduce a pointer to an external spec file for this task. Task was
`enabled: false` in the CC registry pending Gabriel's confirmation — see
RE-ENABLE NOTE below.

## RE-ENABLE NOTE (2026-07-09)

Gabriel confirmed re-enabling this task effective 2026-07-09 (post-recovery-
stabilization). Re-enabled via the supervised `update_scheduled_task` MCP
tool (no registry JSON edited directly) — verified live via
`list_scheduled_tasks`: `enabled: true`, next fire 2026-07-09 ~18:00 ET. This
supersedes the "re-enable only per Gabriel's direction" hold noted above.
## AMENDMENT NOTE (2026-07-09, evening — setup-audit remediation Task 9b)

Block B gained **Check I — Frozen-Date Subject** (subject dateline differing
from send date by >1 day = MEDIUM; report-style subjects and trailing
"— YYYY-MM-DD" suffixes only; event/deadline/period dates exempt; internal +
automated sends INCLUDED for this check). Would have caught the frozen-date
Command Center Daily Brief on 2026-07-08. The "Outside A–H" section header
became "Outside A–I". No other block logic changed; registration untouched
(content-only edit per the LAMS/CC single-writer rule).
