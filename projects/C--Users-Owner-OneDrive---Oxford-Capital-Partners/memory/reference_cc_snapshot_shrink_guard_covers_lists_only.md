---
name: cc-snapshot-shrink-guard-covers-lists-only
description: "ora-cc-snapshot-refresh/ora-lease-snapshot-refresh's section-shrink guard only checks 5 hardcoded list keys, not scalar/dict sections like quickbooks"
metadata: 
  node_type: memory
  type: reference
  originSessionId: b8041321-02f8-4c99-ad04-edf8e6a8241d
  modified: 2026-08-24T15:32:53.546Z
---

The scheduled tasks' Auto-commit section-shrink guard (`oxford-command-center` `data/snapshots/portfolio.json`) only compares counts for `leases`/`deals`/`counterparties`/`properties`/`loans` — five hardcoded top-level list keys. It has no coverage for non-list top-level sections (e.g. `quickbooks`, a server-attached dict that legitimately defaults to `null`).

**Why this matters:** this exact blind spot let the 2026-08-17 incident happen — `npm run extract`/`lease-snapshot-drift-check.ts` silently nulled the whole `quickbooks` block (828 deleted lines: `sourceFile`, `parsedAt`, 8 properties' P&L rows) on a committed run, and the shrink guard never flagged it because it wasn't scanning that key at all. See [[reference_oi140_check_open_items_duplicate_ids_cli_fix_2026-08-13]]-adjacent incident write-up in event_log.md 2026-08-17 for the full diagnosis.

**What's fixed vs. still open:** the *root cause* is fixed — `resolveQuickbooks()` (`server/sources/quickbooks.ts`, commit `6b9b507`) now makes both CLI writers preserve the previous block instead of nulling it. The *guard itself* was never widened to be generic over all top-level keys — if a future server-attached section is added to the snapshot contract the same way `quickbooks` was, it could suffer the identical class of silent loss and the shrink guard still wouldn't catch it.

**How to apply:** before adding a new server-attached (non-workbook-parsed) section to `PortfolioSnapshot`, either wire its own preserve-forward logic like `quickbooks` got, or widen the shrink guard's key list — don't assume the existing 5-key guard has you covered.
