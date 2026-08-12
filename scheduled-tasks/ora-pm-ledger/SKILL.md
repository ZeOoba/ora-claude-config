---
name: ora-pm-ledger
description: ORA Evening Ledger — consolidated daily close. Runs three blocks in order at one cadence — A Notion Daily Digest (every day), B Outbox QC Sweep (weekdays only), C EOD Action Ledger (every day). Restored 2026-07-08 from three separately-archived block specs after the 2026-07-05 CC/MCP registry loss destroyed the original consolidated file; routing/send-path/paths corrected to current canon during restoration (see RESTORATION NOTE at bottom). CC canonical file inlined 2026-07-08 (second restoration same day) to remove a redirect-to-OneDrive pattern that had already broken twice. Re-enabled 2026-07-09 (Gabriel-approved, post-recovery-stabilization confirmation). Block A edit-detection coverage gaps fixed 2026-07-16 (see AMENDMENT NOTE at bottom). [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
output_contract:
  version: 1
  blocks:
    - id: block-a-notion-digest
      artifact:
        type: sent_mail
        mailbox: Sent Items
        subject_pattern: "ORA Notion Daily Digest - {DATE}"
        recipient: ggoldberg@oxfordra.net
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        always: true
      on_missing_severity: alarm
      is_primary_health_signal: true
      notes: "Subject pattern taken verbatim from §0.5 PRE-FLIGHT DE-DUPE GUARD step 1, which already greps Sent Items for this exact string — high confidence, not a guess. Primary signal: runs every day, no branching."
    - id: block-b-outbox-qc
      artifact:
        type: notion_page
        title_pattern: "Outbox QC — {DATE}"
        parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        days_of_week: [Mon, Tue, Wed, Thu, Fri]
      on_missing_severity: warn
      is_primary_health_signal: false
    - id: block-c-eod-ledger
      artifact:
        type: notion_page
        title_pattern: "EOD Action Ledger — {DATE}"
        parent_id: 32b6ecd8-9e59-81f2-b329-df3fd0e25062
      freshness_window_hours: 30
      min_count: 1
      count_semantics: at_least
      expected_on:
        always: true
      on_missing_severity: warn
      is_primary_health_signal: false
      notes: "Every-day cadence like Block A, but Block A is designated the task's primary signal to avoid two alarm-severity blocks firing redundantly off one late/failed run."
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

Added 2026-07-09 after a genuine cross-fleet double-fire: a LAMS run ~16:27 ET
delivered A/B/C, then the CC 18:00 fire re-ran the same day — producing a full
DUPLICATE set of emails and Notion pages, with the duplicate Ops Hub pages also
double-counting in the next morning's brief.

**Root cause RESOLVED 2026-07-12 — not a pending retirement.** The suspected
LAMS/Cowork twin registration was confirmed absent/never-live on both surfaces:
Cowork (LAMS) `list_scheduled_tasks` shows no `ora-pm-ledger` entry, and the
folder once believed to be its live LAMS spec
(`Claude_Workspace\00_Governance\Scheduled\ora-pm-ledger\`) was an orphan never
wired to any scheduler — archived 2026-07-12. CC/MCP (cron `0 18`) is and was
the SOLE live registration; full detail in memory
`reference_ora_pm_ledger_double_fire.md`. This guard is kept anyway as a
**permanent belt-and-suspenders backstop**, not a stopgap awaiting a retirement
that already happened — it is cheap, purely mechanical (no Gabriel input
required per run), and protects against any future re-registration mistake on
either fleet. Run it before anything else:

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
heading). **IDs re-verified live 2026-07-16** (fetched directly, not carried
forward) — all six database sources resolve, and each carries a native Notion
`last_edited_time`-type column; the two page-tree sources (C, D) do not, since
they aren't databases. If a fetch ever errors again, record a COVERAGE GAP, do
not silently drop the source, and re-verify the ID before the next run.

**⚠ The "Native last-edited column" column below states a SCHEMA FACT, not a
working mechanism — do not infer trustworthy edit-detection from it.** A column
existing and being typed `last_edited_time` proves nothing about whether it
advances. Measured per-source truth, established over the Notion REST API
2026-07-16 (supersedes every earlier guess in this file):

**All six ARE reachable and all six A.1 ids below are CORRECT** — they are
**data-source ids**, which is why they 404 against `/v1/databases/{id}`. Query
them at `POST /v1/data_sources/{id}/query` with **`Notion-Version: 2025-09-03`**.
The older `2022-06-28` returns `400 — "Databases with multiple data sources are
not supported in this API version"` on Acquisition Pipeline. (A 2026-07-16 pass
briefly mis-read those 400/404s as "not shared / wrong id" and accused the A.1
table of being wrong. It was not. Version + endpoint, not permissions.)

| Source | Newest last_edited | Oldest | Reality |
|---|---|---|---|
| Acquisition Pipeline Tracker | 2026-07-15 | 2026-03-22 | ✅ **LIVE — varies.** |
| Deal Sourcing Log | 2026-07-15 | 2026-03-22 | ✅ **LIVE — varies.** |
| Broker Relationships | 2026-04-05 21:03 | 2026-04-05 20:06 | ✅ **LIVE — varies.** |
| Tenant Database | 2026-03-30 | 2026-03-22 | ❌ **FROZEN.** Notion itself reports `last_edited_time == created_time`. A zero is a false negative. |
| Property Register | 2026-07-12 | 2026-07-12 | ❌ **Uniform stamp** — all 14 rows share ONE identical timestamp. That is a batch write, not editing. An earlier read of this as "live" was WRONG. |
| CapEx & Maintenance Log | 2026-07-26 | 2026-07-26 | ❌ **Uniform stamp.** The table is no longer empty (6 rows) and every row shares ONE identical timestamp, same failure mode as Property Register: a batch write, not editing. **Detector built 2026-07-27 — see `capex_snapshot_diff.py` (§A.2 step 2, same as the Tenant DB).** The "0 rows, can never report an edit" claim once here was true on 2026-07-16 and is not true now — do not repeat it. |

**Net: Section A (Deal Pipeline) has fully trustworthy, precise, quota-free edit
detection via REST. Section B does not, and no read path will fix it** — Tenant
DB is frozen at the source, and Property Register and CapEx & Maintenance Log
both only ever show their last bulk sync (uniform-stamp).

**The uniform-date tell:** when newest == oldest across every row, the column is
reporting a bulk sync, not edits. Only trust a source whose dates VARY.

Per-source status must still be established at RUN TIME — this table is dated
evidence (2026-07-16), not a standing guarantee.

| # | Section heading | Notion target | ID | Kind | Native last-edited column |
|---|---|---|---|---|---|
| A | **Deal Pipeline** | Acquisition Pipeline Tracker — `bcfe4a03…` is the DATA-SOURCE id, NOT the database page id (db page = `46c8a5c6-8b37-4c53-a10d-0f55c97613e5`). This DB is **multi-source**, so `/v1/databases/{id}/query` 404s on the collection id and 400s on the db id @ Notion-Version 2022-06-28. **REST last-edited query MUST use `POST /v1/data_sources/bcfe4a03-7e61-4ac1-a0bb-c44174fa138b/query` @ Notion-Version 2025-09-03** — verified 200 (2026-07-20). This is why the 2026-07-05→07-20 runs recorded a false "REST 404 coverage gap": the digest code queried `/databases/bcfe4a03` instead of `/data_sources/bcfe4a03` @ the new version. | `bcfe4a03-7e61-4ac1-a0bb-c44174fa138b` (data source) | database | `Last Updated` |
| A | **Deal Pipeline** | Deal Sourcing Log | `9a6ae219-85a3-4621-899c-c757fd062f8b` (canonical pair: database `8d2ddc5177e84cd7b1c0c0f6ef943479` / data source `9a6ae219-85a3-4621-899c-c757fd062f8b`) | database | `Last Updated` |
| A | **Deal Pipeline** | Broker Relationships — the old id `48e43778-b1f2-4b16-8f3c-0bf18f8642e9` was WRONG (404 on every endpoint). **Correct database page id = `dc5bda06-b0b8-4166-a07d-2f99cff8d936`** — single-source, so `POST /v1/databases/dc5bda06-b0b8-4166-a07d-2f99cff8d936/query` @ Notion-Version 2022-06-28 works — verified 200 (2026-07-20). | `dc5bda06-b0b8-4166-a07d-2f99cff8d936` | database | `Last Updated` |
| B | **Tenants & Operations** | Tenant Database — query via data source, NOT the wrapper ID (wrapper `8dbbaec0…` throws "Aggregation property not found"; root cause was a tool-routing quirk, not a broken rollup — fixed 2026-04-27) | `collection://b12f4cfd-a995-4755-8341-6435ae8173b4` | database | `Last Updated` |
| B | **Tenants & Operations** | Property Register | `19a61fc9-21ed-42d7-a0db-aa730d9a9683` (data source `24d6a531-f4b7-4c38-87fb-3b1be4a4f1f3`) | database | `Last Updated` |
| B | **Tenants & Operations** | CapEx & Maintenance Log | `5dfcc3ad-532e-4e5f-bf8d-512e2b69e317` (data source `acd5102e-16bc-4171-9cde-19a2496b1429`) | database | `Last Edited` |
| C | **Knowledge Base & Decisions** | 📚 Oxford Institutional Knowledge Base | `3386ecd8-9e59-8166-af49-da066dc7ca14` | page tree (not a database — no queryable last-edited column) | n/a |
| D | **Operations Hub (everything else)** | Oxford Real Assets — Operations Hub | `32b6ecd8-9e59-81f2-b329-df3fd0e25062` | page tree (not a database — no queryable last-edited column) | n/a |

Section **E — Everything Else Edited Today** is a workspace-wide catch-all
for anything created/edited today that does not belong to A–D.

### A.2 METHOD — HOW TO DETERMINE "CHANGED TODAY"

Use all of the following signals and merge, deduping by page ID:

1. **Newly created today (precise):** `notion-search` with
   `query_type: "internal"` and
   `filters.created_date_range.start_date = {TODAY}`. Run it (a) workspace-wide
   for the catch-all, and (b) scoped to each priority data source via
   `data_source_url` (use the `collection://…` form for the Tenant DB; for the
   others, first `notion-fetch` the database ID to read its
   `<data-source url="collection://…">` tag, then search that data source).

2. **Edited today — SQL last-edited query, OPPORTUNISTIC (NOT "precise", and
   NOT mandatory). Read the two verified defects below before trusting a
   zero.** Each of the six databases does carry a native Notion
   `last_edited_time` column (name per the A.1 table — `Last Updated` for
   five, `Last Edited` for CapEx & Maintenance Log). Where it works, query it:
   ```sql
   SELECT * FROM "<data_source_url>" WHERE date("<column name>") = '{TODAY}'
   ```

   **⚠ DEFECT 1 — the Tenant DB's `Last Updated` DOES NOT BUMP. A zero result
   from it is meaningless.** Measured live 2026-07-16: the column is correctly
   typed `last_edited_time` and the schema annotates it *"automatically set…
   the canonical time for when the page was last edited"* — but every one of
   the 296 rows reports March (`03-22` ×147, `03-23` ×116, `03-26` ×22,
   `03-30` ×11) and **nothing after 2026-03-30 exists in the column**. Proof it
   is broken rather than merely quiet: rows whose own title reads
   `⛔ ARCHIVED 2026-07-12 — …` — self-witnessing evidence of a 2026-07-12
   edit — still report `Last Updated = 2026-03-30`. The retitling of those 124
   rows did not advance the column. Therefore
   `WHERE date("Last Updated") = '{TODAY}'` against the Tenant DB returns **zero
   rows every run, forever**, and reporting that as "no edits today, precisely
   confirmed" is a confident false negative — strictly worse than the honest
   best-effort search it replaced. **For the Tenant DB: never present a zero
   from this query as evidence of no edits. Do NOT even run the timestamp query
   for the Tenant DB — use `tenant_db_snapshot_diff.py` instead (BUILT 2026-07-20;
   see the ✅ BUILT block further down this section). Its snapshot+diff is the
   authoritative detector; only if that SCRIPT errors does the Tenant DB revert to
   a COVERAGE GAP.**

   **What the column actually appears to track (root-cause pass 2026-07-16 —
   behavior PROVEN, mechanism NOT).** Proven: three independent write events
   hit these rows — ~9 rows verified with Notes on 2026-04-27 (corroborated by
   the Ops Hub log), 16 live HubSpot-Contact writes on 2026-07-10 (memory
   `reference_tenant_db_completeness_gap.md`), and 124 retitles on 2026-07-12 —
   and the MAX `last_edited_time` across all 296 rows is still `2026-03-30`.
   Ruled out: an MCP read cache (SQL, `notion-search` and `notion-fetch` all
   independently return `2026-03-30T11:50:30` for the same page, and they return
   today's timestamps for Ops Hub pages), and a stale/duplicate data source
   (database `8dbbaec0` has exactly ONE data source, `b12f4cfd`; the other
   collection ids under it are relation targets). The values cluster on four
   dates (03-22 ×147, 03-23 ×116, 03-26 ×22, 03-30 ×11) matching the bulk-import
   batches, and the sample page's own body reads *"AUTO-CREATED by sync on
   2026-03-30"*. **[SPECULATIVE] leading hypothesis: this column reflects when
   the bulk sync process last wrote the row, not when a human or agent last
   edited it.** Not established — do not repeat it as fact.

   **Corollary — do NOT treat Property Register as a working control.** It
   returned `2026-07-12` for all 14 rows, which was initially read as "the column
   is live there." On the hypothesis above that is more likely a single bulk-sync
   stamp than 14 organic same-day edits — a uniform date across every row of a
   table is the signature of a batch write, not of editing. **Treat EVERY source
   as unproven: a non-zero result is only trustworthy if the dates VARY across
   rows and at least one is genuinely recent.** A table where every row shares
   one date is telling you when it was last synced, not what changed today.

   **The one experiment that would settle the mechanism** (not run — it is a
   write to a live CRM system of record, and a dedicated Tenant DB session was
   working that database concurrently, so a write here risked colliding with
   it): make one controlled, reversible edit to a single already-tombstoned
   `⛔ ARCHIVED` row, then re-read its `Last Updated`. If it advances, the
   column works and all three historical write events used some path that
   bypasses it; if it stays at 2026-03-30, the column is inert for this
   collection and the fallback below is permanent. Ask Gabriel before running it.

   **✅ PREFERRED PATH — Notion REST API via the existing integration token. No
   MCP quota, no plan upgrade, no cost (established 2026-07-16).** The
   entitlement error in DEFECT 2 below is an **MCP-connector upsell**
   (`tool_error_code: entitlement_required`, `source=mcp_tool_upsell`,
   `product=business`) — it is NOT a Notion limit. Notion's own REST API has no
   per-plan query quota for integrations; it is rate-limited at ~3 req/s, which
   is irrelevant at 6 queries/day. A working integration token already exists:
   **`NOTION_TOKEN` in `C:\Users\Owner\oxford-command-center\.env`** (bot name
   "ORA Command Center", verified live 2026-07-16 via `GET /v1/users/me`). Use:
   ```
   POST https://api.notion.com/v1/databases/{database_id}/query
   Authorization: Bearer $NOTION_TOKEN   ·   Notion-Version: 2022-06-28
   {"filter":{"timestamp":"last_edited_time",
              "last_edited_time":{"on_or_after":"{TODAY}T00:00:00Z"}}}
   ```
   This is a true server-side last-edited filter. **Verified working 2026-07-16:**
   sorting `/v1/search` by `last_edited_time` returned real, VARIED timestamps
   (`2026-07-15T13:56`, `2026-07-09T18:55`) — i.e. over REST the field behaves
   correctly, unlike the frozen values the SQL bridge reports for the Tenant DB.

   **✅ GRANT LANDED 2026-07-16 ~23:00 ET.** Gabriel added the **ORA Command
   Center** connection to the Ops Hub via `⋯ → Connections`. Capabilities are
   **read-only** ("Can read content"; cannot insert/update/comment) and cascade
   to child pages — so this path can never write to the workspace. Verified:
   `GET /v1/databases/8dbbaec0…` now returns 200. **Two of the six sit OUTSIDE
   the Ops Hub tree and still 404 — Acquisition Pipeline Tracker and Broker
   Relationships need their own connection grant** (same 3 clicks, on each).

   **⚠ WHAT THE GRANT DID AND DID NOT BUY — read before relying on rung 1.**
   It removes the MCP quota (real, verified) and gives true server-side
   filtering. **It does NOT rescue a frozen column.** Measured immediately after
   the grant: a REST query for `last_edited_time on_or_after 2026-04-01` against
   the Tenant DB returns **0 rows**, when 124 rows were provably retitled
   2026-07-12 and 16 written 2026-07-10. REST is exactly as blind as the SQL
   bridge there. Use rung 1 for the quota win and for the sources whose dates
   VARY — not as a fix for DEFECT 1.

   **✅ DEFECT 1's MECHANISM IS SETTLED (2026-07-16) — stop investigating it.**
   Notion's own REST API reports, for page `3336ecd8-9e59-8108-9287-cd14dd363233`
   (`⛔ ARCHIVED 2026-07-12 — TWO MEN AND A TRUCK`):
   `created_time = 2026-03-30T11:50:00Z` and
   `last_edited_time = 2026-03-30T11:50:00Z` — **identical**, on a page whose own
   title records a 2026-07-12 edit. **The MCP bridge was faithful; it reported
   exactly what Notion holds.** The freeze is inside Notion, upstream of every
   read path, and no client-side change can fix it. (An earlier `[SPECULATIVE]`
   note in this file guessed the column tracked "when the bulk sync last wrote
   the row" — that is now REFUTED and should not be repeated.) WHY Notion does
   this for one database and not another is unresolved and is NOT worth further
   read-only digging: every read path agrees. If it ever matters, it is a Notion
   support question or a controlled-write experiment, not a code change.

   **Consequence — the only mechanism that can detect Tenant DB edits is a
   SNAPSHOT + DIFF**, which the grant now makes affordable: unlimited REST reads
   mean a nightly full pull of the DB, hashed and diffed against yesterday's,
   detects real changes regardless of the broken timestamp.

   **✅ BUILT 2026-07-20 — `tenant_db_snapshot_diff.py` (in this task folder).**
   This is now the AUTHORITATIVE Tenant DB edit detector; the frozen-timestamp
   query is dead and must not be presented as "no edits". Every run, Block A's
   Section B (Tenant Database) MUST invoke:
   ```
   C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \
     C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger/tenant_db_snapshot_diff.py \
     --run --date {TODAY}
   ```
   It pulls all ~296 rows via REST (`/databases/8dbbaec0…/query` @ 2022-06-28,
   single-source, paginated), normalizes each row's properties to plain values
   (skipping the volatile created/last_edited metadata), sha256-fingerprints each
   row, diffs against `state/tenant-db-latest.json`, then rewrites `latest` + a
   dated archive `state/tenant-db-{TODAY}.json`. The last stdout line is
   `RESULT_JSON={...}` with `added/removed/changed` (changed carries field-level
   `old -> new`); parse that and fold it into Section B instead of the frozen
   query. First-ever run reports a BASELINE (296 rows, no diff) — that is normal,
   not a failure; real diffs start the next run.

   **⚠ CORRECTED 2026-07-24 — the original "Verified end-to-end 2026-07-20" claim here was
   WRONG; it is quoted below only as a record of what failed.** That verification was a
   **same-day second pull** (baseline of 296 rows, then a second pull the same day
   reporting 0/0/0), so it never crossed a date boundary. On the first genuine cross-day
   run (2026-07-24) the detector reported **267 of 298 rows changed when only 5 had really
   been edited** — it was fingerprinting five *date-derived formula fields*
   (`Days to Expiration`, `Months Remaining`, `WALT Contribution (Years)`,
   `Tenant Tenure (Months)`, `Months to Expiry`) that recompute from the calendar on every
   read.

   **FIXED 2026-07-24.** Those five are excluded by name via `TIME_DERIVED_FIELDS`
   (by name, not by type — a formula over static inputs is still a real change signal);
   the diff now compares *filtered* fields on both sides instead of the stored hash, so
   snapshots written before the fix still compare cleanly; and a **bulk-field guard** adds
   a `warnings[]` entry whenever a non-excluded field moves on >50% of rows — that guard
   caught `Months to Expiry` on its own first run. Re-verified against the real archived
   snapshots: 07-22→07-24 now **5 changed / 293 unchanged** (was 267), 07-21→07-22 now
   **20** (was 298), 07-20→07-21 **164** — all substantive, no spurious warnings.

   **`RESULT_JSON` now also carries `warnings`. Surface it in Section B whenever it is
   non-empty** — a bulk-field warning means a new derived or bulk-written column has
   appeared and that run's changed-count is not trustworthy until the field is triaged.

   The no-network `--selftest` covers added/removed/changed + field-level + first-run
   baseline, **plus cross-day (date-derived-only movement ⇒ 0 changed; a real edit
   alongside it still detected), pre-fix→post-fix migration, and the bulk-field guard** —
   13 assertions, all passing. Any future change to this script MUST keep the cross-day
   cases: a same-day rerun is not a valid test for a date-sensitive diff.

   Only if the SCRIPT itself errors (token unreadable, REST
   down) does Tenant DB revert to a COVERAGE GAP — a clean 0-diff is now a REAL
   "no edits today", no longer a false negative.

   **✅ BUILT 2026-07-27 — `capex_snapshot_diff.py` (same folder, same pattern).**
   CapEx & Maintenance Log hit the same uniform-stamp failure mode as Property
   Register once it stopped being empty (see §A.1's Reality table). Section B
   (CapEx & Maintenance Log) MUST invoke:
   ```
   C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \
     C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger/capex_snapshot_diff.py \
     --run --date {TODAY}
   ```
   Same `RESULT_JSON=` contract, same `state/capex-*.json` storage shape. Unlike
   the Tenant DB, CapEx carries no date-derived formula fields today (checked
   live at build time — its two formulas, `Annualized Reserve` and `Yield on
   Cost`, are ratios of static numeric inputs, a legitimate change signal, not
   calendar drift), so `TIME_DERIVED_FIELDS` is empty; the bulk-field guard is
   the backstop if one is ever added later. `--selftest` is 21 assertions
   (diff engine, the exclusion mechanism proven against a synthetic field name
   since no real one exists yet, the bulk-field guard incl. the 50% boundary,
   pagination, and `load_prev()` corruption fallback), all passing. Property
   Register remains the one source in §A.1 with no detector — same gap, not
   yet built.

   **⚠ DEFECT 2 — `notion-query-data-sources` is ENTITLEMENT-GATED and will
   hard-fail mid-run.** Measured live 2026-07-16: after ~5 queries the tool
   returns `validation_error` / `entitlement_required` —
   *"You've used all of your plan's free data source queries for now. Upgrade
   to a Business plan or higher…"* — with `tool_error_retryable: "false"`. The
   tool's own docs confirm SQL and view mode need **Business + Notion AI**.
   Six mandatory queries per run therefore cannot be guaranteed to complete,
   and the failure is non-retryable and quota-based (i.e. nondeterministic —
   it may pass some runs and fail others depending on what else drew from the
   quota that day). **On an entitlement error: record that source as a COVERAGE
   GAP by name, fall back down the ladder below, and continue — do NOT halt the
   block and do NOT retry in a loop (it burns the same quota).**

   **MECHANISM LADDER — try in this order; never depend on any single rung:**
   1. **REST API + `last_edited_time` filter** (see PREFERRED PATH above) —
      free, precise, unlimited, server-side. Blocked only on the one-time share.
      **This is the target state; once granted, rungs 2–3 become fallbacks only.**
   2. **`notion-search` via MCP, scoped per `data_source_url`**, keeping results
      whose returned `timestamp` (= last-edited) date == `{TODAY}`. **Not
      entitlement-gated** — it ran freely throughout 2026-07-16 while the SQL
      tool was exhausted, so this rung is always available. Recall is
      ranked/semantic, so it is genuinely best-effort: it can miss rows and MUST
      be labelled best-effort, never "precise".
   3. **`notion-query-data-sources` SQL** — opportunistic ONLY, given the quota.
      If used at all, spend it on the source most likely to matter (A — Deal
      Pipeline) rather than round-robining all six.
   4. **Nothing worked ⇒ name that source in COVERAGE GAPS.** Never a silent pass.

   **Do not wire the REST rung as unverified code.** Every database call 404s
   until the share lands, so it cannot be tested today — and shipping an
   untested query into a daily task is exactly how a silent false negative is
   born (that is the defect this whole section exists to document). Confirm a
   200 from `GET /v1/databases/8dbbaec0-611a-4617-be07-6a77d0d0307a` FIRST, then
   implement, then re-verify against a row known to have changed.

   **Still binding — the anti-skip rule this step was built for:** a source
   returning zero rows from step 1 (created-today) is NOT evidence it has no
   edits today. Every source must be *attempted* by step 2 or step 3 and, if
   neither produced a trustworthy answer, named individually in COVERAGE GAPS.
   The 2026-07-16 finding was exactly this failure mode (the workspace-wide
   created-date search found nothing for Broker Relationships / Property
   Register / CapEx & Maintenance Log, and no per-source edit check was run as
   a result). Before writing A.3, confirm in-session what each of the six
   returned — a source with no confirmation is a COVERAGE GAP, never a silent
   pass.

3. **Edited today — best-effort for the two page-tree sources (C, D) only.**
   Knowledge Base and Operations Hub are page hierarchies, not databases, so
   they have no queryable last-edited column. For these two only:
   `notion-fetch` the page and scan child pages' last-edited stamps, plus a
   broad `notion-search` semantic query, KEEPing any result whose `timestamp`
   date == `{TODAY}`.

**Known limitation — corrected 2026-07-16 ~19:35 ET after live testing.** This
paragraph previously read: *"edit detection is **precise** for all six database
sources (step 2) and best-effort only for the two page-tree sources."* **Both
halves of that were wrong, and the error was the dangerous direction — it
promised precision the tooling does not deliver, which converts a silent miss
into a confident false negative.** Measured reality (evidence in step 2):

- **Tenant DB — NOT precise. The column is frozen** at 2026-03-30 and does not
  bump; provably-edited rows still report March. Its zero is meaningless.
- **All six — NOT guaranteed to run at all.** The SQL tool is entitlement-gated
  and hard-fails (non-retryable) once the plan's free query quota is spent.
- **Property Register — genuinely live** (returned 2026-07-12). So the mechanism
  is real *where it works*; it just cannot be assumed per-source or per-run.
- **Knowledge Base + Ops Hub (C, D)** — best-effort as before; they are page
  trees with no queryable last-edited column.

**Therefore: do not print a precise/best-effort split by SOURCE CLASS. Report
what actually happened, per source, this run.** For each of the eight sources
state which of these it was: `sql-confirmed` (query ran and the column is
trusted for that source) · `sql-unavailable` (entitlement/quota — name it) ·
`column-unreliable` (Tenant DB) · `best-effort` (semantic sweep only). Never
imply completeness that wasn't achieved — and never let a zero from a known-
frozen column read as "nothing changed."

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
Surface the Brief's already-computed flags rather than re-deriving them from the
warehouse: the warehouse's lease/debt tables are not populated well enough to
re-derive from, so re-derivation would silently UNDER-report. List only alerts
that FIRE, most-urgent first:
- **Lease expirations ≤90 days** — tenant · property · annual rent · days out. Source: the day's Command Center Daily Brief critical-dates section.
- **Insurance ≤30 days / expired** — count + total premium + next renewal date. Source: the Brief. MAY be verified/refined directly from the live warehouse `C:\Users\Owner\oxford-command-center\data\warehouse\finance.sqlite`, table `property_insurance_policies` (columns `expiration_date`, `premium_annual`, `policy_type`) — the one alert class fully populated in the warehouse (25 rows, verified 2026-07-16).
- **Loan balloons ≤18 months** — loan · months · balance. Source: the Brief. Warehouse `debt_positions` is NOT empty (earlier wording said "EMPTY" — corrected 2026-07-16): it holds 20 rows = 4 daily snapshots × 5 loans, latest 2026-07-14. Those 5 are exactly the portfolio's 5 `direction: borrower` loans — ORA's real borrowings — and all are Amortizing with maturities 2028–2032, so **a balloon query against it correctly returns nothing**. Do not read that empty result as an under-report; ORA genuinely has no debt balloon inside 18 months. **The live balloon alert is on a note RECEIVABLE** (see the direction trap below), which is why it can only come from the Brief.
- **DSCR < 1.25× or LTV > 40%** — property · figure. Source: the Brief / warehouse `debt_scores` once populated (still 0 rows, verified 2026-07-16).
- **Acquisition deadlines / stalled deals** — deal · market. Already covered by Block A's live Notion Acquisition Pipeline query — cross-reference it, do NOT re-derive.

**Where the Brief's lease/debt alerts actually come from** (established 2026-07-16
— do not re-derive this the hard way): the alerts engine reads
`oxford-command-center\data\snapshots\portfolio.json`, NOT the warehouse. That
file carries `leases` (with `leaseEnd`, `status`, `annualRent`) and `loans` (12
rows, with `direction` = borrower | lender | internal, `maturity`, `balloon`).
Its `meta` block states `source` = the Master Excel Template (DSOR lineage),
`asOf` = the data month, and `generatedAt` = when it was baked — check all three
before treating a figure as current. This is the file to read when an alert needs
verifying or a Brief figure looks wrong; the warehouse will not confirm it.

**The direction trap — read this before reporting any loan alert.** Each loan
carries `direction`: `borrower` (ORA owes — real debt), `lender` (ORA is owed —
a note RECEIVABLE), or `internal` (intercompany). As of 2026-07-16 the Brief's
balloon alert does NOT filter on direction, so it fires on `lender` loans with
the detail line *"Prepare refinance or payoff"* — the wrong action for a note ORA
holds and collects. The live example is **Restoration Church Trust** ($979,772,
9%, balloon 2027-02-20): it is an ASSET, not a liability. Two other `lender`
loans exist (1100 Rarig/Fenton $553,045; 485 S. Walnut St. $252,000). When a
balloon alert fires, check `direction` in `portfolio.json` first and report it as
a collection event, not a refinancing obligation. Do not "fix" `conditions.ts`
from this task — it is financial-decision code (Invariant 4, mandatory
adversarial REFUTE pass); flag it instead.

**The Notion-vs-Brief cross-check — read this before reporting a lease alert
that another source also reports.** The Command Center Brief (via
`portfolio.json`, Master Workbook-sourced) and `ora-am-brief`'s Daily Brief
(via its own daily-brief skill, Notion Tenant DB-sourced, `collection://b12f4cfd-…`)
are two independently-fed pipelines that can and do disagree on the same
tenant's lease-expiration date — Notion Tenant DB has documented,
previously-remediated data-quality problems (duplicate rows, phantom rows,
stale fields from its original March 2026 import; see the 2026-07-12 Tenant DB
cleanup). **Confirmed 2026-07-16:** the two briefs disagreed on tenants
expiring 2026-07-31 — Command Center listed J&R Enterprises; `ora-am-brief`
listed Chesapeake Brands and Stone Crest Counters instead, omitting J&R. Cross-
referencing `portfolio.json` against the live Tenant DB rows by property/unit/
contact/rent (not by name alone — several tenants share near-identical names)
confirmed: J&R Enterprises genuinely expires 2026-07-31 (Notion's live row for
it had no Lease Expiration value at all — a gap, not a conflict); Chesapeake
Brands' Notion row wrongly carried 2026-07-31 (actual, per the Workbook:
2027-03-31); Stone Crest Counters' Notion row likewise wrongly carried
2026-07-31 (actual: 2028-07-31). All three Notion rows were corrected
2026-07-16 to match the Workbook, which CLAUDE.md designates as the firm's
source of record for firm figures. **Going forward:** when this section's
Command Center figure for a tenant and that tenant's live Notion Lease
Expiration disagree (or Notion has no value where the Brief has one), do not
silently trust either — cross-reference `portfolio.json` by property/unit/
contact (not tenant name alone) and flag the specific discrepancy by name in
COVERAGE GAPS rather than letting only one brief's version reach Gabriel
unremarked. Do not silently rewrite Notion tenant data from this read-only
Block A — a mismatch found here is reported, not auto-corrected in-run.

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

### B.2 SENT ITEMS SWEEP — RETRO-SWEEP MODE (rebuilt 2026-07-24)

**The old single-window design ("today 00:00 → run time") is RETIRED. It left two
permanent holes, and its own stated rationale was factually wrong:**

1. **Missed days.** If the task doesn't fire (machine offline overnight), that day's
   outbound mail was never audited and nothing retried it. Confirmed twice in one week:
   **2026-07-17 and 2026-07-23** have no Outbox QC page or send-log entry.
2. **Evening tails.** The old text claimed mail sent after the ~18:00 fire "land[s] in
   next day's window." **It does not.** The next day's window is
   `[D+1 00:00 → D+1 18:00]`, and a message sent 18:30 on day D carries `sentDateTime`
   on day D — so it fell in NO window, ever. Every single day silently lost its
   ~18:00→24:00 tail. Measured at rebuild time: 07-20/21/22/24 tails plus the whole of
   07-23 = **~46.6 hours of unaudited outbound mail in five days.**

Both are the same bug: coverage was modelled as *"did we run today?"* instead of
*"which spans of time have actually been swept?"* Block B now tracks **covered
intervals** and sweeps whatever is uncovered, which closes both holes with one
mechanism.

**Step 1 — plan the windows.** Run:
```
C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe \
  C:/Users/Owner/.claude/scheduled-tasks/ora-pm-ledger/outbox_qc_window.py --plan
```
The last stdout line is `RESULT_JSON={...}` with `days_to_sweep[]` (each carrying
`date`, `is_today`, `weekend`, `gaps[[from,to]]`, `uncovered_minutes`),
`retro_days[]`, and `dropped_beyond_lookback[]`. State lives in
`state/outbox-qc-coverage.json`; lookback is 7 days.

**Step 2 — sweep each gap.** For every entry in `days_to_sweep`, query Sent Items with
`sentDateTime` inside that entry's gap interval(s) — NOT "today". A retro day's gap is
usually the full 24h (missed day) or the evening tail (~18:00→24:00). Run the same
Checks A–I against each gap's messages.

**Step 3 — commit coverage, FAIL-CLOSED.** After a gap's report has *actually* been
delivered (its Notion page posted, and for today, the email sent), record it:
```
outbox_qc_window.py --commit --date <YYYY-MM-DD> --from <iso> --to <iso>
```
**Never commit a gap whose page or send failed** — leave it uncovered so the next run
retries it. Committing on plan rather than on success would silently swallow a day whose
report never reached Gabriel, which is the exact failure class this rebuild exists to
kill.

**`dropped_beyond_lookback` must be surfaced in the report whenever non-empty** — those
are days still uncovered but older than the 7-day reach. They are reported, never
silently lost (no silent caps).

**Weekend days:** Block B itself is Mon–Fri, so Saturday/Sunday mail is never swept
same-day. The Monday run picks Sat/Sun up as retro gaps (flagged `weekend: true`) —
this is intended, and is how Friday-evening-onward mail finally gets audited.

Within each gap, exclude:
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
than the specific property LLC, flag MEDIUM. Root cause fixed 2026-07-24:
`tenant-email` v1.1 and `communication-intelligence` v1.3 now resolve the
LLC from the ratified roster and embed the signature block as literal draft
text instead of depending on Outlook's manual signature picker — daily
recurrence should drop sharply going forward. A message that still trips
this check now most likely predates the fix, was drafted outside those two
skills, or has the correct block overwritten by Outlook's own auto-inserted
default signature (see the "delete the auto-inserted one" step in both
skills) — do not silently downgrade this check on the strength of the fix
alone.

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
Window: [gap start] -> [gap end] ET   (per B.2; today's gap normally 00:00 -> run time.
                                       A retro gap states its own interval, e.g.
                                       "2026-07-23 00:00 -> 23:59 (missed run)" or
                                       "2026-07-22 18:25 -> 23:59 (evening tail)".)
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

**Retro gaps (added 2026-07-24) — one email, pages only where there is something to
report:**
- **Do NOT send a separate email per retro day.** Fold them into today's single email as
  a **"Retro coverage"** section, one line per gap: date · window · messages found ·
  defects · page link (or "no messages"). Reserve the subject line for today's counts,
  appending `· +N retro day(s)` when any retro gap was swept.
- **Only create a Notion page for a retro gap that actually contains messages.** Most
  evening tails are empty; minting near-blank pages for them buries the real ones. An
  empty gap is still **committed** as covered and still reported in the Retro coverage
  line as "0 messages" — coverage is closed either way.
- A retro page is titled `Outbox QC — YYYY-MM-DD` (same format, so the §0.5 de-dupe guard
  and future planner runs both see it) with a first line stating it was a **RETRO sweep**,
  the exact gap interval, and why it was owed (missed run vs. evening tail). If a page for
  that date already exists (a partial same-day sweep), title the new one
  `Outbox QC — YYYY-MM-DD (retro: HH:MM–HH:MM)` rather than overwriting it — the earlier
  page is the audit record of what was checked at the time.
- Retro findings are **reported, never acted on**: a defect found in mail sent days ago is
  a pattern note, not a prompt for a corrective send. B.6's read-only constraint applies
  unchanged.

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
- **Coverage commit is fail-closed (see B.2 step 3).** On ANY failure affecting a gap —
  Outlook query error, Notion post failure, send failure — do NOT `--commit` that gap.
  An uncommitted gap is simply re-planned next run, so a bad run costs a retry, never a
  silent hole. Never batch-commit all gaps up front "and then report": commit each gap
  only after its own delivery succeeded.
- If `outbox_qc_window.py --plan` itself errors (state file corrupt or unreadable), fall
  back to the legacy single-day window (`today 00:00 → now`), record a COVERAGE GAP by
  name in Block C, and commit NOTHING — the planner must be repaired before coverage
  tracking can be trusted again.

### B.8 DEPENDENCIES
- Outlook M365 connector · Notion MCP (LP Database for Check E; Ops Hub for
  posting) · ORA Voice Register v1.0+ (canonical Strike list).
- `outbox_qc_window.py` + `state/outbox-qc-coverage.json` (sweep-window planner,
  retro-sweep mode — B.2). No network; pure local state. `--selftest` covers the
  interval algebra with 20 assertions.

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

**AR / DELINQUENCY — THIS TASK DOES NOT PRODUCE IT (added 2026-07-24).** This
ledger has no AR-computation module and must not claim or imply one. On
2026-07-22 the Command Center Daily Brief's §4c told readers to "refer to the
latest ora-pm-ledger AR run (nightly 18:00 ET)" — that run has never existed;
the pointer was invented at generation time and has been corrected in
`ora-am-brief`'s SKILL.md. Do not "helpfully" build one here: AR's canonical
source is the PM platforms (Rent Manager/Yardi/AppFolio) manually exported to
SharePoint `Cowork OS / QB Exports / AR Aging` (QuickBooks Desktop AR is
explicitly NOT primary; no live connector exists for either), freshness is
gated by `ora-ar-export-freshness-nudge` (1st & 15th), and arrears reach the
Command Center only through the **interactive** `scripts/ar-import.ts`, which
has no automatic trigger BY DESIGN because a human must confirm ambiguous
tenant matches. Auto-running it unattended would write fuzzy-matched arrears
to a financial overlay without confirmation. If a run wants AR, it cites the
last dated export or records a COVERAGE GAP — nothing else.

Freshness guard: if a Notion mirror is >7d behind workbook
`lastModifiedDateTime`, read live; never present stale figures as current.
Do NOT fabricate any item. **Mandated-source discipline:** the Monthly
Checklist, lease-renewal pipeline, and HubSpot (source class B) MUST each be
attempted every run; if any is unreachable on the current surface, record it
by name as a COVERAGE GAP — never silently omit it (the 2026-07-09 run omitted
these without flagging; that is the failure this rule closes). Any other
unreachable source is likewise recorded as a COVERAGE GAP, not dropped.

**DSOR reachability — check BEFORE declaring a COVERAGE GAP (added 2026-07-16):**
the 2026-07-16 run declared the ORA Master Workbook "not locally resolvable
from this surface" without trying either of two paths that do work from
CC/MCP: (1) the workbook is OneDrive-synced locally at
`C:\Users\Owner\OneDrive - Oxford Capital Partners\eric spreadsheets\Master Excel Template Company Wide -- Oxford.xlsx` (2026-07-17: `eric spreadsheets\` is in the OneDrive Business/Personal split's Ambiguous bucket — deliberately NOT moved, still at OneDrive root — do not prepend `Business\` to this path)
(same path `ora-master-workbook-ingest` reads directly — verified present
2026-07-16, `lastModifiedDateTime` 2026-07-15) — read it cell-accurately via
`mcp__Desktop_Commander__read_file`, exactly as that task does; (2) failing
that, `sharepoint_search`/`read_resource` also reaches it directly (confirmed
2026-07-16) under `eric spreadsheets/` in egoldberg's SharePoint. Try both
before recording the DSOR itself as a COVERAGE GAP. **The Monthly Checklist
is NOT a separate file — corrected 2026-07-16 (Gabriel-confirmed):** it is a
sheet (`Monthly Checklist`, plus a mirrored `EXPORT_MonthlyChecklist` tab)
INSIDE this same Master Workbook — read it the same way as any other SoR tab
(`mcp__Desktop_Commander__read_file`, sheet="Monthly Checklist"). The prior
framing of it as an unreachable 31/59-item close workbook living only in
SharePoint was wrong and should not recur. Ignore the stale
(2026-04-17) "Monthly Checklist Accounting+Operations.xlsx" at the OneDrive
root — that's an old standalone export, not the source of record; the live
checklist is the in-workbook sheet.

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
  `C:\Users\Owner\OneDrive - Oxford Capital Partners\Business\ORA\Briefs\outputs\{TODAY}_<block>.html` (path updated 2026-07-17 — `ORA\` moved under `Business\` per the OneDrive Business/Personal split)
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

**RESOLVED 2026-07-16:** the above was never re-checked, and the archived
spec's blanket "best-effort" edit-detection language was never re-examined
either — together these produced a real coverage gap (the per-source edit
sweep silently never ran against these three). Both are now fixed: all three
IDs were fetched live and confirmed correct; each of the six database sources
in §A.1 (not just these three) was found to carry a native `last_edited_time`
column, so §A.2 step 2 now runs a precise SQL query per source instead of a
"broad semantic search," and §A.2 explicitly mandates that step run against
all six named sources every run regardless of what the created-date search
found. See the current §A.1/§A.2 text — this note stays as a record of what
was wrong, not as live guidance.

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

## AMENDMENT NOTE (2026-07-14 — documentation-sync only, no guard-logic change)

§0.5's preamble was reframed: it had described the de-dupe guard as a stopgap
"[u]ntil the redundant registration is retired," but that retirement already
happened — `reference_ora_pm_ledger_double_fire.md` confirms the suspected
LAMS/Cowork twin was found absent/never-live on 2026-07-12, and CC/MCP was
already the sole registration throughout. Updated the prose to state the guard
is a permanent, intentional backstop rather than a pending-cleanup workaround,
so a future reader doesn't re-open an already-closed question. The guard's
actual check logic (§0.5 steps 1–4) is unchanged — this was prompted by a
sweep checking whether other scheduled-task guards shared the
`ora-owner-outreach-queue-refresh` STALE-guard pattern (a one-time human
confirmation the guard has no way to remember). This guard doesn't share that
pattern — it never waits on a Gabriel decision, it re-derives its own answer
mechanically from today's evidence on every run — but its rationale text was
stale relative to memory, which this note corrects.

## AMENDMENT NOTE (2026-07-16 — edit-detection coverage-gap remediation)

Three coverage gaps flagged this date, all fixed in §A.1/§A.2/§A.4 above:

1. **Blanket "best-effort" edit-detection language.** §A.2 previously applied
   one best-effort disclaimer to all eight priority sources. Live-checked all
   six database sources (A + B) and found each carries a native Notion
   `last_edited_time` column — edit detection for those six is now a precise
   SQL query (`WHERE date("Last Updated"/"Last Edited") = '{TODAY}'`), not
   best-effort. Best-effort now correctly applies only to the two page-tree
   sources, C (Knowledge Base) and D (Ops Hub), which have no such column.
2. **Per-source edit sweep never run for Broker Relationships / Property
   Register / CapEx & Maintenance Log**, with their IDs carried forward
   unverified since the 2026-06-11 archived spec. All three IDs re-verified
   live (all resolve correctly — never actually stale); §A.2 step 2 now
   explicitly mandates the sweep run against all six named database sources
   every run, independent of what the created-date search in step 1 found.
3. **Two daily briefs (Command Center vs. `ora-am-brief`) disagreeing on
   lease-expiration data** — added the "Notion-vs-Brief cross-check" note in
   §A.4 documenting the 2026-07-16 case (J&R Enterprises / Chesapeake Brands /
   Stone Crest Counters) and requiring future disagreements to be
   cross-referenced against `portfolio.json` by property/unit/contact and
   flagged by name, not silently resolved to one source. The three
   underlying Notion Tenant DB rows were corrected the same day (outside this
   file — see memory `project_notion_daily_digest_coverage_gaps_2026-07-16.md`).

No block logic, routing, or send-path changed — this was a coverage-quality
and documentation fix to Block A only.

## AMENDMENT NOTE (2026-07-24 — Block B retro-sweep mode)

**Block B's sweep window was rebuilt from "did we run today?" to interval coverage.**
Two permanent holes were closed, one of which the spec had explicitly (and wrongly)
denied:

1. **Missed days.** A day the task didn't fire was never audited and nothing retried it.
   Two occurrences confirmed in one week from the send-log: **2026-07-17** and
   **2026-07-23** have no Outbox QC send or Ops Hub page.
2. **Evening tails.** The old B.2 asserted that mail sent after the ~18:00 fire "land[s]
   in next day's window." It does not — the next day's window is
   `[D+1 00:00 → D+1 18:00]`, so a message sent at 18:30 on day D fell in no window ever.
   **Every day silently lost its ~18:00→24:00 tail.** Measured at rebuild time across
   07-20/21/22/24 tails plus all of 07-23: **~46.6 hours of unaudited outbound mail in
   five days.**

**What shipped:** `outbox_qc_window.py` (`--plan` / `--commit` / `--selftest`) tracking
covered intervals in `state/outbox-qc-coverage.json`; 7-day lookback; `--commit` is a
separate fail-closed step so a gap whose report failed to deliver stays open and retries;
`dropped_beyond_lookback` is reported rather than silently truncated; weekend gaps are
surfaced (flagged) so the Monday run finally audits Friday-evening-onward mail. B.2, B.4,
B.5, B.7, B.8 updated accordingly; retro results fold into ONE email and only mint a
Notion page when the gap actually contains messages.

State was seeded from the real send-log times (07-20 18:20:59, 07-21 18:21:45,
07-22 18:25:37, 07-24 18:15:00; `tracking_since` 2026-07-20), so the next run's plan
correctly shows 07-23 as a full missed day plus four evening tails.

`--selftest` is 20 assertions covering the interval algebra, the missed-day and
evening-tail cases, today-capped-at-now, idempotent re-commit, the lookback clamp with
explicit dropped reporting, the `tracking_since` floor, out-of-order/overlapping commit
merges, weekend flagging, and sub-minute sliver suppression. All passing.

**Not changed:** Block B remains read-only and Mon–Fri; routing and send-path unchanged;
retro findings are pattern notes only and never trigger a corrective send.

## AMENDMENT NOTE (2026-07-27 — CapEx & Maintenance Log coverage-gap correction)

§A.1's Reality table carried a stale claim: CapEx & Maintenance Log recorded as
"0 rows — the table is EMPTY, it can never report an edit, and never could,"
dated to 2026-07-16 evidence. Live-checked over REST during the 2026-07-27 run
(the same run that produced that date's EOD Action Ledger COVERAGE GAPS item):
**the table now holds 6 rows**, all stamped one identical `last_edited_time`
(2026-07-26). That is not "empty" and it is not "reportable" either — it is the
same uniform-stamp/batch-write signature already documented for Property
Register, so it goes in the same bucket: `column-unreliable`, not `sql-confirmed`.

**Fixed:** the CapEx row in the §A.1 Reality table now states the live count and
the uniform-stamp finding instead of the empty-table claim; the "Net:" summary
paragraph no longer says "CapEx has no rows at all" and instead groups it with
Property Register as sharing the same last-bulk-sync limitation.

**Not changed:** no detector exists for this source yet (same gap as Property
Register — the Tenant DB is the only source with a snapshot-diff detector). A
future run that wants trustworthy CapEx edit detection needs one built, not a
timestamp query. No block logic, routing, or send-path changed — documentation
fix to §A.1 only.

## AMENDMENT NOTE (2026-07-27, later same day — CapEx snapshot-diff detector built)

The gap the amendment above named as open ("no detector exists for this source
yet") is closed. `capex_snapshot_diff.py` generalizes `tenant_db_snapshot_diff.py`'s
approach — full REST pull, per-row sha256 fingerprint, diff against the prior
persisted snapshot — to CapEx & Maintenance Log. It is a separate, self-contained
script rather than a shared library extracted from the Tenant DB engine: both are
short, independently selftested, and living alone in this folder is the
established convention (see `outbox_qc_window.py`); a shared-library refactor of
a working, reviewed production script was not asked for and was not done.

**Live-checked at build time:** CapEx carries no date-derived formula fields —
unlike the Tenant DB's five, its two formulas (`Annualized Reserve`, `Yield on
Cost`) are ratios of static numeric inputs, so `TIME_DERIVED_FIELDS` is empty
by default. The exclusion mechanism itself is still proven by `--selftest`
against a synthetic field name, so it is a one-line addition (not a rewrite)
if Notion ever adds a real calendar-derived formula here; the bulk-field guard
is the backstop in the meantime, exactly as it is for the Tenant DB.

**Wired in:** §A.1's Reality table row now points at the script; §A.2 step 2
carries the same `MUST invoke` block as the Tenant DB's. `--run` was smoke-tested
live against the real database (6 rows, baseline established, exit 0) before
this note was written — not merely selftested offline.

**Not done:** Property Register has the same uniform-stamp problem and no
detector. That gap is unchanged and is not implicitly closed by this note.
