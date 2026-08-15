---
name: feedback_sweep_then_verify
description: "A first-pass grep/edit sweep across a repo routinely misses instances a later QC pass catches -- ask for the exhaustive inventory before editing, then re-grep after to prove zero remain."
metadata:
  node_type: memory
  type: feedback
  originSessionId: 15f5b972-9fcc-4292-90d9-bee7020ac2bf
  modified: 2026-08-13T00:00:00.000Z
---

**Pattern (surfaced 2026-08-13, CC usage-insights report cross-checked against real session history).** Across the oxfordra.net SEO audit and the skill-split work, the first editing pass repeatedly missed instances a follow-up QC pass caught: the markets hub, `meta.md`, and portfolio badges were all fixed only after a second sweep, stretching one fix across five PRs; a skill split separately shipped a placeholder instead of real content until a later pass caught it.

**Why this class of miss is cheap to prevent and expensive to leave.** A sweep that edits-as-it-finds treats each grep hit as complete once handled, so it has no way to notice a hit its own pattern didn't cover (a different file extension, a differently-worded occurrence, a path the first grep excluded). The fix isn't a smarter single pass — it's separating "find everything" from "fix everything" into two steps with a machine-checkable boundary between them, which is exactly what [[feedback_absence_claims_need_verification_before_building]] and the Done bar's evidence-before-claim rule already require for absence claims and completion claims respectively. This is the same discipline applied to multi-instance edits specifically.

**How to apply.** Before editing any pattern that could recur more than once across a repo (a rename, a stale reference, a doc inconsistency, a fix that should apply everywhere the bug pattern appears):
1. Grep for the pattern across ALL relevant file types first — not just the type of the file that surfaced the issue — and produce a numbered file:line inventory before touching anything.
2. Edit every item on that inventory.
3. Re-run the identical grep and confirm zero remain (or that every remaining hit is a deliberately-excluded false positive, named as such).
4. If the inventory step is skipped because the task felt too small for it, that is itself the signal it was multi-instance — [[feedback_findings_decay_recheck_before_writing]] describes the adjacent failure of not re-checking before writing; this is the same shape applied to sweep completeness rather than staleness.

Related: [[feedback_absence_claims_need_verification_before_building]] · [[reference_engineering_os_done_bar]] (evidence-before-claim) · [[project_oxfordra_seo_audit_2026-07.md]] (the concrete miss this pattern generalizes from).
