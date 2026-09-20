---
name: reference-notion-free-block-quota-exhausted-2026-09-12
description: "Notion workspace hit its FREE-PLAN block-count ceiling 2026-09-12 — every notion-create-pages call fails ('used all of its free blocks'), fleet-wide. Distinct from the debunked query-quota myth: this one is real and a plan upgrade IS the fix."
metadata:
  type: reference
  originSessionId: 0fc18634-d92f-4211-8be2-5903fcf2975f
  modified: 2026-09-14T18:58:37.599Z
---

**Finding (ora-am-brief Block B, 2026-09-12):** `notion-create-pages` against the Ops Hub parent (`32b6ecd8-9e59-81f2-b329-df3fd0e25062`) failed twice (spec-mandated retry) with:

> Your workspace has used all of its free blocks. Upgrade your plan to create more content.

This is a genuine content-storage ceiling on the Notion workspace's **free plan tier** — not a bug, not a transient error. [OI-288](open-items-tracker.md#OI-288) tracks it.

**Do not confuse this with [[reference_tenant_db_cache_and_notion_quota_myth]].** That finding is about a *different* Notion limit entirely: an `entitlement_required` gate that fires only from `notion-query-data-sources` in SQL mode, and it explicitly warns "do not recommend a Notion plan upgrade for this — it fixes nothing." This new finding is the opposite case: `notion-create-pages`/block-creation genuinely needs more capacity, and an upgrade (or freeing existing blocks) is the correct fix. Two distinct Notion ceilings, two distinct remedies — don't apply one's lesson to the other.

**Why to apply:** any task that calls `notion-create-pages` or `notion-create-database` (new content) will now fail identically until this is resolved — `ora-am-brief` Blocks B/C/D, `ora-pm-ledger`, `automation-health-monitor`, dashboard refreshes, etc. `notion-update-page`, `notion-search`, and `notion-fetch` (reads and edits to EXISTING pages) are unaffected — confirmed live: this session's `notion-fetch`/`notion-search` calls against existing pages worked fine throughout, only the create call failed.

**Mitigation already in place, mitigation still needed:** `daily-brief`'s publication guard already has an email-fallback for exactly this case (send the full brief via Outlook COM instead) — that fired cleanly today, so Gabriel still received the brief. But every OTHER Notion-writing task should be checked for the same fallback; several may not have one, and a silent Notion-post failure with no email fallback is a real content-loss risk, not just an inconvenience.

**Fix direction (Gabriel's call, not applied):** (a) upgrade the Notion plan, or (b) free existing blocks — the workspace already has known deletion candidates from its own history (pages tagged `🗑️ ... [DUPLICATE — SUPERSEDED by ...]`, e.g. several retired Daily Brief duplicates; also consider `_archive`-class content). Either path resolves [OI-288](open-items-tracker.md#OI-288).

**Still active 2026-09-14 (ora-financial-code-integrity-sweep):** `notion-create-pages` against the same Ops Hub parent failed identically ("Your workspace has used all of its free blocks") when writing this week's completion row. No fallback existed for this task's Notion step — the sweep's real HIGH-severity finding was still delivered via the mandatory email step (which does not depend on Notion), but the Notion completion row for 2026-09-14 is simply missing, not degraded-but-present. Two days after the 09-12 finding, this is not resolved and not trending toward resolving itself — treat as still-blocking for every Notion-writing task until Gabriel acts on the fix direction above.

Related: [[reference_tenant_db_cache_and_notion_quota_myth]] · [[open-items-tracker]]
