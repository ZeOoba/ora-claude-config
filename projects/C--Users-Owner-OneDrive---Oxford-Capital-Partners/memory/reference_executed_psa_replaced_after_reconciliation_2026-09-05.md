---
name: reference-executed-psa-replaced-after-reconciliation-2026-09-05
description: A completed PSA reconciliation goes stale silently when the executed instrument on file is replaced — hash/page-count the PDF before trusting any Fact Table.
metadata:
  type: reference
---

**A Canonical Fact Table is only valid against the exact file it was built from, and nothing warns you when that file changes.**

Found 2026-09-05 by `ora-psa-drift-watch` on 754 Old State Route 74 (Cincinnati, DEAL-8). The
executed PSA at the deal-folder root was **26 pages, md5 `7ee9d97baf8b…`, mtime 2026-08-28**. The
2026-08-12 `psa-reconciliation` run — and its 139-fact Fact Table
`20260812_754OldStateRoute74_PSA-Facts_v01.xlsx` — were built against the **25-page** copy now sitting
at `archive/PSA -- 754 Old State Rd Clean 08-10-2026.pdf`, md5 `852637b4cb35…`. Same nominal
document, same "Executed 08-10-2026" identity, one extra page.

The added page was a populated **Exhibit B rent roll**, which silently invalidated **13 Fact Table rows**
(P-076→P-088, all flagged `Missing` purely because Exhibit B was blank) — including P-076, annotated
"THE SINGLE MOST MATERIAL DEFECT IN THIS EXECUTED PSA." Nothing in Notion, the Fact Table, or the
deal folder flagged the swap. Two prior drift-watch runs (08-12, 08-26) had both certified "blank
Exhibit B" as CORROBORATED.

**Why:** reconciliation output is a point-in-time snapshot of a file, but it is stored and cited as if it
were a snapshot of *the deal*. Counsel re-circulates supplemented PDFs under the same name and the
same execution date, so filename, "Executed" token, and stated effective date all stay stable across a
content change. Every ORA convention for identifying the source of record is blind to this.

**How to apply:**
- Before trusting ANY Fact Table, hash and page-count the executed PDF and compare against the copy
  the table was built from (usually in `/archive/`). Page count alone caught this one.
- A post-execution attachment is **not** a cure. This rent roll was dated **08/27/2026 — 17 days after
  the 08/10/2026 certified Effective Date**. Whether it was incorporated by executed amendment or just
  inserted into the PDF is unresolved; that question goes to counsel, never to an assumption.
- Do not let a re-verification pass inherit a prior banner's CORROBORATED list. Re-read the instrument.
  The 08-26 banner's corroboration of "blank Exhibit B" was correct when written and wrong five days later.
- When the instrument moves, re-run `psa-reconciliation` to a v02 table — do not patch v01 in place.

Related: [[feedback_findings_decay_recheck_before_writing]] (same decay mechanic, shorter clock),
[[feedback_verified_null_vs_inferred_null]], [[reference_hookify_noop_hooks_every_tool_call]]
(mtime is not evidence of an event date — here the mtime was the tell, but the hash was the proof).
