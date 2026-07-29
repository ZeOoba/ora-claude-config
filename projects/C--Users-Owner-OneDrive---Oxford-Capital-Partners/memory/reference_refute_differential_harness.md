---
name: refute-differential-harness
description: "Proven REFUTE-pass shape for guard/probe regex edits — recover the OLD version via git show, load both via importlib, run adversarial inputs DIFFERENTIALLY, judge old→new deltas not absolute outputs"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 46a85dfc-a400-4abf-91ca-96d829f85eca
  modified: 2026-07-29T18:56:04.969Z
---

**Pattern (proven 2026-07-29, governor-drift-probe decimal-fragment fix — Phase-2 T1):** when a detection guard/probe's matching logic changes, the adversarial REFUTE pass is strongest run *differentially*:

1. Recover the pre-change version even uncommitted: `git show HEAD:maintenance/<probe>.py > scratchpad/probe_old.py`.
2. Load BOTH via `importlib.util.spec_from_file_location` (the probes' own test files already use this loader shape).
3. Run a battery of adversarial lines through both `scan_*()` functions and tabulate **old → new** per line.
4. Judge DELTAS, not absolutes: a line that "flagged before, silent now" is only a real regression if the old flag was *correct* — in the live case, most old "detections" were the garbage-fragment bug itself firing accidentally (wrong value), which a naive absolute comparison would have defended as lost coverage.
5. Classify residuals into: adopt (hardening), reject (FN-biased), document (loud-not-silent accepted). The refuter's rejection of a plausible exemption widening ('review' token) was worth more than its confirmations.

**Why:** absolute-output review of a regex change systematically overrates the old behavior; the differential table makes "what did this change actually break" a mechanical question with executed evidence.
**How to apply:** for any edit to governor-drift-probe, confidentiality-guard patterns, secret_patterns.py, or similar matchers — pin the refuter ≥ implementer tier (financial/security floor: Fable), require executed code output for every claimed refutation, and file residuals in the commit message. Harness example preserved in the 2026-07-29 Phase-2 REFUTE run (journal Milestone-2, T1 row). Related: [[feedback_refute_pass_proactive_default]].
