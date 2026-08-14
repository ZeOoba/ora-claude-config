---
name: reference-outlook-search-filters-are-utc-not-et
description: "Outlook MCP outlook_email_search date filters apply in UTC, not ET — silently offsets every ET-planned sweep window by 4 hours"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7c750896-9388-4e71-8a83-fd55979171a3
  modified: 2026-08-04T22:29:07.358Z
---

`mcp__…__outlook_email_search`'s `afterDateTime` / `beforeDateTime` are evaluated in **UTC**, not ET, even when passed a bare local-looking datetime.

Querying `afterDateTime: 2026-08-03T00:00:00, beforeDateTime: 2026-08-04T00:00:00` returns the messages sent **2026-08-02 20:00 ET → 2026-08-03 20:00 ET** — not the ET calendar day. Verified 2026-08-04 across six consecutive day-queries: every returned `sentDateTime` was UTC, and each window's earliest/latest bracketed a 20:00-to-20:00 ET span.

**Why it matters:** `ora-pm-ledger` Block B (`outbox_qc_window.py`) plans and commits coverage in **ET intervals**. Since the 2026-07-24 retro-sweep rebuild, every Block B run has silently swept a window shifted 4 hours from the one it then recorded as covered — the exact "coverage was modelled wrong" failure class the rebuild existed to kill, reintroduced one layer down.

**How to apply:** when sweeping an ET day, pass a UTC window offset by the ET offset (EDT = UTC-4, EST = UTC-5) — i.e. for ET day D, query `D T04:00:00Z → D+1 T04:00:00Z`. Then bucket results by `sentDateTime` minus the offset before assigning them to an ET day. Never commit an ET interval on the strength of an unconverted query window.

Second trap in the same tool: results page at 25 and `totalResultCount` is returned only in the final element — a heavy day (36 and 41 results on 2026-07-31 / 08-03) silently truncates unless you page. Both traps compound: a truncated *and* shifted window looks like a clean sweep.

Related: [[feedback-verified-null-vs-inferred-null]], [[reference-ora-pm-ledger-double-fire]]
