---
name: exception-detection
description: "Automated anomaly and exception detection across Oxford Realty Advisors operations. Use when scanning for financial anomalies, tenant exceptions, deal pipeline risks, or system/process failures. Triggers: exception scan, anomaly detection, what's wrong, flag issues, portfolio exception scan, scan for problems, audit exceptions, find anomalies, red flags. Tenant risk scoring / WALT / concentration analytics route to tenant-intelligence. v1.5 — changelog in body."
---

## Changelog (moved from description 2026-07-29 — Phase-4 description token-budget lint; trigger vocabulary unchanged)

v1.5 (2026-09-06: routing only, no detection logic changed — ORA Automation Audit R23-9. Revision 22's own collision fix created a new collision: `10ecba4` moved this skill's trigger from "health check" to "portfolio health check" to de-collide from `automation-health-monitor`'s "fleet health check", and landed it on `tenant-intelligence`'s pre-existing bare "portfolio health". Resolved by construction rather than by spending CLAUDE.md budget: this skill's literal is now "portfolio exception scan", which matches its own identity and CLAUDE.md's "Exception scans" tie-break, and drops the word "health" entirely. Added an explicit deferral for tenant risk / WALT / concentration analytics to `tenant-intelligence`. Each of the three phrases now has exactly one owner: `automation-health-monitor` = fleet health check, this skill = exception scan, `tenant-intelligence` = portfolio health metrics.); v1.4 (2026-08-12: Category 3 hardened — three rules were unfirable or reading the wrong field, and the highest-severity one had been reporting clean while structurally dead. (1) The 🔴 Critical "deal in DD with deadline <7 days" rule keys on `Target Close Date`, which is NULL on every non-terminal deal and has been portfolio-wide since at least 2026-07-31 — the same wall `ora-health-guard` 4d hit and was given a verified-null rule for. Zero possible matches, reported as "no critical exceptions." It now emits `deals_with_null_target_close` / `deals_with_populated_target_close` and states the rule is non-functional pending a backfill, never a bare 0 (note A). (2) New 🔴 companion row reads the `Next Action Date` property added to the tracker 2026-08-11, giving Category 3 a deadline check that can actually fire; PARKED deals downgrade to 🟡 "re-check due" (note C) — a dry-run showed the naive rule would have alarmed Critical on 5515 Catfish Court's own Gabriel-scheduled 08-14 revisit, i.e. on a hold behaving exactly as instructed. (3) Two 🟠 rows ("stuck >21 days", "LOI >14 days no PSA") keyed on `Last Updated`, Notion's system last-edited timestamp — the conflation `ora-deal-command-board` STEP 2 was hardened against 2026-07-17, origin 754 Old State Route 74 false-flagging STALLED at 36 days mid-PSA — and now use the ratified `Last Activity` → `Last Updated` → `createdTime` chain, stating which rung a flagged row used (note B). Scope note: the original rule's `Stage = "Due Diligence"` restriction was left alone; no open deal is in that stage today, so widening it is a semantic decision for Gabriel, flagged in note A rather than made.); v1.3 (2026-08-11: Category 2 extended with a 4th HubSpot cross-check — lease-renewal deal name/target date vs. Notion Lease Expiration drift. Root case: MO Dept of Agriculture — Notion Lease Expiration 2026-12-31 vs. its linked HubSpot deal "MO Dept of Agriculture — Lease Renewal 2026-06-30" (closedwon), a 6-month gap the existing 3 checks don't catch because the deal isn't stale (recently closed) and isn't a name/DB mismatch — it's a stale deal TITLE surviving a term extension. Surfaced by ora-lease-expiration-brief's 2026-08-10 run.); v1.2 (2026-07-21: Category 2 extended with 3 tenant-status cross-checks against HubSpot Lease Renewal deals — archived/vacated/terminated-vs-open-deal conflicts, past-due-untouched deals, and no-counterpart-in-either-system rows; v1.1 2026-06-11: Composio recipe checks retired — connector removed; Category 4 now checks dual-fleet scheduled tasks + dead-man heartbeat)

You are the Oxford Realty Advisors exception detection engine. You scan all connected data sources — Notion, HubSpot, QB exports — and surface anomalies that require human attention, categorized by severity.

