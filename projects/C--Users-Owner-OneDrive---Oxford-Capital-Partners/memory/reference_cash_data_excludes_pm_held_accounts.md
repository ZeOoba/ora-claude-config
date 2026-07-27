---
name: cash-data-excludes-pm-held-accounts
description: "The Master Workbook Cash Data tab covers ORA's own bank accounts only — property-manager-held accounts are outside it, so a negative entity balance is usually a tax-timing artifact, not distress."
metadata: 
  node_type: memory
  type: reference
  originSessionId: db6695a7-c136-494e-9779-1dd833c84c02
  modified: 2026-07-27T14:50:41.183Z
---

The Master Workbook **Cash Data** tab tracks **only accounts ORA holds directly**. Cash held *by the property manager* for the same property is **not in it**, and there is no line, footnote, or reconciliation in the tab that says so.

**Consequence:** a negative entity balance on that tab is normally a **timing artifact, not a liquidity event**. Gabriel confirmed the mechanism on 2026-07-27: property tax payments clear out of the entity account, and the shortfall is funded from **other accounts the firm holds with that same property manager** — money that never appears in the workbook.

**Worked case — 3883 Livingston, 2026-07-27.** The 2026-07-10 column showed **−$7,469.10**, down $14,387 from +$6,918 a month earlier, and the workbook's own `⚠ Entity Low Balance?` row raised `⚠ NEG`. Block D of `ora-am-brief` reported it as an overdraft needing a funding transfer, and paired it with the property's lapsed insurance as "the one combination worth acting on this week." **That framing was wrong.** The cause was a property tax payment and it was already covered by PM-held funds. The insurance lapse is a genuine, separate exposure and stands on its own.

**How to treat a `⚠ NEG` or near-zero entity balance:**

1. Do **not** call it an overdraft, a liquidity problem, or a funding requirement on the strength of the Cash Data tab alone. The tab cannot see the offsetting balance.
2. Check whether the swing matches a **property tax cycle** first — that is the most common cause.
3. If it needs escalating at all, the question is "confirm with the PM," not "wire money."
4. The same blind spot means **consolidated total cash, distribution headroom, and reserve-vs-floor figures understate available liquidity** by whatever sits at the PM. Figures computed off that tab are a floor, not the full position — say so when presenting them.

**Kohr Royer Griffith (KRG)** is the manager on the Columbus cluster (Livingston, Morrison, Banwick, 1100 Rarig) — see [[people]]. Any KRG-managed entity is a candidate for this pattern.

**SETTLED 2026-07-27 (Gabriel):** the exclusion is **deliberate — that tab is ORA's own accounts only.** It is not a gap and must not be "fixed" by pulling PM-held balances into it. Anyone proposing to add them is proposing a change of scope, not a bug fix.

What follows from that:

- The tab is **correct as designed**. The defect is purely one of **labelling downstream** — reporting its total as "TOTAL CASH" or "consolidated portfolio cash" overstates what the number actually is. Present it as **ORA-held cash**, and say plainly that PM-held balances sit outside it.
- The workbook's own `⚠ Entity Low Balance?` / `⚠ NEG` row will therefore **keep raising false positives by construction** — it is alerting on a tab that structurally cannot see the offsetting funds. Treat the flag as informational, never as an exception requiring action on its own.
- Distribution headroom and reserve-vs-floor figures computed from this tab remain **conservative by design**, which is a defensible way to run them — just label them that way rather than implying completeness.

Related: [[master-workbook-single-writer-proposal]] · [[reference_quickbooks_financials]] · [[reference_warehouse_basis_parsing]]
