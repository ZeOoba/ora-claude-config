---
name: ora-calibration-snapshot
description: Quarterly calibration snapshot — logs current property verdicts + resolves due outcomes in the calibration scoring loop (oxford-command-center). Retimed 08:00 → 15:30 ET on 2026-07-27: the 08:00 slot genuinely collided with LAMS ora-tenant-contact-gap-sweep (Mondays 08:00) on any quarter-start falling on a Monday (next real co-fire 2029-01-01), and also sat inside the congested 05:00–09:30 AM pileup. Moved rather than the LAMS side because that fleet is not writable from Claude Code and this task is the rarer, lower-impact of the two. [MODEL: UNVERIFIABLE | checked 2026-07-12]
---

Read and follow C:\Users\Owner\.claude\scheduled-tasks\ora-calibration-snapshot\SKILL.md in full before taking any action.

ORA Calibration Snapshot — quarterly prediction log. Surface: Claude Code (CC/MCP fleet). Self-contained; start fresh with no memory of prior runs.

PURPOSE: The Score-vs-Outcome Calibration Loop needs a steady stream of dated verdicts to grade against actual outcomes over a 40-year horizon. This task fires quarterly (1st of Jan/Apr/Jul/Oct at 8 AM) to emit that snapshot even in quarters with no new warehouse imports.

REPO: C:\Users\Owner\oxford-command-center

STEPS:
1. PRE-FLIGHT: verify the repo exists and the warehouse DB is present at the configured path. If either is missing, write a brief Notion completion row (DB: 8dbbaec0 — Ops Hub page) noting the failure and STOP.

2. RUN THE SNAPSHOT SCRIPT:
   cd "C:\Users\Owner\oxford-command-center"
   npx tsx scripts/calibration-snapshot.ts --task ora-calibration-snapshot --json

   This script (OBSERVATIONAL ONLY) does in order:
   a. resolveDueOutcomes(db) — grade any verdict whose horizon a strictly-later same-grain period now covers
   b. logVerdicts(...) — log current verdicts (scores + anomalies) with emittedBy='snapshot:ora-calibration-snapshot', idempotently

3. PARSE THE JSON OUTPUT and report:
   - verdicts logged this run (new vs skipped/dedup)
   - outcomes resolved this run
   - any errors (ok:false means at least one property failed — report which)

4. NOTION COMPLETION ROW: Write a row to the Ops Hub calibration log page noting date, verdicts logged, outcomes resolved, and ok/error status. Use the Notion MCP (DB 8dbbaec0 or the Ops Hub page 32b6ecd8). The date is the run date computed once at run start with `date '+%A %Y-%m-%d'` (date part in every date slot; weekday only where one is named) and reused verbatim in every title, subject and body. If a create returns no page ID (e.g. a grace-period/quota notice), search by the exact title before any retry; a match created at/after the create call is this run's page — use it; never blind-retry a create (it produced a duplicate). Quota errors → `notion-quota-fallback` skill.

5. EMAIL: Only if ok:false (real error) — send a summary to ggoldberg@oxfordra.net via C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1. Never email on a successful run.

FAIL-OPEN: The script itself never throws. If it returns ok:false, that means observational errors occurred — log them but do not halt or retry aggressively. This is a data-quality observation task, not a pipeline gate.

NEVER edit intel-config.ts, health weights, or DSCR/LTV governors. This task is read/observe/log only.