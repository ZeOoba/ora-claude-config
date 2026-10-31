---
name: ora-county-sales-monitor
description: Monthly Tier A industrial sales/transfer pull (Franklin OH, Baltimore Co MD, Polk IA) per county-sales-monitor skill v0.5 — upserts to the Notion County Sales Comps DB, emails a ggoldberg-only digest. Baltimore Co MD has a known ~4mo recording lag — quiet months there are expected, not a regression. [MODEL: UNVERIFIABLE | checked 2026-08-15]
---

You are the monthly recurring run of ORA's `county-sales-monitor` skill (Oxford Realty Advisors, industrial sales/transfer market-intelligence feed). Read the full spec before doing anything: `C:\Users\Owner\.claude\skills\county-sales-monitor\SKILL.md` — it defines the exact methodology (Steps 0-8), size gate, non-arms-length flagging, and row schema. Also read `C:\Users\Owner\.claude\skills\county-parcel-screen\references\county-endpoints.v1.json`, `county-endpoints.md`, and `market-status.md` for endpoint URLs and field names (`county-endpoints.md` was patched 2026-08-15 with fields the first pilot discovered for these exact counties — read it, don't rediscover from scratch).

## STEP -1 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-06; run before the skill's own Step 0)

This task shares the same catch-up-burst exposure `ora-am-brief`/`ora-deal-aging-sla` were fixed for on 2026-08-09 (the whole fleet fires only while the Desktop app is open, so an offline stretch spanning the 1st re-arms this task at next open) — nothing previously stood a second fire down, and this task's own upsert-not-insert design (see "This is NOT the first run" above) means a same-month double-fire would not duplicate rows, but WOULD send a duplicate email and burn a second full county-endpoint pull for no new data. `--period month` keys the claim to the calendar month rather than the ET date.

Run this as the first action of the run:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py claim --task ora-county-sales-monitor --block main --run-id <run_id> --period month --ttl-min 45
```

- **Exit 10** → this month's pull already completed. Exit without querying county endpoints or Notion, and without emailing; report a NORMAL skip.
- **Exit 11** → another fire is live this month. Stand down identically.
- **Exit 0** → proceed with the skill's own Step 0.

Once the digest email sends, run:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py complete --task ora-county-sales-monitor --block main --run-id <run_id> --period month --email-sent-at <ISO8601>
```

If the run aborts instead:

```
python C:\Users\Owner\.claude\scheduled-tasks\_shared\block-sentinel.py fail --task ora-county-sales-monitor --block main --run-id <run_id> --period month --error "<what broke>"
```

**Only the run that holds the claim may call `complete` or `fail`.** **Always pass `--period month`** on every call — omitting it addresses the day-keyed bucket instead and silently defeats the guard. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

## Scope (locked — do not expand without a human ruling)
Tier A only: **Franklin County OH (Columbus), Baltimore County MD (Maryland), Polk County IA (Des Moines)**. Do not touch Tier B or Tier C counties, do not add Louisville/Jefferson Co KY — all deliberately out of scope until a human expands them.

## Window
Default: trailing 30 days from today (Step 1 of the skill). Building SF < 150,000, keep unpublished-SF rows (never drop).

## This is NOT the first run — upsert, don't blind-insert
The Notion database already holds rows from the 2026-08-15 pilot (304 transactions) plus every prior monthly run. Data source: `collection://63a5e6b3-2655-4e0c-9843-3102d78adc0d` (database `County Sales Comps`, https://app.notion.com/p/311cf71222d14a56aa33da354cb3a1ea). Before writing:
1. Query the data source (use `notion-fetch` on the data source URL, or a `query_data_sources` call if available) for existing rows in the relevant counties.
2. Compute this run's key set: `County + Parcel ID + Sale Date + Sale Price` (matches the skill's Step 1 late-posted-diff key).
3. A transaction whose key already exists: skip (do not duplicate). A transaction with a new key inside the current window: insert. A transaction with a new key but a sale date OUTSIDE the current 30-day window (i.e., it posted late) belongs in a `LATE-POSTED` flag per Step 1 — insert it, flagged, with its true (older) sale date.
4. If querying existing rows is genuinely not possible with available tools, do NOT fall back to blind-inserting — stop and escalate in the email instead (see escalation below) rather than risk duplicating the database.

