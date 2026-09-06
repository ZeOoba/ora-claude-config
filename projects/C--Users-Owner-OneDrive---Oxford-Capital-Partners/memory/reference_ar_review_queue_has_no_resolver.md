---
name: ar-review-queue-has-no-resolver
description: "oxford-command-center's data/ar/review-queue.json is WRITE-ONLY — nothing reads it back. The runbook's \"run scripts/ar-import.ts to resolve\" is a dead pointer: that script takes a PDF path and needs a server the sweep's own guard requires to be down."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2b6b4343-89ec-4a37-a0c3-912a30556587
  modified: 2026-08-24T16:37:33.356Z
---

Verified 2026-08-24 in `oxford-command-center`.

`scripts/ar-import-headless.ts` (the weekly `ora-ar-feed-sweep`) writes unresolvable rows to `data/ar/review-queue.json` and logs "run scripts/ar-import.ts to resolve". The `ora-ar-feed-sweep` SKILL.md repeats it. **Both are wrong:**

- Nothing in the repo reads `review-queue.json` back — grep confirms it is append-only. `appendReviewQueue()` is the only writer; there is no reader.
- `scripts/ar-import.ts` takes a **PDF path** as `argv[2]`, extracts text via pdfplumber, and parses yardi/appfolio formats. It never opens `review-queue.json`.
- It also requires a live server (`POST /api/actions/tenant-arrears`) — which the sweep's own **Guard 2 requires to be DOWN**, because `Brain` loads `data/overlay.json` once at construction and silently reverts concurrent writes.
- Queue rows come from **xlsx** (Format B / `delinquency-bucketed`), which `ar-import.ts` cannot parse at all.

## Consequences to expect

- A queued row is **not durable**. On 2026-08-24 a sibling session's snapshot regen reverted the tracked working tree and the queued row vanished — erased, not resolved. `data/overlay.json` is **gitignored**, so the actual financial writes survived; the queue file (tracked) did not.
- The only path that has ever actually cleared a row is: fix the matcher (`server/ar/resolve-by-unit.ts`) so the row auto-resolves, then re-run the importer. Done once, for a parenthetical-annotation gap (PR #293, `3abbe40`).

## How to apply

- Never tell Gabriel a queue row can be resolved interactively — as of this date there is no tool that does it.
- To resolve one: establish the correct lease from **independent** evidence (move-in date, deposit vs `monthlyRent`, `rentPerSf`), then either fix the matcher or write the overlay deliberately. Re-verify both sweep guards are down first.
- The importer can be re-run against live data from an isolated worktree via `AR_INBOX` / `OVERLAY_PATH` / `SNAPSHOT_PATH` / `AR_MAPPING_CACHE` env overrides — no need to edit the shared checkout.
- Format B never consults `data/ar-mapping-cache.json`; editing it to "teach" a unit mapping does nothing.

Open: closing the general gap (a real resolver, or documenting the matcher-fix route) is spawned as a background task, not done. Related: [[reference-ar-subsystem-exists-but-dark-2026-08-16]]
