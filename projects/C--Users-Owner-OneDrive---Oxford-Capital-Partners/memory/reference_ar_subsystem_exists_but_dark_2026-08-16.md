---
name: reference-ar-subsystem-exists-but-dark-2026-08-16
description: "oxford-command-center has a complete, tested AR ingestion + exception capability that has NEVER been run — data/ar/ doesn't exist, so $204,788 of AR is invisible. Do not rebuild it."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3f365fd1-1946-44aa-b52f-d1ec1458c65c
  modified: 2026-08-16T21:40:20.830Z
---

**`server/ar/` is a complete, adversarially-reviewed AR ingestion subsystem that has never been run.** Shipped as PR #230 (`feat/ar-balances-feed`), hardened over two refute rounds 2026-07-22. 10 modules + `scripts/ar-import.ts` (334 lines) + `scripts/ar-import-headless.ts` (486 lines, built for a scheduled task), 4 test files.

**Why it produces nothing** (verified 2026-08-16): `data/ar/` does not exist · `data/overlay.json` → `tenantArrears` has **0 entries** · no mapping cache, no review queue on disk · nothing schedules it · nothing moves the eight `Business/A.R. Reports/*.xlsx` (dated 7.15.2026) into `AR_INBOX`.

Consequence: `arBalances[]` empty, `arrears-*` and `ar-stale` conditions never fire, daily brief §4c collections block has no data. Meanwhile `Business/Master Lease Database/_pipeline/` computed **$204,788.48** ($172,672.41 active, 31 tenants, 0 unmapped) from the *same eight files* on 2026-07-17 and wrote it to a standalone HTML dashboard nothing else reads.

⛔ **Do NOT rebuild any of this.** `ar-import-headless.ts` already accepts `.xlsx` (not just PDF). `match-tenant.ts` already does confidence-tiered matching with ambiguity detection. `partition-confidence.ts` already implements auto-write-high-confidence-only. `conditions.ts` (896 lines) already has ALL of: `escalation-*`, `lease-lapsed-*`/L-2, `lease-expiry-*`/L-1, `arrears-*`, `ins-*`. `anomaly-floor.ts` is the canonical bulk-change floor (consolidated 2026-07-26 after two reverts — Gabriel-directed).

**Regime registry already exists and is populated:** `property_master.property_manager` in `data/warehouse/finance.sqlite` — KRG (Rarig, 3034, 3540, E Livingston, Sepich) · CRC (Broadway, Red Branch) · SVN (Northwood) · Thomas Park (Info Lane) · Peak Real Estate Partners (9620) · null = self-managed (55 New Plant, 401 Sunburst, 7658 Fishel). **PM firm ≠ software platform** — firm is who to email, platform (AppFolio/Yardi/RentManager) decides the parser. Note 9620 is **Peak**, not Venture Property Management (that report is 2025, stale); 9510 Persimmon Tree Rd is **absent** from `property_master`.

**Why this memory exists:** three successive sessions each wrote a plan that would have rebuilt working code — `_pipeline`, then `server/ar/`, then `conditions.ts`. See [[feedback-absence-claims-need-verification-before-building]]; it was cited *in* the plan that violated it. Audit + re-scoped spec: `oxford-command-center/docs/superpowers/specs/2026-08-16-p4-capability-audit.md` and `…-pm-data-reconciliation-design.md` (branch `feat/p4-pm-reconciliation`).

**The generalized shape (Gabriel, 2026-08-16): work completed but never REGISTERED is undiscoverable, and it recurs at every altitude.** Two instances found the same day:
- **Code layer** — `server/ar/` shipped complete and tested, but no inbox and no scheduled task, so it produced nothing and nothing alarmed.
- **Tracker layer** — `OI-173` reserved an id and `spec-liveness-probe.py` was written, but the tracker row was never filed, so the probe was invisible to anyone searching the punch-list. (Row filed 2026-08-16; orphan reservations went 6 → 5.)

Registration — not completion — is what makes work findable. `git log` and a passing test suite both look identical whether a capability runs or not. **Detection asymmetry to remember:** `spec-liveness-probe.py` compares a fleet spec's claims against live data, so a capability with **no spec at all** is outside its edge *by construction* — the never-registered case is precisely the one no probe currently sees. Gabriel's ruling was to accept this at n=2 and rely on `/build` chain step 0 (added 2026-08-16, PR #137) catching it at design time rather than at rest. **If it happens a third time, that ruling should be revisited — it is then a pattern, not a coincidence.**
