# Standing Review Lenses

**Created:** 2026-08-13 (net-new item #5 from the 2026-08-13 CC usage-insights report evaluation). **Tier:** documentation-only — a prompt fragment to hand to a dispatched reviewer, never auto-loaded into context.

This file holds standing lenses to include when dispatching an independent reviewer or REFUTE agent (via `eos-review-gate.py`'s blocking dispatch, `pr-review-toolkit` agents, or `evidence-dossier-drafting`'s adversarial refuter). It is additive to whatever lens those flows already apply — CLAIM-AUDITOR-style claim re-derivation and TEST-SKEPTIC-style false-PASS hunting are already covered elsewhere (see [[feedback_refute_pass_proactive_default]], [[reference_refute_differential_harness]]). This file exists because neither of those covers *missed call sites*.

## BLAST-RADIUS lens

Grep every symbol, path, config key, and doc reference the diff touches, and report call sites the diff missed.

Concretely, for each renamed/removed/added symbol, config key, or path in the diff:
1. `grep -rn` the old name/value across the whole repo (not just the files in the diff) — a rename in one place that leaves three call sites on the old name is a finding, not a false positive.
2. Check doc references (`docs/`, memory files, `SKILL.md` frontmatter) separately from code — a stale doc pointer doesn't break tests but does mislead the next reader.
3. Report every hit that the diff did not update, with file:line. A hit that is deliberately left on the old value (e.g. a documented backward-compat shim) must be named as such, not silently excluded.

Use this lens whenever a diff renames, removes, or relocates something with more than one plausible caller — not on every diff. Pure additions (new file, new function with no prior callers) don't need it.

Related: [[feedback_auto_review_blast_radius_gate]] (the "blast-radius" term here is the review-scope-trigger list; this lens is a different thing — a grep technique applied *within* a review that's already been triggered) · [[feedback_sweep_then_verify]] (the same grep-inventory-then-verify discipline applied to authoring an edit, rather than reviewing one).
