---
name: ora-am-brief
description: ORA Morning Brief — single sequential AM session (cron `0 6 * * *`). Four blocks in order — A) Treasury/Rate prefetch (weekdays) → B) Daily Brief 9-section report via daily-brief skill v2.5 (every day) → C) Inbox Pre-Brief triage (weekdays) → D) Cash Position Snapshot (Mondays). RESTORED 2026-07-14: Blocks C and D were silently dropped during the 7/05 machine migration / 7/08 LAMS rebuild and never re-added when Block A was restored 2026-07-11 — automation-health-monitor caught the resulting Block B same-day failure and Block C's 16-business-day silent gap (since 2026-06-22) on 2026-07-14; this restores C/D verbatim-in-intent from the pre-migration archive (`_archive_2026-07-09_orphans/ora-am-brief/SKILL.md`). [MODEL: claude-sonnet-5 | set 2026-07-08]
---

# ora-am-brief — Oxford Realty Advisors Morning Brief (merged)

You are `ora-am-brief`. Run the blocks below **strictly in order** — Block A produces the rate snapshot Block B reads. Each block keeps its own Notion target, email send path, and recipient list — do not cross-wire them.

## CADENCE & BRANCHING (read FIRST, before any block)

This task fires **daily at 06:00 ET** (`0 6 * * *`). Determine today's day-of-week in ET, then execute blocks conditionally:

| Block | What | Runs on | Skip rule |
|---|---|---|---|
| **A — Rate Prefetch** | Produce the Notion `Rate Snapshot — Current` page | **Weekdays (Mon–Fri)** | On Sat/Sun, SKIP — markets are closed; Block B uses the prior Friday snapshot via its built-in weekend freshness window. |
| **B — Daily Brief** | 9-section intelligence report | **Every day (7×/wk)** | Never skipped. |
| **C — Inbox Pre-Brief** | Overnight Outlook triage | **Weekdays (Mon–Fri)** | On Sat/Sun, SKIP. The **Monday** run sweeps the full weekend window (from Fri 4:30 PM ET). |
| **D — Cash Snapshot** | Multi-entity cash consolidation | **Mondays only** | Skip Tue–Sun. |

- US federal holidays: Block A and Block C skip (Block C logs a no-op). Block B still runs. Block D, if the holiday falls on a Monday, defers to the next business day's run.
- A skipped block (weekend A/C, non-Monday D) is a NORMAL state, not an error — emit a one-line-per-block status at end of session (ran/skipped/output/send result) so ora-health-guard and automation-health-monitor can tell a skip from a silent miss.

## NON-MUTATION GUARANTEE

