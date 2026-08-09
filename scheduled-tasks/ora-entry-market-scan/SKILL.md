---
name: ora-entry-market-scan
description: Monthly sourcing + screening scan for 4 ORA entry markets (Louisville KY, Delmarva MD/DE, Grand Rapids MI, Des Moines IA) — buy-box filter, SCREEN-mode underwriting, Notion Deal Sourcing Log dedup + update, price-watch re-engage alerts, digest email to ggoldberg only. Complements ora-deal-sourcing-scan (established clusters). v1.1 (2026-07-14): specified a per-listing `Gate Review` Notion field so a Louisville/Delmarva off-taxonomy GATE-FLAGGED listing Gabriel already reviewed doesn't re-ask the identical review question every month while it sits unchanged on-market. v1.2 (2026-08-04): the field specified in v1.1 was never actually created in Notion — it was simulated as free text in `Notes / Flags` for two runs. CREATED 2026-08-04 on Gabriel's approval and all rows backfilled; blank now means "awaiting Gabriel" and must never be placeholdered. v1.3 (2026-08-04): added a mandatory Step 2 doctrine-version check — confirm the live `acquisition-underwriting` skill's ratified RCT version and vintage-ramp floor before scoring any Basis, after the 2026-07-22 run silently computed every basis floor on RCT v02 constants retired 8 days earlier. v1.4 (2026-08-09): retimed 11:00 → 11:45 ET (its 1-7/Tue slot only). First retimed to 11:30, but fleet-status.py (which reads both fleets) immediately surfaced a NEW collision there with LAMS-side `ora-ar-export-freshness-nudge` (days 1 & 15, 11:30) — the CC-only `list_scheduled_tasks` tool doesn't surface LAMS crons, so the first pick wasn't cross-checked against that fleet. 11:45 is clear on both fleets (checked directly against the live registries: 11:20 Mon, 11:00 daily, 11:05 weekdays, 11:30 day-1/15, 11:40 Mon are the only other 11:xx fires). Moved this side (the rarer, ~monthly task) rather than the daily `ora-skill-cache-drift-alert`, per the same minimize-blast-radius rule used for the 2026-07-27 ora-site-exposure-probe/ora-calibration-snapshot retimes. v1.5 (2026-08-09): LOUISVILLE KY REMOVED FROM THE OFF-TAXONOMY CLAUSE — Gabriel ratified it as ORA's 10th canonical cluster (entry-phase) 2026-08-05 (target-markets.json v1.7/v1.8, acquisition-underwriting v4.10), one day after the 2026-08-04 run. Delmarva MD/DE is now the sole off-taxonomy market here; Louisville scores like Grand Rapids/Des Moines (no Ruling 5 market cap, no auto-GATE-FLAGGED, no blank Gate Review, Market baseline 8/12, Ruling 3 unchanged). Caught by the v1.3 doctrine-version check on its first live outing — same failure class as the RCT v02 incident it was built for, different constant (market taxonomy, not the cost table). Six Notion rows re-scored Market 7 to 8 the same day; one verdict flipped (2990 W Jefferson St, PASS-band to T2 WATCH at Combined 60); Gabriel's pending gate-review queue fell 6 to 3, all Delmarva. [MODEL: UNVERIFIABLE | checked 2026-07-12]
---

Read and follow C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\SKILL.md in full before taking any action.

# ORA Entry Market Scan — Monthly Execution

You are running the monthly ORA entry market scan for 4 markets where ORA has NO current holdings but is actively monitoring for acquisition entry:
1. Louisville KY (Jefferson County)
2. Delmarva Peninsula MD/DE (Wicomico/Dorchester/Caroline MD + Sussex/Kent DE)
3. Grand Rapids MI (Kent County)
4. Des Moines IA (Polk County)

## Execution sequence

### Step 1 — SOURCE
Search LoopNet, Crexi, CommercialSearch, CommercialCafe, and local broker listing pages in each of the 4 markets for currently-marketed industrial/flex for-sale listings.

