---
name: ora-am-brief
description: ORA Morning Brief — single sequential AM session (cron `0 6 * * *`). Four blocks in order — A) Treasury/Rate prefetch (weekdays) -> B) Daily Brief 9-section report via the installed daily-brief skill (every day) -> C) Inbox Pre-Brief triage (weekdays) -> D) Cash Position Snapshot (Mondays). MIGRATED to CC/MCP 2026-07-16 (Gabriel-directed): the LAMS/Cowork sandbox has no local COM access, so the email leg on this task structurally could not send (confirmed: no send for the 2026-07-16 edition despite 7/13-7/15 sending fine) — this fleet has proven COM sends today via the same `send-via-outlook.ps1` path (ora-pm-ledger, automation-health-monitor, Command Center Daily Brief all sent clean). Content carried over verbatim from the LAMS spec with three CC/MCP-surface adaptations: (1) Block B's critical-dates sub-section now cites the Command Center alerts engine as authoritative rather than independently deriving lease/debt dates from a live Notion read (Gabriel-ratified 2026-07-16, closing the recurring two-briefs-disagree defect); (2) Block D drops the Cowork-only `mcp__cowork__update_artifact` step and reads the Master Workbook directly at its confirmed local path; (3) NON-MUTATION GUARANTEE's output list drops "the Cowork cash artifact." The superseded LAMS registration is being retired separately. [MODEL: claude-sonnet-5 | set 2026-07-16]
output_contract:
  version: 1
  blocks:
    - id: block-a-rate-prefetch
      artifact:
        type: notion_page
        page_id: 35e6ecd8-9e59-814f-ae22-fe99464084d1
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon, Tue, Wed, Thu, Fri]
      on_missing_severity: warn
      is_primary_health_signal: false
      notes: "Fixed overwrite page 'Rate Snapshot — Current' (STEP A.3); page_id verified against SKILL.md body text. Freshness proxy for prefetch_status/fetched_at header, not a parsed read of it."
    - id: block-b-daily-brief
      artifact:
        type: notion_page
        title_pattern: "Daily Brief — {DATE}"
        parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 26
      min_count: 1
      count_semantics: at_least
      expected_on:
        always: true
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Primary signal for the whole task — Block B runs every day, no branching. A page title prefixed ⚠️/🗑️/[DUPLICATE] still counts as 'present' under this contract's existence check; that content-quality distinction is the existing Step 0.55 beacon's job, not this block's."
    - id: block-c-inbox-pre-brief
      artifact:
        type: notion_page
        title_pattern: "Inbox Pre-Brief — {DATE}"
        parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon, Tue, Wed, Thu, Fri]
      on_missing_severity: warn
      is_primary_health_signal: false
    - id: block-d-cash-snapshot
      artifact:
        type: notion_page
        title_pattern: "Cash Position Snapshot — {DATE}"
        parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon]
      on_missing_severity: warn
      is_primary_health_signal: false
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