---

## EXCEPTION CATEGORIES

### Category 1 — Financial Exceptions

| Exception | Severity | Detection Method |
|-----------|----------|-----------------|
| AR balance >$5,000 and 30+ days | 🔴 Critical | Notion: AR Balance > 5000 AND AR Aging Bucket != "Current" |
| AR balance >$0 and 90+ days | 🔴 Critical | Notion: AR Aging Bucket = "90+ Days" |
| Monthly rent not received by day 7 | 🔴 Critical | Notion: Last Payment Date > 7 days ago AND this month |
| NSF or returned payment | 🔴 Critical | QB export: look for NSF notation |
| AR balance increased month-over-month | 🟠 Elevated | Compare current vs. prior AR Data Date snapshot |
| Rent PSF below $2.50/SF (under-market flag) | 🟡 Watch | Notion: Rent PSF (Annual) / 12 / SF < 2.50/mo |
| QB export not received in 45+ days | 🟡 Watch | Notion: AR Data Date > 45 days ago for any entity |
| Missing rent roll entry (SF with no tenant) | 🟡 Watch | Property SF total vs. sum of tenant SF in Notion |

### Category 2 — Tenant Exceptions

| Exception | Severity | Detection Method |
|-----------|----------|-----------------|
| Lease expired with no renewal signed | 🔴 Critical | Notion: Lease Expiration < today AND Lease Status != "Expired" AND Renewal Status != "Renewal Signed" |
| Lease expiring <30 days, no action taken | 🔴 Critical | Notion: Lease Expiration within 30 days AND Renewal Status = "Not Started" |
| Insurance expired or not on file | 🔴 Critical | Notion: Insurance Status = "Expired" OR "Not on File" |
| No personal guaranty on lease >$5K/mo | 🟠 Elevated | Notion: Monthly Rent > 5000 AND Personal Guaranty = "None" |
| Lease expiring 31-90 days, no outreach | 🟠 Elevated | Notion: Lease Expiration within 90 days AND Renewal Status = "Not Started" |
| Insurance expiring within 30 days | 🟠 Elevated | Notion: Insurance Expiration within 30 days |
| Tenant grade D with lease >12 months remaining | 🟠 Elevated | Notion: Tenant Grade = "D — At Risk" AND lease term >12 months |
| Escalation date passed with no rent increase | 🟡 Watch | Notion: Next Escalation Date < today AND recent rent unchanged |
| HubSpot Contact URL missing | 🟡 Watch | Notion: HubSpot Contact = null AND Lease Status = "Active" |
| Security deposit not recorded | 🟡 Watch | Notion: Security Deposit = null AND Lease Status = "Active" |
| HubSpot "Lease Renewal" deal contradicts Notion tenant status | 🟠 Elevated | Cross-reference HubSpot deal stage/closedate vs. Notion Lease Status + Notes — flag when Notion documents a vacate, termination, or executed addendum (renewal/extension) that the HubSpot deal's stage doesn't reflect |
| HubSpot "Lease Renewal" deal past closedate, stage never advanced, no Notion signal either way | 🟡 Watch | HubSpot: dealstage = "appointmentscheduled" AND closedate < today; Notion has no corroborating Lease Status/Notes update — do not infer an outcome, route to Gabriel for a manual check |
| Tenant record exists in one system with no counterpart in the other | 🟡 Watch | HubSpot "Lease Renewal" deal's tenant name has no matching Notion Tenant DB row (or vice versa) |
| HubSpot lease-renewal deal name/target date drifts from Notion Lease Expiration | 🟡 Watch | Parse the ISO date embedded in the HubSpot deal name (e.g. "... — Lease Renewal 2026-06-30") and compare to the linked Notion tenant's Lease Expiration; flag any difference, including on closedwon deals — a closed deal is not proof the title is current, since the deal is often never renamed after a further term extension. Do not assume which side is correct; route to Gabriel to confirm whether the deal title is stale or the Notion field needs updating. |

### Category 3 — Deal Pipeline Exceptions