Subagent dispatch guardrail (validated 2026-07-07 — see memory feedback_subagent_anti_delegation.md): if this step is fanned out to per-market subagents (e.g. one Agent-tool dispatch per market), every dispatch prompt MUST explicitly forbid the subagent from calling Agent/Task/Workflow itself and MUST require its final message to be the actual findings, never a status/progress update. Without this, roughly half of Tools:* subagents given an open-ended "scout multiple sources" prompt will recurse into a child call and return a placeholder narration instead of data (confirmed on the 2026-07-07 ora-deal-sourcing-scan run: 4/9 first-pass agents recursed at ~65K wasted tokens each; 0/7 recursed once the guardrail clause was added). A per-market agent returning in under ~5 tool calls almost certainly delegated rather than worked — re-dispatch with the guardrail before trusting a thin result.

Apply ORA buy-box filter:
- Price: $500K–$10M
- Size: < 50,000 SF per building
- Type: Class B/C industrial or flex (shallow-bay multi-tenant, flex, office-warehouse, single-tenant ≤40K SF, quasi-IOS)
- Exclude: pure retail, pure office, automotive use, >50K SF single building, multistory warehouse

### Step 2 — SCREEN

**Doctrine-version check (v1.3, 2026-08-04 — mandatory, run BEFORE scoring any listing):** load the live `acquisition-underwriting` skill and read its currently-ratified Replacement Cost Table version and vintage-ramp floor percentages directly from that file — do not reuse constants cached in this task, in memory, or in a prior run's output. State the confirmed doctrine version explicitly in this run's output (e.g. "RCT v03, 65%/60% vintage ramp") before any Basis floor is computed. If the version cannot be confirmed live (skill unreadable, ambiguous version marker), **stop and flag it loudly in QUESTIONS FOR GABRIEL** — do NOT silently fall back to a remembered or cached constant table.
  - **Why this exists:** the 2026-07-22 run computed every basis floor in Louisville, Delmarva, Grand Rapids, and Des Moines on RCT v02 constants and the retired 30%/25% vintage cliff — both superseded by RCT v03 + the 65%/60% ramp ratified 2026-07-14, eight days before that run executed. One verdict was materially wrong as a result (1700 Industrial Park Dr, Federalsburg MD: T2 WATCH under v02 → PASS-band under v03, since Maryland tightened ~23% in the correction). Basis is 25 of 45 Economics points, so every score in that run's pipeline ranking was distorted, not just the one flipped verdict. Full incident record: memory `reference_entry_market_scan_defects_2026-08-04.md`.
  - **Every basis figure reported this run must cite the confirmed RCT version** (per-market LOW/POINT/HIGH and proxy market where applicable) alongside the [est] score — not just "RCT" or a bare dollar figure. This makes a future doctrine drift visible in the output itself rather than requiring a manual audit to catch.

For each qualifying listing, run SCREEN-mode acquisition underwriting (Buy Box & Scorecard v1.1, Rulings 1–5 + Amendments A–G):
- Gates → Floors → Quality Score + Economics Score → Combined Score [est] → Bear-Mode State (from CoStar/broker quarterly data) → P(exec)% → Expected Score → Verdict (T1-PURSUE / T2-WATCH / PASS)
- ORA hurdle rate: 8% (ratified 2026-06-22). DSCR governor ≥ 1.25x. LTV governor ≤ 40%.