This task EMITS outputs only: Notion pages/blocks, emails, and durable state/heartbeat files under `Claude_Workspace\_state\`. It MUST NOT write `settings.json`, `~/.claude/` config, or any memory file.

ORA context (Block B): ~600K SF shallow-bay industrial/flex, ~140 tenants, ~27 properties across OH, MD, IN, WI, MO, KS, TN. Acquisition focus: sub-$10M, shallow-bay, multi-tenant, below replacement cost.

---

BLOCK A — RATE/TREASURY PREFETCH (run FIRST, weekdays only; SKIP Sat/Sun & US federal holidays — on skip days proceed straight to the brief; the brief's own weekend freshness window covers it). You are the interest-rate data producer; Notion is the canonical store — do NOT depend on writing any SharePoint/OneDrive _state file.

A.1 FETCH (best-effort, record every gap; never retry a source more than twice): (a) UST constant-maturity yields, prior trading day's close, 2Y/5Y/10Y/30Y minimum (more tenors where available; interpolate unconfirmed intermediates and tag [DERIVED]) — try U.S. Treasury daily par-yield XML (…/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=YYYYMM) first, then web_search (dshort/Forbes/CNBC/StreetStats). (b) SOFR — overnight print plus 30/90/180-day averages and SOFR Index via NY Fed JSON API (markets.newyorkfed.org/api/rates/secured/sofr/last/5.json and /sofrai/last/3.json); CME Term SOFR is license-gated — mark LICENSE-GATED/n/a. This CC/MCP surface reaches the NY Fed API directly (no 403 — that gap was specific to the Cowork hosted-fetch tooling), so this run should obtain these fields itself rather than relying on `ora-sofr-direct-prefetch`'s later patch — but do NOT characterize that task's later run as a no-op. **PUBLICATION WINDOW (verified 2026-07-24 — this drives everything below).** The NY Fed publishes overnight SOFR at **approximately 8:00 a.m. ET**, and the SOFR Averages and Index "shortly after" it (Federal Reserve Bank of New York, *Additional Information About Reference Rates*). This task fires at **06:00 ET — two hours BEFORE publication.** So on an on-schedule run the newest data that EXISTS is overnight SOFR only through **D−2** (D−1's print lands ~08:00 on D) and SOFR Averages/Index only through **D−1**. Confirmed against the Rate History log: the 2026-07-16 run, fetched at exactly 06:00 ET, carried the 07-15 SOFRAI print and the 07-14 overnight rate (3.63 — 07-15's actual print was 3.64), whereas the 07-24 run at 10:40 ET, after publication, carried the same-day 07-24 print. Consequently `ora-sofr-direct-prefetch` (weekdays ~10:10 AM ET, i.e. after the publication window) typically advances the 30/90/180-day average and Index rows to a genuinely newer effective date — a substantive refresh, not a confirmation (and not a required dependency in either direction). It is a confirmation ONLY on catch-up-burst days when THIS run fires after ~10:10 ET and has actually compared the values. **Never write a forward-looking claim about that task into the page** — the 2026-07-21 run published "`ora-sofr-direct-prefetch` … is a no-op confirmation this run — all SOFR fields already obtained here" while itself carrying 07-20 averages, which the 10:10 task then correctly advanced to the 07-21 print. State a match only retrospectively, and only when this run actually observed it. **SOFR ROW LABELING (hard rule).** Every SOFR strip row must carry the `effectiveDate` the API returned for THAT row — never a date inferred from `prior_trading_day`, never one carried across rows. The header's `prior_trading_day` anchors the **UST close only**; UST and SOFR publish on different latencies, so on an on-schedule 06:00 run the SOFR strip legitimately sits one business day behind that header. That lag is EXPECTED: state it plainly in the row notes, do NOT let it alone set SOURCE_DEGRADED, and do NOT paper over it — it is exactly what the 10:10 task closes. The 2026-07-16 06:00 run printed `prior_trading_day: 2026-07-15` while its SOFR Spot row held the 07-14 rate; a figure printed under a header date it does not belong to is a labeling fabrication, not a rounding detail. (c) Spreads & credit — compute 10Y−2Y bp; BBB OAS (BAMLC0A4CBBB) via fred MCP if loaded, else web_search (FRED HTTP is usually blocked here — do not rely on it); 30Y FRM via web_search "Freddie Mac PMMS 30-year fixed". (d) CME FedWatch — next FOMC date + hold/cut/hike probabilities (best-effort, cite as-of date); Fed funds target range.

A.2 STATUS: OK = 2Y/5Y/10Y/30Y confirmed + overnight SOFR confirmed + BBB OAS via any source + FedWatch retrieved + data is prior trading day (a FRED-only outage with BBB OAS recovered elsewhere is still OK). SOURCE_DEGRADED = UST OK but secondary sources partial/lagged. STALE_DATA = only data obtainable is ≥2 business days old. FAILED = 10Y and overnight SOFR both unobtainable.

A.3 PUBLISH: Overwrite Notion page "Rate Snapshot — Current" (page ID 35e6ecd8-9e59-814f-ae22-fe99464084d1) via notion-update-page replace_content. The page MUST begin with this exact machine-readable header (the brief's Section 3 parses it literally):
prefetch_status: <OK|SOURCE_DEGRADED|STALE_DATA|FAILED>
fetched_at: <YYYY-MM-DD HH:MM ET>
prior_trading_day: <YYYY-MM-DD>
holiday_offset: <true|false>
Then in order: (1) UST yield table (Tenor/Yield/Δ D/D bp/Δ W/W bp/Source), (2) SOFR strip table, (3) Spreads & Credit (10Y−2Y, BBB OAS, 30Y FRM), (4) CME FedWatch, (5) Threshold Crossings — flag any 10Y move across a 25-bp gridline vs prior confirmed close, (6) if status ≠ OK a numbered Prefetch Errors list, (7) Sources list. If FAILED or SOURCE_DEGRADED, put a red > [!warning] callout at the very top. CALLOUT TEMPLATE (assemble the callout by concatenating ONLY the clauses below whose condition is true THIS run — do not free-compose; if no clause is true the status is OK and there is no callout): open with `> [!warning]` then `> {STATUS} — ` then join the true clauses with `. ` and end with ` — see Prefetch Errors.` Allowed clauses, each gated on its own condition: (i) UST — `{tenor list} {is a/are} [DERIVED] interpolation{s}, not independently confirmed` — include ONLY if the UST XML endpoint was unconfirmed this run; (ii) BBB OAS — `BBB OAS is N business days stale (last print YYYY-MM-DD)` — include ONLY if the last obtainable print is ≥2 business days old; (iii) FedWatch — `CME FedWatch {refreshed this run (…) | stale, last as-of YYYY-MM-DD}` — include ONLY if FedWatch state is notable this run; (iv) 30Y FRM — `30Y FRM carrying the {week} PMMS print (release not yet indexed)` — include ONLY if the current-week PMMS was unavailable; (v) overnight SOFR — `overnight SOFR unobtainable this run` — include ONLY if THIS run failed to obtain overnight SOFR after its web_search fallback. There is deliberately NO clause for the SOFR 30/90/180-day averages or SOFR Index — they are never mentioned in the callout under any condition (see hard rule). CALLOUT SCOPE (hard rule): the callout describes ONLY degradations THIS run observed at write time. Then append one row to the Rate History database (data source collection://ae068728-40ed-4089-b30a-38341348d3ed) — fetch its schema and populate Snapshot Date (title), Fetched At, Prior Trading Day, UST tenors, 10Y-2Y Spread bp, SOFR fields, BBB OAS bp, 30Y FRM, FedWatch fields, Threshold Alert/Alert Reason, Sources Status.

A.4 ESCALATION: On OK, stay silent (Notion only). On FAILED, additionally post a short [ALERT] callout to the Operations Hub page 32b6ecd8-9e59-81f2-b329-df3fd0e25062 and best-effort email ggoldberg@oxfordra.net only (no cc) via the COM helper; if the COM send fails, skip the email. Carry prefetch_status/fetched_at forward in-session for the brief's Section 3.

Carry the resulting `prefetch_status`, `fetched_at`, and any `prefetch_errors[]` forward in-session as the `rate_status` context for Block B Section 3 and Block C Step C.0.5 — both read it directly from this in-session result rather than re-fetching.

---

BLOCK B — DAILY BRIEF. Run the daily-brief skill (installed skill; do not pin a version number here, it resolves by name) exactly as written, including Section 0 pre-flight schema integrity check, WITH ONE OVERRIDE (below) to Section 4's critical-dates sourcing. Produce the full ORA Daily Brief and post to Notion per the skill's routing table. Delivery: send the HTML brief via Outlook COM using C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 to ggoldberg@oxfordra.net with cc egoldberg@oxfordra.net (the Daily Brief is the SOLE sanctioned cc to Eric — routing canon 2026-06-10). On non-zero send exit: retry once, then flag the failure loudly in the Notion completion row — do NOT halt. If the send path is unavailable, complete the brief, post it to Notion, and record the send-path gap prominently in the completion row.

**OVERRIDE — critical-dates authority (added 2026-07-16, Gabriel-ratified):** the daily-brief skill's own Section 4b/4c logic independently re-derives lease expirations and debt/insurance dates from a live Notion read. This caused a live incident on 2026-07-16.

**ROOT CAUSE — corrected 2026-07-16 ~19:30 ET; the original wording here blamed the wrong thing.** This override first read: *"two briefs disagreed on 7/31 expirations because a Notion data-entry defect hadn't propagated to a correction yet."* **That is false, and it matters.** A full read-only audit of all 172 live Tenant DB rows against `portfolio.json` that evening established that **Notion was RIGHT on both disputed rows** — Chesapeake Brands `2027-03-31` and STONE CREST COUNTERS `2028-07-31`, agreeing exactly with the workbook. **This task's own morning run invented `2026-07-31` for both.** That date is J&R Enterprises' real expiration — the one row it got right. The generator took a single expiring-soon date and broadcast it across unrelated rows, then attached a property-level select label ("2018 Zettler Rd") to a tenant whose real unit is 2012. Notion did not supply a single one of those wrong values.

**Why the distinction is load-bearing:** the defect was **fabrication/row-misalignment inside the run**, not bad upstream data. Re-pointing the source (below) removes the *disagreement* — it does NOT by itself stop a run from misaligning rows again, because a run that invents values can invent them from `portfolio.json` just as easily. Hence the mandatory per-row verification in step 5, which is the part that actually addresses the root cause. (There IS a real Notion staleness problem — 18 of 77 dates one 3% escalation cycle behind, 60 empty expirations — but it is a separate issue, it did not cause this, and it is tracked separately.)

Going forward, Section 4b/4c of THIS task's Daily Brief MUST NOT independently compute lease/debt critical dates from Notion. Instead:
1. Read that morning's — or if unavailable, the most recent — **Command Center Daily Brief** (posted to Notion Ops Hub ~06:15 ET by the oxford-command-center alerts engine; run-state in `C:\Users\Owner\oxford-command-center\data\brief-health.json`) and the underlying `C:\Users\Owner\oxford-command-center\data\snapshots\portfolio.json` (`leases[]`/`loans[]`, sourced from the Master Excel Template/DSOR lineage) for the actual critical-dates figures.
2. Present those figures in Section 4b/4c, citing "Source: oxford-command-center alerts engine, as of {portfolio.json meta.asOf}" — do not relabel them as independently confirmed.
3. If the Command Center brief/snapshot is unavailable this run (file missing, alerts engine hasn't fired yet), record Section 4b/4c as a COVERAGE GAP — do NOT fall back to an independent live Notion read for critical dates, and do NOT fabricate.
4. This override does not apply to 4a (scheduled-task health) or 4d (Acquisition Pipeline) — those remain live-Notion-sourced as the skill already specifies.

**4c — AR / DELINQUENCY SOURCE OF RECORD (added 2026-07-24; closes an invented-pointer defect).** Section 4c reports delinquency, and `portfolio.json` does **not** carry AR balances. On 2026-07-22 this task's run filled that void by inventing a producer: it told the reader to *"refer to the latest **ora-pm-ledger** AR run (nightly 18:00 ET) for current balances."* **No such run exists.** `ora-pm-ledger` has no AR-computation module and never has — the pointer sent Gabriel to a nonexistent artifact for a financial figure. The real chain, per the 2026-04-28 QuickBooks-Scrub Master Change Set (Notion `3506ecd8-9e59-815b-b6a8-cff24fa5b926`):
   - **Canonical AR source = the PM platforms** (Rent Manager, Yardi, AppFolio), exported **manually** to SharePoint `Cowork OS / QB Exports / AR Aging`. **QuickBooks Desktop AR is explicitly NOT the primary source**, and no live connector exists for QB Desktop or any PM platform.
   - **Export freshness is gated by `ora-ar-export-freshness-nudge`** (LAMS fleet, 1st & 15th @ 11:30 ET), which escalates by platform when a cycle's export is missing or stale.
   - **Arrears reach the Command Center only via `npx tsx scripts/ar-import.ts <path>`** (oxford-command-center, PR #81) — an **interactive** CLI that requires a human to confirm ambiguous tenant matches. It has **no automatic trigger by design**, so no nightly job can or should produce AR.

   Therefore, when AR is absent from the snapshot, Section 4c MUST record a COVERAGE GAP naming this chain plus the last known export date, and MUST NOT invent, promise, or point at any automated AR run. If no real dated artifact can be cited, use the same language `ora-ar-export-freshness-nudge` uses: *"current AR exposure not verifiable — awaiting export."* **Naming a producer that does not exist is a fabrication in the same class as the 2026-07-16 date defect — confidently wrong, and it sends a real person to a real dead end.**
5. **PER-ROW VERIFICATION (mandatory — this is the step that addresses the actual root cause).** Steps 1–3 fix *where the numbers come from*. They do not stop a run from inventing or misaligning them, which is what actually happened on 2026-07-16. Therefore, before Section 4b/4c ships:
   - **Every date must be copied from a specific row, not inferred, remembered, or carried across rows.** For each tenant you list, the date you print must appear in that tenant's OWN `leases[]` entry (match on `company`/`tenantName` + `unit`). If you cannot point at the exact row a date came from, do not print it.
   - **Duplicate-date tripwire.** If two or more tenants in 4b share an identical expiration, STOP and re-read each of their rows individually before shipping. Two tenants genuinely can share a month-end date — but this exact signature (one real date replicated onto unrelated rows) IS the 2026-07-16 defect. Treat a repeat as guilty until re-verified row by row.
   - **Never let a property label stand in for a unit.** Notion's `Property Address` is a SELECT applied to a whole complex — e.g. `"2018 Zettler Rd — Columbus OH"` tags every Zettler unit (2004, 2006, 2012, 2014, 2016, 2020, 112, 203, 301, Cell Tower…). It is NOT the tenant's unit. Stone Crest is at unit **2012**; unit 2018 is Green Home Solutions. Print the `unit` field, never the property-select label, when identifying a suite.
   - **Sanity-check the horizon.** A tenant reported as expiring inside 90 days whose row says otherwise is a fabrication, not a finding. `monthsToExpiry` and `status` (`Expiring Soon` vs `Active`) in `portfolio.json` are independent cross-checks — if `status` says `Active` and you are about to call it 15-days-out, you are wrong.
   - If any row fails these checks, omit it and record the reason in the COVERAGE GAP rather than shipping a number you cannot source. **A missing row is recoverable; a confidently wrong expiration date drives a real renewal push at a real tenant.**

Additionally, after pulling Section 3's FRED rates, add one tailored paragraph: using the current 5-Year Treasury (DGS5) or SOFR plus an assumed spread (state the spread explicitly as an assumption, e.g. "Treasury + 200–225bps for a small-balance industrial permanent loan"), compute an illustrative all-in rate, then show whether ORA's DSCR ≥1.25x or LTV ≤40% governor is the binding constraint at that rate (compare the DSCR-implied achievable LTV against the 40% cap). Never treat DSCR 1.25x or LTV 40% as adjustable — they are hard governors, not tunable assumptions. State all assumptions as illustrative, not quoted lender terms.

**Publication guard:** create the Notion page under Ops Hub (parent 32b6ecd8-9e59-81f2-b329-df3fd0e25062) titled "Daily Brief — [YYYY-MM-DD]"; capture `pages[0].id`; retry once on failure; verify via direct `notion-fetch` on the returned ID (not `notion-search` — index lag produces false negatives). If publication still fails after retry, AUTO-SEND an Outlook email to ggoldberg@oxfordra.net cc egoldberg@oxfordra.net, subject `❌ ora-am-brief DAILY-BRIEF PUBLICATION FAILED — [YYYY-MM-DD]`, full brief in the body. If email delivery fails (COM non-zero after one retry): log the failure inline in a `## DELIVERY LOG` section at the bottom of the brief, and prefix the Notion page title with `⚠️ [EMAIL FAILED] ` so automation-health-monitor's Block-B beacon check surfaces it.

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
1. **ORA Master Workbook — Cash Data tab** (canonical cash SSOT). Read directly, cell-accurate, via `mcp__Desktop_Commander__read_file` (sheet="Cash Data") against the confirmed local path: `C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx` (2026-07-17: `eric spreadsheets\` is in the OneDrive Business/Personal split's Ambiguous bucket — deliberately NOT moved, still at OneDrive root — do not prepend `Business\` to this path) (verified present and OneDrive-synced 2026-07-16 — do NOT use a "(v3)"/"(1)"/"(2)"-suffix variant; re-verify with `get_file_info` if a sync collision reintroduces one). Cash Data's as-of date is MAX(header date row), NOT the Cash Balances summary A2 label (same gotcha `ora-master-workbook-ingest` already documents). If the local path is missing (sync gap), fall back to the Notion Portfolio Intelligence Dashboard (page `3396ecd8-9e59-819c-a598-e55dc5581504`, refreshed weekly by `ora-master-workbook-ingest`) and disclose staleness (dashboard "Last refreshed" date) in §B.
2. **Notion Operations Hub** (32b6ecd8-9e59-81f2-b329-df3fd0e25062) — reserve thresholds and target distribution policies.
3. **Notion debt schedule** — upcoming debt service obligations (next 30 days).

Compute: A. Total cash by entity and consolidated portfolio total. B. Operating reserves vs. policy minimum (flag if below). C. Capex reserves vs. budgeted draws (next 90 days). D. Distribution headroom = consolidated cash − (next 30-day debt service + reserve floors + known payables). E. Week-over-week delta (vs. prior Monday snapshot stored in Notion).

Output:
- **Notion page** in the Operations Hub titled "Cash Position Snapshot — [date]" with full table. Publication guard: capture `pages[0].id`; retry once; verify via `notion-fetch`; if all fail, AUTO-SEND an Outlook email subject `❌ ora-am-brief CASH-SNAPSHOT PUBLICATION FAILED — [date]` to Gabriel with the snapshot inlined as plain text.
- **Email summary** to ggoldberg@oxfordra.net ONLY. Subject: "ORA Cash Position — [date]".
- If any reserve falls below policy floor: prefix the subject line with "[ALERT]" and flag immediately in the body.
- (Dropped on this surface, 2026-07-16 migration: the LAMS spec's `mcp__cowork__update_artifact` refresh of an `ora-cash-position` Cowork artifact — that tool doesn't exist here. The Notion page + email above are this surface's durable outputs; if a live cash artifact is wanted again, it needs a Cowork-side session to maintain it.)

Format: ORA Institutional Style Guide v1.0+.

---

# END-OF-SESSION RUN SUMMARY

After all applicable blocks complete, emit a one-line-per-block status (block · ran/skipped · output · send result) to the session log so ora-health-guard and automation-health-monitor can confirm the merged AM session fired cleanly. A skipped block (weekend Block A/C, non-Monday Block D) is a NORMAL state, not an error.
