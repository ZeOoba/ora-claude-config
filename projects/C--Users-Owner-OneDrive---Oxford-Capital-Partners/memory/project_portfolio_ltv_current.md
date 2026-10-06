---
name: project-portfolio-ltv-current
description: Verified current portfolio LTV (18.71% as of 2026-09-23, Master Workbook 00_Home!G7) — internal only; no numeric LTV in any counterparty/public text
metadata:
  type: project
---

**Portfolio LTV = 18.71% as of 2026-09-23** (gross-external definition: external debt ÷ Oxford-share portfolio value). Source: live ORA Master Workbook `00_Home!G7` (`='External Loans Summary'!C22/'Property NOI'!J20`), read via M365 `read_resource` 2026-09-23; local file mtime 2026-09-23 13:17, so the read is current under the DSOR 7-day rule. Components on that read: external debt $10,605,588 (`00_Tests!E5`), portfolio value $56,668,952 (`00_Home!B7`, 13 properties). `00_Tests!E7` (`ELS!C33`) also reads 18.7%. No OPEN Corrections-register row touches these cells. WBC-012 (the Northwood $2.8M loan) freezes *internal* debt only, not this external-debt LTV.

Supersedes the Jun 1 2026 "17.9% LTV" in [[projects]] and every "~15%" figure in skills and on the site. A separate **net-external** LTV lives on `External Loans Summary` (15.71% at the 09-14 ingest). It was NOT re-read 2026-09-23: the M365 render truncated before ELS, and Excel held the file locked. Never quote "~15%" as current: that figure matches the net definition or the older inflated $65M value basis, not the headline.

**Why:** ~15% was stale doctrine in acquisition-underwriting v4.23 and in loi-generation's outbound Buyer Information page / ora-standards cover-note list. Gabriel ruled 2026-09-23 that no numeric LTV/leverage figure is public on oxfordra.net (site PR #85 removes it).

**How to apply:** any governor test (40% aggregate, STAGE 2.3) reads the live workbook every time; this file is orientation only. Internal docs may cite the figure with its as-of date. Counterparty-facing text (LOI, broker/lender/seller mail) uses "conservative leverage" only, pending Gabriel's ruling on the outbound LOI template. Governor constants are untouched (Invariant 4). Outbound property count: Gabriel confirmed 2026-09-23 that it stays **26 properties**, not the workbook's 14 Property NOI lines, which are groupings. Do not re-raise it. Related: [[project-governor-ltv-remediation-2026-07-24]], [[project-northwood-egflc-loan-miscategorized-2026-07-27]].