Critical market flags:
- **Delmarva MD/DE — the SOLE off-taxonomy market in this task.** Cap Quality Score market component at 60 per Ruling 5. Any T1/T2 verdict = GATE-FLAGGED. Requires Gabriel's explicit review before advancing. Once Gabriel has reviewed a specific listing (recorded in that listing's `Gate Review` field, Step 3), do NOT re-surface it as GATE-FLAGGED in a future run at an unchanged verdict/price — only re-flag it if the score, price, or listing status materially changed since the ratified review. This prevents the same off-taxonomy listing from re-asking Gabriel an identical review question every month while it sits unchanged on-market.
- **Louisville KY — RATIFIED entry cluster, NOT off-taxonomy (v1.5, 2026-08-09).** Gabriel ratified Louisville KY as ORA's **10th canonical cluster (entry-phase) on 2026-08-05** — `target-markets.json` v1.7/v1.8 (changelog_1_7) and `acquisition-underwriting` v4.10 (PROVISIONAL language removed at STAGE 0 Gate 3 and the exit-cap table). Score Louisville **exactly as Grand Rapids and Des Moines are scored: NO Ruling 5 market cap, NO automatic GATE-FLAGGED status, NO blank `Gate Review`.** The peer-matched Quality Market baseline for a ratified entry cluster is **8/12** before any fundamentals adjustment — the value this task itself assigned to 550 Richmond St NW, 2134 E Grand Ave and 11 College Ave on 2026-08-04. **Ruling 3 is UNCHANGED and still governs:** entry clusters, Louisville included, earn NO satellite eligibility until ORA's first closed deal validates the cluster. Exit cap 7.75%. RCT: no native entry — **[PROXY: Indianapolis] LOW $253.83/SF**, so Louisville still carries DENOMINATOR-SENSITIVE.
  - ⚠️ **Do not re-derive the cap from a row label.** The Step 2 doctrine-version check above is the sole authority on market taxonomy — never a cached label, a prior run's output, or this bullet if the live skill has moved on. **Label sweep COMPLETED 2026-08-09:** all 7 Louisville rows in the Notion Deal Sourcing Log were relabelled `Louisville KY / <submarket> (ratified entry cluster 2026-08-05)`; zero Louisville rows still carry `(off-taxonomy)` or `(off-cluster)`. The 6 Delmarva rows correctly RETAIN theirs — Delmarva is still off-taxonomy.
  - 🚩 **Bullitt / Oldham / Shelby County is NOT automatically in-cluster.** The ratification covers **Louisville = Jefferson County**, which is also this task's declared scan scope (Step 1). Outlying Louisville-MSA counties are **satellites**, and STAGE 0 Gate 3 / Ruling 3 is explicit that entry clusters earn **NO satellite eligibility until ORA's first closed deal** validates the cluster. Surfaced 2026-08-09 by 215 Charles Hamilton Way, Shepherdsville (Bullitt Co), which was deliberately NOT relabelled a plain ratified entry cluster for exactly this reason — moot on that row, since it is separately product-disqualified as self-storage, but the distinction must not be lost on the next outlying-county listing.
- Grand Rapids MI: Michigan Proposal A applies. Append PROP-A-UNCAP-PREMORTEM-REQUIRED to every MI listing.