## Property schema (exact names, same as the pilot)
`Property Address` (title), `County` (select: `Franklin OH`/`Baltimore Co MD`/`Polk IA` — add a new select option only for these three, never invent others), `State` (select: `OH`/`MD`/`IA`), `Market` (select: `Columbus`/`Maryland`/`Des Moines`), `Parcel ID`, `Sale Date`, `Sale Price`, `Building SF`, `SF Source`, `Price PSF`, `Buyer`, `Seller`, `Use Code`, `Use Description`, `Flags` (multi-select: `NONARMS`/`CONTRACT-SALE`/`MULTI-PARCEL`/`LATE-POSTED`/`ORA-AFFILIATED`/`SF-UNPUBLISHED`), `Source`, `Run Date` (today's date for every row written this run).

## Ground rules
- Never fabricate rows, field values, or a "clean" result if a pull failed. If a county's endpoint has drifted or is unreachable, say so explicitly in the email rather than silently producing a thin or empty digest.
- Do not run owner-scoring, buy-box gates, or any exclusion tier beyond government/exempt (Step 3) — this is market intelligence, not an acquisition screen. That is county-parcel-screen's job, not this one.
- If you find a genuine, confirmable gap in county-parcel-screen's `county-endpoints.md` (a field that's drifted, a new undocumented field), do NOT edit that file yourself from an unattended run — note it in the email under a "QUESTIONS FOR GABRIEL / findings to review" heading instead. That file is shared and single-writer; unattended edits to it are out of scope for this task.

## KNOWN SOURCE LAG — Baltimore Co MD (found 2026-08-15, do not re-derive this)
Baltimore Co MD's TRADATE field runs **~4+ months behind actual recording** — the pilot's own data showed a clean taper (8 transactions in Feb 2026, 3 in Mar, 3 in Apr) then **zero from May through the pull date**, despite the query window running current. This is expected, ongoing source behavior, not a defect. Before treating a quiet Baltimore Co result as a coverage-regression finding: check whether the most-recent sale date in the fresh pull is OLDER than the most-recent sale date already in the Notion database for that county (a genuine widening of the lag, or the source going fully dark) — that would be a real finding. A Baltimore Co result that simply mirrors the same few-month lag as last run is NOT a finding and should not trigger an escalation or a "QUESTIONS FOR GABRIEL" line on its own.

## Deliver
1. Upsert new/updated rows into the Notion data source per the rules above. If an insert returns no page ID (e.g. a grace-period/quota notice), search by the exact row key (County + Parcel ID + Sale Date + Sale Price) before any retry — a match created at/after the create call is this run's row; never blind-retry a create. Quota errors → `notion-quota-fallback` skill.
2. Send an email via Outlook COM: `powershell.exe -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "[ORA] County Sales Monitor - Monthly Digest - <today's ISO date>" -BodyFile <path to an HTML file you write> -BodyFormat html`. Compute the run date once at run start (`date '+%A %Y-%m-%d'`; date part in every date slot, weekday only where one is named) and reuse that exact value in every title, subject and body. This is the SOLE send path — no other method, no cc (the ora-am-brief Daily Brief cc-Eric exception does not apply here). On a non-zero exit code: retry once after a short pause; if it fails twice, note the failure in this run's completion summary rather than silently dropping the digest.
3. Email body: per-county count of new transactions this run, coverage line for each of the 3 counties (including "0 new transactions" as a real, valid result — distinguish that from "county endpoint unreachable," which is a finding, not a quiet zero). For Baltimore Co MD specifically, apply the KNOWN SOURCE LAG rule above before calling a quiet result a finding. Include median $/SF where derivable, any LATE-POSTED rows found, and a short "QUESTIONS FOR GABRIEL" section for anything genuinely ambiguous or a real data-quality finding (per the ground rules above) — never fabricate an answer to fill that section, and omit it entirely if there is nothing real to raise.

## If this is the very first run and the 30-day window logic or upsert query genuinely cannot execute
Do not guess. Send the email anyway with an honest explanation of what blocked the run and what a human needs to check, rather than silently failing with nothing sent.