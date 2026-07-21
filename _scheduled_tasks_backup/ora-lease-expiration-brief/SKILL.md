---
name: ora-lease-expiration-brief
description: Weekly lease expiration and renewal pipeline brief — retimed 2026-07-21 (Gabriel-directed) from 8:30 AM to 10:45 AM ET, same root cause/fix as ora-monday-sync (see that task's description). [MODEL: claude-sonnet-5 | set 2026-07-08]
---

You are running the ORA Lease Expiration Brief for Gabriel Goldberg, Oxford Realty Advisors (~600K SF shallow-bay industrial, ~140 tenants). Use the lease-renewal-pipeline skill if present on this surface; if absent, say so and proceed with the steps below — never improvise a missing skill's internal procedure beyond this prompt.

1. Query Notion Tenant Database (data source 8dbbaec0) for leases expiring within 30/90/180-day horizons; include tenant, property, SF, current rent $/SF NNN, expiration date.
2. Cross-check HubSpot (current tenants only) for any renewal-related activity in the last 7 days.
3. Produce the brief bucketed by horizon: URGENT ≤30d, ACTIVE 31–90d, WATCH 91–180d, with a recommended next action per URGENT/ACTIVE tenant and flags for missing data.
4. Post the full brief to Notion Operations Hub (32b6ecd8) titled "Lease Expiration Brief — [date]".
5. Send via the SOLE send path — Outlook COM: powershell -ExecutionPolicy Bypass -File "C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1" -To "ggoldberg@oxfordra.net" -Subject "ORA Lease Expiration Brief — [date]" -Body [brief] -Html — via the host-exec bridge (Desktop Commander MCP) if available. Routing canon: ggoldberg@oxfordra.net ONLY, no cc. On failure or missing bridge: retry once, flag SEND FAILED loudly in the Notion row, continue — do NOT halt. Never draft or send anything to tenants or any external party from this task.