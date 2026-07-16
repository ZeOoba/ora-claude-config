---
name: ora-dashboard-refresh
description: Refreshes the ORA Portfolio Command Center dashboard — re-extracts the Master Workbook, re-pulls Notion pipeline + HubSpot, writes data JSONs, redeploys to Cloudflare Pages (ora-command-center.pages.dev, NOT oxfordra.net). Hard-gated confidentiality filter strips any "Fulton" reference before every deploy. Daily 07:00 ET. v1.1 2026-06-03 — already fully COM/ggoldberg-only compliant, no fixes needed.
---

RESTORATION NOTE: Re-registered 2026-07-07 (approved by Gabriel — this task deploys to a public Cloudflare Pages URL, flagged and explicitly approved before restoration) after the 2026-07-05 machine migration orphaned this task. Content restored verbatim — this file was already fully compliant with current canon (COM-only send, ggoldberg-only routing, explicit confidentiality gate), no fixes needed. Note: this deploys to ora-command-center.pages.dev, a separate Cloudflare Pages project — it is NOT oxfordra.net and does not require the oxfordra.net deploy-permission invariant, but it IS an external-facing surface, which is why it was held for explicit sign-off before this restoration.

# ORA Command Center — Daily Data Refresh + Redeploy

> **⚠️ RETARGET DEFERRED (Phase 3 Stage 2, 2026-06-03).** The Phase-3 plan calls for retargeting this task to the React `oxford-command-center` mirror. That is Phase 2 / G1 work and is NOT yet shipped — the React brain's build/deploy path is not established. **Until Phase 2/G1 lands, this task continues to refresh the working ECharts dashboard** (`oxford-perfection\ora-dashboard\` → Cloudflare `ora-command-center.pages.dev`). When the React mirror ships: replace Steps 1–4's data-write + `wrangler pages deploy` with the React mirror's bake/deploy, keep the E. Fulton confidentiality gate and the `history.json` time-series, and retire the ECharts project.
>
> **Companion task `ora-dashboard-finish` was KILLED (2026-06-03)** — do NOT recreate an autonomous overnight dashboard "build" task; the React brain (Phase 2) is the canonical successor.

Keep the live dashboard current. Run all steps; if a source fails, refresh what you can, still deploy, and note the gap. The dashboard project lives at `C:\Users\Owner\oxford-perfection\ora-dashboard\` (static site + `./data/*.json`).

## 🛑 CONFIDENTIALITY (hard rule)
The dashboard is **deployed externally**. The **E. Fulton Street Portfolio** is CONFIDENTIAL — it MUST NOT appear in `pipeline.json`, `hubspot.json`, or anywhere in the deployed build. Filter out any deal whose name/address contains "Fulton" (case-insensitive) before writing data. Verify before deploy. If this deal has closed by the time this task runs, confirm with Gabriel whether the filter can be lifted rather than assuming — default to keeping the filter active.

## 1. Workbook extraction (computed values)
Via Desktop Commander `start_process`, run:
`powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Owner\oxford-perfection\extract-all.ps1"`
Confirm it prints `OK` lines for property_noi, external_loans, cash_balances, rent_roll, insurance, am_fees and a final `DONE`. (Script copies the OneDrive workbook locally first to bypass the file lock, then parses cached values with openpyxl in `extract-all.py` — this avoids Excel COM returning bogus arrays when the master is open interactively.)

## 2. Notion acquisition pipeline → pipeline.json
Using the Notion MCP (`notion-search` on `data_source_url: collection://bcfe4a03-7e61-4ac1-a0bb-c44174fa138b`, then `notion-fetch` each deal page), rebuild the pipeline deal list with the SAME JSON shape already in `ora-dashboard\data\pipeline.json` (read the existing file first to match field names exactly). Per deal capture: Deal Name, Address, Market, Stage, Purchase Price, Total SF, Going-In Cap Rate, DSCR, Levered IRR, Equity Multiple, LOI Status, PSA Status, IC Memo, Target Close Date, Next Action, Last Updated. **EXCLUDE any "Fulton" deal and non-deal pages (e.g., "Stall Alert").** Overwrite pipeline.json.

## 3. HubSpot → hubspot.json (best-effort)
Pull current deals via the HubSpot MCP (uuid a3e380ce-…: `list_open_deals` / `search_crm_objects`). If meaningful, write hubspot.json matching its existing shape; if stale/empty, leave the prior file and note it. Exclude any "Fulton".

## 3b. Trends history + macro + calendar + freshness (THE "MEMORY")
- **History (every run — powers trends/sparklines):** read `ora-dashboard\data\history.json` (an array), compute today's key metrics from the freshly-extracted data, and append `{date, portfolioValue, noi, capRate, totalDebt, ltv, dscr, occupancy, totalCash, tenants, annualRent, pipelineValue, activeDeals}`. Dedupe by date (replace same-day entry). Never delete prior points — this is the firm's time-series memory.
- **FRED macro → `data\macro.json`:** via FRED MCP pull latest DGS10/DGS5/DGS2/SOFR; write `{asOf,dgs10,dgs5,dgs2,sofr,t10y2y}`.
- **Outlook calendar → `data\calendar.json`:** via M365 MCP `outlook_calendar_search`, pull events for the next 90 days (closings, IC meetings, renewal/tax-appeal deadlines). Best-effort; skip on failure.
- **Freshness → `data\_meta.json`:** rewrite `{generatedAt, sources:{workbook,notion,hubspot,fred,calendar}}` with current timestamps.
- Confidentiality still applies to calendar/pipeline: drop any "Fulton" item.

## 4. Redeploy to Cloudflare Pages
Via Desktop Commander `start_process`, run:
`npx wrangler pages deploy "C:\Users\Owner\oxford-perfection\ora-dashboard" --project-name=ora-command-center --commit-dirty=true`
If wrangler reports NOT authenticated / no project, do NOT fail the whole run — log a COVERAGE GAP "deploy skipped: wrangler not configured"; the data JSONs are still refreshed for the next successful deploy.

## 5. QC + confirmation
- Confirm `pipeline.json` and `hubspot.json` contain NO "Fulton" (grep before deploy) — this is a hard gate, do not deploy if it fails; fix and re-check instead.
- On any failure, send a single Outlook line to **ggoldberg@oxfordra.net only** (egoldberg removed 2026-06-03 per the 2026-05-15 directive) via `_shared\send-via-outlook.ps1` (the SOLE send path — Composio removed 2026-06-11; no fallback connector; on a non-zero COM exit retry once, then flag — do not halt), subject `⚠️ ORA dashboard refresh — [issue] [YYYY-MM-DD]`. On full success, stay silent (no inbox noise); an optional one-line `✅ ORA dashboard refreshed [time]` at the 07:00 run is permitted.

## Notes
- Cadence is daily 07:00 ET.
- The dashboard's "what changed in Notion" companion role lives in the live `ora-pm-ledger` Block A (18:00) — different output (that one emails; this one refreshes the dashboard).