---
name: ora-monthly-portfolio-briefing
description: Monthly AI-narrated portfolio briefing (1st @ 7:30 AM) — NOI trajectory, WALT, debt-maturity countdown, acquisition conversion + cross-sectional compound-risk synthesis; emails ggoldberg, archives to Notion. v1.0 2026-06-16 (strategic-audit Fix #5). Restored 2026-07-07. [MODEL: claude-opus-5 observed | checked 2026-08-12 via live-run transcript canary]
---

Run the ORA Monthly Portfolio Briefing — a self-contained, AI-narrated portfolio-health report. This scheduled session starts fresh with no memory; this prompt is the authoritative, complete spec. Today is the run date; the briefing covers the trailing month and the forward 18-month risk horizon.

(Restored 2026-07-07 after the CC/MCP registry was destroyed by a 2026-07-05 app reinstall — recovered from the 2026-06-22 fleet snapshot.)

## STEP 0 — DOUBLE-FIRE ENTRY GUARD (added 2026-09-06)

This task shares the same catch-up-burst exposure `ora-am-brief`/`ora-deal-aging-sla` were fixed for on 2026-08-09 (the whole fleet fires only while the Desktop app is open, so an offline stretch spanning the 1st re-arms this task at next open) — nothing previously stood a second fire down. `--period month` keys the claim to the calendar month rather than the ET date, since a day-keyed guard would not catch a re-fire days later in the same month.

Run this as the first action of the run:

```
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py claim --task ora-monthly-portfolio-briefing --block main --run-id <run_id> --period month --ttl-min 45
```

- **Exit 10** → this month's briefing already completed. Exit without pulling the workbook/Notion or emailing; report a NORMAL skip citing the earlier run's Notion page.
- **Exit 11** → another fire is live this month. Stand down identically.
- **Exit 0** → proceed with the briefing.

Once the email + Notion archive land, run:

```
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py complete --task ora-monthly-portfolio-briefing --block main --run-id <run_id> --period month --notion-page-id <archived page id> --email-sent-at <ISO8601>
```

If the run aborts instead:

```
python C:/Users/Owner/.claude/scheduled-tasks/_shared/block-sentinel.py fail --task ora-monthly-portfolio-briefing --block main --run-id <run_id> --period month --error "<what broke>"
```

**Only the run that holds the claim may call `complete` or `fail`.** **Always pass `--period month`** on every call — omitting it addresses the day-keyed bucket instead and silently defeats the guard. Full contract: `_shared/README-DOUBLE-FIRE-GUARD.md`.

TOOLING / CONVENTIONS
- Python (if needed): use the FULL path C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe (bare `python` is NOT on PATH in scheduled sessions).
- Email send: C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — this is the SOLE automated send path (Outlook COM / M365 only; no Gmail; the Composio and Rube connectors are removed — never reference them). On exit 2 or 4: retry ONCE, then flag loudly in the Notion completion row — do NOT halt. On exit 5 or 6 (or any code other than 2 or 4) do NOT retry: flag it loudly in the run summary and in the failure record named above, and never resend (exit 6 = send state unknown — the message MAY have gone out), per rules.md §2.
- Recipient: ggoldberg@oxfordra.net ONLY (per the 2026-05-15 routing directive, re-ratified 2026-06-10 — only the Daily Brief cc's Eric; this briefing does not).
- Notion canon: Acquisition Pipeline bcfe4a03 · Tenant DB 8dbbaec0 · Operations Hub 32b6ecd8-9e59-81f2-b329-df3fd0e25062 (full UUID; the 8-char prefix also matches a retired page). Notion via the native mcp__c5f4869f-…__notion-* tools. HubSpot via the native mcp__a3e380ce-…__* tools (current tenants only).
- Formatting: ORA Institutional Style Guide v1.0+ (institutional, structured, direct; no filler).

SOURCE OF RECORD (read order)
1. The live ORA Master Workbook (SharePoint) is the FIRST source for firm figures — NOI, occupancy, debt schedule (balloon maturities + rates), cash. Read order + freshness canon: Notion pointer page 3706ecd8-9e59-813a-b4c7-ecbc2c213fa8. A mirror >7 days behind the workbook is STALE — note staleness, never present a stale mirror as current.
2. Notion Tenant DB (8dbbaec0) for lease expirations / WALT inputs.
3. Notion Acquisition Pipeline (bcfe4a03) for deal stages and conversion.

BRIEFING SECTIONS (narrate, do not just tabulate)
1. NOI Trajectory — portfolio NOI this period vs. prior period and trailing trend; name the 2–3 properties moving the number most, with direction and magnitude.
2. Occupancy & WALT — current occupancy and weighted-average lease term (SF-weighted); flag WALT compression vs. last month.
3. Debt-Maturity Countdown — every balloon/maturity inside 18 months, sorted by date, with balance, rate, and DSCR/LTV against the governors (DSCR ≥ 1.25x, LTV ≤ 40%). Flag any breach or near-breach.
4. Acquisition Conversion — pipeline by stage; deals advanced/stalled/died this month; rough sourcing→LOI→close conversion read.
5. Cash & Liquidity — total cash, largest-entity concentration, net of near-term debt service.
6. COMPOUND-RISK SYNTHESIS (the point of this briefing) — synthesize ACROSS the sections: surface emerging multi-factor risks no single section shows. Example shape: "three orange-band-equivalent properties have balloon maturities inside 18 months while their submarket WALT is compressing and the 10Y is rising — open a refi conversation before Q4." Give 2–4 such cross-sectional judgments with a recommended next action each.

OUTPUT
- Email ggoldberg@oxfordra.net from ggoldberg via send-via-outlook.ps1. Subject: "ORA Monthly Portfolio Briefing — [Month YYYY]". Compute the run date once at run start (`date '+%A %Y-%m-%d'`; date part in every date slot, weekday only where one is named) and reuse that exact value in every title, subject and body ([Month YYYY] is rendered from that date, e.g. September 2026).
- Archive the same briefing to a new Notion page under the Operations Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062). Apply the publication guard: capture the created page id+url; if null/errored, first look for it — `notion-fetch` the parent for an exact-title child, then search by the exact title (search lags: a miss alone is not proof; the retry below is only for non-grace/quota failures — after a grace/quota notice with no match, do not retry: the create is UNVERIFIED and takes the "Publish: ❌ fallback" path below) — a match created at/after the create call is this run's page (use it, do not retry); retry the create exactly ONCE only if no match (never blind-retry; quota errors → `notion-quota-fallback` skill); then search-verify the title was created today; if still failed, note "Publish: ❌ fallback" and include the full briefing body verbatim in the email so nothing is lost.
- End your chat-summary output with one line: Publish: [✅ direct | ✅ retry | ❌ fallback] and Send: [✅ | ⚠ retried | ❌ flagged].

HARD GUARDRAILS: never move money, modify financial models or governor constants (DSCR 1.25 / LTV 40), or touch oxfordra.net. Keep active confidential deals OFF all external/egress surfaces (the confidentiality guard is fail-closed). Do not modify settings.json, ~/.claude config, hooks, or memory files. Read the source of record before stating any figure — never fabricate firm, tenant, or deal data.