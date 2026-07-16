---
name: ora-lease-expiration-action-list
description: Weekly lease-expiration action list (Wed @ 8 AM) — ≤180-day expirations ranked by annual revenue-at-risk, cross-referenced to open HubSpot renewal activity; emails ggoldberg, archives to Notion. Read-only (no auto CRM writes). v1.0 2026-06-16 (strategic-audit Fix #6, replaces retired ora-lease-expiration-dashboard).
---

Run the ORA Lease Expiration Action List — a weekly prioritized renewal action list. This scheduled session starts fresh with no memory; this prompt is the authoritative, complete spec. This task REPLACES the retired ora-lease-expiration-dashboard; it is READ-ONLY (it does NOT create or modify HubSpot tasks — the prior auto-escalation accumulated duplicate CRM tasks and was retired; report only).

TOOLING / CONVENTIONS
- Python (if needed): FULL path C:/Users/Owner/AppData/Local/Programs/Python/Python313/python.exe (bare `python` is NOT on PATH in scheduled sessions).
- Email send: C:\Users\Owner\.claude\scheduled-tasks\_shared\send-via-outlook.ps1 — the SOLE automated send path (Outlook COM / M365 only; no Gmail; Composio and Rube are removed — never reference them). On non-zero exit: retry ONCE, then flag loudly in the Notion completion row — do NOT halt.
- Recipient: ggoldberg@oxfordra.net ONLY (2026-05-15 routing directive, re-ratified 2026-06-10).
- HubSpot via native mcp__a3e380ce-…__* (current tenants only). Notion via native mcp__c5f4869f-…__notion-* — Operations Hub 32b6ecd8.
- Formatting: ORA Institutional Style Guide v1.0+.

SOURCE — HubSpot Contacts (canonical tenant roster)
- Query search_crm_objects, objectType=contacts, filterGroups: [{filters:[{propertyName:"monthly_rent",operator:"GT",value:"0"}]}]. Paginate (limit=200, increment offset) until all ~140 retrieved.
- Properties: firstname, lastname, company, email, address, monthly_rent, vacant_, lease_start_date, lease_end_date, square_feet, escalation_percent, next_escalation_date, hs_object_id.
- Field mapping: tenant = company (fall back to firstname+lastname); property = address; SF = square_feet (numeric); annual rent = monthly_rent × 12; expiration = lease_end_date; days-to-expiration = lease_end_date − today. Active = monthly_rent > 0 AND vacant_ ≠ "Yes".

ANALYSIS
1. Compute days-to-expiration for every active tenant.
2. Build the ACTION SET: all active leases expiring within 180 days (include month-to-month / already-past lease_end_date as the top urgency tier).
3. Bucket by urgency: MTM/expired · 0–30d · 31–90d · 91–180d.
4. RANK the action set by annual revenue-at-risk (annual rent), descending — this ordering is the deliverable.
5. Portfolio context: WALT (SF-weighted), total SF and total annual revenue rolling within 180 days, and the largest single expiration inside 18 months (concentration flag).
6. Renewal-activity cross-reference (READ-ONLY): query search_crm_objects, objectType=tasks, filter hs_task_subject CONTAINS_TOKEN "Renewal Outreach", status ≠ COMPLETED. Normalize tenant names (lowercase, strip dashes/commas/periods/whitespace) and mark each action-set tenant as "renewal underway" or "NO renewal activity — needs outreach". Do NOT create, edit, or close any task.

OUTPUT
- Email ggoldberg@oxfordra.net from ggoldberg via send-via-outlook.ps1. Subject: "ORA Lease Expiration Action List — Week of [Mon date]". Three sections: (a) prioritized action list (rank · tenant · property · SF · annual rent · lease end · days · urgency · renewal-activity flag), (b) portfolio context (WALT, SF/revenue rolling 180d, concentration flag), (c) "Needs outreach now" — the ≤180-day tenants with NO open renewal task, top of mind.
- Archive the same content to a Notion page under the Operations Hub (32b6ecd8). Publication guard: capture page id+url; if null/errored retry the create ONCE; search-verify the title created today; if still failed, note "Publish: ❌ fallback" and include the full list verbatim in the email so nothing is lost.
- End your chat-summary with: Publish: [✅ direct | ✅ retry | ❌ fallback] and Send: [✅ | ⚠ retried | ❌ flagged].

HARD GUARDRAILS: never move money, modify financial models or governor constants, or touch oxfordra.net. Keep active confidential deals OFF all external/egress surfaces (fail-closed guard). Do not modify settings.json, ~/.claude config, hooks, or memory files. Read the source before stating any figure — never fabricate tenant or lease data. This task performs NO CRM writes.