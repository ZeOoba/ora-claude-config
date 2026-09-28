# daily-brief — incident history

Background and incident narrative for rules encoded in `SKILL.md`. Split out 2026-08-16 (Automation Audit Revision 15 fix) to keep the main skill body lean for its 7×/week unattended `ora-am-brief` invocation — the operational rules stay in `SKILL.md`; the "why" for each lives here.

## Pre-create dedup guard — why the 1-match branch changed (2026-08-11)

Until 2026-08-11 the rule was "exactly 1 match → overwrite," full stop. That assumed any same-day match is *this run's own retry artifact*. During a **catch-up burst** it is not — it is a completed earlier fire's published brief, and replacing it destroys a brief Gabriel may already have read and acted on.

This is not hypothetical: on **2026-08-09** a machine-offline-overnight burst fired `ora-am-brief` twice (09:06 and 09:11 ET); the second fire avoided clobbering page `3b76ecd8-9e59-8160-bb0f-c6b5c925a278` only because that session read the artifact first and stood down **by hand**. Nothing in the skill at the time made it do that — the fix was to make the 1-match branch check *who created the existing page*, not just count matches.

Note also that this guard only ever protected the **Notion page** — the Outlook COM send was unconditional, so a second fire would re-send the email to Gabriel *and* Eric regardless. That is why the current SKILL.md rule's skip covers the send too, and why a caller running unattended should ALSO carry an entry guard and a pre-send Sent Items probe (`~/.claude/scheduled-tasks/_shared/README-DOUBLE-FIRE-GUARD.md`) rather than relying on this check alone. `ora-am-brief` carries both.

## Section 4b — Notion-vs-Workbook cross-check origin (2026-07-16, Patch 10)

Notion Tenant DB's `Lease Expiration` field has a documented history of data-quality defects from its original March 2026 import (duplicate rows, phantom rows, stale/wrong fields — partially remediated 2026-07-12, but field-level date accuracy was never itself audited).

Confirmed 2026-07-16: this section reported Chesapeake Brands, LLC and Stone Crest Counters LLC both expiring 2026-07-31 — both wrong (Notion carried the identical incorrect date on both rows, a data-entry defect, not two independent errors); the real expirations per the Master Workbook are 2027-03-31 and 2028-07-31 respectively. Meanwhile J&R Enterprises genuinely does expire 2026-07-31 but had no value in Notion at all, so this section silently omitted it. Both Notion rows were corrected 2026-07-16, but the underlying gap in this section's method (no cross-check against the Workbook) is what let it happen and could recur for any other tenant — hence the SKILL.md rule requiring the property+unit+tenant match and the `⚠ DISCREPANCY` tag rather than presenting Notion's figure alone as settled.

## Section 4b — HubSpot third leg origin (2026-07-25, Patch 11)

A lease-date correction is a three-system change (workbook → Notion → HubSpot), not two. The 2026-07-16 fix (above) corrected Notion (workbook was already right) for Chesapeake Brands and Stone Crest Counters, but their HubSpot Lease Renewal deals still carried the original disproven `2026-07-31` closedate **nine days later** — nothing in this section ever checked HubSpot, so nothing caught it. `ora-tenant-hubspot-reconciliation` cannot be relied on to catch this same-day since it only runs monthly — hence the SKILL.md rule to pull the HubSpot deal directly when a DISCREPANCY fires and report all three values if HubSpot disagrees too, rather than leaving HubSpot's state unexamined.
