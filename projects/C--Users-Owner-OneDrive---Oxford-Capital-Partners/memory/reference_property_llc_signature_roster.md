---
name: reference-property-llc-signature-roster
description: "Canonical property→signing-LLC lookup for landlord-capacity mail; resolves the Voice Register's [Property LLC Name] placeholder and the recurring Outbox QC Check-D defect."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a1df4067-a0a1-474e-ab35-bae1d41dc51e
---

Property → signing-LLC lookup lives at `Claude_Workspace/00_Governance/References/Voice/ORA_Property-LLC-Signature-Roster_v01.md` (created 2026-07-09). Landlord↔tenant mail must be signed as the property's own LLC ("[LLC], by Oxford Realty Advisors LLC, its Manager") — NOT the generic firm name or the personal VP/Principal block. That omission is the recurring Outbox QC **Check D MEDIUM** (Banwick, MO AG, 1100 Rarig Avenue LLC, May pages).

Source of record: `Claude_Workspace/03_Code/ORA_Ledger_QuickBooks_Replacement/20260422_ORA_Entities_Input1_v01.xlsx` (sheet `Entities`, 28 entities). Rows marked `VERIFIED` (CP-575/EIN confirmed) vs `PENDING` (legal name not yet EIN-verified — confirm before an executed instrument; never invent an LLC name — Hard Invariant 7). Known gaps to resolve: Banwick (Columbus), 401 Sunburst, 55 New Plant Court.

Wired into the Voice Register §2 ([[standards]]). Regenerate on entity-roster change or new acquisition, before the first tenant letter. See [[reference-ora-pm-ledger-double-fire]].