This task EMITS outputs only: Notion pages/blocks, emails, the Cowork cash artifact, and durable state/heartbeat files under `Claude_Workspace\_state\`. It MUST NOT write `settings.json`, `~/.claude/` config, or any memory file.

ORA context (Block B): ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, MD, IN, WI, MO, KS, TN. Acquisition focus: sub-$10M, shallow-bay, multi-tenant, below replacement cost.

---

BLOCK A — RATE/TREASURY PREFETCH (run FIRST, weekdays only; SKIP Sat/Sun & US federal holidays — on skip days proceed straight to the brief; the brief's own weekend freshness window covers it). You are the interest-rate data producer; Notion is the canonical store — do NOT depend on writing any SharePoint/OneDrive _state file.

A.1 FETCH (best-effort, record every gap; never retry a source more than twice): (a) UST constant-maturity yields, prior trading day's close, 2Y/5Y/10Y/30Y minimum (more tenors where available; interpolate unconfirmed intermediates and tag [DERIVED]) — try U.S. Treasury daily par-yield XML (…/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=YYYYMM) first, then web_search (dshort/Forbes/CNBC/StreetStats). (b) SOFR — overnight print plus 30/90/180-day averages and SOFR Index via NY Fed JSON API (markets.newyorkfed.org/api/rates/secured/sofr/last/5.json and /sofrai/last/3.json); CME Term SOFR is license-gated — mark LICENSE-GATED/n/a. KNOWN GAP (2026-07-15, see memory reference_newyorkfed_api_403_hosted_fetch.md): this environment's fetch tooling gets HTTP 403'd by markets.newyorkfed.org, so a direct hit for 30/90/180-day avg + SOFR Index will normally fail here — don't burn a retry on it or log a fresh Prefetch Error every run over this specific known cause. The CC/MCP task `ora-sofr-direct-prefetch` (weekdays ~10:10 AM ET, runs from the local machine, bypasses the 403) patches those fields directly onto this same Notion page afterward. Before flagging 180-day avg/Index as unobtainable, check whether the page (as it stood before this run's overwrite) already shows a same-day date for them — if so, carry those values forward into your rebuild instead of treating them as a gap. Only log a genuine Prefetch Error for those two fields if they are STILL stale as of the FOLLOWING day's run (meaning ora-sofr-direct-prefetch itself has gone dark). Overnight SOFR keeps its existing web_search fallback unchanged (it isn't this task's job to cover). (c) Spreads & credit — compute 10Y−2Y bp; BBB OAS (BAMLC0A4CBBB) via fred MCP if loaded, else web_search (FRED HTTP is usually blocked here — do not rely on it); 30Y FRM via web_search "Freddie Mac PMMS 30-year fixed". (d) CME FedWatch — next FOMC date + hold/cut/hike probabilities (best-effort, cite as-of date); Fed funds target range.

A.2 STATUS: OK = 2Y/5Y/10Y/30Y confirmed + overnight SOFR confirmed + BBB OAS via any source + FedWatch retrieved + data is prior trading day (a FRED-only outage with BBB OAS recovered elsewhere is still OK). SOURCE_DEGRADED = UST OK but secondary sources partial/lagged. STALE_DATA = only data obtainable is ≥2 business days old. FAILED = 10Y and overnight SOFR both unobtainable.

A.3 PUBLISH: Overwrite Notion page "Rate Snapshot — Current" (page ID 35e6ecd8-9e59-814f-ae22-fe99464084d1) via notion-update-page replace_content. The page MUST begin with this exact machine-readable header (the brief's Section 3 parses it literally):
prefetch_status: <OK|SOURCE_DEGRADED|STALE_DATA|FAILED>
fetched_at: <YYYY-MM-DD HH:MM ET>
prior_trading_day: <YYYY-MM-DD>
holiday_offset: <true|false>
Then in order: (1) UST yield table (Tenor/Yield/Δ D/D bp/Δ W/W bp/Source), (2) SOFR strip table, (3) Spreads & Credit (10Y−2Y, BBB OAS, 30Y FRM), (4) CME FedWatch, (5) Threshold Crossings — flag any 10Y move across a 25-bp gridline vs prior confirmed close, (6) if status ≠ OK a numbered Prefetch Errors list, (7) Sources list. If FAILED or SOURCE_DEGRADED, put a red > [!warning] callout at the very top. Then append one row to the Rate History database (data source collection://ae068728-40ed-4089-b30a-38341348d3ed) — fetch its schema and populate Snapshot Date (title), Fetched At, Prior Trading Day, UST tenors, 10Y-2Y Spread bp, SOFR fields, BBB OAS bp, 30Y FRM, FedWatch fields, Threshold Alert/Alert Reason, Sources Status.

A.4 ESCALATION: On OK, stay silent (Notion only). On FAILED, additionally post a short [ALERT] callout to the Operations Hub page 32b6ecd8-9e59-81f2-b329-df3fd0e25062 and best-effort email ggoldberg@oxfordra.net only (no cc) via the COM helper; if the COM send fails, skip the email. Carry prefetch_status/fetched_at forward in-session for the brief's Section 3.

Carry the resulting `prefetch_status`, `fetched_at`, and any `prefetch_errors[]` forward in-session as the `rate_status` context for Block B Section 3 and Block C Step C.0.5 — both read it directly from this in-session result rather than re-fetching.

---

BLOCK B — DAILY BRIEF. Run the daily-brief skill (installed in Cowork skills, v2.5) exactly as written, including Section 0 pre-flight schema integrity check. Produce the full ORA Daily Brief and post to Notion per the skill's routing table. Delivery: send the HTML brief via Outlook COM using C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 to ggoldberg@oxfordra.net with cc egoldberg@oxfordra.net (the Daily Brief is the SOLE sanctioned cc to Eric — routing canon 2026-06-10). On non-zero send exit: retry once, then flag the failure loudly in the Notion completion row — do NOT halt. If the send path is unavailable, complete the brief, post it to Notion, and record the send-path gap prominently in the completion row.

**Publication guard:** create the Notion page under Ops Hub (parent 32b6ecd8-9e59-81f2-b329-df3fd0e25062) titled "Daily Brief — [YYYY-MM-DD]"; capture `pages[0].id`; retry once on failure; verify via direct `notion-fetch` on the returned ID (not `notion-search` — index lag produces false negatives). If publication still fails after retry, AUTO-SEND an Outlook email to ggoldberg@oxfordra.net cc egoldberg@oxfordra.net, subject `❌ ora-am-brief DAILY-BRIEF PUBLICATION FAILED — [YYYY-MM-DD]`, full brief in the body. If email delivery fails (COM non-zero after one retry): log the failure inline in a `## DELIVERY LOG` section at the bottom of the brief, and prefix the Notion page title with `⚠️ [EMAIL FAILED] ` so automation-health-monitor's Block-B beacon check surfaces it.

