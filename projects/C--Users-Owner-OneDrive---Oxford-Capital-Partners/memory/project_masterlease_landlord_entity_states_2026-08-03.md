---
name: project-masterlease-landlord-entity-states
description: Sourced landlord-entity formation states for MD/MO Master Lease properties (from executed-lease recitals) and an open tenant-identity discrepancy pending verification.
metadata: 
  node_type: memory
  type: project
  originSessionId: e7994827-0768-4ef4-88e7-e7caa0397673
  modified: 2026-08-03T23:00:11.063Z
---

Three landlord entities + formation states sourced from executed-lease recitals (not assumed from property location) for `masterlease-jurisdiction-rebase`'s `config/properties.json`: **29000 INFORMATION LANE, LLC** and **2203 NORTHWOOD, LLC** — Maryland; **9620 STATE 350, LLC** — Missouri.

**Why:** the rebase engine fails closed on a missing `entity_state` (v1.1 fix) rather than assuming an LLC formed in the state where its property sits — a real distinction, not a formality.

**Open, pending verification:** the 2203-2207 Northwood executed lease shows a tenant-name/suite discrepancy — "Baqir" vs "Baquir" and suite "13B" vs "B13" — not yet reconciled against the source document. Do not resolve by guessing which is correct; check the executed lease itself.

**How to apply:** treat these three entity/state pairs as sourced and citable; treat the Baqir/Baquir + suite discrepancy as open until someone reads the actual executed lease. See [[masterlease-jurisdiction-rebase]] canon in `rules.md` §19 for the template master's own location.
