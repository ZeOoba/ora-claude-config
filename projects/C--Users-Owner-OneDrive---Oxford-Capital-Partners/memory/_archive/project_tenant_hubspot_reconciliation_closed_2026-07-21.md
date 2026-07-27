---
name: project-tenant-hubspot-reconciliation-2026-07-21
description: "CLOSED 2026-07-21 — reconciled 7 stale HubSpot Lease Renewal deals against Notion primary-source evidence, extended exception-detection with tenant-status cross-checks, registered a monthly reconciliation task"
metadata: 
  node_type: memory
  type: project
  originSessionId: 156b1fa9-1de0-442e-aacf-4c9ef378327f
  modified: 2026-07-21T16:48:33.613Z
---

# Tenant DB / HubSpot Lease Renewal reconciliation — closed 2026-07-21

**Trigger:** a tenant-DB brief that morning reported several fields "unavailable — Notion source
blocked" plus 4 flagged conflicts (14 stale HubSpot deals, I.M.H LLC, Granite Tops & More,
GT Industrial Supply). Source session for that brief was never located (not in
`search_session_transcripts` coverage — likely Cowork-side or pre-dates indexing).

## What was actually wrong vs. what the flags said

- The "Notion blocked" framing was a red herring — see [[reference_tenant_db_cache_and_notion_quota_myth]].
- I.M.H LLC's "undated" deal and "unresolved duplicate" flags were both wrong: the HubSpot deal has
  a real closedate (2033-07-31, auto-synced), and both archived Notion duplicates already show
  `Row Retired: true` — this tenant's Notion side was already clean from an earlier OI-004/009 pass.
  The real, unflagged issue was a 90+-day $5,079.33 AR delinquency (already in the 07-10 Daily Brief).
- Granite Tops & More and GT Industrial Supply's "archived vs. open deal" framing is the known,
  deliberate `⛔ ARCHIVED` soft-archive convention (not a bug) — but each had a real issue underneath
  once checked directly against Notion: Granite Tops is vacating (Gabriel-confirmed 07-17), GT
  Industrial is 90+ days delinquent ($3,279.20) with no HubSpot reflection of its active
  expansion/renewal conversation.

## HubSpot writes made (all Gabriel-approved after a proposed-changes table; all verified post-write)

Of 14 stale "Lease Renewal" deals (all bulk-created 2026-03-27, stuck in `appointmentscheduled`),
cross-referenced each by tenant name against `ora-pm-ledger`'s Tenant DB cache:

| Deal | Change | Evidence |
|---|---|---|
| Granite Tops & More (58520881824) | → closedlost | Gabriel-confirmed 07-17 vacate, in Notion Notes |
| Square Cow Movers (58510232327) | → closedlost | Notion: Lease Status=Vacant, Row Retired=true |
| InSite Build, LLC (58506659215) | → closedlost | Space lease terminated 2026-12-31 per primary doc; now signage-only license |
| Maryland Hospital Assoc (58522276169) | → closedwon, closedate→2027-06-30 | Third Addendum executed via Adobe Sign 2026-05-06 |
| J&R Enterprises (58524287555) | closedate→2026-07-31 | Notion-corrected expiration (07-16 fix), stays open |
| Soldier Trucking LLC (58514257288) | closedate→2026-10-31 | Notion-corrected expiration, stays open; also 90+ day AR delinquent |
| Carlton L. Handy (58522429699) | closedate→2027-02-28 | Notion-corrected expiration (07-17 fix), stays open |

**Left untouched, no evidence either way (do not infer, ask Gabriel if it matters):** Consult and
Management, Cosmic Spice and Specialty Foods, William D. Smith, MLC Academy Maryland, First Student
(expired 2026-05-31 with zero documented resolution — worth a manual look). **No Notion counterpart
found at all:** Velcani Construction, MO Dept of Agriculture — separate problem, name/sync gap,
unresolved.

**AR delinquency found in passing (90+ days), no write made, just surfaced:** Granite Tops & More
($180.19), GT Industrial Supply ($3,279.20), I.M.H LLC ($5,079.33), Soldier Trucking (bucket only,
balance not pulled).

## Systemic fixes built

- `exception-detection` SKILL.md → v1.2: added 3 Category 2 rows (HubSpot deal contradicts Notion
  tenant status; past-due-untouched-deal-no-signal; no-counterpart-in-either-system). Edited in the
  shared `ora-skills` checkout, NOT committed (left as working-tree change — checked `git status`
  first, only untracked `_staging/` present, no collision).
- New scheduled task `ora-tenant-hubspot-reconciliation` (CC/MCP, `15 8 1 * *`, monthly) — reads
  `ora-pm-ledger`'s cache, cross-references HubSpot, reports ELEVATED/WATCH only, never auto-writes.
  Verified live via `list_scheduled_tasks` (next fire 2026-08-01).

**How to apply:** next time a "stale HubSpot deal" or "tenant status conflict" surfaces, check
whether `ora-tenant-hubspot-reconciliation`'s last report already covers it before re-doing this
ad hoc cross-reference by hand.

Related: [[reference_tenant_db_cache_and_notion_quota_myth]] · [[project_tenant_db_no_sync_rootcause]]
· [[reference_tenant_db_completeness_gap]]
