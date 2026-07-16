---
name: QuickBooks is Desktop-only — no QBO MCP path
description: ORA runs QuickBooks Desktop; the Intuit MCP is QBO-only and cannot auth a Desktop instance. Do not recommend OAuth re-auth as a fix.
type: feedback
originSessionId: d0f2a4b0-5cf5-4b9f-ac9a-96cd3613f6cf
---
ORA runs **QuickBooks Desktop** (not QuickBooks Online) across ~20 LLC company files.

**Why:** Gabriel confirmed this directly on 2026-04-16 when auditing the MCP stack. The
`52fa80c0-fe01-4bd6-b488-39531b108fe4` MCP exposes Intuit's QBO REST API (tools like
`profit-loss-quickbooks-account`, `cash-flow-quickbooks-account`, `quickbooks-transaction-import`)
and requires an OAuth token against a QBO tenant. No QBO tenant exists, so re-authing the
MCP accomplishes nothing.

**How to apply:**
1. Never recommend "re-auth the QuickBooks MCP" as a fix. It is structurally incompatible.
2. The documented future bridge for programmatic access is **CData ODBC/JDBC** wrapped in a
   thin custom MCP. This is already referenced in `CLAUDE.md` and `reference_tech.md`.
3. Current operational workflow is **QB Desktop → SharePoint export → skill parse**
   (monthly-close, re-operations, exception-detection). This is acceptable for monthly cadence
   and not a bottleneck yet.
4. If Gabriel asks about automating QB data flow, the first question is: "Is monthly cadence still
   acceptable, or do you need daily?" Only pursue CData if the answer is daily.
5. If a skill or doc still says "QB MCP — requires OAuth re-auth," flag it as stale.
   Fixed in `workflow-audit/SKILL.md` on 2026-04-16.
