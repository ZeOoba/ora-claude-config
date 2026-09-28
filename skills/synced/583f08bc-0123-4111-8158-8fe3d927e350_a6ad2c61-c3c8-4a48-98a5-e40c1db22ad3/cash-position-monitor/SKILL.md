---
name: cash-position-monitor
description: Multi-entity cash position consolidation across QuickBooks accounts. Use when the user mentions: cash position, cash balance, treasury, reserve adequacy, distribution headroom, cash forecast, weekly cash, daily cash, intercompany, sweep account, cash concentration, debt service coverage of cash, or any task requiring real-time consolidated cash visibility. Powers the ora-cash-position-snapshot scheduled task and the ora-cash-position artifact. v1.0
license: ORA Internal
---

# Cash Position Monitor

Produce consolidated multi-entity cash position views with reserve adequacy checks and distribution headroom calculations.

## Scope

All ORA entities: holding company, property-level SPVs, manager entity. Includes operating, capex, lender-required, and LP-distribution accounts. Excludes Gabriel/Eric personal accounts (see personal-portfolio).

## Triggers

Daily/weekly cash snapshot, reserve adequacy check, distribution decision, refi cash analysis, capital call timing, vendor payment timing, intercompany sweep.

## Inputs

- QuickBooks (cash-flow-quickbooks-account, profit-loss-quickbooks-account) — balances by account
- Notion Operations Hub — reserve policy floors, distribution policy
- Notion debt schedule — upcoming debt service obligations
- LP database — pending capital calls, scheduled distributions
- Vendor payable aging (QuickBooks A/P)

## Standard Workflows

### Weekly Snapshot (Monday 6:30 AM via ora-cash-position-snapshot)
1. Pull current balances by account, by entity.
2. Compute consolidated total.
3. Compute operating reserve adequacy: cash − payables vs. policy floor.
4. Compute distribution headroom: cash − (next 30-day debt service + reserve floors + payables).
5. Compute week-over-week delta.
6. Flag: any reserve below floor (ALERT), any week-over-week drop > 10% (WARN).
7. Update ora-cash-position artifact.
8. Email Gabriel + Eric.

### Distribution Decision Support
1. Pull current cash and outflows for next 90 days.
2. Apply waterfall to compute distributable cash by LP.
3. Stress test: 90-day cash position post-distribution.
4. Output: distribution decision memo (DOCX) with sensitivity to occupancy and tenant payment timing.

### Refi Cash Analysis
1. For a refi candidate, model: closing-day cash impact (prepay penalty, points, reserves, return of equity).
2. Quantify: cash freed for redeployment vs. cash consumed by closing costs.
3. Output: cash impact section of debt-management refi memo.

### Capital Call Timing
1. For an upcoming acquisition, identify cash gap.
2. Stagger call timing to minimize idle LP cash.
3. Output: capital call schedule (xlsx).

## Outputs

- xlsx cash position workbook (entity-level, consolidated, trend)
- DOCX cash memos for distribution and refi decisions
- ora-cash-position artifact refresh
- Notion Operations Hub cash page update
- File naming: YYYYMMDD_Cash-Position_[period]_v##.xlsx

## Boundaries

- This skill READS cash data; it does not move money. Per CLAUDE.md, no actual transfers, ACH, or wires are executed.
- Distribution recommendations are advisory; Gabriel approves all distributions.
- All forecasts beyond 30 days marked [FORECAST].

## Dependencies

- portfolio-reporting skill (NOI inputs)
- xlsx skill (cash schedules)
- docx skill (decision memos)
- ~~investor-relations skill (distribution waterfall)~~ — retired 2026-09-09, no replacement assigned