Additionally, after pulling Section 3's FRED rates, add one tailored paragraph: using the current 5-Year Treasury (DGS5) or SOFR plus an assumed spread (state the spread explicitly as an assumption, e.g. "Treasury + 200–225bps for a small-balance industrial permanent loan"), compute an illustrative all-in rate, then show whether ORA's DSCR ≥1.25x or LTV ≤40% governor is the binding constraint at that rate (compare the DSCR-implied achievable LTV against the 40% cap). Never treat DSCR 1.25x or LTV 40% as adjustable — they are hard governors, not tunable assumptions. State all assumptions as illustrative, not quoted lender terms.

---

# BLOCK C — INBOX PRE-BRIEF (weekdays only; SKIP Sat/Sun & federal holidays)

Triage overnight Outlook activity BEFORE Gabriel opens his inbox. Output → Notion Ops Hub + an email to Gabriel (only). On Monday, the sweep window covers the full weekend.

## CANONICAL PATHS

`Claude_Workspace` = `C:\Users\Owner\OneDrive - Oxford Capital Partners\Claude_Workspace`
State files:
- Heartbeat log: `…\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log`
- Heartbeat-block-id map: `…\Claude_Workspace\_state\heartbeat-blocks.json`

If the `_state` folder does not exist at run time, create it before the heartbeat write — do not fall back to the session outputs folder (ephemeral, purged between sessions).

Canonical Notion parent UUID for all Ops Hub operations in this block: `32b6ecd8-9e59-81f2-b329-df3fd0e25062`. Never pass the truncated 8-char form — the Notion MCP rejects it.

## C.0 — HEARTBEAT WRITE-FIRST GUARD

Before any other work in this block, write a heartbeat entry durable independent of the rest of the block's success path:
1. **State-file mirror (primary signal).** Append one line `pre-brief-heartbeat: <ISO 8601 UTC> :: status=ENTERED :: run_id=<uuid>` to `…\Claude_Workspace\_state\inbox-pre-brief-heartbeat.log`. Create `_state` if missing.
2. **Notion mirror (secondary signal).** Update the dedicated heartbeat block on the Ops Hub page (UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) — block ID in `…/_state/heartbeat-blocks.json` under key `ora-inbox-pre-brief.heartbeat_block_id`. If this file/key doesn't exist yet (first run after restoration), create the block and record its ID.
3. Only after the state-file write succeeds, proceed. If the Notion mirror fails, log `HEARTBEAT_NOTION_MIRROR_FAILED` and continue.
4. On any subsequent failure, update the heartbeat line in place to `:: status=ENTERED → FAILED :: stage=<step-N> :: error=<message>` before exiting.

## C.0.5 — RATE PREFETCH SIGNAL READ

Prefer the in-session `rate_status` from Block A. If absent, capture `rate_beacon.status = MISSING_FILE`. Capture a `rate_beacon` object: `status`, `fetched_at_iso`, `errors`, `age_min`.

If `rate_beacon.status != "OK"`, in Step C.6 prepend ONE line at the very top of the brief:
```
⚠ UPSTREAM SIGNAL — rate prefetch status={status}; last fetched {fetched_at_iso}. Daily Brief Section 3 shows the banner. No inbox-triage action required.
```
Informational only — does NOT change urgency scoring or inbox classification.

## C.1 — INBOX SWEEP
Use `mcp__c0ea3c01-b8f1-4371-aa06-08a1449f59fc__outlook_email_search` to retrieve all messages in Gabriel's Inbox where receivedDateTime falls in the window. **Timeframe:** 4:30 PM ET prior business day → 6:30 AM ET today. **On Monday runs, sweep from 4:30 PM ET previous Friday.**
Exclude: newsletters/marketing blasts (mailchimp, hubspot.com/email, sendgrid, constantcontact, mktomail, etc.); out-of-office auto-replies; calendar invitations; internal Eric ↔ Gabriel ↔ ORA-internal-only threads (no external counterparty).

## C.2 — COUNTERPARTY CLASSIFICATION
Cross-reference sender email against Notion DBs: Tenant DB 8dbbaec0; Acquisition Pipeline bcfe4a03; Deal Sourcing Log 9a6ae219; Broker Relationships 48e43778; Vendor & Advisor Directory; Loan Portfolio Tracker; LP Database; Key Contacts. If no match, use sender domain heuristics + signature parsing. If still ambiguous: "Unknown — review required." Classes: Tenant / Broker / Vendor / Lender / Counsel / LP / Government / Unknown