### Step 3 — LOG
Dedup against and update the Notion Deal Sourcing Log (collection ID: 9a6ae219-85a3-4621-899c-c757fd062f8b):
- Match on address (≥90% similarity) or listing URL (exact). Update existing records in place — do NOT duplicate.
- Create new records for first-time listings.
- Log: Quality Score, Economics Score, Combined Score [est], P(exec)%, Expected Score, Verdict, Source URL, Broker, Confidence (VERIFIED/SNIPPET), Seller Signals, Bear-Mode State, DD-Critical Status, Screen Date, Source Task = ora-entry-market-scan.
- **Gate Review** field (specified v1.1 2026-07-14; **actually created in Notion 2026-08-04** — see the correction note below. **For Delmarva GATE-FLAGGED listings only** — Louisville was removed from this scope in v1.5, 2026-08-09, on its ratification as a canonical entry cluster): blank until Gabriel reviews; once he does, record `Cleared-<date>` or `Rejected-<date>` plus a one-line note. This is the durable ratification Step 2 checks before re-flagging — it stops an unchanged off-taxonomy listing from re-asking the identical review question every month.
  - **Correction (2026-08-04):** v1.1 described this field as added on 2026-07-14, but it was never created — the live schema had no such property, and the 2026-07-22 run silently worked around it by writing the literal string `Gate Review: (blank)` into `Notes / Flags`. The ratification mechanism was therefore prose-only and unqueryable for two runs. The real `Gate Review` rich-text property was created on 2026-08-04 with Gabriel's approval (`ADD COLUMN "Gate Review" RICH_TEXT`) and every existing row backfilled.
  - **Three permitted values — blank is load-bearing:**
    - **blank** → awaiting Gabriel's first review. **ONLY off-taxonomy Delmarva rows at T1/T2 should ever be blank** (v1.5: Louisville rows must NOT be left blank — it is a ratified cluster now, so its T1/T2s take `N/A — ratified cluster` exactly as Grand Rapids and Des Moines T1/T2s do). Scope note: this convention holds for rows written by THIS task. A full-log query on 2026-08-09 found many blank `Gate Review` rows across Columbus, Cincinnati, KC, Indianapolis and Maryland — sibling-task rows the 2026-08-04 backfill (17 rows) never covered. Do not read blank as "awaiting Gabriel" outside this task's four markets.
    - `Cleared-<date>` / `Rejected-<date>` + one-line note → Gabriel has ratified. These are the only values that count as a review.
    - `N/A — <reason>` → gate review does not apply: the verdict is PASS-band, or the market is a ratified cluster (**Grand Rapids, Des Moines, Louisville KY** — Louisville added v1.5, 2026-08-09), or the blocker is a product/environmental/data issue rather than an off-taxonomy question.
  - **⛔ NEVER write `AWAITING REVIEW` or any other non-blank placeholder into a row genuinely awaiting Gabriel.** Step 2 treats any non-blank value as ratified, so a helpful-sounding placeholder would permanently suppress the very review question this field exists to raise. Blank IS the signal — leave it blank.
- Never overwrite prior immutable score snapshots — add new dated fields alongside prior entries.

### Step 4 — PRICE-WATCH
For any previously-screened deal in these 4 markets logged as PASS/T2-WATCH with a gap-to-ask >30% (ask was >30% above ORA walk price at last screen): check current listing price. If the current ask is within 5% of the ORA walk price (basis floor), flag as RE-ENGAGE, update the Notion record, and elevate to top of email.

### Step 5 — EMAIL
Send summary email via Outlook COM:
- Script: C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1
- To: ggoldberg@oxfordra.net ONLY (never cc egoldberg@, never ze@ addresses)
- On COM failure: retry once, then log failure to Notion Ops Hub (32b6ecd8) — do NOT halt
- Subject: "ORA Entry Market Scan — [Month YYYY]: [N] New Candidates, [N] Watched, [N] Passed"
- Body: RE-ENGAGE alerts first (if any), then T1/T2 ranked table (address, market, ask, SF, $/SF, Combined [est], P(exec)%, Expected Score, verdict, top seller signal, flags) — for any GATE-FLAGGED Delmarva listing already carrying a `Gate Review` ratification, mark it "reviewed <date>" in the table instead of re-asking, then market summary, then data gaps / questions for Gabriel (genuinely new items only)

## Invariants
- READ-ONLY task: no LOIs, no counterparty emails, no underwriting commits, no capital decisions.
- Never fabricate listings, scores, or market data. Zero qualifying results = state that explicitly per market.
- Never send to Eric (egoldberg@) — ggoldberg@ only on this task.
- If Notion MCP unavailable: write results to C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\outputs\YYYY-MM-DD_entry-scan-results.json and note fallback in email.
- After each run: archive summary to C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\outputs\YYYY-MM-DD_entry-scan-summary.json

## Sibling tasks (do NOT re-scan their scope)
- ora-deal-sourcing-scan covers ORA established clusters (Columbus, Cincinnati, Indianapolis, Madison, Kansas City, Maryland/DC) — weekly Tuesdays. Do not overlap.

Full procedure, scoring rubric, Notion field map, and escalation logic: C:\Users\Owner\.claude\scheduled-tasks\ora-entry-market-scan\SKILL.md