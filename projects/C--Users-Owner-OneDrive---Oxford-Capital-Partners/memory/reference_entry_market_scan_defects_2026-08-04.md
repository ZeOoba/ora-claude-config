---
name: reference-entry-market-scan-defects-2026-08-04
description: "Two defects found in ora-entry-market-scan on the 2026-08-04 run — the Gate Review Notion field specified by SKILL v1.1 does not exist, and the 2026-07-22 run computed every basis floor on doctrine retired eight days earlier."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2ec8822f-ce44-4fa0-bf85-7890136445b2
  modified: 2026-08-04T18:59:54.031Z
---

# ora-entry-market-scan — two defects found 2026-08-04

## 1. The `Gate Review` Notion field did not exist — CREATED 2026-08-04 (Gabriel-approved)

SKILL.md v1.1 claims this field was "added 2026-07-14." **It was not.** The live schema had 43 properties and none was named `Gate Review` (verified by full schema fetch, 2026-08-04). The 2026-07-22 run silently worked around it by writing the literal string `Gate Review: (blank)` as free text inside `Notes / Flags` — so the ratification mechanism the skill depends on was simulated in prose, unqueryable, for two runs.

**RESOLVED 2026-08-04 on Gabriel's explicit approval.** Added to `9a6ae219-85a3-4621-899c-c757fd062f8b`:

```
ADD COLUMN "Gate Review" RICH_TEXT
```

### The convention now in force — blank is load-bearing

All 17 August-run rows were backfilled so that *blank* carries meaning from day one:

| Value | Meaning |
|---|---|
| **blank** | Awaiting Gabriel's first review. **Only** off-taxonomy (Louisville / Delmarva) rows at T1/T2 should ever be blank. |
| `Cleared-<date>` / `Rejected-<date>` + one-line note | Gabriel has ratified. The doctrine-sanctioned values — nothing else counts as a review. |
| `N/A — <reason>` | Gate review does not apply: verdict is PASS-band, or the market is a ratified cluster (Grand Rapids, Des Moines), or the block is a product/environmental/data issue rather than an off-taxonomy question. |

**Do not write "AWAITING REVIEW" or any other non-blank placeholder into a row that is genuinely awaiting Gabriel.** Step 2's re-flag check treats non-blank as ratified; a helpful-sounding placeholder would silently suppress the review question forever. Blank is the signal.

Post-backfill state: 6 blank (410 Winfield, 1604 Northwestern Pkwy, 1803 Commerce Rd, 3900 Cane Run Rd, 111 Olive St, Tishcon), 11 `N/A`.

**SKILL.md corrected 2026-08-04 (Gabriel-approved), bumped to v1.2.** Both stale provenance claims fixed — the frontmatter description and the Step 3 field note. v1.1's "added 2026-07-14" now reads "specified v1.1 2026-07-14; actually created 2026-08-04", with an inline correction note, the three permitted values, and an explicit ⛔ against placeholdering a blank row. Verified no `added 2026-07-14` string survives in the file. **Not committed** — the `.claude` main checkout carries 60+ uncommitted changes from other live sessions; the edit is path-isolated (`git status` shows only this SKILL.md dirty in that directory) and left for the owning session to land.

## 2. The July run executed on retired doctrine

RCT v03 and its vintage ramp (private RCT file) were **ratified 2026-07-14**. The **2026-07-22** run computed every Louisville / Delmarva / Grand Rapids / Des Moines basis floor on **retired RCT v02 constants** ($118.50 Indiana proxy, $150.45 Maryland, $109.15 Grand Rapids, $107.04 Des Moines) with the **retired 30%/25% cliff** — eight days stale at execution.

Pass/fail verdicts mostly survived; **Basis point scores did not**, and Basis is 25 of the 45 Economics points, so July's pipeline ranking was distorted. One verdict was materially wrong: **1700 Industrial Park Dr, Federalsburg MD** read T2 WATCH / Combined 55 under v02, and is **PASS-band / Combined 38** under v03 (Maryland tightened ~23%, the largest per-market move — max qualifying all-in [RCT-private] against an $81.44/SF ask, which breaches once 2% closing is added).

**Root cause:** the task has no doctrine-version check. It reads the skill at run time but nothing asserts that the constants in use match the currently-ratified table.

**Proposed fix (awaiting Gabriel, raised in the August digest):** add an assertion at Step 2 that cites the RCT version in force and fails loudly if it cannot be confirmed, rather than silently computing on whatever constants are to hand.

## Correct RCT v03 ceilings for the four entry markets

Max qualifying **all-in** basis $/SF at the vintage-ramp floor (all-in = price + 2% closing + CapEx + lease-up carry). All four are `[PROXY]` markets with no native RCT entry, so **every screen carries DENOMINATOR-SENSITIVE**.

| Market | RCT v03 LOW | Proxy | ≤1995 | ≥2005 |
|---|---|---|---|---|
| Louisville KY | [RCT-private] | Indianapolis | [RCT-private] | [RCT-private] |
| Delmarva MD/DE | [RCT-private] | Baltimore | [RCT-private] | [RCT-private] |
| Grand Rapids MI | [RCT-private] | Detroit — RCT v03 flags this its **weakest** proxy, likely **too high** | [RCT-private] | [RCT-private] |
| Des Moines IA | [RCT-private] | Minneapolis | [RCT-private] | [RCT-private] |

Direction-of-error matters on Grand Rapids: if true GR replacement cost is *lower* than the Detroit proxy, real discounts are *smaller* and marginal deals fail **harder**, not softer.

Related: [[deal-decision-ledger]] · [[reference-verified-null-vs-inferred-null]] · [[feedback-verify-before-repeating-session-claims]]