| Exception | Severity | Detection Method |
|-----------|----------|-----------------|
| Deal in Due Diligence with deadline <7 days | 🔴 Critical | Notion: Stage = "Due Diligence" AND `Target Close Date` within 7 days. **⚠ CANNOT FIRE AS WRITTEN — emit a COVERAGE GAP, never a silent clear. See note A below.** |
| Deal with a next-action date inside 7 days | 🔴 Critical (🟡 Watch if PARKED) | Notion: Stage non-terminal AND resolved next-action date within 7 days. Chain: `date:Next Action Date:start` → explicit ISO date in `Next Action` prose → null (identical to `ora-deal-command-board` STEP 2b — keep in sync). **PARKED deals downgrade to 🟡 "re-check due" — see note C.** Added 2026-08-12; see note A. |
| Deal stuck at same stage >21 days | 🟠 Elevated | Notion: resolved **activity date** > 21 days ago AND Stage not terminal. Chain: `date:Last Activity:start` → `Last Updated` → `createdTime`. **Not `Last Updated` alone — see note B.** |
| LOI submitted >14 days with no PSA | 🟠 Elevated | Notion: `LOI Status` = "Submitted" AND resolved **activity date** > 14 days. Same chain and caveat as above (note B). |
| IC Memo not started for deal in DD | 🟠 Elevated | Notion: Stage = "Due Diligence" AND IC Memo = "Not Started" |
| Environmental not ordered for Under Contract deal | 🟠 Elevated | Notion: Stage = "Under Contract" AND Environmental = "Not Ordered" |
| IRR model not built for LOI-stage deal | 🟡 Watch | Notion: Stage = "LOI Pending" OR "LOI Executed" AND IRR Model = "Not Started" |
| Deal with no Next Action entry | 🟡 Watch | Notion: Stage not Closed/Passed AND Next Action = null |

**Note A — the 🔴 Critical deadline rule cannot fire on `Target Close Date`, and reporting it clean is a lie (added 2026-08-12).** `Target Close Date` is NULL on every non-terminal deal and has been since at least 2026-07-31, when `ora-health-guard` block 4d hit the identical wall and was given a verified-null rule for it. A scanner whose highest-severity rule has zero possible matches reports "no critical exceptions" when the truth is "the field this check depends on is empty portfolio-wide" — per `feedback_verified_null_vs_inferred_null.md`, a zero that could mean "couldn't look" is a failure, not a pass. Therefore: **whenever this rule evaluates, emit `deals_with_null_target_close: <n>` and `deals_with_populated_target_close: <n>` alongside the result, and state explicitly that the rule is non-functional pending a `Target Close Date` backfill.** Never emit a bare "0 critical."

The companion row added the same day gives Category 3 a deadline check that *can* fire, reading the `Next Action Date` property added to the tracker 2026-08-11 (populated on 3 of 9 open rows that day). Keep the two rows and their counters **separate** — a Critical tier that silently switched inputs would make a structurally-dead check look revived. **Do NOT backfill either date field yourself**: inventing a deadline on a live deal record is a Hard-Invariant-7 fabrication. Surface the gap; the deal-touching skills stamp `Next Action Date` (see `acquisition-underwriting` PIPELINE & LOGGING, `loi-generation` Phase 6, `deal-execution` NOTION PIPELINE STAMPING, all wired 2026-08-12).

**Open semantic question, flagged not decided:** the original rule scopes to `Stage = "Due Diligence"`, and as of 2026-08-12 **no open deal is in that stage** — ORA's live rows sit at Candidate and Under Contract. So even with a working date field the original row would catch nothing. 754 Old State Route 74 is Under Contract with a running Feasibility Period and arguably belongs in a "deadline imminent" Critical check. Widening the stage scope is a real change to what this rule means and is Gabriel's call — it was deliberately NOT made here.

**Note B — staleness reads the ACTIVITY date, never `Last Updated` alone (corrected 2026-08-12).** Two 🟠 rows above previously keyed off `Last Updated`, Notion's system last-edited timestamp. That conflates any edit with real deal progress AND freezes when work happens off-Notion — both failure directions at once. It is the exact defect `ora-deal-command-board` STEP 2 was hardened against on 2026-07-17, whose origin case was 754 Old State Route 74 false-flagging STALLED at 36 days while under active PSA negotiation, purely because a cosmetic field hadn't moved since 6/11. Use the ratified chain — `date:Last Activity:start` → `Last Updated` → `createdTime` — and say which rung a flagged row used, so coverage gaps stay visible. A row flagged off rung 2 or 3 is weaker evidence than one flagged off rung 1 and should be reported as such.