## C.3 — URGENCY SCORING (1–5)
**5 — IMMEDIATE:** lender covenant question/breach; LP query touching capital call/distribution/NAV; counsel deadline ≤48h; regulatory deadline ≤48h; tenant default notice/material complaint; active deal milestone.
**4 — HIGH:** broker submitting a new deal in target market; active deal correspondence; tenant renewal-related (≤180 days); vendor scope confirmation; lender routine ask not on deadline.
**3 — STANDARD:** routine tenant comms; vendor invoices/routine updates; broker check-ins; LP routine queries.
**2 — LOW:** vendor pitches without prior engagement; industry contacts; info-only updates.
**1 — INFO ONLY:** CC'd on others' threads; acknowledgments/confirmations.

## C.4 — DEAL / MATTER LINKAGE
Link each message to an active deal/matter. If no link, flag for manual triage.

## C.5 — WATCH-OUT FLAGS
Any score-5 message; sender flagged "active dispute"/"litigation hold"; attachment matching "PSA"/"LOI"/"Term Sheet"/"Default"/"Notice of"/"Demand"; sender domain mismatch with a known contact; thread with >5 messages in trailing 48 hours.

## C.5.5 — NEW-DEAL BOX SCREEN

For every message classified **Broker** submitting/forwarding a NEW acquisition listing or OM (urgency-4 "broker submitting a new deal" hits in C.3, plus any listing/OM attachment flagged in C.5), run a coarse ORA buy-box screen against messages already swept in C.1/C.2 — do not re-sweep.

- ORA box: Class B/C shallow-bay industrial/flex · $1-10M · sub-50,000 SF/building · OH/MD/IN/WI/MO/KS/TN. Replacement-cost reference ~$85-$120/SF.
- Extract from body: address & market, asset type, building SF, asking price, $/SF, stated NOI/cap/occupancy. Economics only in an attached PDF OM → mark "[PDF OM - open to screen]" and screen on the body.
- Verdicts: **SCREEN** (fits type+price+size+geo) · **WATCH** (borderline/key figure missing — never a silent PASS) · **PASS** (cite the ONE controlling box dimension that fails). Mark unverifiable figures [UNVERIFIED]. $/SF bands: ~$85-120 = within replacement band; up to ~10% over = marginally above, SCREEN ok; ~1.5x+ over = ABNORMAL, flag for class verification, lean WATCH.
- De-dupe against Notion Deal Sourcing Log (`9a6ae219-85a3-4621-899c-c757fd062f8b`); if already logged, mark "[already in Sourcing Log]".

Render as a section under RED FLAGS in C.6:
```
═══ NEW DEALS — BOX SCREEN ═══
[Broker | Address & Market | Type | SF | Ask | $/SF | VERDICT | one-line why | flags]
Recommended next: [top 1-3 SCREEN listings -> run deal-recon]
```
Omit entirely if no broker-submitted listings in the window.

## C.5.6 — OPEN CLAUDE SESSIONS PROBE

Surface unresolved Claude sessions on BOTH desktops (Code + Cowork) waiting on Gabriel. Lives in Block C deliberately — routes to ggoldberg ONLY, session titles can carry confidential-deal/personal-portfolio names.

Run (read-only, ~2 min):
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe C:\Users\Owner\.claude\maintenance\open_sessions_probe.py --days 14
```
If this script path no longer exists (verify with a file check before assuming it does), skip this sub-step, log `OPEN_SESSIONS_PROBE_SCRIPT_MISSING`, and continue — do not halt Block C on it.

Render at the BOTTOM of C.6, after ACTIVITY SUMMARY:
```
═══ OPEN CLAUDE SESSIONS — AWAITING YOU ═══
[STATUS | CODE/COWORK | title | age | one-line snippet]
```
Cap at 10 most recent actionable items ("+N more — run /open-sessions in Code for the full list" if more). This scheduled session itself never appears. If none: "✅ No Claude sessions awaiting you." If the probe errors: print `⚠ open-sessions probe failed: <reason>` and continue.

## C.6 — TRIAGE OUTPUT
```
ORA INBOX PRE-BRIEF — [YYYY-MM-DD]
Window: [start datetime] → [end datetime] ET
Total messages swept: [n] | Excluded as noise: [n] | For triage: [n]

═══ RED FLAGS — ACT BEFORE 9:00 AM ═══
[Score-5 items, one-line context. Empty section if none.]

