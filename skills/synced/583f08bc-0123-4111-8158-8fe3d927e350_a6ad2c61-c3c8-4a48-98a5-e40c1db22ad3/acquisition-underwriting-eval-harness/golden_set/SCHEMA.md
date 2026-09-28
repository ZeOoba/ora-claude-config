# Golden-Set JSON Schema

One file per frozen deal in `golden_set/*.json`. Fields:

- `deal_id` — kebab-case identifier, matches filename stem.
- `deal_name`, `mode` (SCREEN|SNAPSHOT), `date_seen` — as recorded at freeze time.
- `source` — where the frozen facts + golden verdict were pulled from (Notion collection ID + query date), for auditability.
- `confidence` — `HIGH` | `MEDIUM` | `LOW`, per deal. `diff_verdict.py` scores (gates PASS/FLAG)
  `HIGH` and `MEDIUM` identically; only `LOW` is excluded (informational-only). Driven by how many
  of the 7 scorecard categories the replay can derive from `inputs`, WITH one distinction updated
  2026-08-14 (E Fulton enrichment): a null category counts differently depending on WHY it's null.
  - A null from **input-packet incompleteness** (a recoverable research gap — the fact likely
    exists somewhere, just isn't archived here) keeps a deal at `LOW` regardless of how few
    categories are affected, until the packet is actually enriched with real sourced facts.
  - A null from a **structurally irreducible unknown** (the fact was genuinely unknowable even
    to the ORIGINAL screen at freeze time — e.g. E Fulton's Tenancy & Lease, where ORA's own
    contemporaneous DD status says "rent roll unreconciled") does NOT by itself force `LOW`. A
    deal with only this class of null and every other category resolved from real facts can reach
    `MEDIUM` (not `HIGH` — `HIGH` is reserved for zero nulls of either kind). Backfilling an
    irreducible unknown with later-dated data to force a null closed would violate the
    frozen-snapshot discipline and must never be done to raise a tier.
  - `LOW` and any deal with an internal-consistency gap (see `known_gaps` — e.g. an archived
    Quality+Economics sum not matching the archived Combined) are excluded from strict pass/fail
    scoring — they run and report, but a delta there is INFORMATIONAL, not a flagged regression.
  This mirrors ORA's verified-null-vs-inferred-null convention: a gap in the archive is a
  known-not-recorded fact, not grounds to silently treat the row as high-fidelity — and a
  genuinely-unknowable-at-the-time fact is a different kind of gap than an under-researched one.
- `known_gaps` — array of strings, e.g. missing NOI, price-used-for-scoring differing from
  asking price, or (found in this build — see README "Data-quality finding") an archived
  Quality+Economics sum that does not equal the archived Combined score.
- `inputs` — the frozen facts a SCREEN replay should be given. Never live-refetched.
- `golden` — the recorded verdict to diff against:
  - `quality`, `economics`, `combined`, `expected_score`, `p_exec_pct` — as archived (not
    recomputed/corrected, even where `known_gaps` notes an arithmetic inconsistency).
  - `verdict_tier` — **as of the 2026-08-14 re-baseline, this is the tier produced by the
    fresh replay that also produced `combined`/`quality`/`economics`** (see `baselined_date`,
    `baselined_against_skill_sha`) — NOT a Notion-archived tier. `diff_verdict.py` reads this
    exact key; do not rename it again without updating `lib/diff_verdict.py` and
    `lib/test_diff_verdict.py`'s `make_golden()` fixture in the same change (a 2026-08-14
    rename from `archived_verdict_tier` briefly desynced the two and was caught by the
    mutated-input self-test, not by the unit suite — see harness README).
  - `floor_result`, `category_breakdown` (null where the replay could not derive a component
    from the frozen `inputs`).
  - `archived_pre_v03_reference` (sibling of `golden`, not a field within it) — the ORIGINAL
    Notion-archived score from before the 2026-07-14 RCT v03 recalibration, kept for historical
    context only. Its own tier field is named `archived_verdict_tier` and is never read by
    `diff_verdict.py`.
- `diff_policy` — `primary_signal` (always `combined_score` — see README rationale),
  `tolerance_combined_pts`, and `tier_check` (`informational_only` for every deal in this pilot,
  for the same reason).