**Note C — a PARKED deal's scheduled re-check is the park WORKING, not an exception (added 2026-08-12).** Category 3 previously had no PARKED concept at all, which was survivable only because no rule read a forward-looking date. The new next-action-date row changes that: a `Next Action` containing `PARKED` / `⏸` frequently carries Gabriel's own revisit date, so the naive rule would fire 🔴 Critical on a hold behaving exactly as instructed. Concrete case at the time of writing: 5515 Catfish Court, parked 2026-07-24 with "Revisit 2026-08-14" — three days out, and not an exception in any sense.

Rule: when the resolved date belongs to a deal whose `Next Action` contains `PARKED` / `⏸`, report it as 🟡 **"re-check due"** with the parked date, never as 🔴 Critical, and never fold it into the Critical count. This matches the PARKED handling already ratified in `ora-deal-command-board` STEP 2, `ora-deal-aging-sla` STEP 3d, and `ora-health-guard` 4d (`parked_not_actionable`) — four sites now, and the treatment must stay consistent across them. An explicit Gabriel-ratified hold is a different state from silent staleness, and collapsing the two trains a false alarm into the tier that is supposed to mean "act now."

### Category 4 — System & Process Exceptions

| Exception | Severity | Detection Method |
|-----------|----------|-----------------|
| Scheduled task missed execution | 🔴 Critical | Check automation-health-monitor last run log |
| Dead-man heartbeat stale (>16h) | 🔴 Critical | Check ora-cowork-heartbeat Notion timestamp page (Composio recipes RETIRED 2026-06-11 — no Composio checks remain) |
| QB export overdue (>45 days since last) | 🟠 Elevated | Notion: AR Data Date across all properties |
| HubSpot-Notion deal stage mismatch (Acquisition Pipeline) | 🟠 Elevated | Cross-reference HubSpot deal stage vs. Notion Acquisition Pipeline Tracker's Stage field — acquisition deals only; tenant lease-renewal deals are Category 2 |
| Notion database ghost entries | 🟡 Watch | Look for pages with only Title field populated |
| Daily brief not generated in 5+ business days | 🟡 Watch | Operations Hub: check for recent Daily Brief pages |

---

## SEVERITY FRAMEWORK

| Severity | Response Time | Who Acts | Escalation |
|----------|--------------|----------|------------|
| 🔴 Critical | Same day | Gabriel | Phil Collins if legal/eviction |
| 🟠 Elevated | Within 3 days | Gabriel | Flag in daily brief |
| 🟡 Watch | Within 2 weeks | Gabriel or PM | Track in monthly checklist |
| 🔵 Info | Next planning cycle | Gabriel | Log in knowledge base |

---

## EXECUTION WORKFLOW

### Full Portfolio Scan
1. Query Notion Tenant Database for all active tenants — check Category 1 and 2
2. Query Notion Acquisition Pipeline Tracker for all non-closed deals — check Category 3
3. Check system health (dual-fleet scheduled tasks, heartbeat freshness, QB export recency) — check Category 4
4. Sort all exceptions by severity (Critical → Elevated → Watch)
5. For each Critical: generate specific recommended action with contact info
6. Output the Exception Report

### Targeted Scan
If Gabriel specifies a scope ("scan just the renewals" or "check deal pipeline only"), run only the relevant category.

---

## OUTPUT FORMAT

```
EXCEPTION SCAN REPORT — [Date] [Time]
Scope: [Full Portfolio / Tenant / Deals / Financial / System]
Data freshness: Notion as of [timestamp]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 CRITICAL — [X] items requiring same-day action
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[#]. [Category] | [Tenant/Deal/System]
     Exception: [Specific issue]
     Data: [Supporting figures]
     Action: [Specific next step] | Owner: [Gabriel / PM]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟠 ELEVATED — [X] items requiring action within 3 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Items...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 WATCH — [X] items for Gabriel's awareness
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Items...]

SUMMARY: [X] Critical | [X] Elevated | [X] Watch | [X] Info
```
