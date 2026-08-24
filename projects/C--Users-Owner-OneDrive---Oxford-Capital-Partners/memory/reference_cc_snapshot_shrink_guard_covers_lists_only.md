---
name: cc-snapshot-shrink-guard-covers-lists-only
description: "CLOSED 2026-08-24 — ora-cc-snapshot-refresh/ora-lease-snapshot-refresh's section-shrink guard was 5 hardcoded list keys only; now also has a generic top-level populated->empty/null check"
metadata: 
  node_type: memory
  type: reference
  originSessionId: b8041321-02f8-4c99-ad04-edf8e6a8241d
  modified: 2026-08-24T17:25:10.425Z
---

**CLOSED 2026-08-24 (commit `bcda1fc`, both SKILL.mds).** The scheduled tasks' Auto-commit section-shrink guard (`oxford-command-center` `data/snapshots/portfolio.json`) originally only compared counts for `leases`/`deals`/`counterparties`/`properties`/`loans` — five hardcoded top-level list keys, with no coverage for non-list sections (e.g. `quickbooks`, a server-attached dict that legitimately defaults to `null`).

**Why this mattered:** this exact blind spot let the 2026-08-17 incident happen — `npm run extract`/`lease-snapshot-drift-check.ts` silently nulled the whole `quickbooks` block (828 deleted lines: `sourceFile`, `parsedAt`, 8 properties' P&L rows) on a committed run, and the shrink guard never flagged it because it wasn't scanning that key at all.

**Both halves are now fixed.** Root cause: `resolveQuickbooks()` (`oxford-command-center/server/sources/quickbooks.ts`, commit `6b9b507`, 2026-08-17) makes both CLI writers preserve the previous block instead of nulling it. Guard itself: commit `bcda1fc` (2026-08-24) added a schema-agnostic check to both `SKILL.md`s — any top-level key that was non-empty/non-null in `HEAD` and is empty/null in the working copy is flagged, `SKIP = {leases, deals, counterparties, properties, loans, meta, dataQuality}` (the 5 list keys already handled above, plus `meta` since `generatedAt` always differs, plus `dataQuality` since fewer flags is an improvement). Verified against the real 2026-08-17 incident data (flags correctly), a `dataQuality` 1→0 no-flag case, a no-op clean run, and a bonus `assumptions`-emptied case — all correct. Confirmed byte-identical executable logic across both `SKILL.md`s (comment wording differs only).

**Known residual, disclosed not silently accepted:** only catches a section's TOP LEVEL going populated→empty/null. A nested list shrinking while the parent dict stays non-empty (e.g. `quickbooks.properties` dropping some but not all rows) is NOT caught — would need per-section shape knowledge, which defeats the point of a generic guard. Acceptable: strictly better than the prior zero coverage of non-list sections, not a claim of full coverage.

**How to apply:** no action needed for existing sections. Adding a new server-attached (non-workbook-parsed) section to `PortfolioSnapshot` is now automatically covered by the generic check unless added to `SKIP` — only add to `SKIP` if the new section has different-from-bigger-is-better semantics (like `dataQuality`).
