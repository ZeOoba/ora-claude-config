---
name: reference-hubspot-lease-renewal-pipeline-stalled
description: "Every open HubSpot lease-renewal deal is stuck at appointmentscheduled since the 2026-03-27 bulk import — the renewal-tracking process isn't running, not just slow tenants. Re-confirmed 2026-09-02; do not cite a count from here, re-measure"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8117da08-b2f4-41f7-9a45-6d7de1cb0708
  modified: 2026-08-23T19:16:33.554Z
---

Every lease-renewal deal in HubSpot's default pipeline sits at the initial `appointmentscheduled` stage with `hs_lastmodifieddate` = 2026-03-27T17:2x — the same day each was created, five months of zero stage movement. Sample: Heritage Pool Supply, Robert & Kesha Best, P.U.P.S Dog Training, CJ's Tint Shop, Corsets and Cogs, Hoodz of Delmarva, The Companies LLC, Bakers Specialty, Midwest Closets, BRITMAN CORPORATION — several correspond to leases expiring within days (CJ's Tint Shop 2026-08-31, 8 days out at time of finding).

This lines up with the Command Center Daily Brief's independent "Expiring, no renewal signal" flags (Workbook/`portfolio.json`-sourced) for the same tenants — two independently-fed pipelines agreeing the renewal-tracking *process* itself isn't advancing deals, not that individual tenants are merely slow to respond.

**Why:** found during ora-pm-ledger's 2026-08-23 EOD Action Ledger inventory (source class B, HubSpot mandated-source check) while cross-referencing lease-renewal-pipeline coverage.

**How to apply:** before trusting any HubSpot lease-renewal deal stage as a signal of real progress, check `hs_lastmodifieddate` — a 2026-03-27 timestamp means "never touched since creation," not "recently reviewed and still pending." Root cause not yet investigated (why the automated pipeline never advances past the first stage) — flagged to Gabriel as a recommended scoped root-cause pass via the lease-renewal-pipeline skill, not yet actioned. See [[project_fedex_kinsman_walk_price_breach_2026-08-23]] for an unrelated same-run finding.

---

**Re-confirmed 2026-09-02** by the monthly `ora-tenant-hubspot-reconciliation` sweep — a second, independently-fed observation, 10 days later, of the same stall:

- **37 open deals, every one of them 37+ days idle.** The newest `hs_lastmodifieddate` anywhere in the open pipeline is 2026-07-27; nothing has moved since. Filed as [[open-items-tracker]] `#OI-219`.
- **CJ's Tint Shop — the "8 days out" case named above — expired 2026-08-31 with no renewal, vacate, or holdover recorded in HubSpot, Notion, or the workbook.** All three agree on the date and all three are silent on the outcome. The prediction in this memory came true. Filed as `#OI-218`.
- **Count anchor removed.** This memory originally said "43 total, queried non-closed"; the 2026-09-02 sweep measured **37** open deals against a full 50-deal pull (37 open / 8 closed-lost / 5 closed-won), and no deal closed between 2026-08-23 and 2026-09-02 (every closed deal's `closedate` is 2026-07-21/25/26). So the two counts differ by measurement, not by movement, and the discrepancy is **not resolved** — the 08-23 query's scope was probably wider than "Lease Renewal deals." Re-measure; never cite a count from this file.

**Root cause still not investigated** — unchanged from the original entry.
