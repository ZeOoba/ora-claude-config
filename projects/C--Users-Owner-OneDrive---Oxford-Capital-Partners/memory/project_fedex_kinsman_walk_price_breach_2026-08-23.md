---
name: project-fedex-kinsman-walk-price-breach
description: 3700 Kinsman Blvd Madison WI (FedEx) drafted $3.8M LOI breaches 3 underwriting floors; Gabriel decision due 2026-08-25
metadata: 
  node_type: memory
  type: project
  originSessionId: 8117da08-b2f4-41f7-9a45-6d7de1cb0708
  modified: 2026-08-23T19:16:20.282Z
---

3700 Kinsman Blvd — Madison WI (FedEx single-tenant, 44,200 SF): the drafted $3.8M LOI (STANDARD format, sent for transmission approval 08-18) was overtaken by a FULL-mode underwrite completed 2026-08-22, which returned PASS-band but breached 3 of 5 Stage-1 floors at that price — Basis 58.08% vs 65% floor, Yield 5.88% YoC vs 8% floor, levered 10-yr IRR 5.77% vs 12% floor. Combined score 31.5/100, P(exec) 15%. ORA walk price is $2,661,000 ($60.20/SF) — $1,139,000 below the drafted $3.8M LOI. Acquisition Pipeline Tracker's Next Action was updated 08-22 to HOLD the LOI, with a decision deadline of **2026-08-25** (LOI expiration): withdraw/let it lapse, or log an Exception Register compensating factor to override. Do NOT transmit at $3.8M without an explicit override.

Additional flags on the deal: zoning is CC (Commercial Center) in an IL corridor — the FedEx use is probably legal nonconforming and Wis. Stat. 62.23(7)(h) extinguishes that right after 12 months' discontinuance; the parcel is coded EXEMPT/$0 assessed for 2025-2026, so ORA's purchase triggers a ~$70,894/yr reassessment (~21% FedEx occupancy-cost increase before the 2030 renewal decision) plus possible ~$140K Wis. Stat. 70.44 omitted-property back-tax exposure; FedEx Network 2.0 is closing 475+ stations (~30% of footprint) by end CY2027 with a competing automated hub 3 miles away, though the lease runs to 3/31/2030.

**Why:** surfaced by ora-pm-ledger's 2026-08-23 evening run (Block A digest + Block C EOD Ledger, both delivered) via the newly-built `acquisition_pipeline_snapshot_diff.py` detector — this is that detector's first live cross-day catch of a real, high-stakes field change.

**How to apply:** flag this deal in any acquisition/pipeline conversation until 2026-08-25 passes. If Gabriel has not ruled by then, the LOI lapses by its own terms — confirm with Gabriel whether that happened and what he decided (withdraw vs. override) so this memory can be closed out or converted to a Deal Decision Ledger entry. See [[reference_hubspot_lease_renewal_pipeline_stalled_2026-08-23]] for an unrelated same-run finding.
