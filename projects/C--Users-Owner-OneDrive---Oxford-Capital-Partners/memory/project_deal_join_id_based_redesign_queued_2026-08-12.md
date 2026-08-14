---
name: deal-join-id-based-redesign-queued
description: "MERGED 2026-08-13 (PR #273, commit 6e7c5bd). Replaced name-based seed↔Notion deal joining with Notion's native Deal ID; 3 review rounds found 15 more defects in the redesign itself, incl. a near-self-introduced confidentiality leak"
metadata: 
  node_type: memory
  type: project
  originSessionId: 45979807-1a58-4473-b289-45e88fddcac4
  modified: 2026-08-13T16:27:07.639Z
---

**Status: MERGED 2026-08-13, 16:25 UTC.** [PR #273](https://github.com/ZeOoba/oxford-command-center/pull/273) — 8 commits on `feat/deal-id-join`, squash-free merge to `main` at commit `6e7c5bd`. Branch deleted (local worktree + remote) post-merge. Approved in-turn 2026-08-12 as option (c) alongside PR #271 (the sweep remediation this follows on from).

## What shipped

`mergeDeals` now joins the seed set to the live Notion Acquisition Pipeline Tracker on `Deal.notionDealId` — Notion's native Unique ID property ("Deal ID"), opaque and read-only at the source. All name-based corroboration machinery (`dealJoinKey`-as-join-key, `NOTION_DEALS_NAME_ALIASES`, `NOTION_DEALS_ACCEPTED_NEAR_DUPES`, market/locality corroboration) is retired, not merely satisfied — there is nothing left to corroborate once the key is opaque. `MARKET_MAP` re-derived against the live Notion select (3 of 6 old keys were strings Notion could never emit). Six new `Market` enum members added for pipeline-only metros, split from `PROPERTY_MARKETS` so the portfolio filter doesn't offer markets no property can carry.

## The evidence that motivated it (unchanged from the original queue entry)

`dealJoinKey` stripped Notion's `" — City, ST"` locality tail — the ONE disambiguator for repeating bare street names across metros — so the old join deleted its own safety signal. Four adversarial passes on 2026-08-11/12 found 9+7+5+6 defects in that subsystem alone, including a CRITICAL cross-side wrong merge that published one deal's economics under another's identity and public confidential flag.

## What building it actually cost — 3 more review rounds, ~15 more defects

Replacing the primitive did not retire the defect *rate* — it moved it, briefly, into the redesign itself. Three independent rounds, each on freshly-fixed code:

1. **Adversarial pass on the join redesign** (`wf_80769cd1-096`) — 5 defects, worst HIGH: my own claim that a new "migration tripwire" dominated the old `checkSnapshot` duplicate check was **refuted by execution** — it covered only one of three pair classes the old check caught, reopening the 2026-08-04 Pendleton/2146 incident class.
2. **Adversarial pass on the seed-id cutover** (`wf_850e84c0-73b`) — 4 more, including `fetchNotionDeals` still deduping idless rows by name slug (the id-carrying case was fixed; the idless fallback wasn't).
3. **Independent 8-angle code review**, verified by me against actual consuming code before fixing, then a THIRD adversarial pass (`wf_84a8d6b8-536`) on those fixes — 5+5 more. The most serious: `checkSnapshot`'s duplicate-deal check had lost its reach into `scripts/reconcile-snapshot.ts`'s `gate:ci` path, which validates the *committed* snapshot independent of Notion I/O — reopening the exact 2026-08-03 phantom-vacancy-lease incident class, for deals specifically, that repo already paid to close once.

**The one worth remembering past this task:** mid-fix on that last one, my first draft of the replacement duplicate-check embedded deal **names** directly in a flag — and `checkSnapshot` is a pure function with no local log to redirect them to, and its flags reach the public mirror unswept regardless of `entity`. I caught it before it left the worktree by re-reading `bake-mirror.ts`'s redaction code rather than assuming the existing discipline transferred. **A fix for a confidentiality-leak defect class is not automatically leak-safe itself** — every new flag site in this subsystem needs the same check applied fresh, not inherited by proximity.

Also recurring: `src/data/public-deals.ts`'s declassification allowlist went silently stale mid-branch (documented `notion-<slug>` format, runtime moved to Notion page UUIDs) — `isDeclassified`'s not-in-allowlist path returns `false` with zero signal, so a real Gabriel-ratified declassification would have failed closed with nothing anywhere reporting it. Same "verified null vs inferred null" shape as [[feedback_verified_null_vs_inferred_null]], caught by review rather than by any test, since the whole test corpus exercised only the dead namespace.

## Verification before the PR

typecheck 0, lint 0, full suite 3445/3445 (1 documented environment flake, unrelated). Live-verified against the real Notion API after every round: 22 deals (6 seed-joined + 16 confidential extras), 0 dataQuality flags. `npx tsx scripts/check-refute-required.ts --strict` passes with `Refute-Reviewed` trailers on every commit touching gated paths.

## Open, not part of this PR

- Gabriel ruled 1333 Research Road's live negotiating economics may publish (same posture as E. Fulton) — documented inline in `seed-deals.ts`, not a follow-up.
- Sourcing RCT rows for the 6 newly-enumerated metros (Notion's own formula prices them; only `low` is recoverable without inventing `point`/`high`/`cwHardPsf`).
- `extras` array has no canonical sort before the snapshot write (pre-existing, this PR reduces exposure but doesn't close it) — a Notion-side reorder can still produce a spurious movement-gate diff.
- Live tracker row `DEAL-5` ("Stall Alert — 2026-04-29") is a non-deal artifact counted as a deal — confidential, so no leak, but pollutes counts.
- Catch-up findings H2 + M1 from the original sweep remain untouched; **M2 must land before H2** (fixing H2 first would publish confidential deal names to the public mirror).
