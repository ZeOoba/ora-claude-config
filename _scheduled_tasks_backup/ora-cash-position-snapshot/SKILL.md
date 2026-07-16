---
name: ora-cash-position-snapshot
description: Monday 6:30 AM multi-entity cash position consolidation across QuickBooks accounts, with reserve thresholds and distribution-availability flags. Emails Gabriel + Eric.
---

**[CANARY MIGRATION 2026-05-07 — Composio EOL bridge]** All MCP routing on this task is pinned to the native Composio Platform Outlook connector (`mcp__composio-ora__OUTLOOK_*`), NOT the legacy Rube namespace (`mcp__d6315173-234c-4e6c-bea7-7f5e15d2bde5__RUBE_*`) and NOT the prior `mcp__8a611864-5cda-497f-baf9-6d3c02ab3404__COMPOSIO_*` wrapper (absent from current sessions). Validate the Monday 5/11 06:39 ET run end-to-end before bulk-swapping the remaining 9 Outlook-dependent scheduled tasks. Rollback path: revert this preamble and the explicit Composio pin on the Outlook line below. Tool slugs (`OUTLOOK_SEND_EMAIL`, etc.) are byte-identical between the two stacks; only the MCP server prefix changes.

Run ORA Cash Position Snapshot.

Sources:
1. ORA Master Workbook — Cash Data tab (canonical cash SSOT per the 2026-05-08 architecture directive). Read current balances by account/entity from the mounted workbook folder. QuickBooks MCP is intentionally NOT connected — do not attempt a QuickBooks pull. If the workbook is not mounted, carry forward the most recent ingested vintage and disclose the staleness in §B.
2. Notion Operations Hub (32b6ecd8-9e59-81f2-b329-df3fd0e25062) — pull defined reserve thresholds and target distribution policies.
3. Notion debt schedule — upcoming debt service obligations (next 30 days).

Compute:
A. Total cash by entity and consolidated portfolio total.
B. Operating reserves vs. policy minimum (flag if below).
C. Capex reserves vs. budgeted draws (next 90 days).
D. Distribution headroom = consolidated cash − (next 30-day debt service + reserve floors + known payables).
E. Week-over-week delta (compare to prior Monday snapshot stored in Notion).

Output:
- Notion page in Operations Hub titled "Cash Position Snapshot — [date]" with full table. **Apply v1.1 publication guard (`_shared\PUBLICATION_GUARD.md`):** capture pages[0].id; retry once on failure; search-verify by title; if all fail, AUTO-SEND Outlook email subject `❌ ora-cash-position-snapshot PUBLICATION FAILED — [date]` to Gabriel (ggoldberg only) with the snapshot inlined as plain text.
- Email summary to ggoldberg@oxfordra.net via Outlook from ggoldberg@. (Eric removed per Gabriel directive 2026-05-15.) **Route through `mcp__composio-ora__OUTLOOK_SEND_EMAIL` (Composio Platform native Outlook connector).** Do NOT use the legacy Rube `mcp__d6315173-...__RUBE_MULTI_EXECUTE_TOOL` path, nor the prior `mcp__8a611864-...__COMPOSIO_MULTI_EXECUTE_TOOL` wrapper (absent from current sessions).
- If any reserve falls below policy floor: subject line prefixed "[ALERT]" and immediate flag in body.

Update ora-cash-position artifact (call mcp__cowork__update_artifact) with refreshed numbers.

Format: ORA Institutional Style Guide v1.0+. Email subject: "ORA Cash Position — [date]".