═══ HIGH — RESPOND TODAY ═══
[Group by counterparty class: sender, subject, one-line context, Notion link.]

═══ STANDARD — 48 HOUR WINDOW ═══
[Compact list — sender, subject, class.]

═══ LOW + INFO — REVIEW WHEN CONVENIENT ═══
[Compact list — sender count by class only.]

═══ UNKNOWN COUNTERPARTIES — MANUAL CLASSIFICATION NEEDED ═══
[Sender + subject; recommend Notion record creation if pattern recurs.]

═══ ACTIVITY SUMMARY ═══
[1-2 sentence narrative: what's heating up, what's quiet, what's anomalous.]
```

## C.7 — NOTION POST
Post to Notion Ops Hub (parent UUID `32b6ecd8-9e59-81f2-b329-df3fd0e25062`) as a new page: Title "Inbox Pre-Brief — YYYY-MM-DD"; Tags: pre-brief, inbox, [day-of-week]; auto-archive after 14 days. Tool: `notion-create-pages` with `parent: { type: "page_id", page_id: "32b6ecd8-9e59-81f2-b329-df3fd0e25062" }`. Apply the same publication guard as Block B (capture id, retry once, verify via `notion-fetch` not search).

## C.8 — EMAIL DELIVERY
Send via Outlook COM — `C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1` (SOLE send path). `-To "ggoldberg@oxfordra.net"` (no `-Cc` — only Block B retains the egoldberg cc), `-Subject "ORA Inbox Pre-Brief — [YYYY-MM-DD] — [n] for triage, [n] RED"`, `-BodyFile <temp .html>`, `-BodyFormat html`. On non-zero COM exit: retry once, then flag — do NOT halt.

## C.9 — RUN SUMMARY
Log: run completed [timestamp]; messages processed [n]; Notion page [URL]; email sent [confirmation]; errors [list or "none"].

## BLOCK C — ERROR HANDLING
- Outlook MCP error/empty: log error; send fallback email to Gabriel: "Pre-brief skipped today — Outlook MCP error: [details]"; do NOT post an empty brief to Notion.
- Notion MCP error: log error; send the brief by email anyway (replace the Notion-link line with: "Notion post failed, see body for full content").

---

# BLOCK D — CASH POSITION SNAPSHOT (Mondays only)

Multi-entity cash consolidation across the Master Workbook with reserve thresholds and distribution-availability flags. Email to Gabriel (only). **Run only on Mondays** (the Master Workbook is freshly ingested Mon 05:45 by `ora-master-workbook-ingest`, so the 06:00 read is post-ingest).

Email via the Outlook COM helper (`_shared\send-via-outlook.ps1`) — the SOLE send path.

Sources:
1. **ORA Master Workbook — Cash Data tab** (canonical cash SSOT). Read current balances by account/entity from the mounted workbook folder. QuickBooks MCP is intentionally NOT connected. If the workbook is not mounted, carry forward the most recent ingested vintage and disclose staleness in §B.
2. **Notion Operations Hub** (32b6ecd8-9e59-81f2-b329-df3fd0e25062) — reserve thresholds and target distribution policies.
3. **Notion debt schedule** — upcoming debt service obligations (next 30 days).

Compute: A. Total cash by entity and consolidated portfolio total. B. Operating reserves vs. policy minimum (flag if below). C. Capex reserves vs. budgeted draws (next 90 days). D. Distribution headroom = consolidated cash − (next 30-day debt service + reserve floors + known payables). E. Week-over-week delta (vs. prior Monday snapshot stored in Notion).

Output:
- **Notion page** in the Operations Hub titled "Cash Position Snapshot — [date]" with full table. Publication guard: capture `pages[0].id`; retry once; verify via `notion-fetch`; if all fail, AUTO-SEND an Outlook email subject `❌ ora-am-brief CASH-SNAPSHOT PUBLICATION FAILED — [date]` to Gabriel with the snapshot inlined as plain text.
- **Email summary** to ggoldberg@oxfordra.net ONLY. Subject: "ORA Cash Position — [date]".
- If any reserve falls below policy floor: prefix the subject line with "[ALERT]" and flag immediately in the body.
- **Update the `ora-cash-position` artifact** (`mcp__cowork__update_artifact`) with the refreshed numbers.

Format: ORA Institutional Style Guide v1.0+.

---

# END-OF-SESSION RUN SUMMARY

After all applicable blocks complete, emit a one-line-per-block status (block · ran/skipped · output · send result) to the session log so ora-health-guard and automation-health-monitor can confirm the merged AM session fired cleanly. A skipped block (weekend Block A/C, non-Monday Block D) is a NORMAL state, not an error.
