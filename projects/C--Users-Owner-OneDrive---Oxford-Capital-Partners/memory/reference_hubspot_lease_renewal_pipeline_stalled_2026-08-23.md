---
name: reference-hubspot-lease-renewal-pipeline-stalled
description: "All 43 HubSpot lease-renewal deals stuck at appointmentscheduled since 2026-03-27 — the renewal-tracking process isn't running, not just slow tenants"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8117da08-b2f4-41f7-9a45-6d7de1cb0708
  modified: 2026-08-23T19:16:33.554Z
---

Every lease-renewal deal in HubSpot's default pipeline (43 total, queried non-closed) sits at the initial `appointmentscheduled` stage with `hs_lastmodifieddate` = 2026-03-27T17:2x — the same day each was created, five months of zero stage movement. Sample: Heritage Pool Supply, Robert & Kesha Best, P.U.P.S Dog Training, CJ's Tint Shop, Corsets and Cogs, Hoodz of Delmarva, The Companies LLC, Bakers Specialty, Midwest Closets, BRITMAN CORPORATION — several correspond to leases expiring within days (CJ's Tint Shop 2026-08-31, 8 days out at time of finding).

This lines up with the Command Center Daily Brief's independent "Expiring, no renewal signal" flags (Workbook/`portfolio.json`-sourced) for the same tenants — two independently-fed pipelines agreeing the renewal-tracking *process* itself isn't advancing deals, not that individual tenants are merely slow to respond.

**Why:** found during ora-pm-ledger's 2026-08-23 EOD Action Ledger inventory (source class B, HubSpot mandated-source check) while cross-referencing lease-renewal-pipeline coverage.

**How to apply:** before trusting any HubSpot lease-renewal deal stage as a signal of real progress, check `hs_lastmodifieddate` — a 2026-03-27 timestamp means "never touched since creation," not "recently reviewed and still pending." Root cause not yet investigated (why the automated pipeline never advances past the first stage) — flagged to Gabriel as a recommended scoped root-cause pass via the lease-renewal-pipeline skill, not yet actioned. See [[project_fedex_kinsman_walk_price_breach_2026-08-23]] for an unrelated same-run finding.
